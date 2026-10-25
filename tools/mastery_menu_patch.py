"""Native status submenu: browsable skill trees and spoiler-safe Craymel faculties.

No synthetic unlocks. Implemented spell mastery and Energy can be switched here;
Future character faculties are explicitly marked as in development.
Native status title/character selection is untouched while this panel is closed.
"""
import struct
import textwrap
from mastery_catalog import catalog
from mastery_tree_layout import prepare, connections, LEVELS, NODE_SIZE, ROOT, ORIGIN


def emit_mastery_menu(emit, mem, jump, data, state, symbols, usage, native, expansion=None):
    pref = usage['preferences']
    ui, choices = pref['ui_state_rva'], pref['live_rva']
    from spell_browser import arrange, emit_availability, emit_browser
    rows = prepare(arrange(catalog()))
    payload = bytearray(0x1000)
    strings = {}
    def string(s):
        if s not in strings:
            strings[s]=state+len(payload)
            payload.extend((s+'\0').encode('utf-8'))
        return strings[s]
    def pair(s): return [string(t) for t in s]
    def lineblock(lines):
        pointers=[string(t) for t in lines]
        while len(payload)%4:payload.append(0)
        address=state+len(payload)
        payload.extend(struct.pack('<'+'I'*(len(pointers)+1),len(pointers),*pointers))
        return address
    from mastery_rich_text import encode_runs
    for i,r in enumerate(rows):
        ns=[]
        for n in r['nodes']:
            requirement=(('Prérequis à définir','Requirements to be defined') if not n['required'] else
                (f"Prérequis : {n['required']} utilisations",f"Requires {n['required']} casts") if r['kind']==2 else
                (f"Prérequis : {r['name'][0]} niveau {n['required']}",f"Requires {r['name'][1]} level {n['required']}"))
            requirements=[textwrap.wrap(t,72) for t in requirement]
            assert all(len(lines)<=2 for lines in requirements)
            runs=[encode_runs(t,payload,state,string) for t in n['label']]
            ns.append(struct.pack('<24I',*pair(n['label']),*pair(n['title']),
                *pair(n['description']),*pair(n['detail']),*[lineblock(lines) for lines in requirements],
                n['required'],int(n['implemented']) | (n.get('preference',0)<<8),n['x'],n['y'],*n['neighbors'],
                *[lineblock(lines) for lines in n['lines']],
                *[lineblock(lines) for lines in n['title_lines']],*runs))
        while len(payload)%4: payload.append(0)
        nodes=state+len(payload)
        for n in ns: payload.extend(n)
        name=pair(r['name'])
        from mastery_tree_links import store_links
        links=store_links(connections(r),payload,state)
        while len(payload)%4:payload.append(0)
        link_address=state+len(payload)
        payload.extend(struct.pack('<2I',len(links),r['root'][0]))
        for link in links:payload.extend(struct.pack('<5I',*link))
        struct.pack_into('<8I',payload,i*32,r['kind'],r['key'],r['mask'],*name,nodes,len(ns),link_address)
    labels={k:pair(v) for k,v in {
        'title':('Maîtrise : Facultés','Mastery: Faculties'),
        'entry':('Maîtrise','Mastery'), 'faculties':('Facultés','Faculties'), 'spells':('Sorts','Spells'),
        'spellpage':('Progression des sorts','Spell progression'),
        'energyoff':('Faculté désactivée','Faculty disabled'),
        'energyon':('Faculté activée','Faculty enabled'),
        'energyglobaloff':('Progression de Farah désactivée','Farah progression disabled'),
        'basicglobaloff':('Progression de ce personnage désactivée','This character’s progression is disabled'),
        'excluded':('Comportement natif — aucun bonus par utilisation','Native behavior — no usage bonus'),
        'unknown':('???','???'), 'undefined':('—','—'), 'locked':('Prérequis non atteints','Requirements not met'),
        'pending':('En préparation — aucun effet en combat','In development — no battle effect'),
        'off':('Maîtrise de ce sort désactivée','Mastery disabled for this spell'),
        'on':('Maîtrise de ce sort activée','Mastery enabled for this spell'),
        'globaloff':('Progression magique désactivée','Magic progression disabled'),
        'empty':('Aucune branche disponible dans cette catégorie.','No branch available in this category.'),
        'preview':('Les facultés en préparation ne sont pas encore jouables.','Faculties in development do not have battle effects yet.'),
        'save':('Choix conservés avec la sauvegarde de la partie.','Choices are stored when you save the game.'),
        'character':('Personnage','Character'), 'back':('Retour','Back'), 'browse':('Arbre','Tree'),
        'toggle':('Activer / désactiver','Toggle'), 'tab':('Catégorie','Category'), 'branch':('Branche','Branch'),
        'current':('Niveau :','Level:'), 'next':('Suite : haut / bas','More: up / down'),
        'summonpower':('Invocation : dégâts','Summon: damage'),
        'summonnative':('Invocation : effets natifs','Summon: native effects'),
        'summonoff':('Progression de l’invocation désactivée','Summon progression disabled'),
        'casts':('Utilisations :','Casts:'),
        'recruit':('Prérequis : obtenir ce Craymel.','Requires recruiting this Craymel.'),
        'level':('Niveau requis :','Required level:'),
        'choose':('Choisir','Choose'), 'open_tree':("Voir l'arbre",'View tree'),
        'choose_mastery':('Choisis une maîtrise','Choose a mastery'),
        'choose_spirit':('Choisis un Craymel','Choose a Craymel'),
        'choose_spell':('Choisis un sort','Choose a spell'),
    }.items()}
    chars=[pair((n,n)) for n in ('Reid','Farah','Keele','Meredy','Chat','Max','Rassius')]
    while len(payload)%4: payload.append(0)
    names=state+len(payload)
    for p in chars:payload.extend(struct.pack('<2I',*p))
    assert len(rows)*32 <= 0x1000
    payload.extend(b'\0'*((-len(payload))%0x1000))

    serial=0
    def loc(label, reg='rcx'):
        nonlocal serial
        serial+=1
        fr,en=labels[label]
        return f'''lea {reg}, {mem(en)}
            cmp byte ptr {mem(0x11c9ce8)}, 3
            jne lang_{serial}
            lea {reg}, {mem(fr)}
        lang_{serial}:'''
    def tabletext(register, offset):
        nonlocal serial
        serial+=1
        return f'''mov ecx, dword ptr [{register}+{offset+4}]
            cmp byte ptr {mem(0x11c9ce8)}, 3
            jne lang_{serial}
            mov ecx, dword ptr [{register}+{offset}]
        lang_{serial}:
            lea rax, {mem(0)}
            add rcx, rax'''

    character=emit('mastery_menu_character',f'''
        movzx eax, byte ptr {mem(0x111a674)}
        cmp byte ptr {mem(ui)}, 0
        je native_slot
        movzx eax, byte ptr {mem(ui+0xd)}
    native_slot:
        cmp al, byte ptr {mem(0x111a672)}
        jae invalid
        cmp eax, 7
        jae invalid
        lea rdx, {mem(0x11cad10)}
        movzx eax, word ptr [rdx+rax*2]
        dec eax
        cmp eax, 6
        ja invalid
        ret
    invalid:
        mov eax, -1
        ret
    ''')
    ready=emit('mastery_menu_ready',f'''
        xor eax, eax
        cmp byte ptr {mem(ui+0xc)}, 1
        je technique
        cmp word ptr {mem(0x111a658)}, 0
        jne done
        cmp word ptr {mem(0x111a65a)}, 0
        jne done
        cmp byte ptr {mem(0x111a668)}, 2
        je done
        cmp byte ptr {mem(0x111a669)}, 255
        jne done
        jmp scene
    technique:
        cmp word ptr {mem(0x1119f96)}, 0
        jne done
        cmp byte ptr {mem(0x1119fa4)}, 1
        jne done
        cmp byte ptr {mem(0x1119fa5)}, 255
        jne done
        cmp word ptr {mem(0x1119f98)}, 4
        je scene
        cmp word ptr {mem(0x1119f98)}, 2
        ja done
    scene:
        mov rdx, qword ptr {mem(0x11c9da0)}
        test rdx, rdx
        je ready
        cmp byte ptr [rdx+8], 0
        jne done
    ready:
        mov eax, 1
    done:
        ret
    ''')
    rebuild=emit('mastery_menu_rebuild',f'''
        push rbx
        push rsi
        push rdi
        sub rsp, 0x20
        xor ebx, ebx
        xor edi, edi
        lea rsi, {mem(state)}
    next:
        movzx ecx, byte ptr {mem(ui+4)}
        bt dword ptr [rsi+8], ecx
        jnc skip
        cmp dword ptr [rsi], 2
        sete al
        cmp al, byte ptr {mem(ui+3)}
        jne skip
    append:
        lea rax, {mem(ui+0x20)}
        mov word ptr [rax+rdi*2], bx
        inc edi
    skip:
        add rsi, 32
        inc ebx
        cmp ebx, {len(rows)}
        jb next
        mov byte ptr {mem(ui+5)}, dil
        mov word ptr {mem(ui+1)}, 0
        mov byte ptr {mem(ui+6)}, 0
        add rsp, 0x20
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
    availability=emit_availability(emit,mem,ui,symbols['artesphere_learned'],usage)
    # Native Techniques control mode is indexed by party slot (11cad38),
    # not by character. Auto owns Square; manual/semi-auto own Triangle.
    entry_key=emit('mastery_menu_entry_key',f'''
        mov edx, 0x8000
        cmp byte ptr {mem(ui+0xc)}, 1
        jne done
        cmp word ptr {mem(0x1119f98)}, 4
        je auto_list_key
        movzx r10d, byte ptr {mem(0x111a674)}
        cmp r10d, 7
        jae done
        lea r11, {mem(0x11cad38)}
        cmp byte ptr [r11+r10], 0
        jne done
    auto_list_key:
        mov edx, 0x1000
    done: ret
    ''')
    # RCX row descriptor -> EAX current level/uses, EDX known.
    value=emit('mastery_menu_value',f'''
        mov edx, 1
        mov eax, dword ptr [rcx]
        cmp eax, 0
        je spirit
        cmp eax, 1
        je physical
        cmp eax, 2
        je spell
        xor eax, eax
        ret
    spirit:
        mov eax, dword ptr [rcx+4]
        lea r8, {mem(0x11cafd8)}
        cmp byte ptr [r8+rax*8], 0
        je unknown
        movzx eax, byte ptr [r8+rax*8+1]
        test eax, eax
        je unknown
        cmp eax, 30
        ja unknown
        ret
    unknown:
        xor edx, edx
        xor eax, eax
        ret
    physical:
        mov eax, dword ptr [rcx+4]
        cmp eax, 4
        jae combined
        lea r8, {mem(0x11cb028)}
        movzx eax, byte ptr [r8+rax*8]
        ret
    combined:
        cmp eax, 6
        jne combined_key
        mov eax, 5
    combined_key:
        sub eax, 4
        shl eax, 4
        lea r8, {mem(0x11cb028)}
        movzx r9d, byte ptr [r8+rax+8]
        movzx eax, byte ptr [r8+rax]
        cmp eax, r9d
        cmova eax, r9d
        ret
    spell:
        push rbx
        sub rsp, 0x20
        mov ebx, dword ptr [rcx+4]
        mov ecx, ebx
        call {availability:#x}
        test eax, eax
        setne dl
        movzx r11d, dl
        movzx eax, byte ptr {mem(ui+4)}
        shl eax, 7
        add eax, ebx
        lea r8, {mem(usage['live_rva'])}
        movzx r9d, word ptr [r8+rax*2]
        lea r8, {mem(usage['catchup']['live_rva'])}
        movzx eax, word ptr [r8+rax*2]
        add eax, r9d
        mov edx, r11d
        add rsp, 0x20
        pop rbx
        ret
    ''')
    # Stable saved bit ID. Spell IDs retain their existing layout; Farah's
    # six independent faculties occupy her previously unused IDs 128..133.
    preference=emit('mastery_menu_preference',f'''
        mov r10d, dword ptr [rcx+4]
        cmp dword ptr [rcx], 0
        je spirit
        cmp dword ptr [rcx], 1
        jne spell
        mov eax, dword ptr [rdx+44]
        shr eax, 8
        test eax, eax
        je legacy_preference
        mov r10d, eax
        jmp spell
    legacy_preference:
        # These IDs are independent of node insertion/order and do not
        # overlap Energy 128..133 or the normal-chain switches 134..137.
        cmp r10d, 0; jne not_impact
        cmp dword ptr [rdx+40], 20; jne basic
        mov r10d, 138; jmp spell
    not_impact:
        cmp r10d, 1; jne not_counter
        cmp dword ptr [rdx+40], 25; jne basic
        mov r10d, 139; jmp spell
    not_counter:
        cmp r10d, 4; jne not_guard
        cmp dword ptr [rdx+40], 20; jne mixed_basic
        mov r10d, 140; jmp spell
    not_guard:
        cmp r10d, 6; jne not_landing
        cmp dword ptr [rdx+40], 20; jne mixed_basic
        mov r10d, 141; jmp spell
    not_landing:
        cmp r10d, 4
        jb basic
        cmp r10d, 4
        je mixed_basic
        cmp r10d, 6
        je mixed_basic
        cmp r10d, 5
        jne spell
        mov eax, dword ptr [rcx+20]
        lea r9, {mem(0)}
        add rax, r9
        sub rdx, rax
        mov rax, rdx
        xor edx, edx
        mov r9d, {NODE_SIZE}
        div r9d
        lea r10d, [rax+128]
        jmp spell
    mixed_basic:
        xor r10d, r10d
    basic:
        and r10d, 1
        lea r10d, [r10*2+134]
        cmp dword ptr [rdx+40], 30
        jne spell
        inc r10d
        jmp spell
    spirit:
        mov eax, dword ptr [rcx+20]
        lea r9, {mem(0)}
        add rax, r9
        sub rdx, rax
        mov rax, rdx
        xor edx, edx
        mov r9d, {NODE_SIZE}
        div r9d
        cmp eax, 8
        jae extended_spirit
        lea r10d, [rax+r10*8+128]
        jmp spell
    extended_spirit:
        lea r10d, [rax+r10*4+200]
    spell:
        movzx ecx, byte ptr {mem(ui+4)}
        shl ecx, 8
        add ecx, r10d
        ret
    ''')
    # RCX row, RDX node -> unknown / locked / preview / disabled / active.
    status=emit('mastery_menu_node_status',f'''
        push rbx
        push rsi
        sub rsp, 0x28
        mov rbx, rcx
        mov rsi, rdx
        call {value:#x}
        test edx, edx
        je unknown
        cmp dword ptr [rsi+40], 0
        je pending
        cmp eax, dword ptr [rsi+40]
        jb locked
        # The full interruption ward requires both Gnome and Celsius 30.
        cmp dword ptr [rbx], 0
        jne implementation
        cmp dword ptr [rbx+4], 3
        jne implementation
        mov ecx, dword ptr [rbx+20]
        lea rax, {mem(0)}
        add rcx, rax
        add rcx, {6*NODE_SIZE}
        cmp rsi, rcx
        jne implementation
        cmp byte ptr {mem(0x11cafd8+4*8)}, 0
        je locked
        cmp byte ptr {mem(0x11cafd8+4*8+1)}, 30
        jb locked
    implementation:
        cmp dword ptr [rsi+44], 0
        je pending
        cmp dword ptr [rbx], 1
        jne spell_option
        cmp byte ptr {mem(ui+4)}, 1
        je energy_option
        cmp byte ptr {mem(data+0x1a4f)}, 0
        je disabled
        jmp preference
    energy_option:
        cmp byte ptr {mem(data+0x1a41)}, 0
        je disabled
        jmp preference
    spell_option:
        cmp dword ptr [rbx], 0
        jne ordinary_spell_option
        cmp byte ptr {mem(data+0x1a60)}, 0
        je disabled
        jmp preference
    ordinary_spell_option:
        cmp byte ptr {mem(data+0x1a0c)}, 0
        je disabled
    preference:
        mov rcx, rbx
        mov rdx, rsi
        call {preference:#x}
        lea rdx, {mem(choices)}
        bt dword ptr [rdx], ecx
        jc disabled
        mov eax, 4
        jmp done
    disabled:
        mov eax, 3
        jmp done
    pending:
        mov eax, 2
        jmp done
    locked:
        mov eax, 1
        jmp done
    unknown:
        xor eax, eax
    done:
        add rsp, 0x28
        pop rsi
        pop rbx
        ret
    ''')
    # EAX visible row -> RCX row; EDX column -> RDX node. Return null if empty.
    lookup=emit('mastery_menu_lookup',f'''
        xor ecx, ecx
        cmp al, byte ptr {mem(ui+5)}
        jae done
        lea rcx, {mem(ui+0x20)}
        movzx eax, word ptr [rcx+rax*2]
        shl eax, 5
        lea rcx, {mem(state)}
        add rcx, rax
        cmp edx, dword ptr [rcx+24]
        jb node
        mov edx, dword ptr [rcx+24]
        dec edx
    node:
        imul edx, edx, {NODE_SIZE}
        add edx, dword ptr [rcx+20]
        lea rax, {mem(0)}
        add rdx, rax
    done:
        ret
    ''')
    text=emit('mastery_menu_text',f'''
        sub rsp, 0x58
        cvtsi2ss xmm1, edx
        cvtsi2ss xmm2, r8d
        xorps xmm3, xmm3
        mov dword ptr [rsp+0x28], eax
        cvtsi2ss xmm0, r9d
        movss dword ptr [rsp+0x40], xmm0
        mov dword ptr [rsp+0x20], 0x40e00000
        mov dword ptr [rsp+0x30], 0
        mov dword ptr [rsp+0x38], 0
        mov dword ptr [rsp+0x48], 0x3f800000
        call 0xb480
        add rsp, 0x58
        ret
    ''')
    # Screen coordinates (480x270) -> native 320x240 window coordinates.
    frame=emit('mastery_menu_frame',f'''
        sub rsp, 0x38
        mov dword ptr [rsp+0x20], r9d
        mov r9d, r8d
        xor r8d, r8d
        sub ecx, 80
        sub edx, 15
        lea rax, {mem(0x11cc57c)}
        mov qword ptr [rsp+0x28], rax
        mov dword ptr [rsp+0x30], 255
        call 0x25aaa0
        add rsp, 0x38
        ret
    ''')
    number=emit('mastery_menu_number',f'''
        lea rcx, {mem(ui+0x180+15)}
        mov byte ptr [rcx], 0
        mov r10d, 10
    digit:
        xor edx, edx
        div r10d
        add edx, 48
        dec rcx
        mov byte ptr [rcx], dl
        test eax, eax
        jne digit
        ret
    ''')
    # Front-facing native cage atlas, tinting the same alpha silhouette black.
    icon=emit('mastery_menu_spirit_icon',f'''
        push rbx
        push rsi
        push rdi
        sub rsp, 0x50
        mov edi, ecx
        mov esi, edx
        mov ebx, r8d
        mov ecx, r9d
        call 0x6c550
        mov eax, edi
        xor edx, edx
        mov ecx, 5
        div ecx
        imul eax, eax, 120
        imul edx, edx, 24
        cvtsi2ss xmm0, eax
        movss dword ptr [rsp+0x30], xmm0
        add eax, 24
        cvtsi2ss xmm0, eax
        movss dword ptr [rsp+0x40], xmm0
        cvtsi2ss xmm0, edx
        movss dword ptr [rsp+0x38], xmm0
        add edx, 24
        cvtsi2ss xmm0, edx
        movss dword ptr [rsp+0x48], xmm0
        mov dword ptr [rsp+0x20], 0x41900000
        mov dword ptr [rsp+0x28], 0x41900000
        cvtsi2ss xmm1, esi
        cvtsi2ss xmm2, ebx
        xorps xmm3, xmm3
        call {symbols['ui_draw_spirit_atlas']:#x}
        mov ecx, -1
        call 0x6c550
        add rsp, 0x50
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
    from mastery_badges import emit_badges
    badges=emit_badges(emit,mem,native)
    from spell_bonus_panel import emit_bonus_panel
    bonus=emit_bonus_panel(emit,mem,ui,data,choices,value,text,number,loc,string,payload,state,tabletext,usage)
    browser=emit_browser(emit,mem,ui,rows,payload,state,string,lineblock,lookup,availability,text,frame,icon,tabletext,loc,bonus,data,badges)
    native_input=emit('mastery_status_native_input','push rbx; push rbp; push rsi; push rdi; jmp 0x241965')
    inp=emit('mastery_status_input',f'''
        push rbx
        sub rsp, 0x20
        call {ready:#x}
        test eax, eax
        je native
        call {character:#x}
        cmp eax, 6
        ja native
        cmp byte ptr {mem(ui)}, 0
        jne panel
        call {entry_key:#x}
        test dword ptr {mem(0x8c9184)}, edx
        je native
        movzx edx, byte ptr {mem(0x111a674)}
        mov byte ptr {mem(ui+0xd)}, dl
        mov byte ptr {mem(ui)}, 1
        mov byte ptr {mem(ui+4)}, al
        mov byte ptr {mem(ui+3)}, 0
        call {rebuild:#x}
        jmp handled
    panel:
        cmp al, byte ptr {mem(ui+4)}
        je same_character
        mov byte ptr {mem(ui+4)}, al
        call {rebuild:#x}
    same_character:
        mov ebx, dword ptr {mem(0x8c9184)}
        # Triangle remains the page switch inside the mastery panel.
        test ebx, 0x8000
        jne close
        test ebx, 0x4000
        je category_input
        cmp byte ptr {mem(ui+6)}, 0
        je close
        mov byte ptr {mem(ui+6)}, 0
        jmp handled
    category_input:
        mov eax, ebx
        and eax, 0x300
        cmp eax, 0x100
        je previous_character
        cmp eax, 0x200
        je next_character
        jmp category_page
    previous_character:
        movzx ecx, byte ptr {mem(0x111a672)}
        cmp ecx, 2; jb handled
        cmp ecx, 7; ja handled
        movzx eax, byte ptr {mem(ui+0xd)}
        test eax, eax; jne decrement_character
        mov eax, ecx
    decrement_character:
        dec eax; jmp select_character
    next_character:
        movzx ecx, byte ptr {mem(0x111a672)}
        cmp ecx, 2; jb handled
        cmp ecx, 7; ja handled
        movzx eax, byte ptr {mem(ui+0xd)}
        inc eax
        cmp eax, ecx; jb select_character
        xor eax, eax
    select_character:
        mov byte ptr {mem(ui+0xd)}, al
        call {character:#x}
        cmp eax, 6; ja handled
        mov byte ptr {mem(ui+4)}, al
        cmp eax, 2; jb character_faculties
        cmp eax, 3; jbe rebuild_character
    character_faculties:
        mov byte ptr {mem(ui+3)}, 0
    rebuild_character:
        call {rebuild:#x}
        jmp handled
    category_page:
        test ebx, 0x1000
        je navigate
        cmp byte ptr {mem(ui+4)}, 2
        jb navigate
        cmp byte ptr {mem(ui+4)}, 3
        ja navigate
        xor byte ptr {mem(ui+3)}, 1
        call {rebuild:#x}
        jmp handled
    navigate:
        cmp byte ptr {mem(ui+5)}, 0
        je handled
        mov edx, dword ptr {mem(0x8c9188)}
        or edx, ebx
        cmp byte ptr {mem(ui+3)}, 0
        je faculty_navigation
        call {browser['input']:#x}
        test ebx, 0x2000
        je handled
        jmp toggle
    faculty_navigation:
        cmp byte ptr {mem(ui+6)}, 0
        jne directions
        test edx, 0x10
        je next_branch
        cmp byte ptr {mem(ui+1)}, 0
        je handled
        dec byte ptr {mem(ui+1)}
        mov byte ptr {mem(ui+2)}, 0
        jmp handled
    next_branch:
        test edx, 0x40
        je confirm_branch
        movzx eax, byte ptr {mem(ui+1)}
        inc eax
        cmp al, byte ptr {mem(ui+5)}
        jae handled
        mov byte ptr {mem(ui+1)}, al
        mov byte ptr {mem(ui+2)}, 0
        jmp handled
    confirm_branch:
        test ebx, 0x2000
        je handled
        mov byte ptr {mem(ui+6)}, 1
        mov byte ptr {mem(ui+2)}, 0
        jmp handled
    directions:
        mov r11d, edx
        movzx eax, byte ptr {mem(ui+1)}
        movzx edx, byte ptr {mem(ui+2)}
        call {lookup:#x}
        test r11d, 0x10
        je down
        mov eax, dword ptr [rdx+64]
        jmp select_node
    down:
        test r11d, 0x40
        je left
        mov eax, dword ptr [rdx+68]
        jmp select_node
    left:
        test r11d, 0x80
        je right
        mov eax, dword ptr [rdx+56]
        jmp select_node
    right:
        test r11d, 0x20
        je toggle
        mov eax, dword ptr [rdx+60]
    select_node:
        mov byte ptr {mem(ui+2)}, al
        jmp handled
    toggle:
        test ebx, 0x2000
        je handled
        movzx eax, byte ptr {mem(ui+1)}
        movzx edx, byte ptr {mem(ui+2)}
        call {lookup:#x}
        mov rbx, rcx
        call {status:#x}
        cmp eax, 3
        jb handled
        # Preferences remain editable while the global switch is off.
        movzx eax, byte ptr {mem(ui+1)}
        movzx edx, byte ptr {mem(ui+2)}
        call {lookup:#x}
        call {preference:#x}
        lea rdx, {mem(choices)}
        btc dword ptr [rdx], ecx
        jmp handled
    close:
        mov byte ptr {mem(ui)}, 0
    handled:
        xor eax, eax
        add rsp, 0x20
        pop rbx
        ret
    native:
        mov byte ptr {mem(ui)}, 0
        add rsp, 0x20
        pop rbx
        cmp byte ptr {mem(ui+0xc)}, 1
        jne native_status
        mov eax, 1
        ret
    native_status:
        jmp {native_input:#x}
    ''')
    status_entry=emit('mastery_status_entry',f'mov byte ptr {mem(ui+0xc)}, 0; jmp {inp:#x}')
    jump(0x241960,5,status_entry,'Mastery menu: Square from ready status; isolate tree navigation')

    hints=emit('mastery_menu_hints',f'''
        sub rsp, 0x28
        cmp qword ptr {mem(0x6449f8)}, 0
        je done
        mov ecx, 374
        xor edx, edx
        mov r8d, 0x4000
        {loc('back','r9')}
        mov dword ptr [rsp+0x20], 255
        call 0x21cbb0
        mov ecx, eax
        xor edx, edx
        mov r8d, 0x2000
        {loc('open_tree','r9')}
        cmp byte ptr {mem(ui+3)}, 0
        jne toggle_hint
        cmp byte ptr {mem(ui+6)}, 0
        je confirm_hint
    toggle_hint:
        {loc('toggle','r9')}
    confirm_hint:
        mov dword ptr [rsp+0x20], 255
        call 0x21cbb0
        mov ecx, eax
        mov dword ptr [rsp+0x24], ecx
        cmp byte ptr {mem(ui+4)}, 2
        jb no_tab
        cmp byte ptr {mem(ui+4)}, 3
        ja no_tab
        xor edx, edx
        mov r8d, 0x1000
        {loc('spells','r9')}
        cmp byte ptr {mem(ui+3)}, 0
        je tab_label
        {loc('faculties','r9')}
    tab_label:
        mov dword ptr [rsp+0x20], 255
        call 0x21cbb0
        mov ecx, eax
        mov dword ptr [rsp+0x24], ecx
    no_tab:
        mov ecx, dword ptr [rsp+0x24]
        xor edx, edx
        mov r8d, 0xf0
        {loc('choose','r9')}
        cmp byte ptr {mem(ui+6)}, 0
        je navigation_hint
        {loc('browse','r9')}
    navigation_hint:
        mov dword ptr [rsp+0x20], 255
        call 0x21cbb0
        mov ecx, eax
        xor edx, edx
        mov r8d, 0x300
        {loc('character','r9')}
        mov dword ptr [rsp+0x20], 255
        call 0x21cbb0
    done:
        add rsp, 0x28
        ret
    ''')
    def label(name,x,y,width=390,color=0xffeeeeee):
        return f'''{loc(name)}
            mov edx, {x}
            mov r8d, {y}
            mov r9d, {width}
            mov eax, {color}
            call {text:#x}'''
    from mastery_tree_renderer import emit_tree_draw
    draw=emit_tree_draw(emit,mem,ui,data,lookup,value,status,icon,frame,text,number,hints,
                       loc,tabletext,label,names,string,browser,payload,state,badges)
    from basic_attack_mastery import emit_basic_attacks
    payload.extend(b'\0'*((-len(payload))%16))
    basic_attacks=emit_basic_attacks(emit,mem,jump,data,state+len(payload),choices)
    payload.extend(b'\0'*basic_attacks['size'])
    from fighter_faculties import emit_fighter_faculties
    fighter_faculties=emit_fighter_faculties(emit,mem,jump,data,state+len(payload),choices,expansion)
    payload.extend(b'\0'*fighter_faculties['size'])
    from fighter_arte_chains import emit_fighter_chains
    fighter_chains=emit_fighter_chains(emit,mem,jump,data,state+len(payload),choices,expansion)
    payload.extend(b'\0'*fighter_chains['size'])
    # Capture the actual left edge returned by every native Stats hint. The
    # final call varies with title focus and party size, so capture all tails.
    for site in (0x24167f,0x2416e1,0x241786,0x2417f6,0x241860):
        capture=emit(f'mastery_status_hint_edge_{site:x}',f'''
            call 0x21c6c0
            mov dword ptr {mem(ui+8)}, eax
            jmp {site+5:#x}
        ''')
        jump(site,5,capture,'Mastery: follow the native Stats hint row')
    native_draw=emit('mastery_status_native_draw','mov rax, rsp; mov qword ptr [rax+8], rbx; jmp 0x23fa07')
    entry_hint=emit('mastery_status_entry_hint',f'''
        sub rsp, 0x28
        cmp qword ptr {mem(0x6449f8)}, 0
        je done
        mov ecx, dword ptr {mem(ui+8)}
        test ecx, ecx
        js done
        xor edx, edx
        call {entry_key:#x}
        mov r8d, edx
        xor edx, edx
        {loc('entry','r9')}
        mov dword ptr [rsp+0x20], 255
        call 0x21cbb0
    done:
        add rsp, 0x28
        ret
    ''')
    render=emit('mastery_status_render',f'''
        sub rsp, 0x28
        mov byte ptr {mem(ui+0xc)}, 0
        cmp byte ptr {mem(ui)}, 0
        je native
        call {ready:#x}
        test eax, eax
        je native
        call {draw:#x}
        jmp done
    native:
        mov byte ptr {mem(ui)}, 0
        mov dword ptr {mem(ui+8)}, -1
        call {native_draw:#x}
        call {ready:#x}
        test eax, eax
        je done
        call {character:#x}
        cmp eax, 6
        ja done
        call {entry_hint:#x}
    done:
        add rsp, 0x28
        ret
    ''')
    jump(0x23fa00,7,render,'Mastery menu: native status entry hint and tree renderer')
    tech_input=emit('mastery_tech_input',f'mov byte ptr {mem(ui+0xc)}, 1; jmp {inp:#x}')
    tech_draw=emit('mastery_tech_draw',f'''
        sub rsp, 0x28
        mov byte ptr {mem(ui+0xc)}, 1
        mov dword ptr {mem(ui+8)}, -1
        cmp byte ptr {mem(ui)}, 0
        je native
        call {ready:#x}
        test eax, eax
        je native
        call {draw:#x}
        mov eax, 1
        jmp done
    native:
        mov byte ptr {mem(ui)}, 0
        xor eax, eax
    done:
        add rsp, 0x28
        ret
    ''')
    tech_hint=emit('mastery_tech_hint',f'''
        sub rsp, 0x28
        call {ready:#x}
        test eax, eax
        je done
        call {entry_hint:#x}
    done:
        add rsp, 0x28
        ret
    ''')
    for site in (0x227dc4,0x227e88,0x227f00,0x227fd9,0x228053,0x22810c,0x228216,
                 0x228285,0x228371,0x228437,0x2284b1,0x22856a,0x2286a1,0x228710,
                 0x2287e1,0x22888f,0x2288fe,0x228978,0x228a34):
        edge=emit(f'mastery_tech_hint_edge_{site:x}',f'call 0x21c6c0; mov dword ptr {mem(ui+8)}, eax; jmp {site+5:#x}')
        jump(site,5,edge,'Mastery: follow the native Techniques hint row')
    payload.extend(b'\0'*((-len(payload))%0x1000))
    return dict(state_rva=ui, choices=preferences_info(pref), data_rva=state, size=len(payload),
        rows=rows, spell_browser=browser, basic_attacks=basic_attacks, fighter_faculties=fighter_faculties, fighter_chains=fighter_chains, table_rva=state, row_size=32,node_size=NODE_SIZE,
        tech_input=tech_input,tech_draw=tech_draw,tech_hint=tech_hint,
        entry='Square from status; Square in semi-auto/manual Techniques, Triangle in auto Techniques',
        preview_faculties=True, previews_have_gameplay_effects=False,
        unopened_craymels='black native silhouette; hidden names and faculties; acquisition and level requirements visible',
        spell_switch='per character and spell, applies to all usage tiers',
        energy_switch='six independent saved faculty bits 128..133 for Farah',
        navigation='persistent left sidebar and live tree; confirm focuses nodes; Back returns to the list',
        tree_root=dict(rect=ROOT,origin=ORIGIN), selection_phase_offset=6,
        input_mouse=False, runtime_validated=False),bytes(payload)


def preferences_info(pref):
    return dict(pref, default='zero disable bits: enabled', per_character=True, per_save=True)
