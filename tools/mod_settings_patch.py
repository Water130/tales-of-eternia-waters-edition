"""Water's Edition title menu, native input/font rendering and per-user INI.

French text language is byte 3 at 11c9ce8 (confirmed against the running
French message table); voice language at the next byte is deliberately ignored.
No game save or native options structure is extended. No runtime code writes.
"""
import struct

FEATURES = [
    ('DynamicCamera', 'Caméra dynamique', 'Dynamic camera'),
    ('VictoryTP', 'PT après le combat', 'Post-battle TP recovery'),
    ('BasicHitTP', 'PT par coup physique de base', 'TP from basic physical hits'),
    ('DamageColors', 'Couleurs des dégâts', 'Elemental damage colors'),
    ('CustomHUD', 'HUD personnalisé', 'Custom HUD'),
    ('CastBars', "Barres d'incantation", 'Casting progress bars'),
    ('ItemBar', "Barre de recharge des objets", 'Item cooldown bar'),
    ('SkitNotice', 'Notification des saynètes', 'Skit notification'),
    ('DifficultyRebalance', 'Difficultés rééquilibrées', 'Rebalanced difficulties'),
    ('MultipleMaxVitality', 'Vitalités multiples au MAX', 'Multiple MAX vitality gauges'),
    ('GuardSpellCancel', 'Annulation de sort par garde', 'Guard cancels casting'),
    ('MageGuardJump', 'Saut des mages : Garde + Haut', 'Mage jump: Guard + Up'),
    ('SpellMastery', 'Maîtrise des sorts', 'Spell mastery'),
    ('FighterGuardJump', 'Saut Reid/Farah : Garde + Haut', 'Reid/Farah jump: Guard + Up'),
    ('FarahEnergyBar', 'Barre Énergie de Farah', 'Farah Energy gauge'),
    ('ArteCategoryLabels', 'Catégories des artes', 'Arte category labels'),
    ('SkitShortcut', 'Lecture rapide des saynètes', 'Quick skit playback'),
    ('FarahEnergyMastery', 'Facultés Énergie de Farah', 'Farah Energy faculties'),
]

# Preserve the sixteen existing flag addresses and the menu control bytes.
# Extra flags/snapshots have their own bank, leaving room for future options.
FLAG_OFFSETS = [0x1a00+i if i < 16 else 0x1a40+i-16 for i in range(len(FEATURES))]

# Display order only: persistent feature IDs, flag banks and INI keys stay fixed.
CATEGORIES = [
    ('Quality of Life', 'Quality of Life', [0,3,4,5,6,7,16,15]),
    ('Combat', 'Combat', [1,2,8,9,10,11,13]),
    ('Progression', 'Progression', [12,14,17]),
    ('Autres', 'Other', [len(FEATURES)+1]),
]


