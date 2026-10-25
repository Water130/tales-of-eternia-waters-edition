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

function Write-NewFile([string]$Path, [byte[]]$Bytes) {
    $stream = [IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $stream.Write($Bytes,0,$Bytes.Length); $stream.Flush() } finally { $stream.Dispose() }
}

try {
    $patch = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'patch.json') -Raw | ConvertFrom-Json
    if ($patch.format -ne 2) { throw 'Unsupported patch format.' }
    if (-not $GameDir) { $GameDir = Find-GameFolder }
    $GameDir = [IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($GameDir.Trim().Trim('"')))
    $dllPath = 'Tales of Eternia Remastered_Data/Plugins/x86_64/GameNative.dll'
    $assets = @([pscustomobject]@{path=$dllPath; base_sha256=$patch.base_sha256; profiles=$patch.profiles}) + @($patch.assets)
    $plan = @(); $paths = @{}
    Write-Host ("Tales of Eternia - Water's Edition {0}" -f $patch.version) -ForegroundColor Cyan
    Write-Host ("Game folder: {0}" -f $GameDir)
    if ($Action -ne 'Status') { Assert-GameClosed }
    foreach ($asset in $assets) {
        $target = [IO.Path]::GetFullPath((Join-Path $GameDir $asset.path))
        if (-not $target.StartsWith($GameDir.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase) -or $paths.ContainsKey($target)) { throw 'Invalid or duplicate patch target.' }
        $paths[$target] = $true
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw ("Required game file was not found: {0}. Select the game installation folder." -f $asset.path) }
        $current = [IO.File]::ReadAllBytes($target); $currentHash = Get-Hash $current
        $state = if ($currentHash -eq $asset.base_sha256) { 'Original' } elseif ($currentHash -eq $asset.profiles.Full.sha256) { 'Full' } elseif ($currentHash -eq $asset.profiles.Compatibility.sha256) { 'Compatibility' } else { 'Unsupported / modified' }
        Write-Host ("{0}: {1}" -f [IO.Path]::GetFileName($target),$state)
        if ($Action -eq 'Status') { continue }
        if ($state -eq 'Unsupported / modified') { throw 'Unsupported or modified DLL / asset. Restore a clean compatible game before installing. No files changed.' }
        $backup = $target+'.toe-combat-original'; $stage = $target+'.toe-combat-stage'
        $original = $current; $hasBackup = Test-Path -LiteralPath $backup
        if ($hasBackup) {
            $original = [IO.File]::ReadAllBytes($backup)
            if ((Get-Hash $original) -ne $asset.base_sha256) { throw 'The existing original backup has an unexpected hash. It will not be overwritten.' }
        } elseif ($state -ne 'Original') { throw 'Original backup missing. Restore the original game using the previous installer or Steam.' }
        if (Test-Path -LiteralPath $stage) { throw 'A staging file from another operation exists. No files changed.' }
        if ($Action -eq 'Uninstall') { $payload = $original; $expectedHash = $asset.base_sha256 }
        else { $payload = Get-PatchedBytes $original $asset.profiles.$Mode; $expectedHash = $asset.profiles.$Mode.sha256 }
        if ($currentHash -ne $expectedHash) {
            $plan += [pscustomobject]@{Target=$target; Backup=$backup; Stage=$stage; Original=$original; Current=$current; CurrentHash=$currentHash; Payload=$payload; ExpectedHash=$expectedHash; HasBackup=$hasBackup; StageOwned=$false}
        }
    }
    if ($Action -eq 'Status') { exit 0 }
    if (-not $plan.Count) {
        if ($Action -eq 'Uninstall') { Write-Host 'The original game is already restored.' } else { Write-Host 'This mode is already installed.' }
        exit 0
    }
    $needed = 0L
    foreach ($item in $plan) { $needed += 2*$item.Payload.Length+$item.Original.Length }
    $drive = New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($GameDir))
    if ($drive.AvailableFreeSpace -lt (5GB+$needed)) { throw 'Not enough free space to keep at least 5 GiB free after installation.' }
    if ($DryRun) { Write-Host ("Dry run passed: {0} / {1}. No files changed." -f $Action,$Mode); exit 0 }
    if ($Prompt) {
        Write-Host 'Verified original backups will be kept. Back up your saves separately.'
        $question = if ($Action -eq 'Uninstall') { "Uninstall Water's Edition from this folder? [Y/N]" } else { "Install Water's Edition in this folder? [Y/N]" }
        if (([string](Read-Host $question)).Trim() -notin @('y','yes')) { Write-Host 'Cancelled. No files changed.'; exit 0 }
    }
    $applied = New-Object 'Collections.Generic.List[object]'
    try {
        Assert-GameClosed
        foreach ($item in $plan) {
            if ((Get-Hash ([IO.File]::ReadAllBytes($item.Target))) -ne $item.CurrentHash) { throw 'Game file changed during preparation.' }
            if (-not $item.HasBackup) {
                Write-NewFile $item.Backup $item.Original
                if ((Get-Hash ([IO.File]::ReadAllBytes($item.Backup))) -ne (Get-Hash $item.Original)) { throw 'Original backup verification failed.' }
            }
            Write-NewFile $item.Stage $item.Payload
            $item.StageOwned = $true
            if ((Get-Hash ([IO.File]::ReadAllBytes($item.Stage))) -ne $item.ExpectedHash) { throw 'Staging verification failed.' }
        }
        Assert-GameClosed
        foreach ($item in $plan) {
            if ((Get-Hash ([IO.File]::ReadAllBytes($item.Target))) -ne $item.CurrentHash) { throw 'Game file changed during staging.' }
            [IO.File]::Replace($item.Stage,$item.Target,[NullString]::Value)
            $applied.Add($item)
            if ((Get-Hash ([IO.File]::ReadAllBytes($item.Target))) -ne $item.ExpectedHash) { throw 'Post-install verification failed.' }
        }
    } catch {
        $failure = $_
        for ($i=$applied.Count-1; $i -ge 0; $i--) {
            $item = $applied[$i]
            Write-NewFile $item.Stage $item.Current
            [IO.File]::Replace($item.Stage,$item.Target,[NullString]::Value)
            if ((Get-Hash ([IO.File]::ReadAllBytes($item.Target))) -ne $item.CurrentHash) { throw 'Rollback verification failed. Keep all original backups for recovery.' }
        }
        throw $failure
    } finally {
        foreach ($item in $plan) {
            if ($item.StageOwned -and (Test-Path -LiteralPath $item.Stage)) { Remove-Item -LiteralPath $item.Stage }
        }
    }
    if ($Action -eq 'Uninstall') { Write-Host 'Original game restored and verified. The original backups have been kept.' }
    else { Write-Host ("Installed and verified: {0} mode. You can start the game." -f $Mode) }
    exit 0
} catch {
    Write-Host ("ERROR: {0}" -f $_.Exception.Message) -ForegroundColor Red
    exit 1
}
