"""Craymel milestones shared by battle code and bilingual menu descriptions.

Append new nodes: their indices are persisted choices, never display order.
Legacy IDs 128..207 remain unchanged; extra nodes use reserved IDs 208..247.
"""
BASE_LEVELS = ((10,20,30,20,25,30), (10,20,30,15,30), (10,20,30,20,25),
               (10,20,30,20,25,30,30), (10,20,30,20,25,30),
               (10,20,30,30), (10,15,20,25,30,30), (10,15,20,25,30),
               (5,10,20,30,30), (5,10,15,20,30))

# Level, numerical tier, value (native units), lane, title, benefit, description.
ADDITIONS = (
    ((5,'cost',5,0,('Économie de mana','Mana economy'),('-5% TP','-5% TP'),
      ('Coût des sorts en TP réduit de 5 %.','Spell TP costs reduced by 5%.')),
     (15,'prepared',5,1,('Soin préparé','Prepared healing'),('Soin +5%','Heal +5%'),
      ('Après un sort offensif, le prochain soin restaure 5 % de PV supplémentaires.',
       'After an offensive spell, the next heal restores 5% more HP.'))),
    ((5,'recovery',5,0,('Récupération après lancement','Post-cast recovery'),('-5%','-5%'),
      ('Récupération après lancement réduite de 5 %.','Post-cast recovery reduced by 5%.')),
     (25,'recovery',25,0,('Récupération après lancement','Post-cast recovery'),('-25%','-25%'),
      ('Récupération après lancement réduite de 25 %, au lieu de 20 %.',
       'Post-cast recovery reduced by 25%, up from 20%.'))),
    ((5,'power',3,0,('Puissance magique','Magic power'),('+3%','+3%'),
      ('Dégâts des sorts offensifs augmentés de 3 %.','Offensive spell damage increased by 3%.')),
     (15,'fervor',5,1,('Ferveur magique','Magic fervor'),('Puissance +5%','Power +5%'),
      ('Sous 50 % de PV : puissance magique augmentée de 5 % supplémentaires.',
       'Below 50% HP: magic power increased by an additional 5%.'))),
    ((5,'cast_defense',10,0,('Cast protégé','Protected casting'),('-10%','-10%'),
      ('Dégâts reçus pendant l’incantation réduits de 10 %.','Damage received while casting reduced by 10%.')),
     (15,'light_ward',1500,1,('Garde légère','Light ward'),('Garde 25s','Ward 25s'),
      ('Protège des interruptions légères pendant 5 s lors d’un impact en incantation. Recharge : 25 s.',
       'A hit while casting grants protection from light interruptions for 5s. Cooldown: 25s.'))),
    ((5,'magic_defense',5,0,('Résistance magique','Magic resistance'),('-5%','-5%'),
      ('Dégâts magiques reçus réduits de 5 %.','Magic damage received reduced by 5%.')),
     (15,'stun_reduction',15,1,('Lucidité','Lucidity'),('-15% étourdi','Stun -15%'),
      ('Durée des nouveaux étourdissements réduite de 15 %, sans immunité.',
       'New stuns last 15% less time, without granting immunity.'))),
    ((5,'critical',2,0,('Critiques magiques','Magic criticals'),('2%','2%'),
      ('2 % de chance de critique magique, pour 50 % de dégâts supplémentaires par sort.',
       '2% magic critical chance, for 50% additional damage per cast.')),
     (15,'critical',7,0,('Critiques magiques','Magic criticals'),('7%','7%'),
      ('Chance de critique magique portée de 5 à 7 %, pour 50 % de dégâts supplémentaires par sort.',
       'Magic critical chance rises from 5% to 7%, for 50% additional damage per cast.')),
     (25,'critical',12,0,('Critiques magiques','Magic criticals'),('12%','12%'),
      ('Chance de critique magique portée de 10 à 12 %, pour 50 % de dégâts supplémentaires par sort.',
       'Magic critical chance rises from 10% to 12%, for 50% additional damage per cast.'))),
    ((5,'heal_share',15,0,('Soin solidaire','Shared healing'),('Partage de 15%','Share 15%'),
      ('Un soin monocible soigne aussi un autre allié blessé à hauteur de 15 % du soin principal.',
       'A single-target heal also heals another wounded ally for 15% of the primary heal.')),),
    ((5,'hp_drain',10,0,('Absorption de PV','HP drain'),('1%','1%'),
      ('Les impacts magiques rendent au mage 1 % des PV effectivement retirés à l’ennemi.',
       'Magic hits restore 1% of the HP actually removed from the enemy to the caster.')),),
    ((15,'mana_share',6,0,('Mana solidaire','Shared mana'),('+6 TP / 50 TP','+6 TP / 50 TP'),
      ('Tous les 50 TP dépensés en sorts : rend 6 TP aux autres alliés vivants, au lieu de 5.',
       'Every 50 TP spent on spells restores 6 TP to other living allies, up from 5.')),
     (25,'mana_share',8,0,('Mana solidaire','Shared mana'),('+8 TP / 50 TP','+8 TP / 50 TP'),
      ('Tous les 50 TP dépensés en sorts : rend 8 TP aux autres alliés vivants, au lieu de 6.',
       'Every 50 TP spent on spells restores 8 TP to other living allies, up from 6.'))),
    ((25,'haste',10,0,('Don de célérité','Gift of haste'),('-10%','-10%'),
      ('Durée d’incantation réduite de 10 %, au lieu de 5 %.','Casting time reduced by 10%, up from 5%.')),),
)

LEVELS = tuple(base+tuple(n[0] for n in extra) for base,extra in zip(BASE_LEVELS,ADDITIONS))
assert all(set(levels)=={5,10,15,20,25,30} for levels in LEVELS)
assert all(len(levels)<=12 for levels in LEVELS)

TIERS = {
    'cost':(0,[(0,10),(1,15),(2,20)]), 'prepared':(0,[(3,10),(4,15)]),
    'recovery':(1,[(0,10),(1,20),(2,30)]), 'dodge':(1,[(3,5),(4,10)]),
    'power':(2,[(0,5),(1,10),(2,15)]), 'fervor':(2,[(3,10),(4,15)]),
    'cast_defense':(3,[(0,15),(1,20),(2,25)]), 'light_ward':(3,[(3,1200),(4,900),(5,600)]),
    'magic_defense':(4,[(0,10),(1,15),(2,20)]), 'stun_reduction':(4,[(4,30)]),
    'critical':(5,[(0,5),(1,10),(2,15)]), 'heal_share':(6,[(0,30),(1,50)]),
    'purify':(6,[(2,1800),(3,1200)]), 'hp_drain':(7,[(0,25),(1,50)]),
    'tp_drain':(7,[(2,25),(3,50)]), 'mana_share':(8,[(0,5)]),
    'haste':(9,[(0,5),(4,15)]), 'memory':(9,[(1,20),(2,30)])
}
for spirit,nodes in enumerate(ADDITIONS):
    for index,(_,tier,value,*_) in enumerate(nodes,len(BASE_LEVELS[spirit])):
        assert TIERS[tier][0]==spirit
        TIERS[tier][1].append((index,value))
for spirit,tiers in TIERS.values():
    tiers.sort(key=lambda pair:LEVELS[spirit][pair[0]])


def faculty_id(spirit,index):
    assert 0<=spirit<10 and 0<=index<12
    return 128+spirit*8+index if index<8 else 208+spirit*4+index-8


assert len({faculty_id(s,i) for s in range(10) for i in range(12)})==120
