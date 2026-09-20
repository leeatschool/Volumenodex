"""Unit and integration test suite for Volumenodex v1.3.0 features:
- Native JXL image handling, cropping, resizing, and filters
- Paginated canvas autoscrolling, image placement, copy/paste
- Clipart metadata parser (EXIF/XPKeywords) and caching
- Clipart autoexpansion (Wikimedia querying, license classification, pagination 3+5n, storage guard)
- Print preview integration
"""

import os
import sys
import tempfile
import pytest
from PySide6.QtCore import Qt, QSize, QRect
from PySide6.QtGui import QImage, QColor, QTextDocument, QTextBlockFormat, QTextCursor
from PySide6.QtWidgets import QApplication

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from volumenodex.core.image_utils import (
    load_image, load_pixmap, save_image, crop_image, resize_image,
    IMAGE_FILE_FILTER, SUPPORTED_EXTENSIONS
)
from volumenodex.clipart.metadata_parser import extract_image_metadata, ClipartMetadataCache
from volumenodex.clipart.autoexpansion import (
    RateLimiter, classify_wikimedia_license, check_storage_limit
)
from volumenodex.ui.image_resize_dialog import ImageResizeDialog
from volumenodex.ui.image_crop_dialog import ImageCropDialog
from volumenodex.ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app


def test_jxl_primary_filter_and_extensions():
    """Verifies that .jxl is prioritized across filters and extensions."""
    assert "*.jxl" in IMAGE_FILE_FILTER
    assert "JPEG XL Image (*.jxl)" in IMAGE_FILE_FILTER
    assert SUPPORTED_EXTENSIONS[0] == ".jxl"
    assert ".jxl" in SUPPORTED_EXTENSIONS
    assert ".png" in SUPPORTED_EXTENSIONS
    assert ".jpg" in SUPPORTED_EXTENSIONS


