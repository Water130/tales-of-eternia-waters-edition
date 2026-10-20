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
]


def emit_settings(emit, mem, jump, data, symbols):
    count = len(FEATURES)
    header = count
    keyboard = count + 1
    assert count <= 16  # Two qwords reserved for flags and opening snapshot.
    row_step = min(17, 160//count)
    assert row_step >= 12 and 64.5 + row_step*count < 225
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
    # Tables contain RVAs, not absolute addresses; they survive ASLR.
    payload.extend(b'\0'*((-len(payload))%4))
    table=data+0x2000+len(payload)
    for index in range(count):
        payload.extend(struct.pack('<III',strings[f'key{index}'],strings[f'fr{index}'],strings[f'en{index}']))
    assert len(payload)<0x1000
    flags=data+0x1a00
    initialized=data+0x1a10
    page=data+0x1a11
    selection=data+0x1a12
    error=data+0x1a13
    reset_choice=data+0x1a14
    snapshot=data+0x1a20
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
        lea rdx, {mem(flags)}
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
        lea rdx, {mem(flags)}
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
        lea rdx, {mem(snapshot)}
        mov al, byte ptr [rdx+rbx]
    default_value:
        lea rdx, {mem(flags)}
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
    panel_input=emit('settings_panel_input',f'''
        cmp byte ptr {mem(page)}, 0
        je native
        mov dword ptr {mem(0x10e1c8c)}, 0x4650
        cmp byte ptr {mem(page)}, 2
        je sub_page_input
        cmp esi, 0x4000
        je close
        cmp esi, 8
        je close
    sub_page_input:
        cmp byte ptr {mem(page)}, 2
        jne main_page
        mov eax, dword ptr {mem(data+0x1a30)}
        test eax, eax
        je handled
        lea rcx, {mem(0)}
        add rax, rcx
        call rax
        jmp handled
    main_page:
        movzx eax, byte ptr {mem(selection)}
        cmp r13d, 0x10
        jne down
        cmp eax, {count}
        jne up_eight
        mov eax, {keyboard}
        jmp selected
    up_eight:
        cmp eax, {keyboard}
        jne up_normal
        mov eax, {count-1}
        jmp selected
    up_normal:
        dec eax
        jns selected
        mov eax, {header}
        jmp selected
    down:
        cmp r13d, 0x40
        jne action
        cmp eax, {count-1}
        jne down_eight
        mov eax, {keyboard}
        jmp selected
    down_eight:
        cmp eax, {keyboard}
        jne down_normal
        mov eax, {header}
        jmp selected
    down_normal:
        inc eax
        cmp eax, {keyboard}
        jb selected
        xor eax, eax
    selected:
        mov byte ptr {mem(selection)}, al
        mov edi, 0x8d
        jmp handled
    action:
        cmp eax, {keyboard}
        jne feature_action
        cmp esi, 0x2000
        jne handled
        cmp dword ptr {mem(data+0x1a30)}, 0
        je handled
        mov byte ptr {mem(page)}, 2
        jmp handled
    feature_action:
        cmp eax, {count}
        je header_action
        cmp esi, 0x2000
        je toggle
        cmp esi, 0x20
        je toggle
        cmp esi, 0x80
        jne handled
    toggle:
        cmp eax, {count}
        jae handled
        lea rdx, {mem(flags)}
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
        mov byte ptr {mem(reset_choice)}, 0
        mov byte ptr {mem(page)}, 1
        mov byte ptr {mem(selection)}, 0
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
        mov ecx, 297
        mov edx, 16
        xor r8d, r8d
        mov r9d, 77
        mov dword ptr [rsp+0x20], 18
        lea rax, {mem(0x11cc57c)}
        mov qword ptr [rsp+0x28], rax
        mov dword ptr [rsp+0x30], 255
        call 0x25aaa0
        mov ecx, -55
        mov edx, 34
        xor r8d, r8d
        mov r9d, 429
        mov dword ptr [rsp+0x20], 191
        lea rax, {mem(0x11cc57c)}
        mov qword ptr [rsp+0x28], rax
        mov dword ptr [rsp+0x30], 255
        call 0x25aaa0
        movzx edx, byte ptr {mem(selection)}
        cmp edx, {header}
        je done
        cmp edx, {keyboard}
        jne regular_row
        mov edx, {count}
    regular_row:
        imul edx, edx, {row_step}
        add edx, 55
        cvtsi2ss xmm1, edx
        mov eax, 31
        cvtsi2ss xmm0, eax
        xorps xmm2, xmm2
        movss xmm3, dword ptr {mem(0x524f50)}
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
        mov edx, 33
        mov r8d, 34
        mov r9d, 68
        mov eax, 0xfffffdfa
        call {field:#x}
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
        xor ebx, ebx
        lea rsi, {mem(table)}
        lea rdi, {mem(0)}
    row:
        mov ecx, dword ptr [rsi+8]
        cmp byte ptr {mem(0x11c9ce8)}, 3
        jne label_ready
        mov ecx, dword ptr [rsi+4]
    label_ready:
        add rcx, rdi
        mov edx, 34
        imul r8d, ebx, {row_step}
        add r8d, 55
        mov r9d, 111
        mov eax, 0xff49bfff
        call {field:#x}
        mov edx, 150
        imul r8d, ebx, {row_step}
        add r8d, 55
        xor r9d, r9d
        mov eax, 0xff808080
        lea rcx, {mem(flags)}
        cmp byte ptr [rcx+rbx], 0
        je on_inactive
        mov eax, 0xfffffdfa
    on_inactive:
        {localized('on','rcx')}
        call {field:#x}
        mov edx, 190
        imul r8d, ebx, {row_step}
        add r8d, 55
        xor r9d, r9d
        mov eax, 0xfffffdfa
        lea rcx, {mem(flags)}
        cmp byte ptr [rcx+rbx], 0
        je off_active
        mov eax, 0xff808080
    off_active:
        {localized('off','rcx')}
        call {field:#x}
    next_row:
        add rsi, 12
        inc ebx
        cmp ebx, {count}
        jb row
        {localized('keyboard')}
        mov edx, 34
        mov r8d, {55+row_step*count}
        mov r9d, 111
        mov eax, 0xff49bfff
        call {field:#x}
        {localized('open')}
        mov edx, 150
        mov r8d, {55+row_step*count}
        xor r9d, r9d
        mov eax, 0xfffffdfa
        call {field:#x}
        movzx eax, byte ptr {mem(selection)}
        cmp eax, {keyboard}
        jne feature_cursor
        mov edx, 55
        mov r8d, {43+row_step*count}
        jmp cursor
    feature_cursor:
        cmp eax, {count}
        je header_cursor
        lea rdx, {mem(flags)}
        movzx edx, byte ptr [rdx+rax]
        imul edx, edx, -40
        add edx, 95
        imul r8d, eax, {row_step}
        add r8d, 43
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
        mov r8d, 225
        mov r9d, 6
        call {text:#x}
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
                features=[k for k,_,_ in FEATURES],default='enabled',french_text_language=3,row_step=row_step,
                configuration='%LOCALAPPDATA%/TalesOfEternia-WatersEdition.ini',
                input='native controller/keyboard confirm, back, directions; page uses separate cursor',
                native_entries_preserved=True,visual_validation=False,
                panel_renderer='Native Options capsule, window, gradient, cursor and dynamic input hints; title epilogue overlay',
                title_logo=logo_info),bytes(payload),logo_png
