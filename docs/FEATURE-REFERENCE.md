# Detailed feature reference

[Overview](../README.md) · [Features](FEATURES.md) · [Controls](CONTROLS.md)

This guide covers **version 0.14.30**. Most systems can be switched on or off in Mod settings. Timings below are in **seconds**; casting bonuses can reduce the listed base casting times.

## Added spells

Either Keele or Meredy can learn these spells. The required Craymel must be recruited, reach the indicated level and be in that mage's cage.

| Spell | Requirement | Base power | Base casting time |
| --- | --- | --- | --- |
| Spark Wave / Vague d'étincelles | Volt level 5 | 1400 | 4 seconds |
| Fear Flare / Rafale ardente | Efreet level 10 | 1440 across the full meteor shower | 3 seconds |

Spark Wave is a stronger lightning option than Thunder Blade. Fear Flare sits between Flame Trap and Explode, and costs 24 TP. Its shower contains 18 meteors; the listed total assumes every meteor connects.

**Power is not the damage number shown in battle.** Damage also depends on the caster, the target's defenses and elemental resistance, and active bonuses. For attacks with several hits, not every target will necessarily receive every hit. These spell adaptations apply to player characters; the enemy versions keep their original behavior.

## Spell mastery

Keele and Meredy keep separate progress. Offensive spell mastery grows through completed casts, with all growth tracks reaching their maximum by **500 credited uses**.

| Growth track | Maximum bonus |
| --- | --- |
| Power | +25% |
| Casting time | −15% |
| Recovery after casting | −15% |
| Critical chance | +15 percentage points |
| Projectiles, for supported spells | Up to 3 or 6 extra projectiles, depending on the spell |
| Area, for supported spells | +50% |

Eruption has both area and projectile growth. Its fireballs are capped at **9 in total**. A spell does not receive a projectile or area bonus when that track does not apply to it. Healing spells do not gain the offensive bonuses above.

The mage who is behind can earn up to **3 mastery EXP per cast** of a Craymel spell, without overtaking the other mage. The six starting spells are excluded. This catch-up bonus does **not** increase the actual cast counts used to learn other artes.

### Buff targets

Sharpness, Resist, Barrier and Concentrate can affect more living party members as their mastery grows:

| Credited uses | Additional targets |
| --- | --- |
| 100 | 1 |
| 250 | 2 |
| 500 | 3 |

The original target is counted separately. Extra applications keep the buff's original effect and duration; they do not create a stronger stacked version of the same buff.

## Craymel growth and Fringe

Completed elemental casts earn Craymel EXP after victory: **50** for basic spells, **200** for intermediate spells and **500** for advanced spells. An unrecruited spirit does not receive EXP. Faculty milestones occur at levels **5, 10, 15, 20, 25 and 30**. Each faculty can be enabled or disabled from its tree.

**Fringe: free cages** changes where the supporting spirit may be placed. It does not remove recruitment or level requirements. The main spirit must still be in the mage's cage, but the supporting spirit can be in either cage.

For example, Sharpness needs **Efreet level 5** and **Undine level 7**. With free cages enabled, both may be in the same cage. The mage holding Efreet receives access. With the option disabled, the original cage separation rules apply.

## Reid and Farah

Mastery branches follow Slash and Thrust for Reid, and Punch and Kick for Farah. Farah's **Energy level is the lower of her Punch and Kick levels**. Mixed branches require both component masteries to reach their milestone.

- At level 10, Reid gains two-basic-arte chaining within the corresponding family. Mixed basic chains require both Slash and Thrust at level 10.
- At level 30, Reid can chain two arcane artes from the corresponding family. Slash and Thrust unlock their own arcane chains separately.
- Farah's Punch, Kick and mixed chains allow up to **5 artes at level 15** and **6 at level 30**, while keeping compatible ground and air transitions.
- Reaching level 15 in both physical masteries adds one normal attack; level 30 adds a second.
- At Energy level 30, damage no longer interrupts Farah's healing casts. She can still take damage and receive status ailments.

The tables below list the faculties and their individual requirements.

### Standalone team-up artes

Practise each physical component **50 times**, and the matching spell **50 times with one mage**. Keele's and Meredy's spell counts are not added together. Mastery catch-up does not substitute for these actual uses.

| Character | Arte | Components | TP cost |
| --- | --- | --- | --- |
| Reid | Flaming Sword | Demon Hammer + Fireball | 13 |
| Reid | Earth Divide | Spiral Attack + Cyclone | 54 |
| Farah | Lightning Strike | Twin Palm Strike + Thunder Blade | 36 |
| Farah | Serpent Knuckle | Rising Dragon Strike + Heal | 28 |

Once learned, these artes can be used without a mage casting alongside the fighter, and only the fighter pays the TP cost. You do not need to perform the original combined attack to learn them. Disabling the option restores the original team-up behavior without erasing actual use counts.

