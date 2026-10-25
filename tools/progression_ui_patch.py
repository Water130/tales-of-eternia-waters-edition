"""Private native UI additions: option help, Farah Energy and arte families."""
import struct
import textwrap
from mod_settings_patch import FEATURES, CATEGORIES

# One entry per stable settings flag, followed by Reset and Keyboard.
HELP = [
    ("La caméra suit la position des alliés et des ennemis pour adapter le cadrage pendant les combats.\nDésactivé : cadrage du jeu d'origine.",
     "The camera adjusts the battle framing to the positions of allies and enemies.\nOff: use the game's original camera."),
    ("Rend davantage de PT aux alliés après une victoire. Le taux de récupération dépend de la difficulté :\nNormal : 8 %.\nDifficile : 9 %.\nExtrême : 10 %.\nInconnue : 13 %.\nLes bonus et la récupération minimale du jeu s'ajoutent selon leurs règles habituelles.\nDésactivé : récupération du jeu d'origine.",
     "Allies recover more TP after winning a battle. The recovery rate depends on difficulty:\nNormal: 8%.\nHard: 9%.\nExtreme: 10%.\nUnknown: 13%.\nThe game's bonuses and minimum recovery still apply under their usual rules.\nOff: use the original TP recovery."),
    ('Chaque attaque normale qui touche un ennemi rend des PT à son utilisateur : 2 pour Keele ou Meredy, 1 pour les autres.\nLes attaques aériennes et celles de Quickie comptent aussi. Les artes ne donnent pas ce bonus.',
     "Each normal attack that hits an enemy restores TP to its user: 2 for Keele or Meredy, 1 for other characters.\nAerial attacks and Quickie's attacks also count. Artes do not grant this bonus."),
    ('Les chiffres des dégâts infligés prennent la couleur de leur élément : eau, feu, vent, etc. Les dégâts neutres sont blancs. Les soins utilisent un dégradé vert et les dégâts reçus par les alliés restent distincts.\nCe réglage change les couleurs, pas les dégâts.',
     'Damage dealt uses the color of its element: water, fire, wind, and so on. Neutral damage is white. Healing uses a green gradient, and damage received by allies stays distinct.\nThis changes colors, not damage amounts.'),
    ("Remplace l'affichage des alliés en combat par celui de Water's Edition : chiffres et barres de PV/PT, petits personnages et vitalité des Craymel.\nDésactivé : interface de combat du jeu d'origine.",
     "Uses the Water's Edition party display in battle: HP/TP numbers and bars, small character sprites, and Craymel vitality.\nOff: use the game's original battle interface."),
    ("Une barre sous chaque lanceur indique l'avancement de son incantation. Elle se remplit jusqu'à ce que le sort soit prêt.\nMasquer la barre ne change pas le temps nécessaire pour lancer le sort.",
     'A bar below each caster shows how far their incantation has progressed. It fills until the spell is ready.\nHiding the bar does not change casting time.'),
    ('Affiche une barre indiquant le temps à attendre avant de pouvoir utiliser un autre objet en combat.\nCe réglage affiche le délai ; il ne le raccourcit pas.',
     'Shows a bar for the wait before another item can be used in battle.\nThis displays the cooldown; it does not shorten it.'),
    ("Une bulle vous prévient lorsqu'une saynète est disponible en exploration. Elle disparaît dans les menus et pendant les scènes.\nCette option affiche seulement la notification. Le raccourci pour lire la saynète se règle séparément.",
     'A small notice appears when a skit is available while exploring. It hides in menus and during scenes.\nThis option only shows the notice. The shortcut for playing a skit is a separate setting.'),
    ("Renforce les ennemis en Difficile, Extrême et Inconnue. Normal reste inchangé.\nPar rapport à leurs valeurs de base :\nDifficile : PV x1,5, défense x1,1.\nExtrême : PV x3, défense x1,2.\nInconnue : PV x5, défense x1,3.\nLes attaques à dégâts fixes suivent aussi des multiplicateurs de x1,1 / x1,2 / x1,5 respectivement.\nDésactivé : équilibrage du jeu d'origine.",
     "Makes enemies tougher on Hard, Extreme and Unknown. Normal is unchanged.\nRelative to their base values:\nHard: HP x1.5, defense x1.1.\nExtreme: HP x3, defense x1.2.\nUnknown: HP x5, defense x1.3.\nFixed-damage attacks also use multipliers of x1.1 / x1.2 / x1.5 respectively.\nOff: use the game's original balance."),
    ("Permet de préparer plusieurs invocations à la fois : plusieurs Craymel peuvent rester au MAX de vitalité.\nLancer un sort ne fait plus baisser une jauge déjà au MAX. Utiliser l'invocation consomme toujours sa vitalité.",
     'Lets you prepare several summons at once: more than one Craymel can stay at MAX vitality.\nCasting a spell no longer lowers a gauge that is already at MAX. Using the summon still consumes its vitality.'),
    ('Pendant une incantation, appuyez sur Garde pour interrompre la préparation du sort et vous protéger. Il faut une nouvelle pression sur la touche.\nUn sort déjà lancé continue normalement. Cette commande concerne le personnage contrôlé en manuel ou semi-auto.',
     'While casting, press Guard to stop preparing the spell and defend. This requires a new button press.\nA spell that has already been released continues normally. Applies to the character controlled in Manual or Semi-Auto.'),
    ("Pour faire sauter Keele ou Meredy, maintenez Garde et appuyez sur Haut. Haut seul ne fait plus sauter.\nCela évite les sauts involontaires. Les personnages contrôlés par l'IA gardent leurs commandes habituelles.",
     'To jump with Keele or Meredy, hold Guard and press Up. Up alone no longer makes them jump.\nThis helps avoid accidental jumps. AI-controlled characters keep their usual behavior.'),
    ("Active la progression des sorts et des Craymel, leurs facultés et les améliorations d'invocation. Consultez les pages Maîtrise pour voir les bonus et leurs conditions.",
     'Enables spell and Craymel progression, their faculties and summon improvements. Check the Mastery pages for bonuses and requirements.'),
    ("Pour faire sauter Reid ou Farah, maintenez Garde et appuyez sur Haut. Haut seul ne fait plus sauter.\nCe réglage est indépendant de celui des mages et ne change pas les personnages contrôlés par l'IA.",
     'To jump with Reid or Farah, hold Guard and press Up. Up alone no longer makes them jump.\nThis is separate from the mage jump setting and does not change AI-controlled characters.'),
    ("Ajoute la maîtrise Énergie à la fiche Stats de Farah. Son niveau est le plus bas des niveaux Poing et Pied, avec un maximum de 30.\nExemple : Poing 12 et Pied 10 donnent Énergie 10. Il n'y a pas d'EXP à gagner séparément pour cette barre.",
     "Adds Energy mastery to Farah's Stats page. Its level is the lower of Punch and Kick, up to level 30.\nExample: Punch 12 and Kick 10 give Energy 10. This gauge has no separate EXP to earn."),
    ("Dans Techniques, affiche la famille de chaque arte de Reid ou Farah près de son coût en PT : Tranchant, Estoc, Poing, Pied, Énergie ou une famille mixte.\nCela permet de retrouver sa branche dans Maîtrise. Ce libellé n'indique pas sa place dans un enchaînement.",
     "In the Artes menu, shows each Reid or Farah arte's family beside its TP cost: Slash, Thrust, Punch, Kick, Energy or a mixed family.\nUse it to find the matching Mastery branch. This label does not indicate its position in a combo."),
    ("En exploration, appuyez sur L2 / LT pour lire une saynète disponible.\nSi cette touche est déjà affectée à une autre action d'exploration, utilisez L2 + Select.\nLe raccourci fonctionne même si la notification des saynètes est désactivée. Il reste indisponible pendant les menus et les scènes.",
     'While exploring, press L2 / LT to play an available skit.\nIf that button is already assigned to another exploration action, use L2 + Select.\nThe shortcut works even when skit notifications are off. It is unavailable during menus and scenes.'),
    ('Active les facultés de Farah et sa maîtrise Énergie. Consultez les branches Poing, Pied, Poing + Pied et Énergie pour choisir vos bonus.',
     "Enables Farah's faculties and Energy mastery. Open Punch, Kick, Punch + Kick and Energy to choose your bonuses."),
    ("Permet d'obtenir un sort de fusion même si ses deux Craymel sont dans la même cage.\nLe mage reçoit les sorts du Craymel principal placé chez lui. Le second Craymel peut être chez Keele OU Meredy. Les deux doivent être recrutés et avoir les niveaux requis.\nEXEMPLE : ACUITÉ\nPlacez Efreet niveau 5 chez Keele. Avec Ondine niveau 7 dans l'une ou l'autre cage, Keele peut obtenir Acuité. Placez Efreet chez Meredy pour lui donner accès au sort à la place.\nDésactivé : les deux Craymel doivent être dans des cages opposées, comme dans le jeu d'origine. Leurs niveaux et les compteurs de sorts sont conservés.",
     'Lets you obtain a Fringe spell even when both required Craymels are in the same cage.\nThe mage gets the spells of the primary Craymel assigned to them. The second Craymel may be with EITHER Keele or Meredy. Both must be recruited and meet their required levels.\nEXAMPLE: SHARPNESS\nGive level 5 Efreet to Keele. With level 7 Undine in either cage, Keele can obtain Sharpness. Move Efreet to Meredy to give her access instead.\nOff: the two Craymels must be in opposite cages, as in the original game. Their levels and spell counters are kept.'),
    ("Plus un Craymel monte de niveau, plus son invocation gagne en dégâts et en portée. Le bonus de dégâts est indiqué sous sa bulle dans l'arbre de Maîtrise.\nDésactivé : puissance et portée du jeu d'origine.",
     'As a Craymel levels up, its summon gains damage and reach. The damage bonus is shown below its root bubble in the Mastery tree.\nOff: use the original summon power and reach.'),
    ("Le combat continue pendant les effets des sorts, au lieu de se figer pour leur présentation.\nCela ne raccourcit pas l'incantation du mage. L'option Sorts simultanés règle séparément si plusieurs effets peuvent se jouer ensemble.\nDésactivé : pauses des sorts du jeu d'origine.",
     "Battle continues during spell effects instead of freezing for their presentation.\nThis does not shorten the mage's casting time. Concurrent spells separately controls whether several effects can play together.\nOff: use the game's original spell pauses."),
    ("Deux sorts différents peuvent produire leurs effets en même temps, au lieu d'attendre que le premier se termine.\nDeux exemplaires du même effet, certaines invocations et les effets incompatibles attendent encore leur tour.\nDésactivé : ordre de lancement du jeu d'origine.",
     "Two different spells can play their effects at the same time instead of waiting for the first to finish.\nTwo copies of the same effect, certain summons and incompatible effects still wait their turn.\nOff: use the game's original spell queue."),
    ("Les particules autour du mage pendant l'incantation prennent la couleur de l'élément du sort préparé.\nLes couleurs des chiffres de dégâts se règlent séparément.\nDésactivé : couleurs d'incantation du jeu d'origine.",
     "Particles around a mage during casting use the element color of the spell being prepared.\nDamage-number colors are a separate setting.\nOff: use the game's original casting colors."),
    ("Ajoute deux pages de raccourcis d'artes, B et C, en plus de la page A. Chaque page possède six emplacements à configurer dans Techniques.\nDésactivé : seule la page A est utilisable. Vos affectations des pages B et C restent enregistrées.",
     'Adds two arte shortcut pages, B and C, alongside page A. Each page has six slots to configure in the Artes menu.\nOff: only page A can be used. Your saved assignments on pages B and C are kept.'),
    ("Pour choisir une invocation disponible, gardez la commande d'arte enfoncée jusqu'à la fin de l'incantation. Les conditions habituelles de l'invocation doivent être remplies.\nL1 permet de retenir un sort prêt avant de le libérer.\nDésactivé : commandes du jeu d'origine.",
     'To choose an available summon, keep the arte command held until casting finishes. The summon must meet its usual requirements.\nL1 lets you hold a ready spell before releasing it.\nOff: use the original controls.'),
    ("Pour transformer Geyser en Maelstrom, il faut Ondine niveau 10, au moins 5/10 de vitalité et 50 utilisations créditées de Geyser par le lanceur.\nLa résistance à l'eau n'est plus requise. Le coût en PT et les commandes de lancement restent nécessaires.",
     'To turn Spread into Maelstrom, the caster needs level 10 Undine, at least 5/10 vitality and 50 credited uses of Spread.\nWater resistance is no longer required. TP costs and launch commands still apply.'),
    ("Affiche le nombre d'utilisations des sorts dans Techniques, avec leur élément à côté du compteur. Le rattrapage, lorsqu'il s'applique, est inclus dans ce total.\nDésactiver masque cet affichage sans remettre les compteurs à zéro.",
     'Shows spell use counts in the Artes menu, with their element beside the counter. Catch-up credits are included when applicable.\nTurning this off hides the display without resetting the counters.'),
    ('Après avoir analysé un ennemi avec une Lentille, sa barre de PV reste visible lors des prochaines rencontres.\nPendant la sélection de cible avec R1, une petite fenêtre rappelle ses PV, résistances et faiblesses. Elle attend que la fenêtre de la Lentille soit fermée.\nDésactiver masque ces ajouts, mais conserve les ennemis déjà analysés.',
     'After scanning an enemy with Spectacles, its HP bar remains visible in later encounters.\nWhile selecting a target with R1, a small window shows its HP, resistances and weaknesses. It waits until the original Spectacles window closes.\nTurning this off hides these additions but keeps your scanned enemies.'),
    ("Au prochain lancement du jeu, passe les logos et l'écran d'information pour arriver plus vite à l'ouverture animée. Celle-ci est conservée.\nDésactivé : démarrage complet du jeu d'origine.",
     "On the next game launch, skips logos and the information screen to reach the animated opening sooner. The opening is kept.\nOff: use the game's full original startup sequence."),
    ("Permet à plusieurs projectiles d'Estocade aérienne de toucher la même cible, même s'ils arrivent presque ensemble.\nChaque projectile conserve son propre délai avant de pouvoir toucher à nouveau.\nDésactivé : un impact peut temporairement empêcher les autres projectiles du sort de toucher.",
     "Lets several Air Thrust projectiles hit the same target even when they arrive almost together.\nEach projectile keeps its own delay before it can hit again.\nOff: one hit can briefly prevent the spell's other projectiles from hitting."),
    ("Pendant une course, appuyez sur Garde, Attaque ou une commande d'arte pour vous arrêter et demander cette action. Ses conditions habituelles restent nécessaires.\nConcerne le personnage contrôlé en manuel ou semi-auto.",
     'While running, press Guard, Attack or an arte command to stop and attempt that action. Its usual requirements still apply.\nApplies to the character controlled in Manual or Semi-Auto.'),
    ('Active les facultés de Reid dans les branches Tranchant, Estoc et Tranchant + Estoc. Les niveaux requis et les effets sont détaillés dans Maîtrise.',
     "Enables Reid's faculties in Slash, Thrust and Slash + Thrust. The Mastery page explains their level requirements and effects."),
    ('Les niveaux des Craymel recrutés débloquent des bonus de combat pour Keele et Meredy. Les paliers sont indiqués dans leurs arbres.\nChoisissez les facultés à activer dans Maîtrise pour chaque mage. Désactiver cette option retire leurs effets, sans effacer vos choix.',
     "Recruited Craymel levels unlock battle bonuses for Keele and Meredy. Their trees show the milestones.\nChoose which faculties to enable in each mage's Mastery page. Turning this option off removes their effects without erasing your choices."),
    ("Les Craymel progressent grâce aux sorts de leur élément réussis en combat. Un sort rapporte 50, 200 ou 500 EXP selon son rang ; le total est reçu à la victoire.\nCela remplace leur gain automatique d'EXP de combat. Un Craymel pas encore recruté ne gagne rien.",
     'Craymels grow through successful battle casts of their element. A spell grants 50, 200 or 500 EXP depending on rank; the total is awarded at victory.\nThis replaces their automatic battle EXP. A Craymel you have not recruited earns none.'),
    ("Assouplit les techniques spéciales de Reid.\nCROC DE DRAGON ULTIME / SCEAU DE CYCLONE\nMaintenez Arte pendant Chaos démoniaque oméga ou Sceau oméga : la mystic arte s'enchaîne à la fin si ses conditions sont remplies. Inutile de relâcher puis réappuyer au bon instant.\nChaque mystic arte est limitée à 1 utilisation par combat et coûte 100 PT supplémentaires, prélevés uniquement si elle démarre. Il faut conserver ces 100 PT après avoir payé l'arte de départ. Les dégâts dépendent de Tranchant, de la défense et des résistances adverses, avec des coups finaux renforcés.\nLe seuil de PV de la cible est retiré. Les autres conditions restent : usages de l'arte, portée et cible ; Sceau de cyclone demande notamment un seul ennemi restant, de niveau 50 maximum.\nPhénix brûlant conserve ses règles précédentes : déclenchement, coût, dégâts et limite de 3 utilisations.\nAURORA\nAttaque + Arte, sans Garde. Mur du levant est possible à 25 % des PV max ou moins.\nDésactivé : règles du jeu d'origine.",
     "Relaxes Reid's special techniques.\nFINAL DRAGON FANG / CYCLONE SEAL\nHold Arte during Omega Demon Chaos or Omega Seal: the mystic arte follows at the end if its requirements are met. No precisely timed release and new press is needed.\nEach mystic arte is limited to 1 use per battle and costs an additional 100 TP, charged only when it starts. Keep these 100 TP available after paying for the starting arte. Damage scales with Slash, enemy defense and resistances, with stronger finishing hits.\nThe enemy HP threshold is removed. Other requirements remain: arte uses, range and target; Cyclone Seal still requires one remaining enemy, at level 50 or below.\nBurning Phoenix retains its previous trigger, cost, damage and limit of 3 uses.\nAURORA\nAttack + Arte, without Guard. Aurora Wall is available at 25% max HP or less.\nOff: the original game rules."),
    ("Permet à Reid et Farah d'apprendre quatre attaques combinées, puis de les lancer seuls comme des artes ordinaires.\nPour chaque recette : utilisez l'arte physique 50 fois avec le combattant, et le sort associé 50 fois avec Keele OU Meredy. Un seul mage doit atteindre 50 ; 25 chacun ne suffisent pas.\nL'arte apparaît alors dans Techniques et peut être placé sur un raccourci. Aucun mage n'est nécessaire dans l'équipe pour le lancer, et seul le combattant paie les PT. Inutile de réussir la combinaison à deux pour l'apprendre.\nRECETTES DE REID\nÉpée enflammée (13 PT) : Fendoir démoniaque + Boule de feu.\nFaille terrestre (54 PT) : Lame tournoyante + Cyclone.\nRECETTES DE FARAH\nCoup foudroyant (36 PT) : Double coup de paume + Lame du tonnerre.\nPoing du serpent (28 PT) : Coup ascendant du dragon + Soins.\nLe rattrapage des sorts compte lorsqu'il s'applique.\nDésactivé : retire l'accès à ces versions autonomes, sans effacer les compteurs. Les combinaisons à deux du jeu restent disponibles selon leurs règles habituelles.",
     "Lets Reid and Farah learn four team-up attacks, then use them alone like ordinary artes.\nFor each recipe: use the physical arte 50 times with the fighter, and cast the matching spell 50 times with EITHER Keele or Meredy. One mage must reach 50; 25 each is not enough.\nThe arte then appears in the Artes menu and can be assigned to a shortcut. No mage needs to be in the party to use it, and only the fighter pays TP. You do not need to perform the two-character combination to learn it.\nREID'S RECIPES\nFlaming Sword (13 TP): Demon Hammer + Fireball.\nEarth Divide (54 TP): Spiral Attack + Cyclone.\nFARAH'S RECIPES\nLightning Strike (36 TP): Twin Palm Strike + Thunder Blade.\nSerpent Knuckle (28 TP): Rising Dragon Strike + Heal.\nSpell catch-up credits count where applicable.\nOff: removes access to these standalone versions without erasing counters. The game's two-character combinations remain available under their usual rules."),
    ("Réinit. annule les changements faits depuis l'ouverture de ce menu.\nDéfaut remet les réglages recommandés du mod : toutes les options activées, sauf les cages libres.\nLes changements sont enregistrés automatiquement.",
     "Reset undoes changes made since you opened this menu.\nDefault restores the mod's recommended settings: all options on except free cages.\nChanges are saved automatically."),
    ("Choisissez les touches clavier permettant d'utiliser les pages B et C de l'Artesphere.\nCes touches sont communes à vos parties. Les artes affectés aux emplacements sont enregistrés séparément dans chaque sauvegarde.",
     'Choose keyboard keys for using Artesphere pages B and C.\nThese keys are shared across your games. The artes assigned to the slots are stored separately for each save.'),
    ("Personnalisez ce que vous voyez : caméra, interface, couleurs des dégâts, barres et notifications.\nValidez pour ouvrir les options de confort et d'affichage.",
     'Customize what you see: camera, interface, damage colors, bars and notifications.\nConfirm to open convenience and display options.'),
    ('Réglez les combats : récupération de PT, difficulté, commandes, invocations et déroulement des sorts.\nValidez pour ouvrir ce menu. Chaque option peut être activée séparément.',
     'Adjust battles: TP recovery, difficulty, controls, summons and how spells play out.\nConfirm to open this menu. Each option can be enabled separately.'),
    ('Choisissez les systèmes de progression à utiliser pour les mages, Farah et Reid. Ce menu contient aussi les cages libres et les artes combinés autonomes.\nLes bonus individuels se choisissent ensuite dans les pages Maîtrise.',
     'Choose progression systems for the mages, Farah and Reid. This menu also contains free cages and standalone team-up artes.\nChoose individual bonuses in the Mastery pages.'),
    ('Réglez le démarrage du jeu et les touches clavier supplémentaires des pages Artesphere.\nValidez pour ouvrir ce sous-menu.',
     'Configure game startup and the extra keyboard controls for Artesphere pages.\nConfirm to open this submenu.'),
]


