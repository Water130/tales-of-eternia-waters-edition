"""Private native UI additions: option help, Farah Energy and arte families."""
import struct
import textwrap
from mod_settings_patch import FEATURES, CATEGORIES

# One entry per stable settings flag, followed by Reset and Keyboard.
HELP = [
    ("Adapte le cadrage du combat à la position des combattants. Désactivé : caméra native.",
     "Adjusts the battle framing to the combatants' positions. Off: native camera."),
    ("Augmente la récupération de PT après une victoire : 8 / 9 / 10 / 13 % selon la difficulté. Les bonus et minimums natifs sont conservés.",
     "Increases TP recovery after victory: 8 / 9 / 10 / 13% by difficulty. Native bonuses and minimums are retained."),
    ("Un coup de base qui touche rend 2 PT à Keele ou Meredy, 1 PT aux autres. Inclut les attaques aériennes et Quickie. Les artes ne donnent pas ce bonus.",
     "A basic hit restores 2 TP to Keele or Meredy, 1 TP to others. Includes aerial attacks and Quickie. Artes do not grant this bonus."),
    ("Colore les nombres de dégâts selon l'élément de l'impact. Les dégâts reçus par le groupe et les soins gardent leur distinction.",
     "Colors damage numbers by the impact's element. Party damage received and healing remain visually distinct."),
    ("Utilise la disposition de combat de Water's Edition : PV, PT et miniatures des Craymel. Désactivé : disposition native.",
     "Uses the Water's Edition battle layout for HP, TP and Craymel miniatures. Off: native layout."),
    ("Affiche la progression de l'incantation sous le personnage. Masquer ces barres ne change pas la durée des sorts.",
     "Shows casting progress below the character. Hiding these bars does not change cast duration."),
    ("Affiche le temps restant avant de pouvoir utiliser le prochain objet en combat. Le délai lui-même reste inchangé.",
     "Shows the remaining wait before using the next battle item. The cooldown itself is unchanged."),
    ("Affiche une petite bulle lorsqu'une saynète est disponible. Elle évite les éléments du HUD et reste masquée pendant les menus et scènes.",
     "Shows a small notice when a skit is available. It avoids HUD elements and stays hidden during menus and scenes."),
    ("Modifie Difficile / Extrême / Inconnue : PV x1,5 / x3 / x5 ; défense x1,1 / x1,2 / x1,3 ; dégâts fixes x1,1 / x1,2 / x1,5. Désactivé : valeurs natives.",
     "Changes Hard / Extreme / Unknown: HP x1.5 / x3 / x5; defense x1.1 / x1.2 / x1.3; fixed damage x1.1 / x1.2 / x1.5. Off: native values."),
    ("Plusieurs Craymel peuvent conserver leur vitalité au MAX en même temps. Les sorts ne réduisent plus une jauge déjà au MAX. Une invocation consomme toujours sa vitalité.",
     "Several Craymels can retain MAX vitality at once. Spells no longer reduce a gauge that is already at MAX. Summoning still consumes its vitality."),
    ("Une nouvelle pression sur Garde annule l'incantation en cours et met le personnage en garde. Un sort déjà lancé n'est pas annulé. Contrôle manuel ou semi-auto.",
     "A fresh Guard press cancels a pending cast and enters guard. Already released spells are unaffected. Manual or semi-auto control."),
    ("Keele et Meredy sautent uniquement avec Garde + Haut. Haut seul ne déclenche plus de saut. Ne change pas Reid/Farah ni les personnages contrôlés par l'IA.",
     "Keele and Meredy jump only with Guard + Up. Up alone no longer jumps. Does not affect Reid/Farah or AI-controlled characters."),
    ("Regroupe la progression des sorts, les facultés des Craymel, la puissance et la portée des invocations, l'EXP gagnée par les sorts et les extensions améliorées. Désactivé : règles natives ; niveaux, utilisations et choix conservés.",
     "Groups spell growth, Craymel faculties, summon power and reach, cast-earned Craymel EXP and enhanced extensions. Off: native rules; levels, cast counts and choices are retained."),
    ("Reid et Farah sautent uniquement avec Garde + Haut. Haut seul ne déclenche plus de saut. Réglage indépendant de Keele/Meredy ; l'IA reste inchangée.",
     "Reid and Farah jump only with Guard + Up. Up alone no longer jumps. Independent of Keele/Meredy; AI is unchanged."),
    ("Ajoute la barre Énergie à la fiche Stats de Farah. Énergie = le plus bas des niveaux Poing et Pied, sur 30. Sans EXP séparée. Cette barre seule n'ajoute pas de bonus de soin.",
     "Adds Energy to Farah's Stats page. Energy is the lower of Punch and Kick levels, out of 30, with no separate EXP. This bar alone grants no healing bonus."),
    ("Indique la branche de l'arte de Reid ou Farah près du coût en PT : Tranchant, Estoc, Poing, Pied ou Énergie pour les soins. Une branche mixte est indiquée explicitement. Ce n'est pas le rang d'enchaînement.",
     "Labels Reid and Farah's arte branch beside TP cost: Slash, Thrust, Punch, Kick or Energy for healing. Mixed branches are explicit. This is not the combo rank."),
    ("L2 / LT lance une saynète disponible en exploration. Si L2 est réaffecté à une commande d'exploration, utilisez L2 + Select. Indépendant de la bulle ; aucun lancement pendant un menu ou une scène.",
     "L2 / LT plays an available skit while exploring. If L2 is rebound to an exploration action, use L2 + Select. Independent of the notice; disabled during menus and scenes."),
    ("Regroupe la barre Énergie et toutes les facultés de Farah : Poing, Pied, Poing + Pied et Énergie. Désactivé : bonus retirés et barre masquée, sans effacer la progression ni les choix. Le saut Garde + Haut reste indépendant.",
     "Groups Farah's Energy gauge and all Punch, Kick, Punch + Kick and Energy faculties. Off removes bonuses and hides the gauge, preserving progress and choices. Guard + Up jumping is separate."),
    ("Ignore la cage du Craymel partenaire pour le Fringe. Les niveaux requis et la cage du Craymel principal restent nécessaires. Désactivé par défaut ; désactiver restaure l'accès natif sans effacer les utilisations.",
     "Ignores the partner Craymel's cage for Fringe. Level requirements and the primary Craymel's assignment still apply. Off by default; disabling restores native access without erasing cast counts."),
    ("Les invocations gagnent en puissance et en portée selon le niveau de leur Craymel. Désactivé : dégâts et portée natifs.",
     "Summons gain power and reach with their Craymel's level. Off: native damage and reach."),
    ("Supprime les pauses cinématiques des sorts. Désactivé : durée et pauses natives.",
     "Removes spell cinematic pauses. Off: native pauses and durations."),
    ("Permet à des sorts différents de se dérouler simultanément. Les invocations et les effets incompatibles restent protégés. Désactivé : file d'attente native.",
     "Allows different spells to run simultaneously. Summons and incompatible effects remain protected. Off: native spell queue."),
    ("Colore les particules d'incantation selon l'élément du sort. Désactivé : couleurs natives. Indépendant des couleurs de dégâts.",
     "Tints casting particles by spell element. Off: native colors. Independent of damage colors."),
    ("Ajoute les pages B et C aux six raccourcis d'artes. Désactivé : seule la page A native est utilisée. Les affectations B et C restent enregistrées.",
     "Adds pages B and C to the six arte shortcuts. Off: only native page A is used. Saved B and C assignments are retained."),
    ("Maintenir la commande d'arte jusqu'à la fin de l'incantation choisit l'invocation disponible. L1 retient le sort prêt. Désactivé : commandes natives.",
     "Holding the arte command until casting finishes selects an available summon. L1 holds a ready spell. Off: native controls."),
    ("Maelstrom devient disponible avec Ondine niveau 10 et au moins 5/10 de vitalité, sans résistance à l'eau imposée. Le coût en TP reste requis. Désactivé : critères natifs.",
     "Maelstrom becomes available with level 10 Undine and at least 5/10 vitality, without requiring water resistance. TP cost still applies. Off: native criteria."),
    ("Affiche les utilisations des sorts et place leurs éléments à gauche du compteur. Désactiver masque ces ajouts sans effacer la progression.",
     "Displays spell casts and places elements to the left of the counter. Disabling hides these additions without erasing progression."),
    ("Affiche une barre de PV au-dessus de chaque ennemi déjà analysé avec une Lentille, y compris lors des combats suivants. R1 affiche aussi le nom, les PV, résistances et faiblesses de la cible scannée. Désactiver masque les barres sans effacer les scans.",
     "Shows an HP gauge above each enemy previously scanned with Spectacles, including later encounters. R1 also shows the scanned target’s name, HP, resistances and weaknesses. Disabling hides gauges without erasing scans."),
    ("Passe les logos et l'écran d'information du démarrage. L'ouverture animée est conservée. Désactivé : lancement natif. Ce réglage s'applique au prochain lancement du jeu.",
     "Skips startup logos and the information screen, retaining the animated opening. Off: native startup. This setting applies the next time the game launches."),
    ("Chaque projectile d'Estocade aérienne (Air Thrust) peut toucher la même cible indépendamment des autres. Les collisions et délais entre deux impacts du même projectile sont conservés. Désactivé : délai partagé natif.",
     "Each Air Thrust projectile can hit the same target independently. Collision checks and the delay between repeat hits by one projectile are retained. Off: native shared hit cooldown."),
    ("Garde, Attaque ou Arte arrête la course en contrôle manuel ou semi-auto. L'action demandée est ensuite traitée normalement. Désactivé : comportement natif.",
     "Guard, Attack or Arte stops running in manual or semi-auto control. The requested action is then processed normally. Off: native behavior."),
    ("Regroupe les facultés de Reid : Tranchant, Estoc et Tranchant + Estoc. Les attaques normales gagnent +1 coup au niveau 15 et +2 au niveau 30 de la famille utilisée. Le saut Garde + Haut reste indépendant.",
     "Groups Reid's Slash, Thrust and Slash + Thrust faculties. Normal chains gain one attack at family level 15 and two at 30. Guard + Up jumping remains independent."),
    ("Active les facultés débloquées par les niveaux des Craymel recrutés pour Keele et Meredy. Chaque faculté peut être désactivée dans Maîtrise. Désactiver cette option retire leurs effets sans effacer les choix.",
     "Enables Keele and Meredy's faculties unlocked by recruited Craymel levels. Toggle individual faculties in Mastery. Off removes their effects without erasing choices."),
    ("Les sorts élémentaires réussis donnent de l'EXP au Craymel correspondant, reçue à la victoire. Remplace l'EXP automatique de combat. Aucun gain pour un Craymel encore inconnu. Désactivé : progression native.",
     "Successfully cast elemental spells award EXP to their Craymel at victory, replacing automatic battle EXP. Unknown Craymels earn none. Off: native progression."),
    ("Aurora : Attaque + Arte sans Garde, Mur du levant à 25 % des PV max. Hi-ougi de Reid : seuil de PV ennemi retiré, 3 utilisations par technique et par combat. Autres critères conservés. Désactivé : règles natives.",
     "Aurora: Attack + Arte without Guard, Aurora Wall at 25% max HP. Reid mystic artes: enemy HP ceiling removed, 3 uses per technique per battle. Other criteria retained. Off: native rules."),
    ("Débloque quatre artes autonomes de Reid/Farah après 50 utilisations de l'arte physique et 50 du sort associé par Keele ou Meredy. Aucun mage requis au lancement. Coût : somme des deux techniques. Désactivé : accès retiré, compteurs conservés.",
     "Unlocks four standalone Reid/Farah team-up artes after 50 physical-arte uses and 50 associated casts by Keele or Meredy individually. No mage needed to launch. TP cost: sum of both ingredients. Off removes access, retaining counters."),
    ("Réinit. restaure les réglages présents à l'ouverture de ce menu. Défaut restaure les valeurs recommandées, dont cages Fringe libres désactivé. Les changements sont enregistrés automatiquement.",
     "Reset restores the settings present when this menu was opened. Default restores recommended values, including free Fringe cages off. Changes are saved automatically."),
    ("Configure les touches clavier des pages B et C de l'Artesphere. Les touches sont communes aux parties ; les affectations des artes restent propres à chaque sauvegarde.",
     "Configure keyboard keys for Artesphere pages B and C. Keys are shared across games; arte assignments are kept per save."),
    ("Réglages de confort et d'affichage : caméra, interface de combat, couleurs, barres, saynètes et catégories des artes. Confirmez pour ouvrir ce sous-menu.",
     "Convenience and display settings: camera, battle interface, colors, bars, skits and arte categories. Confirm to open this submenu."),
    ("Règles de combat : récupération de PT, difficultés, vitalités au MAX, annulation d'incantation et commandes de saut. Chaque changement se règle séparément.",
     "Battle rules: TP recovery, difficulty, MAX vitality, cast cancelling and jump controls. Each change can be switched independently."),
    ("Un interrupteur par système : progression magique, progression de Farah et progression de Reid. La règle des cages Fringe reste séparée et désactivée par défaut. Les choix individuels de facultés sont conservés.",
     "One switch per system: magic progression, Farah progression and Reid progression. The Fringe cage rule stays separate and off by default. Individual faculty choices are preserved."),
    ("Configuration des commandes clavier supplémentaires sur PC. Les touches sont communes aux parties ; les affectations d'artes restent propres à chaque sauvegarde.",
     "Configure additional PC keyboard controls. Keys are shared across games; arte assignments are kept per save."),
]


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
    help_hint=[string(t) for t in ('Joystick gauche : défiler haut / bas', 'Left stick: scroll up / down')]
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