Serpent Knuckle also restores **5% of Farah's maximum HP**. This is separate from the healing amount of Healer.

## Faculty reference

Choose a faculty in the mastery menu to see whether its requirements are met. Percentages at successive levels are the bonus at that level, not separate bonuses to add together. Names below use the English interface.


### Undine

| Level | Faculty | Effect |
| --- | --- | --- |
| 5 | Mana Economy | Spell TP costs reduced by 5%. |
| 10 | Mana Economy | Spell TP costs reduced by 10%. |
| 15 | Enhanced Healing | After an offensive spell, the next heal restores 5% more HP. |
| 20 | Mana Economy | Spell TP costs reduced by 15%. |
| 20 | Enhanced Healing | After an offensive spell, the next heal gains 10%. |
| 25 | Enhanced Healing | After an offensive spell, the next heal gains 15%. |
| 30 | Mana Economy | Spell TP costs reduced by 20%. |
| 30 | Undine's Guard | Excess healing creates a shield capped at 15% of maximum HP for 10 seconds. |


### Sylph

| Level | Faculty | Effect |
| --- | --- | --- |
| 5 | Nimble Mage | Reduces the delay before the mage can act again after a successful cast by 5%. |
| 10 | Nimble Mage | Reduces the delay before the mage can act again after a successful cast by 10%. |
| 15 | Perfect Dodge | 5% chance to evade an entire hit: no damage, interruption or harmful effect. |
| 20 | Nimble Mage | Reduces the delay before the mage can act again after a successful cast by 20%. |
| 25 | Nimble Mage | Reduces the delay before the mage can act again after a successful cast by 25%. |
| 30 | Nimble Mage | Reduces the delay before the mage can act again after a successful cast by 30%. |
| 30 | Perfect Dodge | 10% chance to evade an entire hit: no damage, interruption or harmful effect. |


### Efreet

| Level | Faculty | Effect |
| --- | --- | --- |
| 5 | Magic Force | Offensive spell damage increased by 3%. |
| 10 | Magic Force | Offensive spell damage +5%. |
| 15 | Burning Will | Below 50% HP: magic power increased by an additional 5%. |
| 20 | Magic Force | Offensive spell damage +10%. |
| 20 | Burning Will | Below 50% HP: magic power increased by 10%. |
| 25 | Burning Will | Below 50% HP: magic power increased by 15%. |
| 30 | Magic Force | Offensive spell damage +15%. |


### Gnome

| Level | Faculty | Effect |
| --- | --- | --- |
| 5 | Casting Guard | Damage received while casting reduced by 10%. |
| 10 | Casting Guard | Damage received while casting reduced by 15%. |
| 15 | Concentration | A hit while casting grants protection from light interruptions for 5 seconds. Cooldown: 25 seconds. |
| 20 | Casting Guard | Damage received while casting reduced by 20%. |
| 20 | Concentration | Light interruption protection for 5 seconds; cooldown 20 seconds. |
| 25 | Concentration | Light interruption protection for 5 seconds; cooldown 15 seconds. |
| 30 | Casting Guard | Damage received while casting reduced by 25%. |
| 30 | Concentration | Light interruption protection for 5 seconds; cooldown 10 seconds. |
| 30 | Unshakable | Gnome AND Celsius level 30: full interruption protection for 5 seconds, cooldown 20 seconds. The light ward has priority. |


### Celsius

| Level | Faculty | Effect |
| --- | --- | --- |
| 5 | Magic Resistance | Magic damage received reduced by 5%. |
| 10 | Magic Resistance | Magic damage received reduced by 10%. |
| 15 | Lucidity | New stuns last 15% less time, without granting immunity. |
| 20 | Magic Resistance | Magic damage received reduced by 15%. |
| 20 | Mental Clarity | Halve the Casting Delay penalty. |
| 25 | Lucidity | Stun duration reduced by 30%, without immunity. |
| 30 | Magic Resistance | Magic damage received reduced by 20%. |
| 30 | Survival | Once per battle: a fatal hit leaves 1 HP and grants 2 seconds of protective stasis. No actions during stasis; allies can heal you. |


### Volt

| Level | Faculty | Effect |
| --- | --- | --- |
| 5 | Critical Spell | 2% magic critical chance, for 50% additional damage per cast. |
| 10 | Critical Spell | 5% magic critical chance, for +50% damage per cast. |
| 15 | Critical Spell | Magic critical chance rises from 5% to 7%, for 50% additional damage per cast. |
| 20 | Critical Spell | 10% magic critical chance, for +50% damage per cast. |
| 25 | Critical Spell | Magic critical chance rises from 10% to 12%, for 50% additional damage per cast. |
| 30 | Critical Spell | 15% magic critical chance, for +50% damage per cast. |
| 30 | Flash Casting | 5% chance for a spell to cast instantly. |


