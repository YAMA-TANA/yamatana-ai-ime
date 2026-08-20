"""Read-only validation for the Yamatana distribution MSI and admin image."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import msilib


def query_one(database: msilib.Database, sql: str) -> tuple[str, ...]:
    view = database.OpenView(sql)
    view.Execute(None)
    record = view.Fetch()
    if record is None:
        raise AssertionError(f"MSI row not found: {sql}")
    return tuple(record.GetString(index) for index in range(1, record.GetFieldCount() + 1))


def validate(msi_path: Path, admin_root: Path) -> None:
    database = msilib.OpenDatabase(str(msi_path), msilib.MSIDBOPEN_READONLY)
    expected_properties = {
        "ProductName": "Yamatana AI IME (MOZC Ver)",
        "ProductVersion": os.environ.get("YAMATANA_PRODUCT_VERSION", "0.1.0.0"),
        "Manufacturer": "Yamatana",
        "UpgradeCode": "{A9FD6996-83DE-4DBE-9BE9-8C7F9016493A}",
    }
    for name, expected in expected_properties.items():
        actual = query_one(
            database,
            f"SELECT `Value` FROM `Property` WHERE `Property`='{name}'",
        )[0]
        if actual != expected:
            raise AssertionError(f"{name}: expected {expected!r}, got {actual!r}")

    startup = query_one(
        database,
        "SELECT `Value` FROM `Registry` WHERE `Registry`='RunYamatanaAIIME'",
    )[0]
    if "YamatanaAIIME.exe" not in startup:
        raise AssertionError(f"Unexpected startup command: {startup}")

    for action in ("RegisterTIP64", "UnregisterTIP64", "LaunchYamatanaTray"):
        query_one(
            database,
            f"SELECT `Type`, `Source`, `Target` FROM `CustomAction` WHERE `Action`='{action}'",
        )
        query_one(
            database,
            f"SELECT `Sequence` FROM `InstallExecuteSequence` WHERE `Action`='{action}'",
        )
    query_one(
        database,
        "SELECT `Name` FROM `Binary` WHERE `Name`='mozc_installer_helper.dll'",
    )
    query_one(
        database,
        "SELECT `Dialog` FROM `Dialog` WHERE `Dialog`='WelcomeEulaDlg'",
    )

    names = {
        path.name: path
        for path in admin_root.rglob("*")
        if path.is_file()
    }
    required = (
        "mozc_tip32.dll", "mozc_tip64.dll", "mozc_server.exe",
        "YamatanaAIIME.exe", "ruri-ime-fp16.onnx", "ruri-ime-int8.onnx",
        "PRIVACY.md", "LICENSE", "NOTICE", "THIRD_PARTY_LICENSES.md",
        "tokenizer.json",
    )
    missing = [name for name in required if name not in names]
    if missing:
        raise AssertionError(f"Admin image missing: {', '.join(missing)}")

    digest = hashlib.sha256(msi_path.read_bytes()).hexdigest().upper()
    file_count = sum(1 for path in admin_root.rglob("*") if path.is_file())
    print(f"VALIDATION_PASS files={file_count}")
    print(f"MSI_SHA256={digest}")
    print(f"MSI_BYTES={msi_path.stat().st_size}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("msi", type=Path)
    parser.add_argument("admin_root", type=Path)
    args = parser.parse_args()
    validate(args.msi.resolve(), args.admin_root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
