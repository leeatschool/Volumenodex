"""Image processing utilities for Volumenodex Word Processing Studio.

Provides first-class native support for JPEG XL (.jxl) as the primary and preferred
image format, alongside PNG, JPEG, WebP, GIF, and BMP. Handles robust loading,
conversion, cropping, and resizing with PySide6 and Pillow integration.
"""

import os
import io
from typing import Optional, Union, Tuple
from PySide6.QtCore import QRect, QRectF, QSize, Qt, QBuffer, QIODevice
from PySide6.QtGui import QImage, QPixmap

# Register pillow-jxl-plugin if available
try:
    import pillow_jxl  # noqa: F401
except ImportError:
    pass

try:
    import PIL.Image
    from PIL import ImageQt
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


# Preferred file filters across all studio dialogs (JXL prioritized)
IMAGE_FILE_FILTER = (
    "Supported Images (*.jxl *.png *.jpg *.jpeg *.webp *.bmp *.gif);;"
    "JPEG XL Image (*.jxl);;"
    "PNG Image (*.png);;"
    "JPEG Image (*.jpg *.jpeg);;"
    "WebP Image (*.webp);;"
    "All Files (*.*)"
)

SUPPORTED_EXTENSIONS = (
    ".jxl",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".gif",
)

PRIMARY_IMAGE_EXTENSION = ".jxl"


def is_jxl_file(file_path: str) -> bool:
    """Returns True if the file path has a .jxl extension."""
    return os.path.splitext(file_path)[1].lower() == ".jxl"


def load_image(file_path: str) -> Optional[QImage]:
    """Loads an image from disk into a QImage.
    
    Seamlessly handles .jxl files via pillow-jxl-plugin and standard formats via Qt.
    """
    if not file_path or not os.path.exists(file_path):
        return None

    ext = os.path.splitext(file_path)[1].lower()

    # If JXL or when Qt fails, use Pillow
    if ext == ".jxl" or _HAS_PIL:
        if ext == ".jxl":
            try:
                pil_img = PIL.Image.open(file_path)
                if pil_img.mode not in ("RGB", "RGBA"):
                    pil_img = pil_img.convert("RGBA")
                # Convert via ImageQt
                qimg = ImageQt.ImageQt(pil_img)
                # Clone to own QImage buffer
                return QImage(qimg)
            except Exception as e:
                pass

    # Standard Qt loader fallback
    img = QImage(file_path)
    if not img.isNull():
        return img

    # Fallback to Pillow for other formats if Qt had an issue
    if _HAS_PIL:
        try:
            pil_img = PIL.Image.open(file_path)
            if pil_img.mode not in ("RGB", "RGBA"):
                pil_img = pil_img.convert("RGBA")
            qimg = ImageQt.ImageQt(pil_img)
            return QImage(qimg)
        except Exception:
            pass

    return None


def load_pixmap(file_path: str) -> Optional[QPixmap]:
    """Loads an image from disk into a QPixmap with full .jxl support."""
    qimg = load_image(file_path)
    if qimg is not None and not qimg.isNull():
        return QPixmap.fromImage(qimg)
    return None


def save_image(
    image: Union[QImage, QPixmap],
    target_path: str,
    format_str: Optional[str] = None,
    quality: int = 92
) -> bool:
    """Saves a QImage or QPixmap to disk, supporting .jxl, .png, .jpg, etc."""
    if isinstance(image, QPixmap):
        image = image.toImage()

    if image.isNull():
        return False

    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    ext = os.path.splitext(target_path)[1].lower()
    fmt = format_str.upper() if format_str else (ext[1:].upper() if ext else "JXL")

    if ext == ".jxl" or fmt == "JXL":
        if _HAS_PIL:
            try:
                # Convert QImage to PIL Image via QBuffer
                qbuf = QBuffer()
                qbuf.open(QIODevice.OpenModeFlag.WriteOnly)
                if image.save(qbuf, "PNG"):
                    pil_img = PIL.Image.open(io.BytesIO(qbuf.data().data()))
                    pil_img.save(target_path, format="JXL")
                    return True
            except Exception:
                pass

    return image.save(target_path)


def crop_image(
    image_or_path: Union[QImage, QPixmap, str],
    crop_rect: Union[QRect, QRectF, Tuple[int, int, int, int]]
) -> Optional[QImage]:
    """Crops an image to the given rectangle coordinates (x, y, w, h)."""
    if isinstance(image_or_path, str):
        img = load_image(image_or_path)
    elif isinstance(image_or_path, QPixmap):
        img = image_or_path.toImage()
    elif isinstance(image_or_path, QImage):
        img = image_or_path
    else:
        return None

    if img is None or img.isNull():
        return None

    if isinstance(crop_rect, tuple):
        x, y, w, h = crop_rect
        qrect = QRect(int(x), int(y), int(w), int(h))
    elif isinstance(crop_rect, QRectF):
        qrect = crop_rect.toRect()
    else:
        qrect = crop_rect

    # Clamp to image bounds
    bounded_rect = qrect.intersected(QRect(0, 0, img.width(), img.height()))
    if bounded_rect.isEmpty() or bounded_rect.width() <= 0 or bounded_rect.height() <= 0:
        return None

    return img.copy(bounded_rect)


def resize_image(
    image_or_path: Union[QImage, QPixmap, str],
    width: int,
    height: int,
    keep_aspect: bool = True
) -> Optional[QImage]:
    """Resizes an image using smooth transformation."""
    if isinstance(image_or_path, str):
        img = load_image(image_or_path)
    elif isinstance(image_or_path, QPixmap):
        img = image_or_path.toImage()
    elif isinstance(image_or_path, QImage):
        img = image_or_path
    else:
        return None

    if img is None or img.isNull() or width <= 0 or height <= 0:
        return None

    aspect_mode = (
        Qt.AspectRatioMode.KeepAspectRatio
        if keep_aspect
        else Qt.AspectRatioMode.IgnoreAspectRatio
    )
    return img.scaled(
        width,
        height,
        aspect_mode,
        Qt.TransformationMode.SmoothTransformation
    )