### Rem

| Level | Faculty | Effect |
| --- | --- | --- |
| 5 | Shared Healing | A single-target heal also heals another wounded ally for 15% of the primary heal. |
| 10 | Shared Healing | A second wounded ally receives 30% of a single-target heal. |
| 15 | Shared Healing | The secondary heal becomes 50% of the initial amount. |
| 20 | Purification | A heal also removes a compatible ailment, cooldown 30 seconds. |
| 25 | Purification | Purification cooldown reduced to 20 seconds. |
| 30 | Regeneration | After healing: regenerate 25% of the initial amount over 5 seconds. |
| 30 | Saving Guard | Healing an ally below 25% HP grants 50% damage reduction for 5 seconds. Once per battle for each mage. |


### Shadow

| Level | Faculty | Effect |
| --- | --- | --- |
| 5 | Life Steal | Magic hits restore 1% of the HP actually removed from the enemy to the caster. |
| 10 | Life Steal | Restore 2.5% of damage dealt as HP after a spell hits. |
| 15 | Life Steal | Restore 5% of damage dealt as HP after a spell hits. |
| 20 | Spirit Steal | Defeating an enemy with magic restores 2.5% of damage as TP. |
| 25 | Spirit Steal | Defeating an enemy with magic restores 5% of damage as TP. |
| 30 | Vital Link | Heal the ally with the lowest HP ratio for 5% of the mage’s damage. |


### Sekundes

| Level | Faculty | Effect |
| --- | --- | --- |
| 5 | Speed Cast | Casting time reduced by 5%. |
| 10 | Spell Memory | Retain 20% of a cancelled cast. |
| 15 | Spell Memory | Retain 30% of a cancelled cast. |
| 20 | Reprise | Each repetition of the same completed spell reduces the next cast by 5%, up to 15%. Changing spells resets this bonus. |
| 25 | Speed Cast | Casting time reduced by 10%, up from 5%. |
| 30 | Speed Cast | Casting time reduced by 15%. |


### Maxwell

| Level | Faculty | Effect |
| --- | --- | --- |
| 5 | Spiritual Gift | Every 50 TP spent on spells restores 5 TP to other living allies. |
| 10 | Mana Coat | Absorb 25% of damage, spending 1 TP per 5 HP protected. Protection stops at 25% of maximum TP or less. |
| 15 | Spiritual Gift | Every 50 TP spent on spells restores 6 TP to other living allies, up from 5. |
| 20 | Resource Sharing | A recovery item shares 25% of the HP or TP actually restored. The original recipient keeps the full recovery. |
| 25 | Spiritual Gift | Every 50 TP spent on spells restores 8 TP to other living allies, up from 6. |
| 30 | Second Wind | A spell crosses the 25% TP threshold: restore 25% of maximum TP. Once per battle. |
| 30 | Singularity | The first magic impact pulls nearby small grounded enemies toward the target. Cooldown: 10 seconds. |


### Reid — Slash

| Level | Faculty | Effect |
| --- | --- | --- |
| 10 | Double technique | Chain two basic artes from this family. |
| 15 | Wide Slash | Widens the final normal slash hitbox by 25% to reach clustered enemies. |
| 20 | Lasting Blade | Sonic Blade dissipates more slowly and travels farther at the same speed. The projectile still ends on its first hit. |
| 20 | Heavy Impact | The final grounded normal hit adds 10% hitstun once per chain. Heavy and immune targets remain protected. |
| 25 | Guard Breaker | Land three normal attacks in one chain to prepare the next Slash arte: its first collision breaks an ordinary guard. Special protections remain effective. |
| 30 | Double Arcane | Chain two arcane artes from this family. Mixing families requires both masteries and both faculties. |


### Reid — Thrust

| Level | Faculty | Effect |
| --- | --- | --- |
| 10 | Double technique | Chain two basic artes from this family. |
| 10 | Precise Guard | Block within about 0.13 seconds of starting a guard to regain 3 TP. Each enemy attack rewards this only once, including multi-hit attacks. |
| 15 | Close Pressure | Pure Thrust artes halve grounded pushback against light enemies. Launches and heavy enemies are unaffected. |
| 20 | Step In | While guarding, press toward the target for a short forward step. Release the direction before repeating. Guard + Up still jumps. |
| 25 | Counterattack | After a successful block, press Attack within 0.4 seconds for a normal thrust counter. Once per blocked hit. |
| 30 | Double Arcane | Chain two arcane artes from this family. Mixing families requires both masteries and both faculties. |


### Reid — Slash + Thrust

