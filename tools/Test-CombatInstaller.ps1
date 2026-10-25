# Exercise the real installer with tiny fixtures, never the game directory.
$ErrorActionPreference='Stop'
$env:TOE_GAME_DIR=$null
$root=Split-Path $PSScriptRoot
$fixture=Join-Path $root 'work/installer-01412-fixture'
if (Test-Path -LiteralPath $fixture) { throw 'Test fixture already exists.' }
function Hash([byte[]]$bytes) { ([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes))).ToLowerInvariant() }
function Json($value,$path) { $value | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $path -Encoding utf8 }
function Same($path,$hash) { if ((Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant() -ne $hash) { throw "Incorrect content: $path" } }
$old=[Text.Encoding]::UTF8.GetBytes('test original DLL');$new=[Text.Encoding]::UTF8.GetBytes('test new DLL')
$oldFont=[Text.Encoding]::UTF8.GetBytes('test original font');$newFont=[Text.Encoding]::UTF8.GetBytes('test new font')
$game=Join-Path $fixture 'game';$stage=Join-Path $fixture 'build/combat-test'
$dll=Join-Path $game 'Tales of Eternia Remastered_Data/Plugins/x86_64/GameNative.dll'
$font=Join-Path $game 'Tales of Eternia Remastered_Data/StreamingAssets/font.bundle'
$installer=Join-Path $fixture 'Install-CombatTest.ps1'
$source=Get-Content -LiteralPath (Join-Path $root 'Install-CombatTest.ps1') -Raw
$source=$source.Replace('$gameRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot ''local/game''))',('$gameRoot = '''+$game+''''))
$source=$source.Replace('6488be2ce5ecc1dc9fc0216aa2462ec9aeba7a464468d5fd61ad3c2a8356849b',(Hash $old))
$checks=[Collections.Generic.List[string]]::new()
try {
    foreach ($dir in @((Split-Path $dll),(Split-Path $font),(Join-Path $stage 'hp-tp-font'))) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [IO.File]::WriteAllBytes($dll,$old);[IO.File]::WriteAllBytes($font,$oldFont)
    [IO.File]::WriteAllBytes((Join-Path $stage 'GameNative.dll'),$new)
    [IO.File]::WriteAllBytes((Join-Path $stage 'hp-tp-font/font.bundle'),$newFont)
    Json @{version='fixture';features=@();patched_sha256=(Hash $new)} (Join-Path $stage 'manifest.json')
    Json @{passed=$true;patched_sha256=(Hash $new);note='Synthetic installer fixture, not a game verification'} (Join-Path $stage 'verification.json')
    Json @{passed=$true;outside_pixels_unchanged=$true;damage_digits_unchanged=$true;target_relative='Tales of Eternia Remastered_Data/StreamingAssets/font.bundle';file='font.bundle';original_sha256=(Hash $oldFont);patched_sha256=(Hash $newFont)} (Join-Path $stage 'hp-tp-font/verification.json')
    $source | Set-Content -LiteralPath $installer -Encoding utf8
    $pwsh=(Get-Process -Id $PID).Path
    function Run($action,[bool]$success=$true) {
        $output = & $pwsh -NoProfile -File $installer -Action $action 2>&1
        if (($LASTEXITCODE -eq 0) -ne $success) { throw ($output | Out-String) }
    }
    Run Install;Same $dll (Hash $new);Same $font (Hash $newFont);$checks.Add('install DLL and HP/TP asset')
    Run Install;Same $dll (Hash $new);Same $font (Hash $newFont);$checks.Add('idempotent install')
    Run Restore;Same $dll (Hash $old);Same $font (Hash $oldFont);$checks.Add('restore both owned originals')
    [IO.File]::WriteAllText($font,'foreign modification')
    Run Install $false;Same $dll (Hash $old);$checks.Add('unknown asset rejected before any DLL mutation')
    [IO.File]::WriteAllBytes($font,$oldFont)
    $injected=$source.Replace('$applied.Add($change)','$applied.Add($change); if ($applied.Count -eq 1) { throw ''Injected I/O failure'' }')
    $injected | Set-Content -LiteralPath $installer -Encoding utf8
    Run Install $false;Same $dll (Hash $old);Same $font (Hash $oldFont);$checks.Add('failure after first replacement rolls back transaction')
    foreach ($folder in @('combat-test','combat-release')) {
        $report=Join-Path $root ('build/'+$folder)
        New-Item -ItemType Directory -Path $report -Force | Out-Null
        Json @{passed=$true;checks=@($checks);real_game_modified=$false} (Join-Path $report 'installer-verification.json')
    }
    $checks
} finally {
    $resolved=[IO.Path]::GetFullPath($fixture)
    $expected=[IO.Path]::GetFullPath((Join-Path $root 'work/installer-01412-fixture'))
    if ($resolved -ne $expected -or -not $resolved.StartsWith([IO.Path]::GetFullPath((Join-Path $root 'work'))+[IO.Path]::DirectorySeparatorChar)) { throw 'Unsafe fixture cleanup path.' }
    if (Test-Path -LiteralPath $resolved) { Remove-Item -LiteralPath $resolved -Recurse -Force }
}
