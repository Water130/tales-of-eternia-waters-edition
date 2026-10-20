TALES OF ETERNIA - WATER'S EDITION
0.12.5 - Experimental test release
Windows / Steam build 25190541 only

This is the current combat and interface prototype. It is intended for testing;
it is not a finished release or an official Bandai Namco product.

AUTHORSHIP / BUGS / USE AT YOUR OWN RISK
Water's Edition was created, designed and directed by Water, a human.
All of the mod's code was written by AI.

This mod has bugs. Unknown bugs and new regressions may appear in current and
future versions. Crashes, visual glitches and unintended gameplay behavior are
possible. Not all bugs will necessarily be fixed. Fixes, support and future
updates are not guaranteed.

Use this mod at your own risk. It is provided as-is, without warranty. To the
extent permitted by applicable law, the creator accepts no liability for
problems or losses resulting from its use, including damage to game files,
save corruption or lost progress. Back up your saves separately before installing.
The installer/uninstaller do not directly edit saves, but gameplay bugs may
still affect your progress.

INSTALL
1. Close the game completely. Extract this entire ZIP to a normal folder.
2. Double-click Install.cmd in the main folder. Keep all extracted files together.
3. The installer searches your Steam libraries. If it cannot choose one folder,
   paste the game folder path from Steam > Manage > Browse local files.
4. Check the displayed folder, type Y and press Enter to confirm.
5. Wait for "Installed and verified", then launch the game normally through Steam.

Windows PowerShell 5.1 is sufficient. No Python, mod loader or downloads are
required. The CMD launchers use a process-only execution policy; they do not
change your system's PowerShell policy. Review Patch-Mod.ps1 if you wish.
Normally no administrator access is needed. If the Steam folder denies writes,
the installer reports the error rather than requesting elevation automatically.

For a manual path from PowerShell:
  .\Support\Patch-Mod.ps1 -Action Install -Prompt -GameDir 'D:\SteamLibrary\steamapps\common\Tales of Eternia Remastered'

MODES / REMOVAL
- Install.cmd: all current features, including limited concurrent spell effects.
- Support/Compatibility-Mode.cmd: the same mod with the native spell queue restored.
  Use this to test whether an issue depends on overlapping spells. It does not
  remove the camera, HUD, TP changes or cinematic-freeze changes.
- Uninstall.cmd: type Y and press Enter to restore the verified original DLL.
- Support/Status.cmd: display the selected installation and current mode.

You can switch between these two modes with the game closed. The installer
keeps one original backup beside GameNative.dll, named
GameNative.dll.toe-combat-original. Keep it for uninstalling. The ZIP does not
contain an original game DLL. Uninstalling leaves this verified backup in place.
The installer never reads or edits your save files.

IF UNINSTALLING FAILS
Close the game and try Steam's game-file verification:
Steam Library > game Properties > Installed Files > Verify integrity of game files.
Official guide: https://help.steampowered.com/en/faqs/view/0C48-FCBD-DA71-93EB
Reinstalling the game may be necessary if problems persist. Verification and
reinstallation do not guarantee recovery of damaged saves or lost progress.

IN-GAME MOD SETTINGS
Open the new Mod settings entry at the bottom of the title menu. The title also
displays a blue, textured Water's Edition wordmark with a soft cyan glow below
Remastered, inspired by the original title lettering. It appears after the
original title reveal, including on the Press Start screen.
Version 0.12.5 places the page after the title's drawing pass so the logo no
longer draws over it. It uses the native Options layout: capsule heading,
window frames and color, gold labels, side-by-side choices, gradient highlight
and hand cursor. Bottom-right button hints use the game's live keyboard and
controller glyph selection. The title-screen crash fix from 0.10.2 is retained.
Use the controller or keyboard:
Up/Down selects a setting, Confirm or Left/Right toggles it, and Back closes
the panel. Up from the first row selects Reset/Default at the top right.
Choose one with Left/Right and press Confirm: Reset restores the settings from
when you opened the page; Default enables all eight features. Mouse selection
of the custom entry/panel is not implemented.

Eight switches are available and enabled by default:
- Dynamic camera (including the related framing/ground/effect adjustments)
- Post-battle TP recovery (Off restores the native recovery amount)
- TP from basic physical hits (Off removes the additional TP)
- Elemental damage colors (Off restores native damage colors)
- Custom HUD (including the Craymel vitality display)
- Casting progress bars
- Item cooldown bar
- Skit notification

The switches are independent. For example, you can keep the casting/item bars
while using the original HUD. The menu saves each change automatically to:
  %LOCALAPPDATA%\TalesOfEternia-WatersEdition.ini
Settings apply to the next battle without restarting and survive relaunches.
If saving fails, the panel displays an error and keeps the change for the current
session. Uninstalling leaves this small preferences file in place.

Mod interface text is French when the game's TEXT language is French, and
English for every other text language. Voice language does not affect it. This
only translates the mod's added text; the base game keeps its selected language.

VERSION CHECKS
The original DLL must have this SHA-256:
6488be2ce5ecc1dc9fc0216aa2462ec9aeba7a464468d5fd61ad3c2a8356849b

The installer checks the complete file, reconstructs the patch locally and checks
the final hash before replacing anything. Unknown game updates and other DLL
mods are refused. There is no force-install option. Keep at least 5 GiB free on
the game drive after installation. If Steam updates the game, do not replace its
new DLL with an old backup: wait for a compatible patch.
If you used an earlier private version of this mod, restore its original DLL
with that version's installer first. For an earlier public release, run its
Uninstall.cmd before installing this version. Other GameNative.dll mods cannot be combined
automatically. Other platforms and builds have not been verified.

