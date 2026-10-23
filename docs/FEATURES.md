# Features and limits

[Overview](../README.md) · [Installation](INSTALLATION.md) · [Controls](CONTROLS.md)

This page describes the published **0.13.8** release.

## Combat

- Normal physical hits restore **1 TP**, or **2 TP for Keele and Meredy**.
- Victory TP recovery starts at **8% on Normal**, retaining native minimums and modifiers.
- Dynamic camera, fewer spell freezes and overlap between supported, different ordinary spells.
- Hold **Arte** through an elemental cast for an eligible full-vitality summon; **L1** holds a finished cast instead.
- Optional **Guard** casting cancellation and separate **Guard + Up** jumps for mages and Reid/Farah.
- Optional multiple MAX Craymel vitality gauges.
- Rebalanced Hard/Extreme/Unknown: enemy HP **×1.5/×3/×5**, physical defense **×1.1/×1.2/×1.3**,
  enemy fixed-damage attacks **×1.1/×1.2/×1.5**. These are not multipliers on every attack.

## Artesphere and progression

- **18 arte assignments:** three pages of six commands, saved per game slot.
- Separate spell counters and mastery choices for each mage and save.
- Offensive spell mastery: **+1% damage per 25 casts**, capped at **+25%** in 0.13.8.
- Single-target buffs gain **1/2/3 extra recipients at 100/250/500 uses**, with native duration.
- Farah's Energy healing faculties, with six individually saved choices. Energy uses the lower Punch/Kick level.
- Mastery menu from **Stats → Square**, rooted trees, prerequisite links and progress gauges.
- Two five-column spell pages show unknown, available and unavailable spells.

**In 0.13.8, physical arte-chain and Craymel faculty trees are previews with no battle effect.**
They should not be confused with Farah's implemented Energy faculties or spell usage mastery.

### Farah's Energy faculties

| Energy level | Effect |
| --- | --- |
| 10 | Healer restores **40%** of the target's maximum HP instead of 30%. |
| 15 | Detoxify also restores **25%** of maximum HP. |
| 20 | Healer reaches a second target for **50%** of its original healing. |
| 25 | Detoxify removes a wider range of status ailments. |
| 30 | Healer reaches a third target for **25%** of its original healing; Life revives with **35%** maximum HP. |

Each faculty can be toggled individually. Healing spells do not gain the offensive
spell usage bonus. Spell lists use **???** for unknown spells, white for available
spells and gray for known but unavailable spells. Starting spells remain visible
before their Craymel joins.

## Interface and settings

- Custom HP/TP HUD, casting bars, item cooldown bar and Craymel vitality miniatures.
- Element-colored casting/damage effects, arte categories and spell usage counters.
- Skit notifications and quick playback while exploring.
- Startup presentation screens skipped to reach the opening movie.
- Four settings groups: **Quality of Life**, **Combat**, **Progression**, **Other**.
  Choices save automatically; keyboard and controller navigation are supported.
- French mod text with French game text, English otherwise. Installer files are English.

## Compatibility and limits

- **Windows / Steam build 25190541 only.** Other platforms and updates are unverified.
- Other mods replacing **GameNative.dll** cannot be combined automatically.
- Same-effect casts and special sequences can still queue. Optional Compatibility mode restores the native queue.
- Camera edges, summon backdrops and concurrent effects still need broader play testing.
- Custom menus do not support mouse selection. This release does not claim to fix slow shutdown.
- Offline native-code and installer checks do not guarantee whole-game stability.

The archive contains binary differences, not a complete game DLL. Your compatible game installation is required.
[Authorship, permissions and risks](ABOUT.md) · [Changes by version](../CHANGELOG.md)
