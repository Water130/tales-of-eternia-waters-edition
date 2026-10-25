"""Playable fighter chain milestones; stable saved IDs independent of order."""
def extend_fighters(rows, node):
    physical={r['key']:r for r in rows if r['kind']==1}
    for key in (0,1,4):
        n=physical[key]['nodes'][0]
        n.update(implemented=True,preference={0:151,1:152,4:153}[key])
        n['label']=('2 artes de base','2 basic artes')
    physical[4]['nodes']=[n for n in physical[4]['nodes'] if n['required']]
    for key in (0,1):
        physical[key]['nodes'].append(node(30,('2 arcanes','2 arcanes'),('Double arcane','Double Arcane'),
            ('Permet deux arcanes successifs de cette famille. Pour mêler les familles, les deux maîtrises et facultés sont nécessaires.',
             'Chain two arcane artes from this family. Mixing families requires both masteries and both faculties.'),
            implemented=True,preference=148+key,lane=2))
    for key,first in ((2,142),(3,144),(6,146)):
        r=physical[key]
        r['nodes']=[n for n in r['nodes'] if n['implemented']]
        for level,count in ((15,5),(30,6)):
            r['nodes'].append(node(level,(f'{count} artes',f'{count} artes'),
                ('Enchaînements mixtes','Mixed Chains') if key==6 else ('Chaînes prolongées','Extended Chains'),
                ((f'Enchaîne jusqu’à {count} artes de Poing et de Pied. Les deux maîtrises doivent atteindre ce niveau.' if key==6 else
                  f'Enchaîne jusqu’à {count} artes de cette famille.')+' Respecte les positions au sol et en l’air.',
                 (f'Chain up to {count} Punch and Kick artes. Both masteries must reach this level.' if key==6 else
                  f'Chain up to {count} artes from this family.')+' Grounded and airborne requirements still apply.'),
                implemented=True,preference=first+(level==30)))
    physical[5]['nodes'].append(node(30,('Soin ininterrompu','Unbroken casting'),('Soin inébranlable','Steadfast Healer'),
        ('Les coups n’interrompent plus Guérisseur, Désintoxication et Renaissance pendant leur incantation. Les dégâts et altérations restent subis.',
         'Hits no longer interrupt Healer, Detoxify or Life while casting. Damage and status ailments still apply.'),
        implemented=True,preference=150,lane=3))