ARTESPHERE AND SKIT NOTICE
- Two arte pages, seven assignments each (14 total). In the arte menu, tap
  L2/LT to switch pages. In battle, hold L2/LT for page B; release for page A.
- R2/RT is the seventh shortcut, assigned through the normal arte menu.
  It can command an active ally. Its native cursor, description and button
  images are integrated into the seven-row layout.
- Keyboard defaults: F7 for the page key, F8 for the seventh shortcut.
  Change these under Mod settings > Keyboard controls (PC). Choose keys
  that do not conflict with existing game controls.
- Extra assignments are saved per game save slot, including autosaves, in
  %LOCALAPPDATA%\TalesOfEternia-WatersEdition.ini. The game's save format
  is unchanged. Copy and back up this INI alongside your saves when moving
  computers; it is not automatically included in Steam Cloud.
- An optional, enabled-by-default skit notice indicates a camp skit is available.
  It prefers the lower left on the overworld and lower right in other areas,
  moves around occupied HUD space, and hides during menus and story scenes.

CHANGES IN 0.12.5
- Separate native palette ownership prevents a later supported spell from
  overwriting the palette used by an earlier spell's live projectiles.
  The Air Thrust -> Spread regression is covered by native offline tests.
  Final in-game rendering of this change still requires visual validation.
- Native R2 and RT button images replace the plain seventh-shortcut label.
- Includes earlier fixes for the seventh-row cursor/description, skit placement,
  unsupported battle-camera layouts and victory TP numbers above the HUD.

CURRENT FEATURES
- Basic physical hits restore 1 TP to party members; Keele and Meredy restore
  2 TP instead. Spells, artes, enemy hits and hits dealing no damage do not count.
- Post-battle TP recovery starts at 8% of max TP on Normal, with the four native
  difficulty indices using 8/9/10/13%. The native 10-TP minimum, bonus and status
  exclusions remain. Small TP pools may recover more than the base percentage.
- Adaptive battle camera follows the controlled character and selected target,
  with smoother movement and framing toward the arena interior.
- Forest stages 6-8 additionally account for the offset rear background layer
  when constraining the camera, to address the exposed strip at the left edge.
- Spell cinematic freezes are reduced by removing the patched freeze paths;
  battle-menu pauses and actual time-stop effects remain.
- Full mode permits overlapping supported, DIFFERENT ordinary spell effects.
  Same-effect casts, loading and special sequences can still wait their turn.
- Hold the Arte command through the end of an offensive elemental cast to
  request the matching learned, owned Craymel at full vitality. Release Arte
  before completion for the ordinary spell. Unsupported choices use native
  behavior. Autonomous AI casting is not remapped.
- Hold L1 to keep a finished spell ready; release L1 to let it go. L1 takes
  priority over the summon choice. Controller handling targets Steam's primary
  controller slot; other controller slots retain the native controls.
- Ordinary same-element spells no longer reduce full vitality from 10 to 5.
  Actual summons retain their native vitality consumption.
- Element-colored casting effects for Keele and Meredy, including hand glyphs
  and ground effects. Colors follow the native spell family.
- Element-colored damage numbers; neutral damage stays white. Damage received
  by your party uses a light red-to-white tint. Healing and TP numbers retain
  their native display types.
- Animated green HP and blue TP gauges in a compact, lowered HUD, with room for
  four HP digits. Pink casting bars sit below the caster's feet.
- A shared item recharge bar appears at the top center above the battle menu
  only after an item is used and while its cooldown is active.
- Owned Craymel miniatures below Keele/Meredy's HUD portraits show elemental
  0/10 through 9/10 text, then MAX. The first icon aligns with its portrait and
  the text is centered below each icon. Several spirits extend the row to the
  right. Smaller miniatures use an eight-direction turn, mirroring the original
  intermediate poses for the other half of the rotation.
- Startup presentation screens are skipped to reach the opening movie.
- Spread's water column keeps its original proportions and texture mapping;
  a small textured cap closes its upper edge. Experimental water-backdrop edge
  adjustments for Undine and shadow scaling are also included.

KNOWN LIMITS / TEST STATUS
- The spell queue is only partially removed. This is not unrestricted parallel
  casting. Compatibility mode restores the queue if you need to compare behavior.
- Camera bounds use 82 audited stage grids. The new forest backdrop constraint
  passed native projection tests; other background families may still show
  side seams. Unsupported stages retain the original camera framing.
- Summons and special sequences retain native cameras. Undine's backdrop and
  other summon scenes can still show framing issues. This is not a fix for every
  spell, stage or summon backdrop.
- The blue title wordmark and pre-Start glow have been confirmed in-game.
  The native-style settings menu was confirmed in earlier builds.
  Machine-code tests cover native frame construction and French/English glyph
  emission; this does not validate every device or setting combination.
  Spell overlap, camera coverage and summon effects still need broader testing.
- Parts of the earlier HUD/camera have been tested interactively. Emulated native
  code tests passed at two load addresses, including projection, atlas UVs,
  ownership, TP rules and guard cases. These do not prove whole-game stability.
- This release does not claim to fix slow game shutdown.

PACKAGE CONTENTS
Patch scripts, binary differences, English documentation and SHA-256 checksums.
No complete game executable/DLL, original game textures, music, saves, personal
logs or local developer paths are included. The new blue wordmark is embedded
in the patch data. The patch requires your own compatible installation.
Support/SHARE.txt contains a short English introduction you can copy into your server.
