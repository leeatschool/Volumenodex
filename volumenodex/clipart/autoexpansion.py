"""Clipart Library Autoexpansion Engine for Volumenodex.

Integrates Wikimedia Commons search and download infrastructure directly into the
studio. Automatically queries and downloads high-quality Public Domain / CC-licensed
illustrations when local search results are sparse, with rate-limiting, license filtering,
pagination offset logic, and hard-drive storage safeguards.
"""

import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal, QThread

try:
    import pillow_jxl  # noqa: F401
except ImportError:
    pass

from volumenodex.core.image_utils import load_image, save_image

logger = logging.getLogger("volumenodex.clipart.autoexpansion")

DEFAULT_USER_AGENT = (
    "Volumenodex/2.2.0 "
    "(https://github.com/leeatschool/Volumenodex; contact: studio@volumenodex.local) "
    "Python-urllib"
)

BITMAP_MIMES = {
    "image/jpeg",
    "image/pjpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/tiff",
    "image/bmp",
}


class RateLimiter:
    """Thread-safe rate limiter guaranteeing a minimum delay (1.0s) between Wikimedia requests."""

    def __init__(self, min_interval_seconds: float = 1.0):
        self.min_interval = max(1.0, float(min_interval_seconds))
        self.last_request_time = 0.0
        self._lock = threading.Lock()

    def wait(self, cancel_event: Optional[threading.Event] = None) -> bool:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_request_time
            remaining = self.min_interval - elapsed
            if remaining > 0:
                end_time = now + remaining
                while time.time() < end_time:
                    if cancel_event and cancel_event.is_set():
                        return False
                    time.sleep(min(0.05, max(0.0, end_time - time.time())))
            self.last_request_time = time.time()
            return True


_global_rate_limiter = RateLimiter(1.0)


def classify_wikimedia_license(extmetadata: Dict[str, Any]) -> str:
    """Classifies Wikimedia metadata into 'pd_cc0', 'cc_by', 'cc_by_sa', or 'other'."""
    if not extmetadata:
        return "other"

    lic = (extmetadata.get("License", {}).get("value") or "").lower().strip()
    short = (extmetadata.get("LicenseShortName", {}).get("value") or "").lower().strip()
    terms = (extmetadata.get("UsageTerms", {}).get("value") or "").lower().strip()
    cpr = (extmetadata.get("Copyrighted", {}).get("value") or "").lower().strip()
    attr = (extmetadata.get("AttributionRequired", {}).get("value") or "").lower().strip()
    cats = (extmetadata.get("Categories", {}).get("value") or "").lower().strip()

    pd_prefixes = ("pd", "pd-", "cc0", "cc-zero", "pdm", "unrestricted", "public domain")
    if any(lic == p or lic.startswith(p) for p in pd_prefixes):
        return "pd_cc0"
    if any(term in short for term in ("public domain", "cc0", "cc-zero", "no copyright")) or short == "pd":
        return "pd_cc0"
    if any(term in terms for term in ("public domain", "cc0", "no copyright")):
        return "pd_cc0"
    if cpr == "false" and attr == "false":
        return "pd_cc0"
    if any(k in cats for k in ("public domain", "pd-us", "pd-art", "pd-old", "cc-zero", "cc0")):
        return "pd_cc0"

    if "cc-by-sa" in lic or "cc by-sa" in short or "share alike" in terms or "cc-by-sa" in cats:
        return "cc_by_sa"
    if "cc-by" in lic or "cc by" in short or "cc-by" in cats:
        return "cc_by"

    return "other"


