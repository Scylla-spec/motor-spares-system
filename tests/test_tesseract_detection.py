import platform
from unittest.mock import patch, MagicMock
import pytest
from utils.image_importer import _build_tesseract_install_guide, is_tesseract_available


def test_install_guide_windows():
    with patch("platform.system", return_value="Windows"):
        guide = _build_tesseract_install_guide()
        assert "winget install UB-Mannheim.TesseractOCR" in guide


def test_install_guide_macos():
    with patch("platform.system", return_value="Darwin"):
        guide = _build_tesseract_install_guide()
        assert "brew install tesseract" in guide


def test_install_guide_linux():
    with patch("platform.system", return_value="Linux"):
        guide = _build_tesseract_install_guide()
        assert "apt install tesseract-ocr" in guide


def test_is_tesseract_available_callable():
    res = is_tesseract_available()
    assert isinstance(res, bool)