def emit_settings(emit, mem, jump, data, symbols):
    count = len(FEATURES)
    header = count
    keyboard = count + 1
    category_first = count + 2
    assert sorted(i for _,_,ids in CATEGORIES for i in ids)==list(range(count))+[keyboard]
    assert count <= 32
    row_step, visible_rows = 17, 10
    payload = bytearray()
    strings = {}
    def string(name, text, wide=False):
        if wide and len(payload)&1:payload.append(0)
        strings[name] = data+0x2000+len(payload)
        payload.extend((text+'\0').encode('utf-16-le' if wide else 'utf-8'))
        return strings[name]
    string('kernel','kernel32.dll')
    for name in ('GetEnvironmentVariableW','GetPrivateProfileIntW','WritePrivateProfileStringW'):string(name,name)
    for name,text in [('environment','LOCALAPPDATA'),('suffix','\\TalesOfEternia-WatersEdition.ini'),('section','Features'),('zero','0'),('one','1')]:string(name,text,True)
    for index,(key,fr,en) in enumerate(FEATURES):
        string(f'key{index}',key,True);string(f'fr{index}',fr);string(f'en{index}',en)
    for name,fr,en in [
        ('menu','Options de mods','Mod settings'),
        ('keyboard','Commandes clavier (PC)','Keyboard controls (PC)'),
        ('open','Configurer','Configure'),
        ('enter','Ouvrir','Open'),
        ('heading',"Water's Edition — Options de mods","Water's Edition — Mod settings"),
        ('on','Activé','On'),('off','Désactivé','Off'),
        ('back','Retour','Back'),('select','Sélect.','Select'),('modify','Modifier','Modify'),
        ('confirm','Valider','Confirm'),('reset','Réinit.','Reset'),('default','Défaut','Default'),
        ('saved','Réglages enregistrés automatiquement','Settings are saved automatically'),
        ('error','Échec de sauvegarde : réglages valables pour cette session','Could not save: settings apply to this session only'),
    ]:
        string(name+'_fr',fr);string(name+'_en',en)
    string('brand',"Water's Edition")
    string('cursor','>')
    string('scroll_up','^');string('scroll_down','v')
    for i,(fr,en,_) in enumerate(CATEGORIES):
        string(f'category{i}_fr',fr);string(f'category{i}_en',en)
    # Tables contain RVAs, not absolute addresses; they survive ASLR.
    payload.extend(b'\0'*((-len(payload))%4))
    table=data+0x2000+len(payload)
    for index in range(count):
        payload.extend(struct.pack('<III',strings[f'key{index}'],strings[f'fr{index}'],strings[f'en{index}']))
    item_labels=data+0x2000+len(payload)
    for index in range(count):
        payload.extend(struct.pack('<2I',strings[f'fr{index}'],strings[f'en{index}']))
    for name in ['reset','keyboard']+[f'category{i}' for i in range(len(CATEGORIES))]:
        payload.extend(struct.pack('<2I',strings[name+'_fr'],strings[name+'_en']))
    menus=[list(range(category_first,category_first+len(CATEGORIES)))+[header]]+[ids for _,_,ids in CATEGORIES]
    menu_entries=[]
    for ids in menus:
        menu_entries.append((data+0x2000+len(payload),len(ids)))
        payload.extend(bytes(ids))
    payload.extend(b'\0'*((-len(payload))%4))
    menu_table=data+0x2000+len(payload)
    for entry in menu_entries:payload.extend(struct.pack('<2I',*entry))
    assert len(payload)<0x1000
    flags=data+0x1a00
    initialized=data+0x1a10
    page=data+0x1a11
    selection=data+0x1a12
    error=data+0x1a13
    reset_choice=data+0x1a14
    scroll_top=data+0x1a15
    category_state=data+0x1a16 # zero = category list; 1..4 = category contents
    snapshot=data+0x1a20
    address_serial = 0
    def indexed_flag(register, index, opening=False):
        nonlocal address_serial
        address_serial += 1
        label = f'flag_address_{address_serial}'
        return f'''lea {register}, {mem(snapshot if opening else flags)}
            cmp {index}, 16
            jb {label}
            add {register}, {0x20 if opening else 0x30}
        {label}:'''
    path=data+0x3000
    def address(name):return mem(strings[name])
    def localized(name,register='rcx'):
        return f'''lea {register}, {address(name+'_en')}
            cmp byte ptr {mem(0x11c9ce8)}, 3
            jne language_{name}_{register}
            lea {register}, {address(name+'_fr')}
        language_{name}_{register}:'''

    initialize=emit('settings_initialize',f'''
        cmp byte ptr {mem(initialized)}, 0
        jne fast_return
        push rbx
        push rsi
        push rdi
        sub rsp, 0x20
        mov byte ptr {mem(initialized)}, 2
        mov byte ptr {mem(error)}, 1
        lea rcx, {address('kernel')}
        call qword ptr {mem(0x2a9058)}
        test rax, rax
        je done
        mov rbx, rax
        mov rcx, rbx
        lea rdx, {address('GetEnvironmentVariableW')}
        call qword ptr {mem(0x2a9060)}
        mov qword ptr {mem(data+0x1b00)}, rax
        test rax, rax
        je done
        mov rcx, rbx
        lea rdx, {address('GetPrivateProfileIntW')}
        call qword ptr {mem(0x2a9060)}
        mov qword ptr {mem(data+0x1b08)}, rax
        test rax, rax
        je done
        mov rcx, rbx
        lea rdx, {address('WritePrivateProfileStringW')}
        call qword ptr {mem(0x2a9060)}
        mov qword ptr {mem(data+0x1b10)}, rax
        test rax, rax
        je done
        lea rcx, {address('environment')}
        lea rdx, {mem(path)}
        mov r8d, 960
        call qword ptr {mem(data+0x1b00)}
        test eax, eax
        je done
        cmp eax, 960
        jae done
        lea rdi, {mem(path)}
        lea rdi, [rdi+rax*2]
        lea rsi, {address('suffix')}
    copy_suffix:
        movzx eax, word ptr [rsi]
        mov word ptr [rdi], ax
        add rsi, 2
        add rdi, 2
        test ax, ax
        jne copy_suffix
        xor edi, edi
        lea rsi, {mem(table)}
        lea rbx, {mem(0)}
    load:
        lea rcx, {address('section')}
        mov edx, dword ptr [rsi]
        add rdx, rbx
        mov r8d, 1
        lea r9, {mem(path)}
        call qword ptr {mem(data+0x1b08)}
        test eax, eax
        setne al
        {indexed_flag('rdx', 'rdi')}
        mov byte ptr [rdx+rdi], al
        add rsi, 12
        inc edi
        cmp edi, {count}
        jb load
        mov byte ptr {mem(initialized)}, 1
        mov byte ptr {mem(error)}, 0
    done:
        add rsp, 0x20
        pop rdi
        pop rsi
        pop rbx
    fast_return:
        ret
    ''')
    save=emit('settings_save_selected',f'''
        sub rsp, 0x28
        mov byte ptr {mem(error)}, 1
        cmp byte ptr {mem(initialized)}, 1
        jne done
        movzx eax, byte ptr {mem(selection)}
        cmp eax, {count}
        jae done
        {indexed_flag('rdx', 'rax')}
        lea r8, {address('zero')}
        cmp byte ptr [rdx+rax], 0
        je value_ready
        lea r8, {address('one')}
    value_ready:
        imul eax, eax, 12
        lea rdx, {mem(table)}
        mov edx, dword ptr [rdx+rax]
        lea rax, {mem(0)}
        add rdx, rax
        lea rcx, {address('section')}
        lea r9, {mem(path)}
        call qword ptr {mem(data+0x1b10)}
        test eax, eax
        sete byte ptr {mem(error)}
    done:
        add rsp, 0x28
        ret
    ''')
    restore=emit('settings_restore',f'''
        push rbx
        push rsi
        sub rsp, 0x28
        xor ebx, ebx
        xor esi, esi
    next:
        mov al, 1
        cmp byte ptr {mem(reset_choice)}, 0
        jne default_value
        {indexed_flag('rdx', 'rbx', True)}
        mov al, byte ptr [rdx+rbx]
    default_value:
        {indexed_flag('rdx', 'rbx')}
        mov byte ptr [rdx+rbx], al
        mov byte ptr {mem(selection)}, bl
        call {save:#x}
        or sil, byte ptr {mem(error)}
        inc ebx
        cmp ebx, {count}
        jb next
        mov byte ptr {mem(selection)}, {header}
        mov byte ptr {mem(error)}, sil
        add rsp, 0x28
        pop rsi
        pop rbx
        ret
    ''')

    # The first mouse poll can otherwise hover/click the native menu through
    # the opaque panel, before the controller dispatch below is reached.
    mouse=emit('settings_title_mouse_poll',f'''
        cmp byte ptr {mem(page)}, 0
        jne blocked
        call 0x1a5d0
        jmp 0x1b8f9a
    blocked:
        xor eax, eax
        jmp 0x1b8f9a
    ''')
    jump(0x1b8f95,5,mouse,'Prevent native mouse actions behind the mod settings panel')

    # Entry immediately before native mouse/action dispatch. While the panel
    # is open, consume its input, including the native Quit shortcut.
    menu_items=emit('settings_menu_items',f'''
        movzx eax, byte ptr {mem(category_state)}
        cmp eax, {len(CATEGORIES)}
        jbe valid
        xor eax, eax
        mov byte ptr {mem(category_state)}, 0
    valid:
        lea rdx, {mem(menu_table)}
        lea rdx, [rdx+rax*8]
        mov ecx, dword ptr [rdx+4]
        mov edx, dword ptr [rdx]
        lea rax, {mem(0)}
        add rdx, rax
        ret
    ''')
    menu_index=emit('settings_menu_index',f'''
        sub rsp, 0x28
        call {menu_items:#x}
        movzx r8d, byte ptr {mem(selection)}
        xor eax, eax
    find:
        cmp r8b, byte ptr [rdx+rax]
        je done
        inc eax
        cmp eax, ecx
        jb find
        xor eax, eax
        mov r8b, byte ptr [rdx]
        mov byte ptr {mem(selection)}, r8b
    done:
        add rsp, 0x28
        ret
    ''')
    item_label=emit('settings_item_label',f'''
        lea rcx, {mem(item_labels)}
        lea rcx, [rcx+rax*8]
        cmp byte ptr {mem(0x11c9ce8)}, 3
        je french
        add rcx, 4
    french:
        mov ecx, dword ptr [rcx]
        lea rax, {mem(0)}
        add rcx, rax
        ret
    ''')
    panel_input=emit('settings_panel_input',f'''
        cmp byte ptr {mem(page)}, 0
        je native
        mov dword ptr {mem(0x10e1c8c)}, 0x4650
        cmp byte ptr {mem(page)}, 2
        je keyboard_input
        cmp esi, 0x4000
        je back
        cmp esi, 8
        je back
        call {menu_index:#x}
        cmp r13d, 0x10
        jne down
        dec eax
        jns selected
        lea eax, [rcx-1]
        jmp selected
    down:
        cmp r13d, 0x40
        jne action
        inc eax
        cmp eax, ecx
        jb selected
        xor eax, eax
    selected:
        mov al, byte ptr [rdx+rax]
        mov byte ptr {mem(selection)}, al
        mov edi, 0x8d
        jmp handled
    keyboard_input:
        mov eax, dword ptr {mem(data+0x1a30)}
        test eax, eax
        je handled
        lea rcx, {mem(0)}
        add rax, rcx
        call rax
        jmp handled
    action:
        movzx eax, byte ptr [rdx+rax]
        cmp byte ptr {mem(category_state)}, 0
        jne category_action
        cmp eax, {header}
        je header_action
        cmp esi, 0x2000
        jne handled
        sub eax, {category_first-1}
        mov byte ptr {mem(category_state)}, al
        mov byte ptr {mem(scroll_top)}, 0
        call {menu_items:#x}
        mov al, byte ptr [rdx]
        mov byte ptr {mem(selection)}, al
        mov edi, 0x8e
        jmp handled
    category_action:
        cmp eax, {keyboard}
        jne feature_action
        cmp esi, 0x2000
        jne handled
        cmp dword ptr {mem(data+0x1a30)}, 0
        je handled
        mov byte ptr {mem(page)}, 2
        jmp handled
    feature_action:
        cmp esi, 0x2000
        je toggle
        cmp esi, 0x20
        je toggle
        cmp esi, 0x80
        jne handled
    toggle:
        cmp eax, {count}
        jae handled
        {indexed_flag('rdx', 'rax')}
        xor byte ptr [rdx+rax], 1
        call {save:#x}
        mov edi, 0x8e
        jmp handled
    header_action:
        cmp esi, 0x2000
        je restore_values
        cmp esi, 0x20
        je header_right
        cmp esi, 0x80
        jne handled
        mov byte ptr {mem(reset_choice)}, 0
        jmp header_changed
    header_right:
        mov byte ptr {mem(reset_choice)}, 1
    header_changed:
        mov edi, 0x8d
        jmp handled
    restore_values:
        call {restore:#x}
        mov edi, 0x8e
        jmp handled
    back:
        movzx eax, byte ptr {mem(category_state)}
        test eax, eax
        je close
        add eax, {category_first-1}
        mov byte ptr {mem(selection)}, al
        mov byte ptr {mem(category_state)}, 0
        mov byte ptr {mem(scroll_top)}, 0
        mov edi, 0x8f
        jmp handled
    close:
        mov byte ptr {mem(page)}, 0
        mov edi, 0x8f
    handled:
        xor r14d, r14d
        jmp 0x1b98d7
    native:
        movzx r8d, byte ptr {mem(0x8624ae)}
        jmp 0x1b9110
    ''')
    jump(0x1b9108,8,panel_input,'Consume mod panel input without opening native title actions')
    navigation=emit('settings_title_navigation',f'''
        movzx r8d, word ptr {mem(0x10e1d3c)}
        test r8d, r8d
        jne native
        mov rcx, qword ptr {mem(0x11cc540)}
        mov eax, ecx
        and eax, 2
        shr eax, 1
        add eax, 5
        movzx edx, word ptr {mem(0xbb1c64)}
        cmp r13d, 0x10
        jne down
        dec edx
        jns changed
        lea edx, [rax-1]
        jmp changed
    down:
        cmp r13d, 0x40
        jne action
        inc edx
        cmp edx, eax
        jb changed
        xor edx, edx
    changed:
        mov word ptr {mem(0xbb1c64)}, dx
        mov edi, 0x8d
    action:
        dec eax
        cmp edx, eax
        jne continue_native
        cmp esi, 0x2000
        jne continue_native
        call {initialize:#x}
        mov rax, qword ptr {mem(flags)}
        mov qword ptr {mem(snapshot)}, rax
        mov rax, qword ptr {mem(flags+8)}
        mov qword ptr {mem(snapshot+8)}, rax
        mov rax, qword ptr {mem(data+0x1a40)}
        mov qword ptr {mem(data+0x1a50)}, rax
        mov rax, qword ptr {mem(data+0x1a48)}
        mov qword ptr {mem(data+0x1a58)}, rax
        mov byte ptr {mem(reset_choice)}, 0
        mov byte ptr {mem(page)}, 1
        mov byte ptr {mem(selection)}, {category_first}
        mov byte ptr {mem(category_state)}, 0
        mov byte ptr {mem(scroll_top)}, 0
        mov edi, 0x8e
        xor r14d, r14d
        jmp 0x1b98d7
    continue_native:
        mov r10d, 2
        mov r11d, 3
        jmp 0x1b9417
    native:
        jmp 0x1b92bf
    ''')
    jump(0x1b92b7,8,navigation,'Append Mod settings after every existing title entry')

    # Private ABI: UTF-8 RCX, X EDX, Y R8D, size R9D, ABGR EAX.
    # A negative size selects left alignment; positive sizes are centered.
    text=emit('settings_text',f'''
        push rbx
        push rbp
        push rsi
        push rdi
        sub rsp, 0x68
        mov rbx, rcx
        mov ebp, edx
        mov esi, r8d
        mov edi, r9d
        mov dword ptr [rsp+0x58], eax
        test edi, edi
        jns centered
        neg edi
        cvtsi2ss xmm1, ebp
        jmp positioned
    centered:
        cvtsi2ss xmm1, edi
        cmp qword ptr {mem(0x644a18)}, 0
        je measure
        movzx eax, byte ptr {mem(0x11c9ce8)}
        lea edx, [rax-1]
        cmp edx, 5
        jbe adjusted
        cmp eax, 10
        jb measure
    adjusted:
        addss xmm1, dword ptr {mem(0x524860)}
    measure:
        xor r8d, r8d
        xor r9d, r9d
        mov dword ptr [rsp+0x20], 0
        mov dword ptr [rsp+0x28], -1
        call 0xb240
        mulss xmm0, dword ptr {mem(0x524860)}
        cvtsi2ss xmm1, ebp
        subss xmm1, xmm0
    positioned:
        cvtsi2ss xmm2, esi
        xorps xmm3, xmm3
        cvtsi2ss xmm0, edi
        movss dword ptr [rsp+0x20], xmm0
        mov eax, dword ptr [rsp+0x58]
        mov dword ptr [rsp+0x28], eax
        mov dword ptr [rsp+0x30], 0
        mov dword ptr [rsp+0x38], 0
        mov dword ptr [rsp+0x40], 0
        mov dword ptr [rsp+0x48], 0x3f800000
        mov rcx, rbx
        call 0xb480
        add rsp, 0x68
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
    from title_logo_patch import emit_title_logo
    logo, logo_png, logo_info = emit_title_logo(emit, mem, data)
    # Native Options text ABI, including fractional font size and automatic
    # horizontal fitting. RCX string, EDX X, R8D Y, R9D max width, EAX ABGR.
    field=emit('settings_field',f'''
        sub rsp, 0x58
        cvtsi2ss xmm1, edx
        cvtsi2ss xmm2, r8d
        xorps xmm3, xmm3
        mov dword ptr [rsp+0x28], eax
        cvtsi2ss xmm0, r9d
        movss dword ptr [rsp+0x40], xmm0
        mov dword ptr [rsp+0x20], 0x41080000
        mov dword ptr [rsp+0x30], 0
        mov dword ptr [rsp+0x38], 0
        mov dword ptr [rsp+0x48], 0x3f800000
        call 0xb480
        add rsp, 0x58
        ret
    ''')
    # Scroll a fixed-height viewport; keep stable option IDs and INI keys.
    scroll=emit('settings_scroll',f'''
        sub rsp, 0x28
        call {menu_index:#x}
        movzx r9d, byte ptr {mem(scroll_top)}
        sub ecx, {visible_rows}
        xor edx, edx
        cmp ecx, edx
        cmovl ecx, edx
        cmp r9d, ecx
        cmova r9d, ecx
        cmp byte ptr {mem(selection)}, {header}
        je done
        cmp eax, r9d
        cmovb r9d, eax
        lea edx, [r9+{visible_rows}]
        cmp eax, edx
        jb done
        lea r9d, [rax-{visible_rows-1}]
    done:
        mov byte ptr {mem(scroll_top)}, r9b
        add rsp, 0x28
        ret
    ''')
    # Use the same capsule, nine-slice frame and gradient as 1349f0.
    # Window RGB comes from saved options, not uninitialized menu scratch.
    backdrop=emit('settings_backdrop',f'''
        sub rsp, 0x58
        mov rcx, qword ptr {mem(0x644a10)}
        test rcx, rcx
        je done
        cmp qword ptr [rcx+0x4d0], 0
        je done
        movsxd rax, dword ptr [rcx+0x4e0]
        add rax, 180
        cmp rax, qword ptr [rcx+0x4d8]
        jae done
        mov rax, qword ptr {mem(0x644a58)}
        test rax, rax
        je done
        cmp dword ptr [rax+0x2000008], 0x1fff000
        ja done
        cmp qword ptr {mem(0x11c9e18)}, 0
        je done
        call 0x21c460
        mov ecx, -54
        mov edx, 15
        xor r8d, r8d
        mov r9d, 61
        mov dword ptr [rsp+0x20], 0
        lea rax, {mem(0x11cc57c)}
        mov qword ptr [rsp+0x28], rax
        mov dword ptr [rsp+0x30], 255
        call 0x25a090
        cmp byte ptr {mem(category_state)}, 0
        jne body
        mov ecx, 297
        mov edx, 16
        xor r8d, r8d
        mov r9d, 77
        mov dword ptr [rsp+0x20], 18
        lea rax, {mem(0x11cc57c)}
        mov qword ptr [rsp+0x28], rax
        mov dword ptr [rsp+0x30], 255
        call 0x25aaa0
    body:
        mov ecx, -55
        mov edx, 34
        xor r8d, r8d
        mov r9d, 429
        mov dword ptr [rsp+0x20], 191
        lea rax, {mem(0x11cc57c)}
        mov qword ptr [rsp+0x28], rax
        mov dword ptr [rsp+0x30], 255
        call 0x25aaa0
        call {scroll:#x}
        cmp byte ptr {mem(selection)}, {header}
        je done
        call {menu_index:#x}
        mov edx, eax
        movzx eax, byte ptr {mem(scroll_top)}
        sub edx, eax
        imul edx, edx, {row_step}
        add edx, 55
        cvtsi2ss xmm1, edx
        mov eax, 31
        cvtsi2ss xmm0, eax
        xorps xmm2, xmm2
        mov eax, 209
        cvtsi2ss xmm3, eax
        mov dword ptr [rsp+0x20], 0x41080000
        mov dword ptr [rsp+0x30], 0xbf800000
        mov dword ptr [rsp+0x40], 0x40000000
        mov dword ptr [rsp+0x48], 255
        call 0x24490
    done:
        add rsp, 0x58
        ret
    ''')
    # 21cbb0 -> 21c6c0 -> 140c0 -> 13d70 resolves current keyboard bindings
    # and controller glyph family each frame. No hard-coded key names/icons.
    hints=emit('settings_hints',f'''
        sub rsp, 0x28
        cmp qword ptr {mem(0x6449f8)}, 0
        je done
        mov ecx, 374
        xor edx, edx
        mov r8d, 0x4000
        {localized('back','r9')}
        mov dword ptr [rsp+0x20], 255
        call 0x21cbb0
        mov ecx, eax
        xor edx, edx
        mov r8d, 0x50
        {localized('select','r9')}
        mov dword ptr [rsp+0x20], 255
        call 0x21cbb0
        mov ecx, eax
        xor edx, edx
        mov r8d, 0xa0
        {localized('modify','r9')}
        cmp byte ptr {mem(selection)}, {header}
        jb modify
        mov r8d, 0x2000
        {localized('confirm','r9')}
    modify:
        mov dword ptr [rsp+0x20], 255
        call 0x21cbb0
    done:
        add rsp, 0x28
        ret
    ''')
    draw=emit('settings_draw',f'''
        push rbx
        push rbp
        push rsi
        push rdi
        sub rsp, 0xf8
        call {initialize:#x}
        cmp byte ptr {mem(page)}, 0
        jne panel
        cmp word ptr {mem(0x10e1d3c)}, 0
        jne done
        mov ebx, dword ptr {mem(0x11cc540)}
        and ebx, 2
        shr ebx, 1
        add ebx, 4
        mov r8d, 12
        cmp byte ptr {mem(0x861919)}, 0
        je spacing
        mov r8d, 14
    spacing:
        imul r8d, ebx
        add r8d, 176
        {localized('menu')}
        mov edx, 240
        mov r9d, 9
        mov eax, 0xfffffdfa
        cmp word ptr {mem(0xbb1c64)}, bx
        jne draw_entry
        mov eax, 0xff51ff4b
    draw_entry:
        call {text:#x}
        jmp done
    panel:
        cmp byte ptr {mem(page)}, 2
        jne normal_panel
        mov eax, dword ptr {mem(data+0x1a34)}
        test eax, eax
        je done
        lea rcx, {mem(0)}
        add rax, rcx
        call rax
        jmp done
    normal_panel:
        call {backdrop:#x}
        {localized('menu','r10')}
        mov rcx, r10
        movzx eax, byte ptr {mem(category_state)}
        test eax, eax
        je heading_ready
        add eax, {category_first-1}
        call {item_label:#x}
    heading_ready:
        mov edx, 33
        mov r8d, 34
        mov r9d, 68
        mov eax, 0xfffffdfa
        call {field:#x}
        cmp byte ptr {mem(category_state)}, 0
        jne start_list
        {localized('reset')}
        mov edx, 387
        mov r8d, 36
        mov r9d, 29
        mov eax, 0xfffffdfa
        cmp byte ptr {mem(reset_choice)}, 0
        je reset_text
        mov eax, 0xff808080
    reset_text:
        call {field:#x}
        {localized('default')}
        mov edx, 420
        mov r8d, 36
        mov r9d, 31
        mov eax, 0xff808080
        cmp byte ptr {mem(reset_choice)}, 0
        je default_text
        mov eax, 0xfffffdfa
    default_text:
        call {field:#x}
    start_list:
        movzx ebp, byte ptr {mem(scroll_top)}
        mov ebx, ebp
        call {menu_items:#x}
        mov rsi, rdx
        mov edi, ecx
    row:
        cmp ebx, edi
        jae list_end
        movzx eax, byte ptr [rsi+rbx]
        cmp eax, {header}
        je list_end
        call {item_label:#x}
        mov edx, 34
        mov r8d, ebx
        sub r8d, ebp
        imul r8d, r8d, {row_step}
        add r8d, 55
        mov r9d, 111
        mov eax, 0xff49bfff
        call {field:#x}
        movzx eax, byte ptr [rsi+rbx]
        cmp eax, {count}
        jae open_item
        mov edx, 150
        mov r8d, ebx
        sub r8d, ebp
        imul r8d, r8d, {row_step}
        add r8d, 55
        xor r9d, r9d
        {indexed_flag('rcx', 'rax')}
        cmp byte ptr [rcx+rax], 0
        mov eax, 0xff808080
        je on_inactive
        mov eax, 0xfffffdfa
    on_inactive:
        {localized('on','rcx')}
        call {field:#x}
        mov edx, 190
        mov r8d, ebx
        sub r8d, ebp
        imul r8d, r8d, {row_step}
        add r8d, 55
        xor r9d, r9d
        movzx eax, byte ptr [rsi+rbx]
        {indexed_flag('rcx', 'rax')}
        cmp byte ptr [rcx+rax], 0
        mov eax, 0xfffffdfa
        je off_active
        mov eax, 0xff808080
    off_active:
        {localized('off','rcx')}
        call {field:#x}
        jmp next_row
    open_item:
        {localized('enter')}
        cmp byte ptr [rsi+rbx], {keyboard}
        jne open_ready
        {localized('open')}
    open_ready:
        mov edx, 150
        mov r8d, ebx
        sub r8d, ebp
        imul r8d, r8d, {row_step}
        add r8d, 55
        mov r9d, 80
        mov eax, 0xfffffdfa
        call {field:#x}
    next_row:
        inc ebx
        lea eax, [rbp+{visible_rows}]
        cmp ebx, eax
        jb row
    list_end:
        test ebp, ebp
        je below
        lea rcx, {address('scroll_up')}
        mov edx, 238
        mov r8d, 52
        mov r9d, 9
        mov eax, 0xffffad61
        call {field:#x}
    below:
        lea eax, [rbp+{visible_rows}]
        cmp eax, edi
        jae list_cursor
        lea rcx, {address('scroll_down')}
        mov edx, 238
        mov r8d, 216
        mov r9d, 9
        mov eax, 0xffffad61
        call {field:#x}
    list_cursor:
        cmp byte ptr {mem(selection)}, {header}
        je header_cursor
        call {menu_index:#x}
        movzx r10d, byte ptr [rdx+rax]
        sub eax, ebp
        imul r8d, eax, {row_step}
        add r8d, 43
        mov edx, 55
        cmp r10d, {count}
        jae cursor
        {indexed_flag('rcx', 'r10')}
        movzx edx, byte ptr [rcx+r10]
        imul edx, edx, -40
        add edx, 95
        jmp cursor
    header_cursor:
        movzx edx, byte ptr {mem(reset_choice)}
        imul edx, edx, 33
        add edx, 292
        mov r8d, 24
    cursor:
        mov ecx, 1
        mov r9d, 2
        mov dword ptr [rsp+0x20], 255
        call 0x250b50
        call {hints:#x}
        cmp byte ptr {mem(error)}, 0
        jne failure
        {localized('saved')}
        mov eax, 0xffd8bca0
        jmp footer
    failure:
        {localized('error')}
        mov eax, 0xff9090ff
    footer:
        mov edx, 240
        mov r8d, 232
        mov r9d, 6
        call {text:#x}
        mov eax, dword ptr {mem(data+0x1a38)}
        test eax, eax
        je done
        lea rcx, {mem(0)}
        add rax, rcx
        call rax
    done:
        add rsp, 0xf8
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
    # Mid-function call: preserve every volatile value, flags and XMM0..5.
    save_regs='pushfq\n'+ '\n'.join('push '+r for r in ('rax','rcx','rdx','r8','r9','r10','r11'))
    restore_regs='\n'.join('pop '+r for r in ('r11','r10','r9','r8','rdx','rcx','rax'))+'\npopfq'
    render=emit('settings_title_render',f'''
        {save_regs}
        sub rsp, 0x80
        {chr(10).join(f'movdqu xmmword ptr [rsp+{0x20+i*16}], xmm{i}' for i in range(6))}
        cmp byte ptr {mem(page)}, 0
        jne deferred
        call {draw:#x}
    deferred:
        {chr(10).join(f'movdqu xmm{i}, xmmword ptr [rsp+{0x20+i*16}]' for i in range(6))}
        add rsp, 0x80
        {restore_regs}
        movzx ecx, word ptr {mem(0x10e1d3c)}
        jmp 0x1ba980
    ''')
    jump(0x1ba979,7,render,"Draw the extra title entry, deferring the open panel until after the logo")
    # The native title submits its logo much later, through 1bb994. Render
    # the page at the common epilogue AFTER all title geometry and pointer
    # commands. Keep the native entry path intact (including R12's save).
    overlay=emit('settings_title_overlay',f'''
        {save_regs}
        sub rsp, 0x80
        {chr(10).join(f'movdqu xmmword ptr [rsp+{0x20+i*16}], xmm{i}' for i in range(6))}
        cmp byte ptr {mem(page)}, 0
        je done
        call {draw:#x}
    done:
        {chr(10).join(f'movdqu xmm{i}, xmmword ptr [rsp+{0x20+i*16}]' for i in range(6))}
        add rsp, 0x80
        {restore_regs}
        mov rcx, qword ptr [rsp+0x170]
        jmp 0x1bbc15
    ''')
    jump(0x1bbc0d,8,overlay,"Draw mod options above the completed native title, before its stack-cookie check")
    # Common title path AFTER the native logo animation has settled. Phase 230
    # is also the native Press Start threshold. Never show branding during the
    # early title reveal, even when the PNG has already been cached.
    branding=emit('settings_title_branding',f'''
        {save_regs}
        sub rsp, 0x80
        {chr(10).join(f'movdqu xmmword ptr [rsp+{0x20+i*16}], xmm{i}' for i in range(6))}
        cmp ebx, 230
        jb done
        cmp ebx, 1000000
        jae done
        cmp byte ptr {mem(page)}, 0
        jne done
        cmp qword ptr {mem(0x10e1e70)}, 0
        je done
        cmp qword ptr {mem(0x10e1e78)}, 0
        je done
        call {logo:#x}
    done:
        {chr(10).join(f'movdqu xmm{i}, xmmword ptr [rsp+{0x20+i*16}]' for i in range(6))}
        add rsp, 0x80
        {restore_regs}
        cmp ebx, 0xe6
        jmp 0x1baea3
    ''')
    jump(0x1bae9d,6,branding,"Show blue branding after native title reveal, including before Start")
    logo_info['visibility']='After native title reveal (phase >=230), before and after Start; hidden in settings and transitions'
    return dict(flags_rva=flags, initialized_rva=initialized,page_rva=page,selection_rva=selection,
                error_rva=error,reset_choice_rva=reset_choice,snapshot_rva=snapshot,path_rva=path,strings=strings,table_rva=table,
                features=[k for k,_,_ in FEATURES],flag_rvas=[data+i for i in FLAG_OFFSETS],
                snapshot_rvas=[snapshot+i if i<16 else data+0x1a50+i-16 for i in range(count)],default='enabled',french_text_language=3,row_step=row_step,
                visible_rows=visible_rows,scroll_top_rva=scroll_top,
                category_state_rva=category_state,category_first=category_first,
                categories=[dict(fr=fr,en=en,items=ids) for fr,en,ids in CATEGORIES],
                configuration='%LOCALAPPDATA%/TalesOfEternia-WatersEdition.ini',
                input='native controller/keyboard confirm, back, directions; page uses separate cursor',
                native_entries_preserved=True,visual_validation=False,
                panel_renderer='Native Options capsule, window, gradient, cursor and dynamic input hints; title epilogue overlay',
                title_logo=logo_info),bytes(payload),logo_png
