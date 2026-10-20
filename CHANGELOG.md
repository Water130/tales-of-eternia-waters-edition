# Changelog

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
