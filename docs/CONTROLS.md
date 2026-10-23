# Controls

[Overview](../README.md) · [Installation](INSTALLATION.md) · [Features](FEATURES.md)

## Artesphere pages

Each page has **six assignments**. The original directional artes and two ally shortcuts keep their game bindings.

| Page | Color | Controller | Default keyboard key |
| --- | --- | --- | --- |
| A | Blue | Release both modifiers | Release F7/F8 |
| B | Red | L2 / LT | F7 |
| C | Yellow | R2 / RT | F8 |

- **In battle:** hold a modifier to use that page. C takes priority if both are held.
- **In the assignment menu:** tap a modifier to toggle its page/A; close the arte/caster chooser first.
- Page modifiers alone do not cast, and switching pages does not replace a spell already being cast.
- Hold **L1** to keep a finished spell ready; it takes priority over the held-Arte summon command.

## Other shortcuts

| Action | Input |
| --- | --- |
| Open Mastery from Stats | Square, or the displayed mapped equivalent |
| Open Mastery from Techniques in semi-auto/manual | Square |
| Open Mastery from Techniques in auto | Triangle |
| Play an available skit | L2 / LT; L2 + Select if L2 is assigned to another exploration action |
| Cancel casting, with the option enabled | Guard |
| Jump, with the corresponding mage/fighter option enabled | Guard + Up |

In Mastery, select a branch or Craymel in the left list, then confirm to enter its
tree. For Keele and Meredy, **Triangle** switches between Faculties and Spell
progression. In the spell list, Left/Right changes columns and pages; Up/Down
scrolls spells.

## Change keyboard modifiers

Open **Mod settings → Other → Keyboard controls (PC)**. Select a modifier,
confirm, release held keys, then press the new key. **Esc** cancels.
Choose two different keys that do not conflict with the game's own controls.
Bindings are shared across saves; arte assignments are stored separately per save.

For manual configuration, close the game and edit `%LOCALAPPDATA%\TalesOfEternia-WatersEdition.ini`:

```ini
[ArtesphereControls]
PageKey=118
PageCKey=119
```

These are Windows virtual-key codes: **118 = F7**, **119 = F8**. Invalid or identical
values fall back to the defaults. Do not edit the INI's encoded save records.
Back up this file alongside saves; it is not automatically included in Steam Cloud.
