[CmdletBinding()]
param(
    [ValidateSet('Install','Uninstall','Status')][string]$Action = 'Status',
    [ValidateSet('Full','Compatibility')][string]$Mode = 'Full',
    [string]$GameDir,
    [switch]$DryRun,
    [switch]$Prompt
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2

function Get-Hash([byte[]]$Bytes) {
    $hasher = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hasher.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() }
    finally { $hasher.Dispose() }
}
function Assert-GameClosed {
    if (@(Get-Process -Name 'Tales of Eternia Remastered' -ErrorAction SilentlyContinue).Count) {
        throw 'Close Tales of Eternia Remastered completely before installing or uninstalling.'
    }
}
function Find-GameFolder {
    $libraries = @()
    $steam = Get-ItemProperty -LiteralPath 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue
    if ($steam -and $steam.PSObject.Properties['SteamPath']) { $libraries += [string]$steam.SteamPath }
    foreach ($key in @('HKLM:\SOFTWARE\WOW6432Node\Valve\Steam','HKLM:\SOFTWARE\Valve\Steam')) {
        $machineSteam = Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue
        if ($machineSteam -and $machineSteam.PSObject.Properties['InstallPath']) { $libraries += [string]$machineSteam.InstallPath }
    }
    if (${env:ProgramFiles(x86)}) { $libraries += (Join-Path ${env:ProgramFiles(x86)} 'Steam') }
    foreach ($library in @($libraries)) {
        $vdf = Join-Path $library 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $vdf) {
            foreach ($match in [regex]::Matches([IO.File]::ReadAllText($vdf), '"path"\s+"([^"]+)"')) {
                $libraries += $match.Groups[1].Value.Replace('\\','\')
            }
        }
    }
    $found = @($libraries | Select-Object -Unique | ForEach-Object {
        $candidate = Join-Path $_ 'steamapps\common\Tales of Eternia Remastered'
        if (Test-Path -LiteralPath (Join-Path $candidate 'Tales of Eternia Remastered_Data\Plugins\x86_64\GameNative.dll')) { $candidate }
    })
    if ($found.Count -eq 1) { return $found[0] }
    Write-Host 'In Steam: right-click the game > Manage > Browse local files.'
    $answer = [string](Read-Host 'Paste the full game folder path here')
    if ([string]::IsNullOrWhiteSpace($answer)) { throw 'No game folder selected. Run Install.cmd or Uninstall.cmd again and select the full game folder path.' }
    return $answer.Trim().Trim('"')
}
function Get-PatchedBytes([byte[]]$Original, $Profile) {
    if (($Profile.result_size -lt $Original.Length) -or ($Profile.result_size -gt 16777216)) {
        throw 'Invalid patch output size. Extract a fresh copy of the release.'
    }
    $result = New-Object byte[] ([int]$Profile.result_size)
    [Array]::Copy($Original, $result, $Original.Length)
    $previousEnd = 0
    foreach ($run in $Profile.runs) {
        $offset = [long]$run[0]
        $bytes = [Convert]::FromBase64String([string]$run[1])
        if (($offset -lt $previousEnd) -or ($offset -gt $result.Length - $bytes.Length)) {
            throw 'Invalid patch range. Extract a fresh copy of the release.'
        }
        [Array]::Copy($bytes,0,$result,[int]$offset,$bytes.Length)
        $previousEnd = $offset + $bytes.Length
    }
    if ((Get-Hash $result) -ne $Profile.sha256) { throw 'Patch reconstruction failed its SHA-256 check. No game files changed.' }
    return ,$result
}

