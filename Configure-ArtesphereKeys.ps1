[CmdletBinding()]
param(
    [string]$PageKey,
    [Alias('ShortcutKey')]
    [string]$PageCKey,
    [switch]$Show,
    [string]$ConfigPath = (Join-Path $env:LOCALAPPDATA 'TalesOfEternia-WatersEdition.ini')
)
$ErrorActionPreference = 'Stop'
if (-not ('WatersEdition.ArtesphereKeys' -as [type])) {
    Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
namespace WatersEdition {
    public static class ArtesphereKeys {
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode)]
        public static extern uint GetPrivateProfileIntW(string section, string key, int fallback, string path);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        public static extern bool WritePrivateProfileStringW(string section, string key, string value, string path);
    }
}
'@
}
function ConvertTo-KeyCode([string]$Name) {
    $key = $Name.Trim().ToUpperInvariant()
    if ($key -match '^[A-Z0-9]$') { return [int][char]$key }
    if ($key -match '^F([1-9]|1[0-9]|2[0-4])$') { return 111 + [int]$Matches[1] }
    $named = @{
        SHIFT=16; CTRL=17; ALT=18; SPACE=32; TAB=9; ENTER=13; ESC=27;
        HOME=36; END=35; INSERT=45; DELETE=46; PAGEUP=33; PAGEDOWN=34;
        LSHIFT=160; RSHIFT=161; LCTRL=162; RCTRL=163; LALT=164; RALT=165
    }
    if ($named.ContainsKey($key)) { return $named[$key] }
    throw "Unsupported key '$Name'. Use A-Z, 0-9, F1-F24, SHIFT, CTRL, ALT, SPACE, TAB, HOME, END, INSERT, DELETE, PAGEUP or PAGEDOWN."
}
$resolvedPath = [IO.Path]::GetFullPath($ConfigPath)
if ($Show) {
    [pscustomobject]@{
        Config = $resolvedPath
        PageBKeyCode = [WatersEdition.ArtesphereKeys]::GetPrivateProfileIntW('ArtesphereControls','PageKey',118,$resolvedPath)
        PageCKeyCode = [WatersEdition.ArtesphereKeys]::GetPrivateProfileIntW('ArtesphereControls','PageCKey',
            [WatersEdition.ArtesphereKeys]::GetPrivateProfileIntW('ArtesphereControls','ShortcutKey',119,$resolvedPath),$resolvedPath)
    }
    return
}
if (Get-Process -Name 'Tales of Eternia Remastered' -ErrorAction SilentlyContinue) {
    throw 'Close Tales of Eternia Remastered before changing these bindings, then start it again.'
}
Write-Host "Water's Edition - Artesphere keyboard controls"
Write-Host 'These two keys supplement the existing controls configured inside the game.'
Write-Host 'Choose keys that are not already assigned to another action.'
if (-not $PageKey) {
    $PageKey = Read-Host 'Page B key (Enter uses the default F7)'
    if (-not $PageKey) { $PageKey = 'F7' }
}
if (-not $PageCKey) {
    $PageCKey = Read-Host 'Page C key (Enter uses the default F8)'
    if (-not $PageCKey) { $PageCKey = 'F8' }
}
$pageCode = ConvertTo-KeyCode $PageKey
$pageCCode = ConvertTo-KeyCode $PageCKey
if ($pageCode -eq $pageCCode) { throw 'The two bindings must use different keys.' }
if (-not (Test-Path -LiteralPath ([IO.Path]::GetDirectoryName($resolvedPath)) -PathType Container)) {
    throw 'The configuration folder does not exist.'
}
foreach ($entry in @(@('PageKey',$pageCode),@('PageCKey',$pageCCode))) {
    if (-not [WatersEdition.ArtesphereKeys]::WritePrivateProfileStringW('ArtesphereControls',$entry[0],[string]$entry[1],$resolvedPath)) {
        throw 'Could not save the keyboard bindings. Check that the configuration file is writable.'
    }
}
Write-Host "Saved: Page B = $PageKey; Page C = $PageCKey"
Write-Host 'In the arte menu, tap the B key to switch B/A, or the C key to switch C/A.'
Write-Host 'In battle, hold the B or C key for that page; release both to return to A.'
Write-Host 'Page C takes priority if both keys are held. Page keys alone do not cast.'
Write-Host "Configuration: $resolvedPath"
