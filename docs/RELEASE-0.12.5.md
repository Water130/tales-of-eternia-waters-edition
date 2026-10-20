# Water's Edition 0.12.5 - Easy Install

Experimental release for **Tales of Eternia Remastered, Windows / Steam build 25190541**.

## 0.12.5 - Experimental release

- Fix shared native spell palettes: loading a later supported spell no longer
  replaces an earlier spell's palette. The Air Thrust -> Spread case is covered
  by native load/draw regressions; final in-game rendering still needs confirmation.
- Show native R2 and RT button images, separated by a slash, on the seventh arte row.
- Includes the changes since 0.10.4: two seven-slot arte pages, per-save assignments,
  configurable keyboard aliases, and native seventh-row selection and descriptions.
- Add an optional skit notification for the overworld and fields/dungeons, with
  HUD collision avoidance, bottom-center fallback and dialogue/menu suppression.
- Improve spell texture isolation and particle capacity for supported simultaneous casts.
- Refine elemental colors, Craymel miniature size/rotation and Keele's fast-cast pad position.
- Preserve the original camera on unsupported battle layouts and move victory TP
  recovery numbers above the HUD.
- Refresh the English Install/Uninstall package and current feature documentation.

Native x64 checks pass at two image bases. Installer and uninstaller checks pass
on disposable test copies. These are not a guarantee of whole-game stability.


## Install or update

Download **Tales-of-Eternia-Waters-Edition-0.12.5-Easy-Install.zip** below. If updating, first uninstall your older release
using its own Uninstall.cmd. Close the game, extract the entire new ZIP,
double-click **Install.cmd**, and confirm the detected folder with **Y**.
To remove this release, run **Uninstall.cmd** and confirm with **Y**.
No Python or mod loader is required. Unknown game builds or modified DLLs are refused.

The ZIP contains binary differences, not a complete game DLL. Keep the verified
original backup created by the installer. Back up your game saves and
`%LOCALAPPDATA%\TalesOfEternia-WatersEdition.ini` separately.

Same-effect and special spells still queue. Compatibility-Mode.cmd restores the
native spell queue while keeping the other changes.

## Authorship, bugs and use at your own risk

Water's Edition was created, designed and directed by **Water, a human**.
**All of the mod's code was written by AI.**

This mod was done strictly for my personal use, I am just sharing it with whoever wants it, I wont take requests.

**If you're on a crusade agaisnt AI, do not be hypocrite and do not download this mod, I have neither the time nor the desire to learn codding, I'm just a random lambda guy that likes to tweaks games and give them my personal touch with the help of AI like Codex or Claude.**

You may download, install and play the official release. To share the mod,
please link to this repository or its official release page.

**❌ Not allowed without Water's prior written permission:**

- Reuploading or redistributing the mod on other platforms.
- Distributing modified versions of the mod, including release packages built from forks.
- Reusing original code or assets created specifically for Water's Edition in other publicly distributed projects.
- Selling the mod or including it in paid mod packs.

**Do not claim authorship of Water's Edition or misrepresent who created it.**

These conditions apply only to material over which Water holds enforceable rights.
The original game and third-party code or assets remain subject to their respective
owners' rights and licenses. These conditions do not override rights granted by
applicable law, third-party licenses or
[GitHub's Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#5-license-grant-to-other-users),
including the right to view and fork public repositories within GitHub.
A GitHub fork does not imply Water's endorsement or permission to distribute a mod release
beyond those existing rights.

**This mod has bugs.** Unknown bugs and new regressions may appear in current
and future versions. Crashes, visual glitches and unintended gameplay behavior
are possible. **Not all bugs will necessarily be fixed.** Fixes, support and
future updates are not guaranteed.

**Use this mod at your own risk.** It is provided as-is, without warranty.
To the extent permitted by applicable law, the creator accepts no liability
for problems or losses resulting from its use, including damage to game files,
save corruption or lost progress. Back up your saves separately before installing.
The installer and uninstaller do not directly edit saves; this is not a guarantee
that bugs during gameplay cannot affect your progress.

If the uninstaller fails, close the game and try
[Steam's game-file verification](https://help.steampowered.com/en/faqs/view/0C48-FCBD-DA71-93EB).
Reinstalling the game may be necessary if problems persist. Neither verification
nor reinstallation guarantees recovery of damaged saves or lost progress.


## Archive checksum

SHA-256 of **Tales-of-Eternia-Waters-Edition-0.12.5-Easy-Install.zip**:

```text
b828849965d4e2375879d3b2fbf12a9f3af360172c162df148897a211e7dd3d7
```
