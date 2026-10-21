"""Private mastery-menu content. Preview nodes NEVER enable gameplay effects.

Only implemented spell-usage bonuses and Farah Energy faculties are actionable.
Unknown Craymel text is masked before titles, requirements or descriptions draw.
"""
import json
from pathlib import Path


def node(level, label, title, description, detail='', *, implemented=False, lane=0):
    def pair(v): return v if isinstance(v, tuple) else (v, v)
    return dict(required=level, label=pair(label), title=pair(title),
                description=pair(description), detail=pair(detail), implemented=implemented, lane=lane)


def catalog():
    rows = []
    def row(kind, key, mask, name, nodes):
        rows.append(dict(kind=kind, key=key, mask=mask, name=name, nodes=nodes))
    # Native mastery fields, corroborated with the status numeric renderer.
    for key, name in [(0, ('Tranchant','Slash')), (1, ('Estoc','Thrust'))]:
        row(1,key,1,name,[node(10,('Double','Double'),('Double technique','Double technique'),
            ('Enchaîner deux artes basiques de cette famille.','Chain two basic artes from this family.'))])
    row(1,4,1,('Tranchant + Estoc','Slash + Thrust'),[
        node(10,('Mixte','Mixed'),('Double technique mixte','Mixed double technique'),
             ('Tranchant ET Estoc niveau 10 : deux artes basiques mixtes.',
              'Slash AND Thrust level 10: chain two basic artes across families.')),
        node(0,('Chaînes','Chains'),('Enchaînements avancés','Advanced chains'),
             ('Base > base > arcane, puis des chaînes plus libres au maximum.',
              'Base > base > arcane, then more flexible chains at maximum level.'),
             ('Paliers précis encore à définir.','Exact unlock requirements are still being designed.'))])
    for key,name in [(2,('Poing','Punch')),(3,('Pied','Kick'))]:
        row(1,key,2,name,[node(30,('Chaînes','Chains'),('Chaînes prolongées','Extended chains'),
            ('Objectif : cinq ou six artes, en respectant les contraintes aériennes.',
             'Goal: five or six artes while preserving airborne requirements.'),
            ('La longueur exacte reste à définir.','The exact chain length is still being designed.'))])
    row(1,6,2,('Poing + Pied','Punch + Kick'),[
        node(30,('5–6 artes','5–6 artes'),('Enchaînements mixtes','Mixed chains'),
             ('Prolonge les enchaînements mêlant Poing et Pied jusqu’à cinq ou six artes.',
              'Extends mixed Punch and Kick chains to five or six artes.'),
             ('',''))])
    row(1,5,2,('Énergie','Energy'),[
        node(10,'40%',('Guérisseur renforcé','Improved Healer'),
             ('Guérisseur rend 40 % des PV max de la cible au lieu de 30 %.',
              'Healer restores 40% of the target’s max HP instead of 30%.'),
             ('Énergie = minimum de Poing et Pied. Combat et menu.',
              'Energy = the lower of Punch and Kick. Battle and menus.'),implemented=True),
        node(20,('+1 cible','+1 ally'),('Guérisseur partagé','Shared Healer'),
             ('Un autre allié vivant reçoit 50 % du soin principal théorique.',
              'Another living ally receives 50% of the theoretical primary heal.'),
             ('Priorité au plus faible pourcentage de PV. Aucun coût supplémentaire.',
              'Lowest HP ratio first. No additional TP cost.'),implemented=True),
        node(30,('+2 cibles','+2 allies'),('Guérisseur étendu','Extended Healer'),
             ('Un troisième allié reçoit 25 % du soin principal théorique.',
              'A third ally receives 25% of the theoretical primary heal.'),
             ('Cibles distinctes, PV manquants comme plafond. Partage à 50 % conservé.',
              'Distinct targets; capped at missing HP. The 50% share is retained.'),implemented=True),
        node(15,('Soin 25%','Heal 25%'),('Désintoxication curative','Healing Detoxify'),
             ('Désintoxication rend aussi 25 % des PV max de sa cible vivante.',
              'Detoxify also restores 25% of its living target’s max HP.'),
             ('Ne réanime pas. Coût natif de 4 TP conservé.',
              'Does not revive. Native 4 TP cost retained.'),implemented=True,lane=1),
        node(25,('Purifier','Purify'),('Désintoxication étendue','Extended Detoxify'),
             ('Applique la purification native de Rétablissement.',
              'Applies the native purification of Recover.'),
             ('Le KO et les états spéciaux exclus de Rétablissement restent inchangés.',
              'KO and special states outside Recover remain unchanged.'),implemented=True,lane=1),
        node(30,('Vie 35%','Life 35%'),('Renaissance renforcée','Improved Life'),
             ('Renaissance réanime avec 35 % des PV max au lieu des 20 % natifs.',
              'Life revives with 35% of max HP instead of the native 20%.'),
             ('Coût natif de 50 TP. Combat et menu.',
              'Native 50 TP cost. Battle and menus.'),implemented=True,lane=2),
    ])
    for char,name,titles,descs in [
        (5,('Artillerie','Artillery'),['Préparation','Garde','Économie','Alternance','Cadence'],[
            'Tir préparé plus vite après une attaque normale réussie.',
            'Reprendre la garde plus tôt après un tir.',
            'Une commande de tir réussie réduit le coût de la prochaine technique.',
            'Alterner deux éléments de tir renforce le second.',
            'Trois techniques différentes préparent une accélération temporaire.']),
        (4,('Ingéniosité','Ingenuity'),['Duo','Repli','Rebond','Exploitation','Trio'],[
            'Enchaîner deux gadgets simples différents.',
            'Reprendre le déplacement plus tôt après un lancer.',
            'Un marteau rebondit vers une seconde cible avec des dégâts réduits.',
            'Dégâts des gadgets renforcés contre une cible affectée par un malus.',
            'Enchaîner trois gadgets simples différents ; dernier moins coûteux.'])]:
        en = (['Faster shot preparation after a successful normal attack.',
               'Guard sooner after firing.', 'A successful shot command discounts the next technique.',
               'Alternating shot elements strengthens the second.',
               'Three different techniques prepare a temporary speed boost.'] if char==5 else
              ['Chain two different simple gadgets.', 'Move sooner after a throw.',
               'A hammer rebounds toward a second enemy with reduced damage.',
               'Gadgets deal more damage to enemies affected by an ailment.',
               'Chain three different simple gadgets; the last costs less.'])
        row(3,0,1<<char,name,[node(l,(t,f'Lv {l}'),(t,f'{name[1]} {l}'),(d,e),
            ('Valeurs et progression encore en préparation.','Values and progression are still being designed.'))
            for l,t,d,e in zip((10,15,20,25,30),titles,descs,en)])
    # Native summon order is derived from the audited arte descriptor IDs.
    native = json.loads((Path(__file__).resolve().parents[1]/'audit/build-25190541/artes_native.json').read_text(encoding='utf-8'))
    summon = [r for r in native if 43 <= r['id'] <= 52]
    by_name = {r['name'].lower().replace('★','').strip(): r['id']-43 for r in summon}
    def spirit(name, fr, nodes):
        matches=[i for n,i in by_name.items() if name.lower() in n]
        assert len(matches)==1, (name,by_name)
        row(0,matches[0],12,(fr,name),nodes)
    spirit('Undine','Ondine',[
        node(10,'-10% TP',('Économie de mana','Mana economy'),('Coût des sorts en TP réduit de 10 %.','Spell TP costs reduced by 10%.')),
        node(20,('-15% TP','-15% TP'),('Économie et soin préparé','Economy and prepared healing'),
             ('Coûts -15 %. Après un sort offensif, le prochain soin gagne 10 %.','Costs -15%. An offensive spell strengthens the next heal by 10%.')),
        node(25,('Soin +15%','Heal +15%'),('Soin préparé','Prepared healing'),('Le prochain soin après un sort offensif gagne 15 %.','The next heal after an offensive spell gains 15%.')),
        node(30,('Bouclier','Shield'),('Économie et soin protecteur','Economy and protective healing'),
             ('Coûts -20 %. Le soin excédentaire peut créer un bouclier limité.','Costs -20%. Excess healing can create a limited shield.'),
             ('Plafond et durée du bouclier à définir.','Shield cap and duration are still being designed.'))])
    spirit('Sylph','Sylphe',[
        node(l,f'-{p}%',('Récupération après lancement','Post-cast recovery'),
             (f'Récupération après lancement réduite de {p} %.',f'Post-cast recovery reduced by {p}%.'),
             (('Au niveau 30 : déplacement en cast si le rendu est convaincant.','At level 30: movement during casting, subject to visual approval.') if l==30 else ''))
        for l,p in [(10,10),(20,20),(30,30)]])
    spirit('Efreet','Efreet',[
        node(10,'+5%',('Puissance magique','Magic power'),('Dégâts des sorts offensifs +5 %.','Offensive spell damage +5%.')),
        node(20,'+10%',('Puissance et ferveur','Power and fervor'),('Dégâts +10 %. Sous 50 % de PV : bonus conditionnel de 10 %.','Damage +10%. Below 50% HP: an additional conditional 10% bonus.')),
        node(25,('Ferveur','Fervor'),('Ferveur magique','Magic fervor'),('Sous 50 % de PV : bonus conditionnel porté à 15 %.','Below 50% HP: the conditional bonus becomes 15%.')),
        node(30,'+15%',('Puissance magique','Magic power'),('Dégâts des sorts offensifs +15 %.','Offensive spell damage +15%.'))])
    spirit('Gnome','Gnome',[
        node(10,'-15%',('Cast protégé','Protected casting'),('Dégâts reçus pendant l’incantation réduits de 15 %.','Damage received while casting reduced by 15%.')),
        node(20,('Garde 20s','Ward 20s'),('Garde légère','Light ward'),('Dégâts -20 % en cast. Protection légère 5 s, recharge 20 s.','Casting damage -20%. Light interruption ward for 5s, cooldown 20s.')),
        node(25,('Garde 15s','Ward 15s'),('Garde légère','Light ward'),('Protection légère de 5 s, recharge réduite à 15 s.','Light interruption ward for 5s, cooldown reduced to 15s.')),
        node(30,('Garde 10s','Ward 10s'),('Garde renforcée','Improved ward'),('Dégâts -25 % en cast. Garde légère : 5 s, recharge 10 s.','Casting damage -25%. Light ward: 5s, cooldown 10s.'),
             ('Gnome + Celsius 30 : protection complète 5 s, recharge 20 s.','Gnome + Celsius 30: full interruption ward for 5s, cooldown 20s.'))])
    spirit('Celsius','Celsius',[
        node(10,'-10%',('Résistance magique','Magic resistance'),('Dégâts magiques reçus réduits de 10 %.','Magic damage received reduced by 10%.')),
        node(20,('Limpide','Clear'),('Esprit limpide','Clear spirit'),('Résistance magique 15 %. Pénalité d’Entrave mentale divisée par deux.','Magic resistance 15%. Halve the Casting Delay penalty.')),
        node(25,('Lucidité','Lucidity'),('Lucidité','Lucidity'),('Durée d’Étourdissement réduite de 30 %, sans immunité.','Stun duration reduced by 30%, without immunity.')),
        node(30,('Stase','Stasis'),('Stase de survie','Survival stasis'),('Une fois par combat : coup fatal > 1 PV, stase protectrice de 2 s.','Once per battle: a fatal hit leaves 1 HP and grants 2s of protective stasis.'),
             ('Résistance magique 20 %. Aucune action en stase ; soins possibles.','Magic resistance 20%. No actions during stasis; allies can heal you.'))])
    spirit('Volt','Volt',[
        node(l,f'{p}%',('Critiques magiques','Magic criticals'),
             (f'{p} % de critiques magiques, pour +50 % de dégâts par sort.',f'{p}% magic critical chance, for +50% damage per cast.'),
             (('5 % de chance de lancer un sort instantanément.','5% chance to cast a spell instantly.') if l==30 else ''))
        for l,p in [(10,5),(20,10),(30,15)]])
    spirit('Rem','Rem',[
        node(10,('Soin lié','Linked heal'),('Soin solidaire','Shared healing'),('Un second allié blessé reçoit 30 % du soin monocible.','A second wounded ally receives 30% of a single-target heal.')),
        node(15,'50%',('Soin solidaire','Shared healing'),('Le soin secondaire passe à 50 % du montant initial.','The secondary heal becomes 50% of the initial amount.')),
        node(20,('Purifier','Purify'),('Guérison purifiante','Purifying heal'),('Un soin retire aussi une altération compatible, recharge 30 s.','A heal also removes a compatible ailment, cooldown 30s.')),
        node(25,('Purifier+','Purify+'),('Guérison purifiante','Purifying heal'),('Recharge de la purification réduite à 20 s.','Purification cooldown reduced to 20s.')),
        node(30,('Régén.','Regen.'),('Protection et régénération','Protection and regeneration'),('Après un soin : 25 % du montant initial régénéré sur 5 s.','After healing: regenerate 25% of the initial amount over 5s.'),
             ('Protection d’un allié en danger : une fois par combat.','Protect an ally in danger once per battle.'))])
    spirit('Shadow','Shadow',[
        node(l,f'{p}%',('Absorption de PV' if l<20 else 'Absorption de TP','HP drain' if l<20 else 'TP drain'),
             ((f'Rend {p} % des dégâts infligés en PV après un sort qui touche.',f'Restore {p}% of damage dealt as HP after a spell hits.') if l<20 else
              (f'Vaincre un ennemi par magie rend {p} % des dégâts en TP.',f'Defeating an enemy with magic restores {p}% of damage as TP.')))
        for l,p in [(10,2.5),(15,5),(20,2.5),(25,5)]]+[
        node(30,('Lien vital','Life link'),('Lien vital','Life link'),('Soigne l’allié au plus faible % de PV pour 5 % des dégâts du mage.','Heal the ally with the lowest HP ratio for 5% of the mage’s damage.'))])
    spirit('Sekundes','Sekundes',[
        node(5,'-5%',('Don de célérité','Gift of haste'),('Durée d’incantation réduite de 5 %.','Casting time reduced by 5%.')),
        node(10,('Mémoire','Memory'),('Mémoire d’incantation','Casting memory'),('Conserve 20 % d’une incantation annulée.','Retain 20% of a cancelled cast.')),
        node(15,('Mémoire+','Memory+'),('Mémoire d’incantation','Casting memory'),('Conserve 30 % d’une incantation annulée.','Retain 30% of a cancelled cast.')),
        node(0,('Répétition','Repeat'),('Répétition accélérée','Faster repetition'),('Répéter le même sort terminé accélère son incantation.','Repeating the same completed spell speeds up its cast.'),('Niveaux, valeurs et remise à zéro à définir.','Levels, values and reset conditions are still being designed.')),
        node(30,'-15%',('Don de célérité','Gift of haste'),('Durée d’incantation réduite de 15 %.','Casting time reduced by 15%.'))])
    spirit('Maxwell','Maxwell',[
        node(5,('Solidarité','Sharing'),('Mana solidaire','Shared mana'),('Tous les 50 TP dépensés en sorts : +5 TP aux autres alliés vivants.','Every 50 TP spent on spells restores 5 TP to other living allies.')),
        node(10,('Rempart','Bulwark'),('Rempart de mana','Mana bulwark'),('Absorbe 25 % des dégâts : 1 TP pour 5 PV protégés.','Absorb 25% of damage, spending 1 TP per 5 HP protected.'),('Protection inactive à 25 % des TP maximum ou moins.','Protection stops at 25% of maximum TP or less.')),
        node(20,('Partage','Sharing'),('Partage des ressources','Resource sharing'),('Un objet de soin partage 25 % des PV ou TP réellement récupérés.','A recovery item shares 25% of the HP or TP actually restored.'),('Le bénéficiaire initial conserve tout son gain.','The original recipient keeps the full recovery.')),
        node(30,('Souffle','Second wind'),('Second souffle arcanique','Arcane second wind'),('Un sort fait passer sous le seuil de 25 % de TP : restaure 25 % du max.','A spell crosses the 25% TP threshold: restore 25% of maximum TP.'),('Une seule fois par combat.','Once per battle.')),
        node(0,('Singularité','Singularity'),('Singularité','Singularity'),('Un impact magique attire brièvement les petits ennemis proches.','A magic impact briefly pulls nearby small enemies together.'),('Niveau, déclencheur, force et recharge à définir.','Level, trigger, strength and cooldown are still being designed.'))])
    for r in native:
        aid=r['id']
        if aid not in list(range(54,102))+[112,113]: continue
        if aid in (63,64,65,66):
            nodes=[node(v,f'+{i}',('Cibles supplémentaires','Additional targets'),
                (f'Le buff touche jusqu’à {i} allié(s) supplémentaire(s) sans ce bonus.',f'The buff reaches up to {i} additional allies without this buff.'),
                ('Comportement et durée natifs conservés.','Native behavior and duration are preserved.'),implemented=True)
                for i,v in enumerate((100,250,500),1)]
        elif aid < 70:
            nodes=[node(0,('Natif','Native'),('Soin ou soutien natif','Native healing or support'),
                ('Utilisations suivies séparément pour ce personnage. Aucun bonus offensif.',
                 'Casts are tracked separately for this character. No offensive bonus.'),
                ('Ce sort conserve ses effets natifs ; pas de palier par utilisation.',
                 'This spell keeps its native effects; no usage milestone.'))]
        else:
            nodes=[node(v,f'+{v//25}%',('Maîtrise offensive','Offensive mastery'),
                ('+1 % de dégâts tous les 25 lancements ; plafond +25 %.','+1% damage every 25 casts, capped at +25%.'),
                ('L’interrupteur concerne toute la maîtrise de ce sort.','The switch applies to this spell’s entire mastery.'),implemented=True)
                for v in (25,125,250,500,625)]
        row(2,aid,12,(r['name_fr'],r['name']),nodes)
    separate_paths(rows)
    # Descriptions explain the faculty, not storage, menu or unchanged costs.
    for r in rows:
        for n in r['nodes']:
            if r['kind']!=0:n['detail']=('','')
    energy=next(r for r in rows if r['kind']==1 and r['key']==5)
    energy['nodes'][1]['description']=(
        'Guérisseur soigne une deuxième cible vivante à hauteur de 50 % du soin principal. Priorité au plus faible pourcentage de PV.',
        'Healer also heals a second living ally for 50% of the primary heal. Lowest HP ratio first.')
    energy['nodes'][2]['description']=(
        'Guérisseur soigne une troisième cible à hauteur de 25 % du soin principal, en plus de la deuxième cible à 50 %.',
        'Healer also heals a third ally for 25% of the primary heal, retaining the second ally’s 50% heal.')
    energy['nodes'][4]['description']=(
        'Désintoxication retire désormais les mêmes altérations que Rétablissement. Le KO et les états spéciaux non purifiables sont exclus.',
        'Detoxify now removes the same ailments as Recover. KO and special states that cannot be cleansed are excluded.')
    bubble_boosts(rows)
    assert all(len(r['nodes'])<=12 for r in rows)
    return rows