def get_directory_size_bytes(dir_path: str) -> int:
    """Calculates the total disk space consumed by files in dir_path."""
    if not os.path.exists(dir_path):
        return 0
    total = 0
    try:
        for root, _, files in os.walk(dir_path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    except OSError:
        pass
    return total


def check_storage_limit(dir_path: str, limit_value: float, limit_unit: str) -> Tuple[bool, float, float]:
    """Returns (is_exceeded, current_gb, limit_gb)."""
    unit_multipliers = {
        "KB": 1024,
        "MB": 1024 * 1024,
        "GB": 1024 * 1024 * 1024,
        "TB": 1024 * 1024 * 1024 * 1024,
    }
    multiplier = unit_multipliers.get(limit_unit.upper(), 1024 * 1024 * 1024)
    limit_bytes = float(limit_value) * multiplier

    cur_bytes = get_directory_size_bytes(dir_path)
    cur_gb = cur_bytes / (1024 * 1024 * 1024)
    limit_gb = limit_bytes / (1024 * 1024 * 1024)

    return (cur_bytes >= limit_bytes, cur_gb, limit_gb)


class AutoexpansionWorker(QObject):
    """Background worker that queries Wikimedia Commons and saves images directly into the library."""

    imageDownloaded = Signal(str, dict)  # (file_path, metadata_dict)
    downloadFinished = Signal(int, int)  # (downloaded_count, next_offset)
    storageLimitExceeded = Signal(float, float)  # (current_gb, limit_gb)
    statusMessage = Signal(str)

    def __init__(
        self,
        query: str,
        destination_dir: str,
        offset: int = 0,
        max_images: int = 5,
        target_size_mode: str = "500px",  # "500px", "1000px", "full"
        allow_pd_cc0: bool = True,
        allow_cc_by: bool = False,
        allow_cc_by_sa: bool = False,
        limit_val: float = 2.0,
        limit_unit: str = "GB",
        seen_titles: Optional[set] = None,
        parent=None
    ):
        super().__init__(parent)
        self.query = query.strip()
        self.destination_dir = os.path.abspath(destination_dir)
        self.offset = max(0, int(offset))
        self.max_images = max(1, min(20, int(max_images)))
        self.target_size_mode = target_size_mode
        self.allow_pd_cc0 = allow_pd_cc0
        self.allow_cc_by = allow_cc_by
        self.allow_cc_by_sa = allow_cc_by_sa
        self.limit_val = limit_val
        self.limit_unit = limit_unit
        self.seen_titles: set = set(t.lower() for t in seen_titles) if seen_titles else set()
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self) -> None:
        """Executes the autoexpansion query."""
        if not self.query:
            self.downloadFinished.emit(0, self.offset)
            return

        # 1. Storage limit check
        exceeded, cur_gb, limit_gb = check_storage_limit(
            self.destination_dir, self.limit_val, self.limit_unit
        )
        if exceeded:
            self.storageLimitExceeded.emit(cur_gb, limit_gb)
            self.downloadFinished.emit(0, self.offset)
            return

        os.makedirs(self.destination_dir, exist_ok=True)
        self.statusMessage.emit(f"Searching Wikimedia Commons for '{self.query}'...")

        # 2. Determine target width
        target_width: Optional[int] = 500
        if self.target_size_mode == "1000px":
            target_width = 1000
        elif self.target_size_mode == "full":
            target_width = None

        downloaded_count = 0
        current_offset = self.offset
        next_offset = self.offset

        try:
            # Build API query params
            endpoint = "https://commons.wikimedia.org/w/api.php"
            params: Dict[str, Any] = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": self.query,
                "gsrnamespace": 6,  # File namespace
                "gsrlimit": min(50, max(30, self.max_images * 5)),
                "gsroffset": current_offset,
                "prop": "imageinfo",
                "iiprop": "url|size|mime|extmetadata",
            }
            if target_width:
                params["iiurlwidth"] = target_width

            url = f"{endpoint}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})

            _global_rate_limiter.wait(self._cancel_event)
            if self._cancel_event.is_set():
                self.downloadFinished.emit(0, current_offset)
                return

            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            pages = data.get("query", {}).get("pages", {})
            candidates = sorted(pages.values(), key=lambda p: p.get("index", 999999))

            # Determine next offset from Wikimedia's continue token
            continue_data = data.get("continue", {})
            if "gsroffset" in continue_data:
                try:
                    next_offset = int(continue_data["gsroffset"])
                except (ValueError, TypeError):
                    next_offset = current_offset + len(candidates)
            else:
                next_offset = current_offset + len(candidates)

            for page in candidates:
                if self._cancel_event.is_set() or downloaded_count >= self.max_images:
                    break

                # Re-check storage limit
                exceeded, cur_gb, limit_gb = check_storage_limit(
                    self.destination_dir, self.limit_val, self.limit_unit
                )
                if exceeded:
                    self.storageLimitExceeded.emit(cur_gb, limit_gb)
                    break

                img_info_list = page.get("imageinfo", [])
                if not img_info_list:
                    continue
                info = img_info_list[0]
                mime = (info.get("mime") or "").lower()

                if mime not in BITMAP_MIMES:
                    continue

                ext = info.get("extmetadata", {})
                lic_cat = classify_wikimedia_license(ext)

                # License filter
                allowed = False
                if lic_cat == "pd_cc0" and self.allow_pd_cc0:
                    allowed = True
                elif lic_cat == "cc_by" and self.allow_cc_by:
                    allowed = True
                elif lic_cat == "cc_by_sa" and self.allow_cc_by_sa:
                    allowed = True

                if not allowed:
                    continue

                # Download URL
                dl_url = info.get("thumburl") if (target_width and info.get("thumburl")) else info.get("url")
                if not dl_url:
                    continue

                # Clean Title
                raw_title = page.get("title", "")
                clean_title = re.sub(r"^File:", "", raw_title, flags=re.IGNORECASE)
                clean_title = os.path.splitext(clean_title)[0]
                safe_name = re.sub(r'[\\/:*?"<>|]', "_", clean_title).strip()
                if not safe_name:
                    safe_name = f"{self.query}_{current_offset + downloaded_count + 1}"

                # ZERO REPEAT DEDUPLICATION:
                # 1. Skip if title or safe_name was already seen in library or downloaded this session
                norm_titles = {
                    safe_name.lower(),
                    clean_title.lower(),
                    safe_name.lower().replace(" ", "_"),
                    safe_name.lower().replace("_", " "),
                    clean_title.lower().replace(" ", "_"),
                    clean_title.lower().replace("_", " "),
                }
                if any(t in self.seen_titles for t in norm_titles):
                    continue

                # 2. Skip if file already exists in library destination folder (.jxl or other format)
                possible_stems = {safe_name, safe_name.replace(" ", "_"), safe_name.replace("_", " ")}
                already_exists = False
                for stem in possible_stems:
                    for chk_ext in (".jxl", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".bmp", ".gif"):
                        if os.path.exists(os.path.join(self.destination_dir, f"{stem}{chk_ext}")):
                            already_exists = True
                            break
                    if already_exists:
                        break

                if already_exists:
                    self.seen_titles.update(norm_titles)
                    continue

                target_path = os.path.join(self.destination_dir, f"{safe_name}.jxl")

                # Mark as seen immediately to avoid race conditions
                self.seen_titles.update(norm_titles)

                # Rate limit before image download
                _global_rate_limiter.wait(self._cancel_event)
                if self._cancel_event.is_set():
                    break

                # Download bytes
                dl_req = urllib.request.Request(dl_url, headers={"User-Agent": DEFAULT_USER_AGENT})
                with urllib.request.urlopen(dl_req, timeout=15) as dl_resp:
                    img_bytes = dl_resp.read()

                # Load into QImage and save as JXL
                from PySide6.QtGui import QImage
                qimg = QImage.fromData(img_bytes)
                if qimg.isNull():
                    continue

                saved = save_image(qimg, target_path)
                if not saved or not os.path.exists(target_path):
                    alt_path = os.path.join(self.destination_dir, f"{safe_name}.png")
                    if qimg.save(alt_path, "PNG"):
                        target_path = alt_path
                    else:
                        continue

                # Extract metadata details
                artist_raw = ext.get("Artist", {}).get("value", "")
                artist = re.sub(r"<[^<]+?>", "", artist_raw).strip()
                desc_raw = ext.get("ImageDescription", {}).get("value", "")
                description = re.sub(r"<[^<]+?>", "", desc_raw).strip()
                lic_name = ext.get("LicenseShortName", {}).get("value", lic_cat.upper())

                meta = {
                    "title": clean_title,
                    "artist": artist,
                    "description": description,
                    "license": lic_name,
                    "license_category": lic_cat,
                    "attribution": f"Photo: {artist or 'Unknown'} / Wikimedia Commons ({lic_name})" if lic_cat != "pd_cc0" else "",
                }

                downloaded_count += 1
                self.imageDownloaded.emit(target_path, meta)

        except Exception as e:
            logger.warning("Error during autoexpansion query for '%s': %s", self.query, e)

        self.downloadFinished.emit(downloaded_count, next_offset)
