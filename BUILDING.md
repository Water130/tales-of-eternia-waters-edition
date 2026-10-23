# Building and testing

[Overview](README.md) · [Documentation](docs/README.md)

These steps are for developers. To play, follow the [installation guide](docs/INSTALLATION.md).

## Requirements

- Windows and Python 3.10 or later.
- Dependencies from requirements-dev.txt; use a virtual environment.
- Your own clean GameNative.dll from Steam build 25190541.
- At least 5 GiB free after staging and installation.

Put your local original DLL at:

```text
backups/build-25190541/GameNative.dll
```

Expected SHA-256:

```text
6488be2ce5ecc1dc9fc0216aa2462ec9aeba7a464468d5fd61ad3c2a8356849b
```

The backups and build directories are ignored by Git. Never commit the original DLL,
generated game binaries, saves, extracted game assets or private machine reports.

## Build the current default patch

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe tools/build_combat_patch.py
.\.venv\Scripts\python.exe tools/test_combat_patch.py
```

The builder creates build/combat-test/GameNative.dll and local reports. It never installs
the result or starts the game. Offline tests execute injected x64 code in Unicorn with
controlled game structures. Real gameplay/rendering testing is still needed.

Expected 0.13.8 Full-mode SHA-256:

```text
9eafc9a25863d3daf74322e9bf7d49ff032d68aa34be10be78990fe544bba128
```

## Package and check the English installer

```powershell
.\.venv\Scripts\python.exe tools/build_share_package.py
.\.venv\Scripts\python.exe tools/test_share_package.py
.\.venv\Scripts\python.exe tools/build_share_package.py --zip
```

The package tests use disposable game-file copies. Installation and uninstalling are
tested without modifying the installed game. The packaging step requires verification
of the exact staged files and includes only an explicit file list.

The patch is version-locked. Do not adapt it to an unknown game build by removing the
hash check: native addresses, instructions and data layouts require a fresh audit.