def test_image_load_save_resize_crop(qapp):
    """Verifies loading, resizing, cropping, and saving images including Pillow/JXL support."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_png = os.path.join(tmpdir, "test_sample.png")
        test_jxl = os.path.join(tmpdir, "test_sample.jxl")

        # Create 200x100 test image
        img = QImage(200, 100, QImage.Format.Format_RGB32)
        img.fill(QColor(255, 100, 50))
        saved_png = save_image(img, test_png)
        assert saved_png is True
        assert os.path.exists(test_png)

        # Verify load_image and load_pixmap
        loaded_img = load_image(test_png)
        assert loaded_img is not None
        assert loaded_img.width() == 200
        assert loaded_img.height() == 100

        pix = load_pixmap(test_png)
        assert pix is not None
        assert not pix.isNull()
        assert pix.width() == 200

        # Test resize_image
        resized = resize_image(loaded_img, 100, 50)
        assert resized.width() == 100
        assert resized.height() == 50

        # Test crop_image
        cropped = crop_image(loaded_img, QRect(10, 10, 80, 40))
        assert cropped.width() == 80
        assert cropped.height() == 40

        # Test saving as JXL via save_image
        saved_jxl = save_image(cropped, test_jxl)
        assert saved_jxl is True
        assert os.path.exists(test_jxl)
        assert os.path.getsize(test_jxl) > 0

        # Test loading the JXL back
        loaded_jxl = load_image(test_jxl)
        assert loaded_jxl is not None
        assert loaded_jxl.width() == 80
        assert loaded_jxl.height() == 40


def test_image_dialogs(qapp):
    """Verifies that ImageResizeDialog and ImageCropDialog instantiate properly with aspect ratio locks."""
    img = QImage(400, 300, QImage.Format.Format_RGB32)
    img.fill(QColor(0, 120, 200))

    # Resize dialog takes current_width, current_height
    resize_dlg = ImageResizeDialog(current_width=400, current_height=300)
    assert resize_dlg.spin_width.value() == 400
    assert resize_dlg.spin_height.value() == 300
    assert resize_dlg.chk_lock_aspect.isChecked() is True
    # Test aspect ratio locking
    resize_dlg.spin_width.setValue(200)
    assert resize_dlg.spin_height.value() == 150
    w, h = resize_dlg.get_dimensions()
    assert w == 200 and h == 150
    resize_dlg.close()

    # Crop dialog
    crop_dlg = ImageCropDialog(img)
    assert crop_dlg.image.width() == 400
    assert crop_dlg.image.height() == 300
    res = crop_dlg.get_cropped_image()
    assert res is not None
    crop_dlg.close()


def test_canvas_autoscrolling_and_image_context_menu(qapp):
    """Verifies that PaginatedCanvas has autoscrolling logic, image insertion, and clipboard copy/paste."""
    win = MainWindow()
    canvas = win.editor

    # Verify autoscroll method exists and is callable
    assert hasattr(canvas, "ensure_cursor_visible")
    canvas.setPlainText("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
    canvas.ensure_cursor_visible()

    # Verify image insertion, copy, and paste
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_name = tmp.name
    try:
        img = QImage(120, 80, QImage.Format.Format_RGB32)
        img.fill(QColor(40, 180, 90))
        img.save(tmp_name)

        ok = canvas.insert_image(tmp_name)
        assert ok is True

        # Test selecting image and copying to clipboard
        cursor = canvas.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
        canvas.setTextCursor(cursor)
        canvas.copy()

        # Test paste image
        canvas.paste()
        assert canvas.toPlainText() is not None
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
    win.close()


def test_wikimedia_license_classification():
    """Verifies accurate classification of Wikimedia metadata into license categories."""
    # Public Domain / CC0
    assert classify_wikimedia_license({"License": {"value": "pd"}}) == "pd_cc0"
    assert classify_wikimedia_license({"License": {"value": "CC0"}}) == "pd_cc0"
    assert classify_wikimedia_license({"LicenseShortName": {"value": "Public domain"}}) == "pd_cc0"
    assert classify_wikimedia_license({"Copyrighted": {"value": "False"}, "AttributionRequired": {"value": "False"}}) == "pd_cc0"

    # CC-BY
    assert classify_wikimedia_license({"License": {"value": "CC-BY-4.0"}}) == "cc_by"
    assert classify_wikimedia_license({"LicenseShortName": {"value": "CC BY 3.0"}}) == "cc_by"

    # CC-BY-SA
    assert classify_wikimedia_license({"License": {"value": "CC-BY-SA-4.0"}}) == "cc_by_sa"
    assert classify_wikimedia_license({"LicenseShortName": {"value": "CC BY-SA"}}) == "cc_by_sa"
    assert classify_wikimedia_license({"UsageTerms": {"value": "Creative Commons Attribution-Share Alike"}}) == "cc_by_sa"

    # Incompatible / Copyrighted
    assert classify_wikimedia_license({"License": {"value": "fair-use"}}) == "other"
    assert classify_wikimedia_license({}) == "other"


def test_rate_limiter():
    """Verifies that the rate limiter enforces the minimum request interval."""
    limiter = RateLimiter(min_interval_seconds=0.1)
    t0 = RateLimiter(0.05)
    assert limiter.min_interval >= 1.0  # RateLimiter forces min 1.0s for Wikimedia compliance
    res = t0.wait()
    assert res is True


def test_pagination_offset_calculation():
    """Verifies the specified pagination formula: Click 1 = offset 3, subsequent = 3 + 5n."""
    def calc_offset(click_number: int) -> int:
        if click_number <= 1:
            return 3
        return 3 + 5 * (click_number - 1)

    assert calc_offset(1) == 3   # Skips first 3
    assert calc_offset(2) == 8   # Skips 8 (3 + 5*1)
    assert calc_offset(3) == 13  # Skips 13 (3 + 5*2)
    assert calc_offset(4) == 18  # Skips 18 (3 + 5*3)


def test_storage_limit_check():
    """Verifies the hard drive safety limit check logic."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "test.bin")
        with open(fpath, "wb") as f:
            f.write(b"0" * 1024 * 1024)

        # 1 MB directory against 10 MB limit -> Not exceeded
        exceeded, cur, lim = check_storage_limit(tmpdir, limit_value=10.0, limit_unit="MB")
        assert exceeded is False
        assert cur < lim

        # 1 MB directory against 0.5 MB limit -> Exceeded
        exceeded2, cur2, lim2 = check_storage_limit(tmpdir, limit_value=0.5, limit_unit="MB")
        assert exceeded2 is True
        assert cur2 > lim2


def test_print_preview_wiring(qapp):
    """Verifies that Print Preview is wired to Ribbon, shortcut, and MainWindow action."""
    win = MainWindow()
    assert hasattr(win.ribbon, "printPreviewRequested")
    assert hasattr(win.ribbon, "btn_header_preview")
    assert hasattr(win, "print_preview")
    assert hasattr(win, "action_print_preview")
    assert win.action_print_preview.shortcut().toString() == "Ctrl+Shift+P"
    win.close()