def bubble_boosts(rows):
    """Second card line describes the benefit; requirements remain below the tree."""
    boosts={
        'Double technique':('2 artes basiques','2 basic artes'),
        'Double technique mixte':('2 bases mixtes','2 mixed basics'),
        'Enchaînements avancés':('Chaînes libres','Flexible chains'),
        'Chaînes prolongées':('5–6 artes','5–6 artes'),
        'Guérisseur renforcé':('40% PV max','40% max HP'),
        'Guérisseur partagé':('+1 cible à 50%','+1 ally at 50%'),
        'Guérisseur étendu':('+1 cible à 25%','+1 ally at 25%'),
        'Désintoxication étendue':('Purification','Purification'),
        'Soin protecteur':('Excès en bouclier','Overheal shield'),
        'Mobilité en incantation':('Cast en mouvement','Moving cast'),
        'Esprit limpide':('Pénalité ÷2','Penalty ÷2'),
        'Lucidité':('-30% étourdi','Stun -30%'),
        'Stase de survie':('1 PV / 2 s','1 HP / 2s'),
        'Garde complète':('5 s / recharge 20 s','5s / cooldown 20s'),
        'Éclair de génie':('5% instantané','5% instant cast'),
        'Régénération':('25% sur 5 s','25% over 5s'),
        'Protection salvatrice':('1 fois / combat','Once per battle'),
        'Lien vital':('5% soin allié','5% ally heal'),
        'Répétition accélérée':('Cast accéléré','Faster cast'),
        'Mana solidaire':('+5 TP / 50 TP','+5 TP / 50 TP'),
        'Rempart de mana':('25% absorbés','25% absorbed'),
        'Partage des ressources':('Partage de 25%','Share 25%'),
        'Second souffle arcanique':('+25% TP max','+25% max TP'),
        'Singularité':('Attire les ennemis','Pulls enemies'),
        'Soin ou soutien natif':('Effet natif','Native effect'),
    }
    for r in rows:
        for n in r['nodes']:
            title=n['title'][0]
            if title in boosts:n['label']=boosts[title]
            if title=='Soin solidaire':
                p=30 if n['required']==10 else 50
                n['label']=(f'Partage de {p}%',f'Share {p}%')
            elif title=='Guérison purifiante':
                s=30 if n['required']==20 else 20
                n['label']=(f'Recharge {s} s',f'Cooldown {s}s')
            elif title=='Mémoire d’incantation':
                p=20 if n['required']==10 else 30
                n['label']=(f'{p}% conservés',f'{p}% retained')
            elif title=='Cibles supplémentaires':
                p={100:1,250:2,500:3}[n['required']]
                n['label']=(f'+{p} cible'+('s' if p>1 else ''),f'+{p} '+('allies' if p>1 else 'ally'))
        if r['kind']==3:
            english=(['Preparation','Guard','Economy','Alternation','Cadence'] if r['mask']==32 else
                     ['Duo','Retreat','Rebound','Exploitation','Trio'])
            benefits=([('Préparation rapide','Faster preparation'),('Garde anticipée','Earlier guard'),
                       ('Coût du tir réduit','Lower shot cost'),('Dégâts renforcés','Stronger damage'),
                       ('Cadence accélérée','Faster cadence')] if r['mask']==32 else
                      [('2 gadgets','2 gadgets'),('Déplacement rapide','Earlier movement'),
                       ('+1 cible','+1 target'),('Bonus contre malus','Ailment damage'),('3 gadgets','3 gadgets')])
            for n,en,benefit in zip(r['nodes'],english,benefits):
                n['title']=(n['title'][0],en);n['label']=benefit