try {
    $patch = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'patch.json') -Raw | ConvertFrom-Json
    if ($patch.format -ne 1) { throw 'Unsupported patch format.' }
    if (-not $GameDir) { $GameDir = Find-GameFolder }
    $GameDir = [IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($GameDir.Trim().Trim('"')))
    $target = Join-Path $GameDir 'Tales of Eternia Remastered_Data\Plugins\x86_64\GameNative.dll'
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw 'GameNative.dll was not found. Select the game installation folder, not its Data or Plugins subfolder.' }
    $backup = $target + '.toe-combat-original'
    $stage = $target + '.toe-combat-stage'
    $current = [IO.File]::ReadAllBytes($target)
    $currentHash = Get-Hash $current
    $supportedHashes = @($patch.base_sha256, $patch.profiles.Full.sha256, $patch.profiles.Compatibility.sha256)
    $state = if ($currentHash -eq $patch.base_sha256) { 'Original' } elseif ($currentHash -eq $patch.profiles.Full.sha256) { 'Full' } elseif ($currentHash -eq $patch.profiles.Compatibility.sha256) { 'Compatibility' } else { 'Unsupported / modified' }
    Write-Host ("Tales of Eternia - Water's Edition {0} - TEST RELEASE" -f $patch.version) -ForegroundColor Cyan
    Write-Host ("Game folder: {0}" -f $GameDir)
    Write-Host ("Current state: {0}" -f $state)
    if ($Action -eq 'Status') { exit 0 }
    Assert-GameClosed
    if ($currentHash -notin $supportedHashes) {
        throw ("Unsupported or modified DLL. This release only supports the original Steam build {0} or this exact mod version. No files changed. Restore a clean compatible game before installing; do not force the patch after a Steam update." -f $patch.steam_build)
    }
    $backupBytes = $null
    if (Test-Path -LiteralPath $backup) {
        $backupBytes = [IO.File]::ReadAllBytes($backup)
        if ((Get-Hash $backupBytes) -ne $patch.base_sha256) { throw 'The existing original backup has an unexpected hash. It will not be overwritten.' }
    }
    if (($state -ne 'Original') -and ($null -eq $backupBytes)) {
        throw 'Original backup missing. Restore the original DLL using your previous installer or Steam before using this package.'
    }
    if ($Action -eq 'Uninstall') {
        if ($state -eq 'Original') { Write-Host 'The original game is already restored.'; exit 0 }
        $payload = $backupBytes
        $expectedHash = $patch.base_sha256
    } else {
        $source = $current
        if ($state -ne 'Original') { $source = $backupBytes }
        $profile = $patch.profiles.$Mode
        $payload = Get-PatchedBytes $source $profile
        $expectedHash = $profile.sha256
        if ($currentHash -eq $expectedHash) { Write-Host 'This mode is already installed.'; exit 0 }
    }
    $drive = New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($target))
    if ($drive.AvailableFreeSpace -lt (5GB + 2*$payload.Length)) { throw 'Not enough free space to keep at least 5 GiB free after installation.' }
    if (Test-Path -LiteralPath $stage) { throw 'A staging file from another operation exists. No files changed. Check GameNative.dll.toe-combat-stage before trying again.' }
    if ($DryRun) { Write-Host ("Dry run passed: {0} / {1}. No files changed." -f $Action,$Mode); exit 0 }
    if ($Prompt) {
        Write-Host ''
        if ($Action -eq 'Uninstall') {
            Write-Host 'This will restore the original game. Your saves and mod preferences will be kept.'
            $question = "Uninstall Water's Edition from this folder? [Y/N]"
        } else {
            Write-Host 'This will install the mod and keep a verified original backup. Your saves will not be changed.'
            $question = "Install Water's Edition in this folder? [Y/N]"
        }
        $answer = ([string](Read-Host $question)).Trim()
        if ($answer -notin @('y','yes')) { Write-Host 'Cancelled. No files changed.'; exit 0 }
    }
    Assert-GameClosed
    if ((Get-Hash ([IO.File]::ReadAllBytes($target))) -ne $currentHash) { throw 'Game file changed during preparation. Try again after Steam finishes.' }
    if (($Action -eq 'Install') -and ($null -eq $backupBytes)) {
        # CreateNew refuses a concurrent overwrite. One original backup only.
        $stream = [IO.File]::Open($backup,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try { $stream.Write($current,0,$current.Length); $stream.Flush() } finally { $stream.Dispose() }
        if ((Get-Hash ([IO.File]::ReadAllBytes($backup))) -ne $patch.base_sha256) { throw 'Original backup verification failed. Game DLL not changed.' }
    }
    $stageOwned = $false
    try {
        $stream = [IO.File]::Open($stage,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $stageOwned = $true
        try { $stream.Write($payload,0,$payload.Length); $stream.Flush() } finally { $stream.Dispose() }
        if ((Get-Hash ([IO.File]::ReadAllBytes($stage))) -ne $expectedHash) { throw 'Staging verification failed.' }
        Assert-GameClosed
        if ((Get-Hash ([IO.File]::ReadAllBytes($target))) -ne $currentHash) { throw 'Game file changed during staging. Nothing replaced.' }
        [IO.File]::Replace($stage,$target,[NullString]::Value)
        if ((Get-Hash ([IO.File]::ReadAllBytes($target))) -ne $expectedHash) { throw 'Post-install verification failed. Keep the original backup for recovery.' }
    } finally {
        if ($stageOwned -and (Test-Path -LiteralPath $stage)) { Remove-Item -LiteralPath $stage }
    }
    if ($Action -eq 'Uninstall') { Write-Host 'Original game restored and verified. The original backup has been kept.' }
    else { Write-Host ("Installed and verified: {0} mode. You can start the game." -f $Mode) }
    exit 0
} catch {
    Write-Host ("ERROR: {0}" -f $_.Exception.Message) -ForegroundColor Red
    exit 1
}