| Level | Faculty | Effect |
| --- | --- | --- |
| 10 | Mixed double technique | Slash AND Thrust level 10: chain two basic artes across families. |
| 10 | Controlled Alternation | Chain a Slash arte into a Thrust arte, or vice versa: the third physical arte costs 20% less TP. Once per chain. |
| 15 | Extended attacks | Adds 1 normal attack to grounded chains. Both masteries must reach this level. |
| 20 | Bulwark | While Reid guards, nearby allies take 10% less physical damage. Reid does not benefit from his own protection. |
| 20 | Guard Artes | After a successful block, use a basic arte within 0.4 seconds. Native TP costs, requirements and chain limits still apply. |
| 25 | Technical Return | Return from an arcane to a basic arte once per chain. The two-basic-arte limit and other chain quotas still apply. |
| 30 | Composure | Hits no longer interrupt Reid while executing an arcane arte. Damage and status ailments still apply. |
| 30 | Extended attacks | Adds 2 normal attacks to grounded chains. Both masteries must reach this level. |


### Farah — Punch

| Level | Faculty | Effect |
| --- | --- | --- |
| 5 | Prepared Fist | Guard without moving for about 0.33 seconds to prepare the next Punch arte: it resists one light interruption. The preparation expires three seconds after stationary guarding ends. |
| 10 | Varied Sequence | Land three different Punch artes in one chain to regain 10% of the TP spent on its Punch artes. Triggers once per chain. |
| 15 | Extended Chains | Chain up to 5 artes from this family. Grounded and airborne requirements still apply. |
| 20 | Staggering Palm | Twin Palm Strike’s final impact adds 0.1 seconds of hitstun to a light grounded enemy, once per chain. Bosses and protected targets are excluded. |
| 25 | Breaking Palm | Land three different Punch artes in one chain to prepare Twin Palm Strike: its first collision breaks an ordinary guard. Special protections remain effective. |
| 30 | Extended Chains | Chain up to 6 artes from this family. Grounded and airborne requirements still apply. |


### Farah — Kick

| Level | Faculty | Effect |
| --- | --- | --- |
| 15 | Extended Chains | Chain up to 5 artes from this family. Grounded and airborne requirements still apply. |
| 20 | Controlled Ascent | Adds 0.1 seconds to the chain-input window after a rising arte. The next arte must be a compatible dive, with sufficient height. |
| 30 | Extended Chains | Chain up to 6 artes from this family. Grounded and airborne requirements still apply. |


### Farah — Punch + Kick

| Level | Faculty | Effect |
| --- | --- | --- |
| 10 | Martial Rhythm | Land three artes alternating Punch and Kick to prepare the next heal: its casting time is reduced by 75%. Holds one preparation and does not stack with Emergency Heal. |
| 15 | Mixed Chains | Chain up to 5 Punch and Kick artes. Both masteries must reach this level. Grounded and airborne requirements still apply. |
| 15 | Extended attacks | Adds 1 normal attack to grounded chains. Both masteries must reach this level. |
| 20 | Active Landing | Halves landing recovery after an aerial arte. No extra jump or reset of arte chain limits. |
| 25 | Back to Battle | After a heal takes effect, press Attack during recovery to resume immediately with a grounded normal attack. |
| 30 | Mixed Chains | Chain up to 6 Punch and Kick artes. Both masteries must reach this level. Grounded and airborne requirements still apply. |
| 30 | Extended attacks | Adds 2 normal attacks to grounded chains. Both masteries must reach this level. |


### Farah — Energy

| Level | Faculty | Effect |
| --- | --- | --- |
| 10 | Improved Healer | Healer restores 40% of the target’s max HP instead of 30%. |
| 10 | Vital Momentum | Restoring missing HP with a heal reduces the cost of Farah’s next physical arte by 20%. Does not stack or trigger on a full-HP target. |
| 15 | Emergency Heal | When Farah has strictly less than 25% of her max HP, Healer casts twice as fast. Has a 15-second cooldown. Martial Rhythm takes priority. |
| 15 | Healing Detoxify | Detoxify also restores 25% of its living target’s max HP. |
| 20 | Shared Healer | Healer also heals a second living ally for 50% of the primary heal. Lowest HP ratio first. |
| 20 | Lasting Purification | When Detoxify removes an ailment, the target resists that same ailment for ten seconds. Other ailments are not prevented. |
| 25 | Protective Revival | An ally revived by Life takes 25% less damage for five seconds. |
| 25 | Extended Detoxify | Detoxify now removes the same ailments as Recover. KO and special states that cannot be cleansed are excluded. |
| 30 | Extended Healer | Healer also heals a third ally for 25% of the primary heal, retaining the second ally’s 50% heal. |
| 30 | Improved Life | Life revives with 35% of max HP instead of the native 20%. |
| 30 | Steadfast Healer | Hits no longer interrupt Healer, Detoxify or Life while casting. Damage and status ailments still apply. |