from custom_test_artes import HELP as TEST_HELP
HELP.insert(36, TEST_HELP)

def emit_progression_ui(emit, mem, jump, data, state, symbols):
    from settings_help import DETAILS, emit_help
    for i, detail in DETAILS.items(): HELP[i] = detail
    payload = bytearray()
    def string(s):
        p = state + len(payload)
        payload.extend((s+'\0').encode('utf8'))
        return p
    titles = [(f[1],f[2]) for f in FEATURES] + [('Réinitialisation','Reset'),('Commandes clavier','Keyboard controls')] + [(fr,en) for fr,en,_ in CATEGORIES]
    assert len(HELP) == len(titles)
    entries=[]
    for title, detail in zip(titles, HELP):
        langs=[]
        for lang in range(2):
            lines=[title[lang], '']
            for paragraph in detail[lang].split('\n'):
                lines.extend(textwrap.wrap(paragraph,43) or [''])
            assert len(lines)<65535
            langs.append([string(l) for l in lines])
        entries.append(langs)
    while len(payload)%4:payload.append(0)
    descriptors=[]
    for langs in entries:
        ds=[]
        for lines in langs:
            start=state+len(payload)
            payload.extend(struct.pack('<'+'I'*len(lines),*lines))
            ds += [start,len(lines)]
        descriptors.append(ds)
    help_table=state+len(payload)
    for d in descriptors:payload.extend(struct.pack('<4I',*d))
    labels=[(string(fr),string(en)) for fr,en in (
        ('Niveau Poing','Punch Lv.'),('Niveau Pied','Kick Lv.'),('Niveau Énergie','Energy Lv.'),
        ('Tranchant','Slash'),('Estoc','Thrust'),('Tranchant / Estoc','Slash / Thrust'),
        ('Poing','Punch'),('Pied','Kick'),('Poing / Pied','Punch / Kick'),
        ('Énergie','Energy'),('Levant','Aurora'))]
    levels=[string(f'{n}/30') for n in range(31)]
    while len(payload)%4:payload.append(0)
    label_table=state+len(payload)
    for pair in labels:payload.extend(struct.pack('<2I',*pair))
    level_table=state+len(payload)
    payload.extend(struct.pack('<31I',*levels))
    def label(index):
        return f'''lea rax, {mem(label_table)}
            mov ecx, dword ptr [rax+{index*8+4}]
            cmp byte ptr {mem(0x11c9ce8)}, 3
            jne lang_{index}
            mov ecx, dword ptr [rax+{index*8}]
        lang_{index}:
            lea rax, {mem(0)}
            add rcx, rax'''
    # Screen rectangles; same native window as Options/Status.
    frame=emit('progression_ui_frame',f'''
        sub rsp, 0x38
        mov dword ptr [rsp+0x20], r9d
        mov r9d, r8d
        sub ecx, 80
        sub edx, 15
        xor r8d, r8d
        lea rax, {mem(0x11cc57c)}
        mov qword ptr [rsp+0x28], rax
        mov dword ptr [rsp+0x30], r10d
        call 0x25aaa0
        add rsp, 0x38
        ret
    ''')
    help_hint=[string(t) for t in ('Stick droit : défiler haut / bas', 'Right stick: scroll up / down')]
    help_draw, help_input, help_state, help_visible = emit_help(
        emit, mem, data, symbols, help_table, len(entries), help_hint)
    save='pushfq; '+ '; '.join('push '+r for r in ('rax','rcx','rdx','r8','r9','r10','r11'))
    restore='; '.join('pop '+r for r in ('r11','r10','r9','r8','rdx','rcx','rax'))+'; popfq'
    def preserve(body):
        return f'''{save}
            sub rsp, 0x80
            {chr(10).join(f'movdqu xmmword ptr [rsp+{0x20+i*16}], xmm{i}' for i in range(6))}
            {body}
            {chr(10).join(f'movdqu xmm{i}, xmmword ptr [rsp+{0x20+i*16}]' for i in range(6))}
            add rsp, 0x80
            {restore}'''
    energy_rows=[]
    for index in range(3):
        y=204+12*index
        level=(f'movzx ebx, byte ptr {mem(0x11cb038+index*8)}' if index<2 else
            f'''movzx ebx, byte ptr {mem(0x11cb038)}
                movzx eax, byte ptr {mem(0x11cb040)}
                cmp ebx, eax
                cmova ebx, eax''')
        energy_rows.append(f'''
            {level}
            mov eax, 30
            cmp ebx, eax
            cmova ebx, eax
            {label(index)}
            mov edx, 40
            mov r8d, {y}
            mov r9d, 58
            mov eax, r12d
            shl eax, 24
            or eax, 0x49bfff
            call {symbols['settings_field']:#x}
            mov ecx, 22
            mov edx, {y-15}
            xor r8d, r8d
            mov r9d, 128
            mov dword ptr [rsp+0x20], 128
            mov dword ptr [rsp+0x28], 128
            mov dword ptr [rsp+0x30], 60
            mov dword ptr [rsp+0x38], r12d
            call 0x251390
            mov ecx, 22
            mov edx, {y-15}
            xor r8d, r8d
            mov r9d, 192
            mov dword ptr [rsp+0x20], 192
            mov dword ptr [rsp+0x28], 48
            lea eax, [rbx+rbx]
            mov dword ptr [rsp+0x30], eax
            mov dword ptr [rsp+0x38], r12d
            call 0x251390
            lea rax, {mem(level_table)}
            mov ecx, dword ptr [rax+rbx*4]
            lea rax, {mem(0)}
            add rcx, rax
            mov edx, 175
            mov r8d, {y}
            mov r9d, -7
            mov eax, r12d
            shl eax, 24
            or eax, 0xfffdfa
            call {symbols['settings_text']:#x}
        ''')
    energy=emit('farah_energy_draw',f'''
        push rbx
        sub rsp, 0x40
        {''.join(energy_rows)}
        add rsp, 0x40
        pop rbx
        ret
    ''')
    # This branch is reached only by native Farah status (one-based char ID 2).
    energy_hook=emit('farah_energy_status',f'''
        cmp byte ptr {mem(data+0x1a0e)}, 0
        je native
        {preserve(f'call {energy:#x}')}
        jmp 0x240979
    native:
        mov rcx, qword ptr {mem(0x644a70)}
        jmp 0x240628
    ''')
    jump(0x240621,7,energy_hook,'Farah optional third Energy mastery bar, derived from Punch and Kick')

    # ECX arte ID -> EAX label index; native metadata bits 0x400/0x800.
    category=emit('arte_category_index',f'''
        cmp ecx, 134; je custom_reid
        cmp ecx, 135; jne custom_done
    custom_reid: mov ecx, 14; jmp virtual_teamup
    custom_done:
        cmp ecx, 130; jb virtual_teamup
        cmp ecx, 133; ja virtual_teamup
        mov ecx, 25
    virtual_teamup:
        cmp ecx, 126
        jne map127
        mov ecx, 4
    map127:
        cmp ecx, 127
        jne map128
        mov ecx, 31
    map128:
        cmp ecx, 128
        jne map129
        mov ecx, 5
    map129:
        cmp ecx, 129
        jne mapped
        mov ecx, 30
    mapped:
        mov eax, -1
        cmp ecx, 1
        jb done
        cmp ecx, 42
        ja done
        cmp ecx, 22
        jb physical
        cmp ecx, 24
        jbe aurora
        cmp ecx, 39
        jb physical
        cmp ecx, 41
        jbe energy
    physical:
        lea rdx, {mem(0x562a50)}
        imul r8d, ecx, 24
        movzx edx, word ptr [rdx+r8]
        and edx, 0xc00
        mov eax, 5
        cmp edx, 0x400
        jne thrust
        mov eax, 3
        jmp owner
    thrust:
        cmp edx, 0x800
        jne owner
        mov eax, 4
    owner:
        cmp ecx, 25
        jb done
        add eax, 3
        ret
    energy:
        mov eax, 9
        ret
    aurora:
        mov eax, 10
    done:
        ret
    ''')
    tag=emit('arte_category_draw',f'''
        push rbx
        sub rsp, 0x20
        cmp byte ptr {mem(data+0x1a0f)}, 0
        je done
        mov ecx, ebp
        call {category:#x}
        test eax, eax
        js done
        mov ebx, eax
        mov ecx, 298
        mov edx, 198
        mov r8d, 82
        mov r9d, 13
        mov r10d, r13d
        call {frame:#x}
        lea rax, {mem(label_table)}
        mov ecx, dword ptr [rax+rbx*8+4]
        cmp byte ptr {mem(0x11c9ce8)}, 3
        jne language
        mov ecx, dword ptr [rax+rbx*8]
    language:
        lea rax, {mem(0)}
        add rcx, rax
        mov edx, 302
        mov r8d, 200
        mov r9d, 74
        mov eax, r13d
        shl eax, 24
        or eax, 0xffffc0
        call {symbols['settings_field']:#x}
    done:
        add rsp, 0x20
        pop rbx
        ret
    ''')
    tag_hook=emit('arte_category_hook',preserve(f'call {tag:#x}')+f'''
        mov r10, qword ptr {mem(0x644a70)}
        jmp 0x2272b1
    ''')
    jump(0x2272aa,7,tag_hook,'Optional native-framed mastery family label left of TP cost')
    payload.extend(b'\0'*((-len(payload))%0x1000))
    return dict(data_rva=state,size=len(payload),help_draw_rva=help_draw,
        help_table=help_table,help_entries=entries,category_rva=category,
        help_input_rva=help_input,help_state_rva=help_state,help_visible_lines=help_visible,
        energy='min(Punch, Kick), capped at 30; display only; no separate EXP',
        energy_flag_index=14,arte_category_flag_index=15,
        runtime_validated=False),bytes(payload)
