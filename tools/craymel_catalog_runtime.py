"""Catalog copy for the implemented Craymel battle faculties."""
from craymel_milestones import LEVELS, ADDITIONS


def update_faculties(rows,node):
    spirits={r['name'][1]:r for r in rows if r['kind']==0}
    sylph=spirits['Sylph']
    sylph['nodes']=sylph['nodes'][:3]+[
        node(level,(f'Esquive {chance}%',f'Dodge {chance}%'),
             ('Esquive parfaite','Perfect dodge'),
             (f'{chance} % de chance d’esquiver entièrement un coup : aucun dégât, interruption ou effet néfaste.',
              f'{chance}% chance to evade an entire hit: no damage, interruption or harmful effect.'),lane=1)
        for level,chance in ((15,5),(30,10))]
    n=spirits['Undine']['nodes'][5]
    n['description']=('Le soin excédentaire forme un bouclier, limité à 15 % des PV max, pendant 10 s.',
                      'Excess healing creates a shield capped at 15% of maximum HP for 10s.')
    n['detail']=('','')
    n=spirits['Rem']['nodes'][5]
    n['description']=('Un soin sur un allié sous 25 % de PV lui accorde 50 % de réduction des dégâts pendant 5 s. Une fois par combat pour chaque mage.',
                      'Healing an ally below 25% HP grants 50% damage reduction for 5s. Once per battle for each mage.')
    n['detail']=('','')
    n=spirits['Sekundes']['nodes'][3];n['required']=20
    n['description']=('Chaque répétition du même sort terminé réduit l’incantation suivante de 5 %, jusqu’à 15 %. Changer de sort réinitialise le bonus.',
                      'Each repetition of the same completed spell reduces the next cast by 5%, up to 15%. Changing spells resets this bonus.')
    n['detail']=('','')
    n=spirits['Maxwell']['nodes'][4];n['required']=30
    n['description']=('Le premier impact magique attire les petits ennemis au sol vers la cible touchée. Recharge : 10 s.',
                      'The first magic impact pulls nearby small grounded enemies toward the target. Cooldown: 10s.')
    n['detail']=('','')
    for r in spirits.values():
        for level,_,_,lane,title,label,description in ADDITIONS[r['key']]:
            r['nodes'].append(node(level,label,title,description,lane=lane))
        assert tuple(n['required'] for n in r['nodes'])==LEVELS[r['key']],r['name']
        for n in r['nodes']:n['implemented']=True
    from craymel_faculty_names import rename_faculties
    rename_faculties(rows)
