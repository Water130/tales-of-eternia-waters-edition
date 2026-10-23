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
$groups = 'core', 'mastery', 'mastery-menu', 'energy', 'fringe', 'craymel-exp', 'teamup', 'faculties'
foreach ($group in $groups) {
    .\.venv\Scripts\python.exe tools/test_combat_patch.py "--$group-only"
    if ($LASTEXITCODE -ne 0) { throw "Failed verification: $group" }
}
.\.venv\Scripts\python.exe tools/aggregate_combat_verification.py
```

The builder creates build/combat-test/GameNative.dll and local reports. It never installs
the result or starts the game. Offline tests execute injected x64 code in Unicorn with
controlled game structures. Each group runs in a fresh process to bound emulator
memory usage. The aggregator refuses stale reports or reports for another DLL.
Real gameplay/rendering testing is still needed.

Expected 0.14.11 Full-mode SHA-256:

```text
fcdf90c08660c1664ca0d7305f7a50fc1d073b723b879e12f0f083acc46c939b
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
