from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from scripts.release_version import parse_product_version, write_pyinstaller_version_info


def test_release_version_is_embedded_in_pyinstaller_metadata() -> None:
    with tempfile.TemporaryDirectory() as temp:
        target = write_pyinstaller_version_info(
            Path(temp) / "version.txt", "2.0.0.0", "2.0.0-beta"
        )
        text = target.read_text(encoding="utf-8")
    assert "filevers=(2, 0, 0, 0)" in text
    assert "prodvers=(2, 0, 0, 0)" in text
    assert "StringStruct('FileVersion', '2.0.0.0')" in text
    assert "StringStruct('ProductVersion', '2.0.0-beta')" in text


@pytest.mark.parametrize("value", ["0.1.1", "0.1.beta.0", "01.1.1.0", "256.0.0.0"])
def test_invalid_release_version_is_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        parse_product_version(value)
