[CmdletBinding()]
param(
    [ValidateSet('Install','Restore','Status','NoSpellOverlap')]
    [string]$Action = 'Status',
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$gameRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'local/game'))
if ($env:TOE_GAME_DIR) { $gameRoot = [IO.Path]::GetFullPath($env:TOE_GAME_DIR) }
$targetPath = Join-Path $gameRoot 'Tales of Eternia Remastered_Data\Plugins\x86_64\GameNative.dll'
$packageRoot = Join-Path $projectRoot 'build\combat-test'
$backupRoot = Join-Path $projectRoot 'backups\build-25190541'
$backupPath = Join-Path $backupRoot 'GameNative.dll'
$installedPath = Join-Path $packageRoot 'installed.json'
$originalHash = '6488be2ce5ecc1dc9fc0216aa2462ec9aeba7a464468d5fd61ad3c2a8356849b'

function Get-BytesHash([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Assert-GameStopped {
    $running = @(Get-Process -Name 'Tales of Eternia Remastered' -ErrorAction SilentlyContinue)
    if ($running.Count -gt 0) { throw 'Close Tales of Eternia Remastered before modifying its files.' }
}

$manifest = Get-Content -LiteralPath (Join-Path $packageRoot 'manifest.json') -Raw | ConvertFrom-Json
$currentHash = (Get-FileHash -LiteralPath $targetPath -Algorithm SHA256).Hash.ToLowerInvariant()
$installed = if (Test-Path -LiteralPath $installedPath) { Get-Content -LiteralPath $installedPath -Raw | ConvertFrom-Json } else { $null }
if ($Action -eq 'Status') {
    [pscustomobject]@{ Action='Status'; CurrentSHA256=$currentHash; Original=($currentHash -eq $originalHash); InstalledRecord=$installed } | ConvertTo-Json -Depth 5
    exit 0
}
Assert-GameStopped
if (($currentHash -ne $originalHash) -and ($currentHash -ne $manifest.patched_sha256) -and
    (($null -eq $installed) -or ($currentHash -ne $installed.sha256))) {
    throw 'Unknown or modified DLL. Refusing to overwrite it.'
}

if ($Action -eq 'Restore') {
    if (-not (Test-Path -LiteralPath $backupPath)) { throw 'Original backup missing.' }
    $payload = [IO.File]::ReadAllBytes($backupPath)
    if ((Get-BytesHash $payload) -ne $originalHash) { throw 'Backup hash mismatch.' }
    $features = @()
} else {
    $verified = Get-Content -LiteralPath (Join-Path $packageRoot 'verification.json') -Raw | ConvertFrom-Json
    $payload = [IO.File]::ReadAllBytes((Join-Path $packageRoot 'GameNative.dll'))
    if ((Get-BytesHash $payload) -ne $manifest.patched_sha256) { throw 'Package hash mismatch.' }
    if ((-not $verified.passed) -or ($verified.patched_sha256 -ne $manifest.patched_sha256)) { throw 'Native code verification missing or stale.' }
    $features = @($manifest.features)
    if ($Action -eq 'NoSpellOverlap') {
        $queueEdits = @($manifest.without_spell_overlap.reverted_edits)
        if ($queueEdits.Count -lt 3) { throw 'Compatibility profile incomplete.' }
        foreach ($editName in $queueEdits) {
            $edit = @($manifest.edits | Where-Object name -EQ $editName)
            if ($edit.Count -ne 1) { throw "Ambiguous concurrency patch : $editName" }
            $hex = $edit[0].original
            for ($i=0; $i -lt $hex.Length/2; $i++) {
                $payload[[int]$edit[0].offset+$i] = [Convert]::ToByte($hex.Substring($i*2,2),16)
            }
        }
        $checksumBytes = [BitConverter]::GetBytes([uint32]$manifest.without_spell_overlap.checksum)
        [Array]::Copy($checksumBytes,0,$payload,[int]$manifest.without_spell_overlap.checksum_offset,4)
        if ((Get-BytesHash $payload) -ne $manifest.without_spell_overlap.sha256) { throw 'Compatibility profile mismatch.' }
        $features = @($features | Where-Object { $_ -ne 'concurrent_spells' })
    }
}
$desiredHash = Get-BytesHash $payload
# The optional asset delivery is limited to the FR HP/TP numeral strip.
# Preflight every file before replacing any, and retain the owned original.
$changes = [Collections.Generic.List[object]]::new()
$changes.Add([pscustomobject]@{ Target=$targetPath; Payload=$payload; Previous=$currentHash; Desired=$desiredHash; Backup=$backupPath; Original=$originalHash })
$fontReportPath = Join-Path $packageRoot 'hp-tp-font/verification.json'
$font = $null
if (Test-Path -LiteralPath $fontReportPath) {
    $font = Get-Content -LiteralPath $fontReportPath -Raw | ConvertFrom-Json
    if (-not $font.passed -or -not $font.damage_digits_unchanged -or -not $font.outside_pixels_unchanged) { throw 'HP/TP verification failed.' }
    $fontTarget = [IO.Path]::GetFullPath((Join-Path $gameRoot $font.target_relative))
    if (-not $fontTarget.StartsWith($gameRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Bundle path outside game folder.' }
    if ([IO.Path]::GetFileName($fontTarget) -ne $font.file) { throw 'Bundle name mismatch.' }
    $fontBackup = Join-Path $backupRoot ('hp-tp-font/'+$font.file)
    $fontCurrent = (Get-FileHash -LiteralPath $fontTarget -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($fontCurrent -notin @($font.original_sha256,$font.patched_sha256)) { throw 'Unknown French bundle: no files will be replaced.' }
    if ($Action -eq 'Restore') {
        $fontSource = if ($fontCurrent -eq $font.original_sha256) { $fontTarget } else { $fontBackup }
        $fontDesired = $font.original_sha256
    } else {
        $fontSource = Join-Path $packageRoot ('hp-tp-font/'+$font.file)
        $fontDesired = $font.patched_sha256
    }
    $fontPayload = [IO.File]::ReadAllBytes($fontSource)
    if ((Get-BytesHash $fontPayload) -ne $fontDesired) { throw 'HP/TP bundle mismatch.' }
    $changes.Add([pscustomobject]@{ Target=$fontTarget; Payload=$fontPayload; Previous=$fontCurrent; Desired=$fontDesired; Backup=$fontBackup; Original=$font.original_sha256 })
}
# Workspace stage + one original rollback + one small target-side atomic stage.
foreach ($driveLetter in @(([IO.Path]::GetPathRoot($projectRoot)).Substring(0,1), 'E')) {
    $free = [IO.DriveInfo]::new("${driveLetter}:\").AvailableFreeSpace
    if ($free -lt (5GB + 3*$payload.Length)) { throw "Insufficient space on ${driveLetter}: to retain 5 GiB free." }
}
if ($DryRun) {
    [pscustomobject]@{ Action=$Action; DryRun=$true; CurrentSHA256=$currentHash; ProposedSHA256=$desiredHash; Features=$features; Files=@($changes | Select-Object Target,Previous,Desired) } | ConvertTo-Json -Depth 5
    exit 0
}
if ($Action -ne 'Restore') {
    if (-not (Test-Path -LiteralPath $backupPath)) {
        if ($currentHash -ne $originalHash) { throw 'Back up the original DLL before the first installation.' }
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        Copy-Item -LiteralPath $targetPath -Destination $backupPath
    }
    if ((Get-FileHash -LiteralPath $backupPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $originalHash) {
        throw 'Invalid original backup. Installation refused.'
    }
}
Assert-GameStopped
foreach ($change in $changes) {
    if ((Get-FileHash -LiteralPath $change.Target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $change.Previous) { throw 'A file changed during preparation.' }
    if (Test-Path -LiteralPath ($change.Target+'.combat-test-stage')) { throw 'Staged file already exists; manual inspection required.' }
    if (-not (Test-Path -LiteralPath $change.Backup)) {
        if ($change.Previous -ne $change.Original) { throw 'Original missing: installation refused.' }
        New-Item -ItemType Directory -Path (Split-Path $change.Backup) -Force | Out-Null
        Copy-Item -LiteralPath $change.Target -Destination $change.Backup
    }
    if ((Get-FileHash -LiteralPath $change.Backup -Algorithm SHA256).Hash.ToLowerInvariant() -ne $change.Original) { throw 'Invalid original backup.' }
    $change | Add-Member -NotePropertyName PreviousBytes -NotePropertyValue ([IO.File]::ReadAllBytes($change.Target))
}
$applied = [Collections.Generic.List[object]]::new()
try {
    foreach ($change in $changes) {
        if ($change.Previous -eq $change.Desired) { continue }
        $stagePath = $change.Target+'.combat-test-stage'
        [IO.File]::WriteAllBytes($stagePath,$change.Payload)
        if ((Get-FileHash -LiteralPath $stagePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $change.Desired) { throw 'Staged file mismatch.' }
        Assert-GameStopped
        [IO.File]::Replace($stagePath,$change.Target,[NullString]::Value)
        $applied.Add($change)
        if ((Get-FileHash -LiteralPath $change.Target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $change.Desired) { throw 'Post-installation verification failed.' }
    }
} catch {
    $failure = $_
    Assert-GameStopped
    for ($idx=$applied.Count-1; $idx -ge 0; $idx--) {
        $change=$applied[$idx]; $stagePath=$change.Target+'.combat-test-stage'
        [IO.File]::WriteAllBytes($stagePath,$change.PreviousBytes)
        [IO.File]::Replace($stagePath,$change.Target,[NullString]::Value)
        if ((Get-FileHash -LiteralPath $change.Target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $change.Previous) { throw 'Rollback failed: inspect the game files.' }
    }
    throw $failure
} finally {
    foreach ($change in $changes) {
        $stagePath=$change.Target+'.combat-test-stage'
        if (Test-Path -LiteralPath $stagePath) { Remove-Item -LiteralPath $stagePath }
    }
}
$record = [ordered]@{ action=$Action; version=$(if ($Action -eq 'Restore') { 'original' } else { $manifest.version });
    previous_sha256=$currentHash; sha256=$desiredHash; installed_at=(Get-Date).ToString('o');
    steam_build=25190541; features=$features; target=$targetPath; original_backup=$backupPath;
    assets=@($changes | Select-Object -Skip 1 | ForEach-Object { [ordered]@{ target=$_.Target; previous_sha256=$_.Previous; sha256=$_.Desired; original_backup=$_.Backup; original_sha256=$_.Original } });
    runtime_validated=$false }
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $installedPath -Encoding UTF8
$record | ConvertTo-Json -Depth 5
