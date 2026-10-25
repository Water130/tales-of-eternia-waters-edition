# Building and testing

[Overview](README.md) · [Installation](docs/INSTALLATION.md)

Requires Windows, PowerShell 7 for developer fixtures, Python 3.10+, and your own
Steam build 25190541 installation. Keep at least 5 GiB free after staging.
Set `TOE_NATIVE_ORIGINAL` to a clean GameNative.dll kept outside this checkout.
Required original SHA-256:
`6488be2ce5ecc1dc9fc0216aa2462ec9aeba7a464468d5fd61ad3c2a8356849b`.
Set `TOE_FONT_ORIGINAL` to your clean French font bundle, also outside the checkout:
`group_residenttexture_texture_assets_0x08010036_2f5ba85385ed9112aa6b5e3b7e26860e.bundle`.
Its SHA-256 must be `dc71f69e962189e9e7c83fca06c9466f63f50b2a69159b54b7eb8f6d3a68f0d7`.
Build, package and fixture tools read these originals without modifying them.
Other owned font bundles and DATA.zarc are read through `TOE_GAME_DIR`.
Never commit game binaries, extracted assets, backups or saves.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:TOE_GAME_DIR = 'C:\Path\To\Tales of Eternia Remastered'
$env:TOE_EDITION = 'R' # T enables the personal prototype roster
.\.venv\Scripts\python.exe tools/build_combat_patch.py
.\.venv\Scripts\python.exe tools/build_hp_tp_font.py
$groups = 'core','mastery','mastery-menu','energy','fringe','craymel-exp','teamup','faculties','farah-artes','expansion','custom-artes','camera-floor','camera','casting'
foreach ($group in $groups) {
    .\.venv\Scripts\python.exe tools/test_combat_patch.py "--$group-only"
    if ($LASTEXITCODE -ne 0) { throw "Failed verification: $group" }
}
foreach ($script in 'test_mastery_badges','test_tidal_presentation','test_tidal_recoil','verify_native_detour_branches') {
    .\.venv\Scripts\python.exe "tools/$script.py"
    if ($LASTEXITCODE -ne 0) { throw "Failed verification: $script" }
}
pwsh -NoProfile -File tools/Test-CombatInstaller.ps1
.\.venv\Scripts\python.exe tools/aggregate_combat_verification.py
```

R writes `build/combat-release`; T writes `build/combat-test`. Building never
installs or launches the game. Tests execute injected x64 code at two ASLR bases
in isolated Unicorn processes. Rendering and whole-game behavior still need
manual testing. The aggregator rejects stale or mismatched binary reports.

## Package the public release

```powershell
.\.venv\Scripts\python.exe tools/build_share_package.py
.\.venv\Scripts\python.exe tools/test_share_package.py
.\.venv\Scripts\python.exe tools/build_share_package.py --zip
```

Packaging uses the verified R build only. Disposable fixtures exercise the real
Windows PowerShell 5.1 installer: both files, repeated installation, restoration,
unknown file rejection and rollback after injected replacement failures.
The ZIP contains binary differences and an English installer, not full game files.

Expected 0.14.30R Full DLL SHA-256:
`36607195ea9a6dee698c8c1c578cfc12b1c019f123b1d7e1f21fff1204e062a9`.
Do not remove hash guards to support another game build; audit native layouts first.
