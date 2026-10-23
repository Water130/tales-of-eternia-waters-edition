# Changelog

[Overview](README.md) · [Installation](docs/INSTALLATION.md) · [All releases](https://github.com/Water130/tales-of-eternia-waters-edition/releases)

## 0.13.8 - Experimental release

- Add a persistent Mastery list and rooted skill trees from Stats (Square),
  with level meters, prerequisite links, readable colored cards and descriptions.
- Implement optional Farah Energy healing faculties with six independently saved
  choices. Energy is the lower Punch/Kick level, without independent experience.
- Implement optional spell usage mastery: +1% offensive damage per 25 casts,
  capped at +25%; buffs reach +1/2/3 allies at 100/250/500 uses with native duration.
  Healing is excluded. Counts and choices are separate for each mage/save.
- Add two fixed five-column spell pages, unknown/available/unavailable states,
  starting spells before Craymel acquisition and next-gain bars with MAX caps.
- Character combo and Craymel faculty trees are previews with no battle effects.
- Group mod options into Quality of Life, Combat, Progression and Other, with
  detailed help. Add separate Guard + Up controls for Reid/Farah.
- Add arte category labels, aligned with the native name and TP cost.
- Add L2/LT skit playback (L2 + Select if rebound) and improve compass avoidance.

Offline x64 regression and installer fixture checks pass. Real in-game rendering
and whole-game stability still require player testing; bugs and regressions may occur.

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

## 0.12.6 - Experimental release

- Fix invisible R2 / RT images on the seventh arte row. The buttons now use the
  native row's full RGBA color instead of a value with zero alpha, including menu fades.
- Use **Artesphere** without an accent in French and English.
- Color the **Artesphere — Page A** heading blue and **Artesphere — Page B** red.
- Extend native rendering tests to cover actual color, atlas binding and quad commands,
  with opaque, half-opacity and transparent menu states. The test reproduces the
  invisible-button defect in 0.12.5.
- Retain the 0.12.5 spell-palette isolation changes; no new spell changes are included.

Native x64 checks pass at two image bases. Installer and uninstaller checks pass
on disposable test copies. Final in-game rendering of the newest changes and the
earlier palette-isolation fix still needs visual confirmation.
These checks do not guarantee whole-game stability.

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

## 0.10.4 - Experimental release

- Documentation refreshed on 18 October 2026: human authorship and entirely AI-written code,
  expected bugs, no guaranteed fixes/support, use-at-your-own-risk notice and recovery guidance.
  Removed the Report a problem section and requests for bug reports from the guides.
  The refreshed Easy Install ZIP changes documentation/checksums only; the patch and installer are unchanged.
- Fixed the title logo drawing over the Mod settings panel.
- Matched the native Options layout, including window frames, gold labels, side-by-side choices,
  selection highlight, hand cursor and Reset/Default controls.
- Added live native keyboard/controller button hints to the settings page.
- Retained the title-screen crash fix and the blue wordmark with its cyan glow.
- Packaged two simple English launchers: Install.cmd and Uninstall.cmd, with automatic
  Steam-folder detection and Y/N confirmation.
- Verified installation, cancellation, exact original-file restoration and protection
  against unsupported or corrupted files on disposable test copies.

This is the first GitHub release. Existing combat/HUD features are described in the README.
The Easy Install packaging does not change the tested 0.10.4 game patch.
