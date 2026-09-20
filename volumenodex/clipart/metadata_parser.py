"""EXIF, IPTC, XMP, and Windows Explorer XPKeywords metadata extractor and caching engine for Clip Art."""

import os
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("volumenodex.clipart.metadata")

# Register pillow-jxl-plugin if available
try:
    import pillow_jxl  # noqa: F401
except ImportError:
    pass

try:
    import PIL.Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


def _clean_str(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, bytes):
        # Try UTF-16LE (Windows XP tags) first if there are null bytes, else UTF-8/latin-1
        if b"\x00" in val:
            try:
                return val.decode("utf-16le", errors="ignore").rstrip("\x00").strip()
            except Exception:
                pass
        for enc in ("utf-8", "latin-1", "ascii"):
            try:
                return val.decode(enc, errors="ignore").rstrip("\x00").strip()
            except Exception:
                pass
        return ""
    return str(val).strip()


def extract_image_metadata(file_path: str) -> Dict[str, str]:
    """Extracts rich metadata from an image file including EXIF, IPTC, XMP, and Windows XPKeywords."""
    meta: Dict[str, str] = {
        "title": "",
        "description": "",
        "artist": "",
        "copyright": "",
        "keywords": "",
        "comments": "",
    }

    if not _HAS_PIL or not file_path or not os.path.exists(file_path):
        return meta

    try:
        with PIL.Image.open(file_path) as img:
            # 1. EXIF Tags
            exif = img.getexif()
            if exif:
                # 270: ImageDescription
                if 270 in exif:
                    meta["description"] = _clean_str(exif[270])
                # 315: Artist / Author
                if 315 in exif:
                    meta["artist"] = _clean_str(exif[315])
                # 33432: Copyright
                if 33432 in exif:
                    meta["copyright"] = _clean_str(exif[33432])
                # 37510: UserComment
                if 37510 in exif:
                    meta["comments"] = _clean_str(exif[37510])
                # Windows XP Tags:
                # 40091: XPTitle
                if 40091 in exif and not meta["title"]:
                    meta["title"] = _clean_str(exif[40091])
                # 40092: XPComment
                if 40092 in exif:
                    xp_c = _clean_str(exif[40092])
                    meta["comments"] = f"{meta['comments']} {xp_c}".strip()
                # 40093: XPAuthor
                if 40093 in exif and not meta["artist"]:
                    meta["artist"] = _clean_str(exif[40093])
                # 40094: XPKeywords (Windows Explorer Tags/Keywords)
                if 40094 in exif:
                    meta["keywords"] = _clean_str(exif[40094])

            # 2. Text / Info dictionary (PNG, WebP, JXL, etc.)
            info = getattr(img, "info", {})
            if isinstance(info, dict):
                if not meta["description"] and "description" in info:
                    meta["description"] = _clean_str(info["description"])
                if not meta["artist"] and "author" in info:
                    meta["artist"] = _clean_str(info["author"])
                if not meta["copyright"] and "copyright" in info:
                    meta["copyright"] = _clean_str(info["copyright"])
                if not meta["comments"] and "comment" in info:
                    meta["comments"] = _clean_str(info["comment"])

    except Exception as e:
        logger.debug("Failed reading metadata for %s: %s", file_path, e)

    return meta


class ClipartMetadataCache:
    """Persistent disk cache for clipart metadata ensuring instantaneous library search."""

    def __init__(self, cache_file_path: Optional[str] = None):
        if cache_file_path:
            self.cache_file = cache_file_path
        else:
            cache_dir = os.path.expanduser("~/.volumenodex")
            os.makedirs(cache_dir, exist_ok=True)
            self.cache_file = os.path.join(cache_dir, "clipart_metadata_cache.json")

        self._cache: Dict[str, Dict[str, Any]] = {}
        self._dirty = False
        self.load()

    def load(self) -> None:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                self._dirty = False
            except Exception as e:
                logger.warning("Could not read clipart metadata cache: %s", e)
                self._cache = {}

    def save(self) -> None:
        if not self._dirty:
            return
        try:
            temp_path = self.cache_file + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
            if os.path.exists(self.cache_file):
                os.replace(temp_path, self.cache_file)
            else:
                os.rename(temp_path, self.cache_file)
            self._dirty = False
        except Exception as e:
            logger.warning("Could not write clipart metadata cache: %s", e)

    def get_metadata(self, full_path: str) -> Dict[str, str]:
        """Returns metadata for full_path, using cache if mtime matches, else extracts and caches."""
        try:
            mtime = os.path.getmtime(full_path)
        except OSError:
            return {}

        abs_path = os.path.abspath(full_path)
        cached_entry = self._cache.get(abs_path)
        if cached_entry and cached_entry.get("mtime") == mtime:
            return cached_entry.get("meta", {})

        # Extract and update
        meta = extract_image_metadata(full_path)
        self._cache[abs_path] = {
            "mtime": mtime,
            "meta": meta
        }
        self._dirty = True
        return meta
