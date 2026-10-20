# Water's Edition 0.12.13 - Easy Install

Experimental release for **Tales of Eternia Remastered, Windows / Steam build 25190541**.

## 0.12.13 - Experimental release

- Replace the seventh shortcut with **three Artesphere pages of six commands
  (18 total)**. Restore the original six-row layout, spacing, cursor and descriptions.
- Page A is blue; B is red (**L2/LT**); C is yellow (**R2/RT**). Hold the modifier
  in battle; tap it in the editor to toggle that page/A. C takes priority if
  both are held. Page modifiers alone do not cast.
- Preserve per-save A/B assignments. On migration, C initially copies B;
  new profiles initialize both extra pages from A. Legacy records are retained.
- Keep configurable keyboard modifiers: **F7** for B and **F8** for C by default.
  The former seventh-slot key becomes the C modifier.
- Add per-character usage counters to spells, including healing/support spells
  and summons, and display element icons to the left of usage counters for
  spells and physical artes. Counters start at zero; earlier uses cannot be recovered.
- Keep victory TP numbers at their original position and animation, drawing
  in front of the TP gauge instead of behind it.
- Add optional **Rebalanced difficulties**: Hard/Extreme/Unknown enemy HP
  factors **1.5/3/5**, physical defense **1.1/1.2/1.3**, and enemy fixed-damage
  attack factors **1.1/1.2/1.5**, relative to base values. Other native difficulty
  rules remain. This is not a multiplier on every enemy attack.
- Add optional **multiple MAX vitality**, letting several Craymels remain full.
  Summoning still consumes the selected Craymel's vitality.
- Add optional **Guard cancels casting**, including a completed incantation
  held with L1. Already-released effects continue normally.
- Add optional **Mage jump: Guard + Up** for player-controlled Keele and Meredy,
  avoiding accidental jumps from Up alone. Other characters keep native controls.

The four new settings are independent, saved, and enabled by default. Existing
preferences remain intact. Configure them at the title screen before loading.
Native x64 regression checks pass at two image bases. English install/uninstall
checks pass on disposable game-file copies. In-game validation of the newest
changes remains pending; these tests do not guarantee whole-game stability.


## Install or update

Download **Tales-of-Eternia-Waters-Edition-0.12.13-Easy-Install.zip** below. If updating, first uninstall your older release
using its own Uninstall.cmd. Close the game, extract the entire new ZIP,
double-click **Install.cmd**, and confirm the detected folder with **Y**.
To remove this release, run **Uninstall.cmd** and confirm with **Y**.
No Python or mod loader is required. Unknown game builds or modified DLLs are refused.

Back up your saves and `%LOCALAPPDATA%\TalesOfEternia-WatersEdition.ini` separately.
Keep the installer's verified original DLL backup. The ZIP contains binary
differences, not a complete game DLL. Existing A/B assignments migrate automatically
when their saved profile matches; C begins as a copy of B.

Same-effect and special spells can still queue. Support/Compatibility-Mode.cmd
restores the native spell queue while keeping the other changes.

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

SHA-256 of **Tales-of-Eternia-Waters-Edition-0.12.13-Easy-Install.zip**:

```text
d932803471e268a80f5829200a4c744a4b18eee26a408cd7b9da09a1d1d0a273
```