def separate_paths(rows):
    """Separate effects formerly bundled in level cards; no new gameplay unlocks."""
    spirits={r['name'][1]:r for r in rows if r['kind']==0}
    def series(lane, levels, values, title, description, label):
        return [node(l,(label[0].format(v),label[1].format(v)),title,
                     (description[0].format(v),description[1].format(v)),lane=lane)
                for l,v in zip(levels,values)]
    r=spirits['Undine']; old=r['nodes']
    r['nodes']=series(0,[10,20,30],[10,15,20],('Économie de mana','Mana economy'),
        ('Coût des sorts en TP réduit de {} %.','Spell TP costs reduced by {}%.'),('-{}% TP','-{}% TP'))
    r['nodes']+=series(1,[20,25],[10,15],('Soin préparé','Prepared healing'),
        ('Après un sort offensif, le prochain soin gagne {} %.','After an offensive spell, the next heal gains {}%.'),('Soin +{}%','Heal +{}%'))
    r['nodes'].append(node(30,('Bouclier','Shield'),('Soin protecteur','Protective healing'),
        ('Le soin excédentaire peut créer un bouclier limité.','Excess healing can create a limited shield.'),old[-1]['detail'],lane=2))
    r=spirits['Sylph'];r['nodes'][-1]['detail']=('','')
    r['nodes'].append(node(30,('Mobilité','Mobility'),('Mobilité en incantation','Casting movement'),
        ('Déplacement pendant l’incantation, sous réserve d’un rendu convaincant.',
         'Movement while casting, subject to convincing animation.'),lane=1))
    r=spirits['Efreet']
    r['nodes']=series(0,[10,20,30],[5,10,15],('Puissance magique','Magic power'),
        ('Dégâts des sorts offensifs +{} %.','Offensive spell damage +{}%.'),('+{}%','+{}%'))
    r['nodes']+=series(1,[20,25],[10,15],('Ferveur magique','Magic fervor'),
        ('Sous 50 % de PV : bonus conditionnel de {} %.','Below 50% HP: additional conditional {}% damage.'),('Ferveur {}%','Fervor {}%'))
    r=spirits['Gnome']
    r['nodes']=series(0,[10,20,30],[15,20,25],('Cast protégé','Protected casting'),
        ('Dégâts reçus pendant l’incantation réduits de {} %.','Damage received while casting reduced by {}%.'),('-{}%','-{}%'))
    r['nodes']+=series(1,[20,25,30],[20,15,10],('Garde légère','Light ward'),
        ('Protection légère contre les interruptions pendant 5 s ; recharge {} s.',
         'Light interruption protection for 5s; cooldown {}s.'),('Garde {}s','Ward {}s'))
    r['nodes'].append(node(30,('Synergie','Synergy'),('Garde complète','Complete ward'),
        ('Gnome ET Celsius niveau 30 : protection complète 5 s, recharge 20 s.',
         'Gnome AND Celsius level 30: full interruption protection for 5s, cooldown 20s.'),
        ('La garde légère garde la priorité.','The light ward has priority.'),lane=2))
    r=spirits['Celsius'];old=r['nodes']
    r['nodes']=series(0,[10,20,30],[10,15,20],('Résistance magique','Magic resistance'),
        ('Dégâts magiques reçus réduits de {} %.','Magic damage received reduced by {}%.'),('-{}%','-{}%'))
    r['nodes'] += [node(20,('Limpide','Clear'),('Esprit limpide','Clear spirit'),
        ('Pénalité d’Entrave mentale divisée par deux.','Halve the Casting Delay penalty.'),lane=1)]
    old[2]['lane']=1;r['nodes'].append(old[2])
    old[3]['lane']=2;old[3]['detail']=('Aucune action en stase ; soins possibles.','No actions during stasis; allies can heal you.')
    r['nodes'].append(old[3])
    r=spirits['Volt'];r['nodes'][-1]['detail']=('','')
    r['nodes'].append(node(30,('Instantané','Instant'),('Éclair de génie','Flash of insight'),
        ('5 % de chance qu’un sort se lance instantanément.','5% chance for a spell to cast instantly.'),lane=1))
    r=spirits['Rem'];r['nodes'][2]['lane']=r['nodes'][3]['lane']=1
    r['nodes'][4]['lane']=2;r['nodes'][4]['title']=('Régénération','Regeneration');r['nodes'][4]['detail']=('','')
    r['nodes'].append(node(30,('Protection','Protection'),('Protection salvatrice','Lifesaving protection'),
        ('Protège un allié en danger après un soin, une fois par combat.',
         'Protect an ally in danger after a heal, once per battle.'),
        ('Seuil, durée et intensité encore à définir.','Threshold, duration and strength are still being designed.'),lane=3))
    r=spirits['Shadow']
    for i,n in enumerate(r['nodes']):n['lane']=0 if i<2 else 1 if i<4 else 2
    r=spirits['Sekundes']
    for i,n in enumerate(r['nodes']):n['lane']=0 if i in (0,4) else 1 if i in (1,2) else 2
    r=spirits['Maxwell']
    for i,n in enumerate(r['nodes']):n['lane']=[0,1,0,1,2][i]
