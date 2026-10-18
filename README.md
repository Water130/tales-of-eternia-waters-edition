# Tales of Eternia - Water's Edition

A combat and interface mod for **Tales of Eternia Remastered on Windows / Steam**.

**[Download Water's Edition 0.10.4 - Easy Install](https://github.com/Water130/tales-of-eternia-waters-edition/releases/download/v0.10.4-test/Tales-of-Eternia-Waters-Edition-0.10.4-Easy-Install.zip)**

Experimental test release. Supports **Steam build 25190541**. The installer
checks the exact game file before making any changes.

## Authorship, bugs and use at your own risk

Water's Edition was created, designed and directed by **Water, a human**.
**All of the mod's code was written by AI.**

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

Download the **Easy-Install.zip** release asset, rather than GitHub's automatically
generated **Source code** archive. Keep the extracted launchers and Support folder together.

## Current features

- Basic physical hits restore **1 TP**, or **2 TP for Keele and Meredy**.
- Post-battle TP recovery starts at **8% on Normal**. Native minimums and modifiers remain.
- A smoother dynamic battle camera follows the controlled character and selected target.
- Reduced spell cinematic freezes and limited overlap between supported, different spell effects.
- Hold **Arte** through an elemental cast to choose the matching owned, learned Craymel at full vitality;
  hold **L1** to keep a completed spell ready.
- Compact custom HUD with animated green HP and blue TP gauges, casting bars and an item cooldown bar.
- Element-colored casting effects and damage numbers.
- Animated Craymel miniatures and elemental vitality counters below the mage portraits.
- Startup skips the presentation screens and goes directly to the opening movie.
- Blue **Water's Edition** title lettering with a cyan glow.
- A native-style **Mod settings** page with keyboard/controller hints and seven independent switches.

The settings page can toggle the camera, post-battle TP, basic-hit TP, damage colors,
custom HUD, casting bars and item cooldown bar. Settings are saved automatically.

Mod text is **French when the game's text language is French**, and **English for
every other language**. All installation archives and public documentation are in English.

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
Automated tests cover native hooks and installation/restoration on disposable test copies;
they do not prove stability in every battle. The 0.10.4 settings menu was also confirmed in-game by the tester.

Unofficial fan mod, not affiliated with or endorsed by Bandai Namco Entertainment.
Tales of Eternia and its original assets belong to their respective rights holders.
