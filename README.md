# Tales of Eternia Remastered

<p align="center">
  <img src="assets/branding/waters-edition-blue.png" alt="Water's Edition — blue title logo" width="860">
</p>

A combat and interface mod for **Tales of Eternia Remastered on Windows / Steam**.

**[Download Water's Edition 0.12.13 - Easy Install](https://github.com/Water130/tales-of-eternia-waters-edition/releases/download/v0.12.13-test/Tales-of-Eternia-Waters-Edition-0.12.13-Easy-Install.zip)**

Experimental test release. Supports **Steam build 25190541**. The installer
checks the exact game file before making any changes.

## Current features

- Basic physical hits restore **1 TP**, or **2 TP for Keele and Meredy**.
- Post-battle TP recovery starts at **8% on Normal**. Native minimums and modifiers remain.
  Recovery numbers retain their original animation and draw in front of the TP bars.
- A smoother dynamic battle camera follows the controlled character and selected target.
  Unsupported stage layouts retain the original framing.
- Reduced spell cinematic freezes and overlap between supported, different ordinary spells.
  Spell texture descriptors and palettes are isolated to prevent cross-spell replacement.
- Hold **Arte** through an elemental cast to choose the matching owned, learned Craymel
  at full vitality; hold **L1** to keep a completed spell ready.
- **Artesphere: three pages of six assignments (18 total)**, using the original six-row menu.
  A is blue, B is red (**L2/LT**), and C is yellow (**R2/RT**).
  Hold a modifier in battle; tap it in the editor to toggle that page/A.
  Assignments are stored separately per save. Existing A/B assignments are preserved.
- Configurable keyboard modifiers: **F7** for B and **F8** for C, changeable under
  **Mod settings > Keyboard controls (PC)**.
- Per-character spell usage counters, with element icons to their left.
  Physical artes retain their native counters and also show their elements.
- Optional **Rebalanced difficulties**: Hard/Extreme/Unknown enemy HP **×1.5/×3/×5**,
  physical defense **×1.1/×1.2/×1.3**, and enemy fixed-damage attacks **×1.1/×1.2/×1.5**.
- Optional **multiple MAX vitality**, allowing several Craymels to remain fully charged.
- Optional **Guard spell cancelling** and **Guard + Up jumps for Keele/Meredy**.
- Compact custom HUD with animated green HP and blue TP gauges, casting bars and an item cooldown bar.
- Vivid elemental casting effects and damage numbers.
- Smaller rotating Craymel miniatures and colored vitality counters below mage portraits.
- Optional **skit notification**, on the overworld and in fields/dungeons.
  It avoids occupied HUD space and hides during menus, dialogue and story scenes.
- Startup skips presentation screens and goes directly to the opening movie.
- Blue **Water's Edition** title lettering with a cyan glow.
- A native-style **Mod settings** page with keyboard/controller hints, twelve independent
  switches and a dedicated keyboard configuration page.

All twelve switches are enabled by default and saved automatically. Existing
preferences are retained. Configure the new combat settings at the title screen
before loading your save.

Mod text is **French when the game's text language is French**, and **English for
every other language**. All installation archives and public documentation are in English.

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

## Install or uninstall

1. Close the game and extract the entire release ZIP with **Extract All**.
2. Double-click **Install.cmd**, check the detected game folder, type **Y** and press Enter.
3. Wait for **Installed and verified**, then launch the game normally through Steam.

To remove the mod, close the game, run **Uninstall.cmd**, and confirm with **Y**.
The original game file is restored. The installer and uninstaller do not directly edit saves.

Steam libraries are detected automatically. If asked for a folder, use
**Steam > Manage > Browse local files** and paste that folder's path.
No Python, mod loader or extra download is needed to install the release.

Extra arte assignments are stored per save slot in
`%LOCALAPPDATA%\TalesOfEternia-WatersEdition.ini`. Back up this file with your saves
and copy it when moving to another PC; Steam Cloud does not automatically include it.

Download the **Easy-Install.zip** release asset, rather than GitHub's automatically
generated **Source code** archive. Keep the extracted launchers and Support folder together.

## Compatibility and current limits

- Only the exact supported Windows / Steam build is accepted. Other platforms and game updates are unverified.
- Other mods that replace `GameNative.dll` cannot be combined automatically. Uninstall an older
  Water's Edition release using that release's uninstaller before updating.
- The spell queue is only partially removed. Same-effect casts and special sequences can still wait.
- Some camera edges, summon backdrops and the Spread cap need broader visual testing.
- Mod settings support keyboard/controller navigation; mouse selection is not implemented.
- This release does not claim to fix slow game shutdown.

The release also includes an optional **Support/Compatibility-Mode.cmd** launcher,
which restores the native spell queue while keeping the other changes.

See [full feature and compatibility details](docs/FEATURES.txt),
[installation help](docs/INSTALLATION.txt), and the [changelog](CHANGELOG.md).

## Source and verification

The repository contains the mod's native patch generators, offline tests, installer sources,
an authored title wordmark and derived stage-boundary measurements. Building requires your own
compatible original game DLL; it is **not** included. See [BUILDING.md](BUILDING.md).

The shared ZIP contains binary differences, not a complete game executable or DLL.
The installer preserves a verified original backup and refuses unknown game-file hashes.
Automated tests cover native hooks at two image bases and installation/restoration on
disposable test copies. They do not prove whole-game stability. The newest controls,
save migration and rendering changes still need in-game validation.

Unofficial fan mod, not affiliated with or endorsed by Bandai Namco Entertainment.
Tales of Eternia and its original assets belong to their respective rights holders.
