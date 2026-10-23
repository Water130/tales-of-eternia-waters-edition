# Features and limits

[Overview](../README.md) · [Installation](INSTALLATION.md) · [Controls](CONTROLS.md)

This guide describes **0.14.11**. Features marked as previews are not active battle effects.

## Choose your setup

Mod settings are organized into **Quality of Life, Combat, Progression and Other**.
Most features can be toggled, with saved preferences and scrollable help.
Progression systems use coherent groups instead of requiring several dependent switches:

| Switch | Includes |
| --- | --- |
| Magic progression | Spell growth, Craymel faculties, summon damage/area growth, cast-earned Craymel EXP and supported improved extensions |
| Farah progression | Energy gauge and healing faculties, Punch/Kick and mixed-branch progression |
| Reid progression | Slash/Thrust and mixed-branch progression |
| Separate options | General boosts, mage/fighter jumps, Reid special techniques, standalone team-up artes and other combat/QoL settings |

Disabling progression removes its effects without erasing stored progression or
faculty choices. Craymel faculties activate when unlocked and can also be disabled
individually. **Fringe: free cages is off by default.** It ignores only the partner
Craymel's location; discovery, level requirements and primary ownership still apply.

## Combat and interface

- Dynamic battle camera and custom HUD, with casting and item cooldown bars.
- TP recovery from normal attacks and victory; optional difficulty and vitality changes.
- Elemental damage colors, with a pale healing color distinct from wind damage.
- Optional spell-pause removal and overlapping supported spells. Some effects still queue.
- Guard to cancel casting; separate Guard + Up jump options for mages and Reid/Farah.
- Optional stopping of automatic running when guarding, attacking or using an arte.
- Separate Air Thrust projectile impacts.
- **Three Artesphere pages of six assignments**, saved per game save. See [controls](CONTROLS.md).
- Enemy scan memory, HP bars above target frames and a compact R1 information panel
  with native elemental icons after the original Lens window closes.
- Arte categories, skit notices and quick playback.

## Spell progression

Keele and Meredy keep **separate usage counts and spell levels**. A mage behind the
other receives **three credited uses per cast** until caught up. These credited
uses also count toward usage-based unlock requirements.

Offensive spells reach their maximum overall **level 30 at 999 uses**. The overall
level follows their individual growth tracks, each with its own level and next-gain
EXP bar. Capped bars remain full and show **MAX**.

| Growth track | Maximum bonus | Uses to reach the cap |
| --- | --- | --- |
| Power | +25% | 500 |
| Casting time | −15% | 500 |
| Post-cast recovery | −15% | 500 |
| Critical chance | +15 percentage points | 500 |
| Projectiles **or** area, depending on the spell | +3/+6 projectiles, or +50% area | 999 |

Victory messages announce both overall spell level-ups and individual bonus
level-ups, even when the overall level stays unchanged. Messages use French when
the game is in French, otherwise English; gains are combined into one notice per
spell and caster.

Two pages group spells into five elemental columns each. Starting spells appear
under their element even before its Craymel is discovered. Unknown entries show
`???`; known but unavailable spells are greyed out. Usage counts, prerequisites
and progress remain visible in the lower panel.

## Craymel progression

Successfully cast spells award their elemental Craymel **50 / 200 / 500 EXP** for
basic / intermediate / advanced tiers. EXP is awarded **on victory**, replacing
free automatic EXP while Magic progression is enabled. Gauges in the cage and
mastery menus show progress toward the **next level**.

- Summon damage and area increase with Craymel level.
- **72 implemented faculties** cover all ten Craymel, with benefits at levels
  **5, 10, 15, 20, 25 and 30**.
- Element-themed French/English names, numerical bonuses, detailed descriptions,
  unlock conditions, active highlights and elemental tree links.
- Effects include spell TP costs, recovery, magic power, healing, protection,
  perfect evasion, critical effects, draining, mana sharing and casting bonuses.
- Numerical tiers use the highest enabled bonus; independent faculty choices
  are retained for each mage.

The improved Maelstrom requirement is **Undine level 10, 50 Spread uses and at
least 5/10 vitality**. This does not mean every planned extension is implemented.

## Reid and Farah

Farah's Energy is based on the lower of Punch and Kick. Her six healing faculties are:

| Energy level | Effect |
| --- | --- |
| 10 | Healer restores 40% max HP instead of 30% |
| 15 | Detoxify also restores 25% max HP |
| 20 | Healer reaches a second target for 50% of the initial healing |
| 25 | Detoxify removes a broader set of ailments, with rare exceptions |
| 30 | Healer reaches a third target for 25% of the initial healing |
| 30 | Life revives at 35% max HP instead of 25% |

Mixed **Punch + Kick** and **Slash + Thrust** branches grant **one extra normal
attack at level 15 and two at level 30**. Advanced arte-chain nodes are still previews.

The separate **Reid special techniques** option changes Aurora commands to
**Attack + Arte**, sets Aurora Wall's HP threshold to **25%**, and removes the
enemy-HP restriction for his mystic artes, with **three uses per technique per
battle**. Other requirements remain.

Four **standalone team-up artes** unlock after 50 uses of the physical arte and
50 uses of its associated spell by Keele or Meredy. They need no mage at launch
and cost the sum of the two component techniques.

## Compatibility and limits

- **Windows / Steam build 25190541 only.** The installer refuses unsupported or
  already modified DLLs. Other mods editing GameNative.dll are not automatically compatible.
- The download contains binary differences, not original game binaries or assets.
- This is an experimental release. Offline tests do not prove whole-game stability,
  every battle sequence or final GPU rendering. Concurrent spell effects and camera
  edges may still need further testing; same-effect and special spells can still queue.
- Advanced Reid/Farah arte chains and other character preview nodes have no battle
  effect yet. New water/wind/fire spells and general extension/sublimed rules are
  not all implemented.
- New Craymel healing faculties currently apply in battle, not to out-of-battle menu healing.
- Individual spell-bonus inspection is not yet available; the existing spell toggle remains.
- Final live HP/TP font appearance still needs follow-up.

Mod text is French or English; the installer and public guides are in English.
Read the [creator's statement and use-at-your-own-risk notice](ABOUT.md), and back
up saves and mod preferences before installing.
