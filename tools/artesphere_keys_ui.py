"""In-game PC binding page, using native frames, font and device-aware hints.
Key bindings are mod-owned VK aliases; native Unity bindings remain untouched.
"""

def emit_keys_ui(emit,mem,data,state,string,loc,symbols,keyboard):
    strings=[('keytitle','Commandes clavier (PC)','Keyboard controls (PC)'),
        ('keypage','Maintenir : page B des artes','Hold: arte page B'),
        ('keyextra','Maintenir : page C des artes','Hold: arte page C'),
        ('keyinfo','Validez une commande, puis appuyez sur la touche souhaitée.','Confirm a command, then press the desired key.'),
        ('keywait','Relâchez les touches, puis appuyez sur la nouvelle touche.','Release all keys, then press the new key.'),
        ('keycancel','Échap : annuler','Esc: cancel'),
        ('keyduplicate','Cette touche est déjà attribuée à l’autre commande.','This key is already assigned to the other command.'),
        ('keyerror','Impossible d’enregistrer la touche. Réessayez.','Could not save the key. Try again.'),
        ('keydone','Touches enregistrées pour ce PC. Affectations d’artes par sauvegarde.','Keys are saved for this PC. Arte assignments are saved per game.')]
    for k,fr,en in strings:string(k+'_fr',fr);string(k+'_en',en)
    keynames={8:'Backspace',9:'Tab',13:'Enter',16:'Shift',17:'Ctrl',18:'Alt',32:'Space',
              33:'Page Up',34:'Page Down',35:'End',36:'Home',37:'Left',38:'Up',39:'Right',40:'Down',
              45:'Insert',46:'Delete'}
    selection=state+0x330;capture=state+0x331;error=state+0x332
    keys=keyboard['keys_rva'];api=keyboard['api_rva'];buf=state+0xd50
    # EAX unsigned number, RDX buffer end -> RAX first ASCII digit (NUL-terminated).
    number=emit('artesphere_key_number',f'''
        mov byte ptr [rdx], 0
        mov r9, rdx
        mov r8d, 10
    digit:
        xor edx, edx
        div r8d
        add dl, 48
        dec r9
        mov byte ptr [r9], dl
        test eax, eax
        jne digit
        mov rax, r9
        ret
    ''')
    branches=''
    for k,name in keynames.items():
        branches+=f'''cmp ecx, {k}; jne key_{k}
            lea rax, {mem(string('labelvk'+str(k),name))}; ret
        key_{k}:\n'''
    key_name=emit('artesphere_key_name',f'''
        {branches}
        lea rax, {mem(buf)}
        cmp ecx, 48
        jb function
        cmp ecx, 90
        ja function
        cmp ecx, 57
        jbe letter
        cmp ecx, 65
        jb function
    letter:
        mov byte ptr [rax], cl
        mov byte ptr [rax+1], 0
        ret
    function:
        cmp ecx, 112
        jb numeric
        cmp ecx, 135
        ja numeric
        sub ecx, 111
        mov eax, ecx
        lea rdx, {mem(buf+15)}
        sub rsp, 0x28
        call {number:#x}
        add rsp, 0x28
        dec rax
        mov byte ptr [rax], 70
        ret
    numeric:
        mov eax, ecx
        lea rdx, {mem(buf+15)}
        sub rsp, 0x28
        call {number:#x}
        add rsp, 0x28
        sub rax, 4
        mov dword ptr [rax], 0x20234b56
        ret
    ''')
    # ECX row, EDX VK. Commit only after INI write succeeds.
    save=emit('artesphere_key_save',f'''
        push rbx
        push rsi
        sub rsp, 0x28
        mov ebx, ecx
        mov esi, edx
        mov eax, edx
        lea rdx, {mem(buf+15)}
        call {number:#x}
        lea r8, {mem(buf+32)}
        xor ecx, ecx
    wide:
        movzx edx, byte ptr [rax+rcx]
        mov word ptr [r8+rcx*2], dx
        inc ecx
        test edx, edx
        jne wide
        lea rdx, {mem(keyboard['page_name_rva'])}
        test ebx, ebx
        je name
        lea rdx, {mem(keyboard['page_c_name_rva'])}
    name:
        lea rcx, {mem(keyboard['section_rva'])}
        lea r9, {mem(data+0x3000)}
        cmp qword ptr {mem(data+0x1b10)}, 0
        je failed
        call qword ptr {mem(data+0x1b10)}
        test eax, eax
        je failed
        lea rax, {mem(keys)}
        mov dword ptr [rax+rbx*4], esi
        mov byte ptr {mem(error)}, 0
        jmp done
    failed:
        mov byte ptr {mem(error)}, 2
    done:
        add rsp, 0x28
        pop rsi
        pop rbx
        ret
    ''')
    # Values 1 and 2 mean wait-for-release then listen-for-next-press.
    listen=emit('artesphere_key_capture',f'''
        push rbx
        push rsi
        sub rsp, 0x28
        xor esi, esi
        mov ebx, 8
    scan:
        mov ecx, ebx
        call qword ptr {mem(api)}
        test ax, 0x8000
        je next
        test esi, esi
        jne next
        mov esi, ebx
    next:
        inc ebx
        cmp ebx, 255
        jb scan
        cmp byte ptr {mem(capture)}, 1
        jne pressed
        test esi, esi
        jne done
        mov byte ptr {mem(capture)}, 2
        jmp done
    pressed:
        test esi, esi
        je done
        cmp esi, 27
        je cancel
        movzx ecx, byte ptr {mem(selection)}
        mov edx, ecx
        xor edx, 1
        lea rax, {mem(keys)}
        cmp esi, dword ptr [rax+rdx*4]
        je duplicate
        mov edx, esi
        call {save:#x}
        jmp cancel
    duplicate:
        mov byte ptr {mem(error)}, 1
    cancel:
        mov byte ptr {mem(capture)}, 0
        mov dword ptr {mem(0x8c9184)}, 0
        mov dword ptr {mem(0x8c9188)}, 0
    done:
        add rsp, 0x28
        pop rsi
        pop rbx
        ret
    ''')
    input_fn=emit('artesphere_keys_input',f'''
        sub rsp, 0x28
        cmp byte ptr {mem(keyboard['initialized_rva'])}, 1
        jne done
        # Focus is also checked during rebinding, not just when casting.
        call qword ptr {mem(api+8)}
        mov rcx, rax
        lea rdx, [rsp+0x20]
        call qword ptr {mem(api+16)}
        call qword ptr {mem(api+24)}
        cmp eax, dword ptr [rsp+0x20]
        jne done
        cmp byte ptr {mem(capture)}, 0
        je navigate
        call {listen:#x}
        jmp done
    navigate:
        mov eax, dword ptr {mem(0x8c9184)}
        test eax, 0x4008
        jne close
        test dword ptr {mem(0x8c9188)}, 0x50
        je confirm
        xor byte ptr {mem(selection)}, 1
        mov byte ptr {mem(error)}, 0
        jmp done
    confirm:
        test eax, 0x2000
        je done
        mov byte ptr {mem(capture)}, 1
        mov byte ptr {mem(error)}, 0
        jmp done
    close:
        mov byte ptr {mem(data+0x1a11)}, 1
    done:
        add rsp, 0x28
        ret
    ''')
    text=symbols['settings_text'];field=symbols['settings_field']
    def label(k,x,y,size=-8,color=0xffffffff):
        return f'''{loc(k)}
            mov edx, {x}; mov r8d, {y}; mov r9d, {size}; mov eax, {color}; call {text:#x}'''
    draw=emit('artesphere_keys_draw',f'''
        sub rsp, 0x58
        mov rcx, qword ptr {mem(0x644a10)}
        test rcx, rcx
        je done
        cmp qword ptr [rcx+0x4d0], 0
        je done
        movsxd rax, dword ptr [rcx+0x4e0]
        test rax, rax
        js done
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
        mov r9d, 90
        mov dword ptr [rsp+0x20], 0
        lea rax, {mem(0x11cc57c)}
        mov qword ptr [rsp+0x28], rax
        mov dword ptr [rsp+0x30], 255
        call 0x25a090
        mov ecx, -55
        mov edx, 34
        xor r8d, r8d
        mov r9d, 429
        mov dword ptr [rsp+0x20], 191
        lea rax, {mem(0x11cc57c)}
        mov qword ptr [rsp+0x28], rax
        mov dword ptr [rsp+0x30], 255
        call 0x25aaa0
        movzx eax, byte ptr {mem(selection)}
        imul eax, eax, 24
        add eax, 65
        cvtsi2ss xmm1, eax
        mov eax, 31
        cvtsi2ss xmm0, eax
        xorps xmm2, xmm2
        movss xmm3, dword ptr {mem(0x524f50)}
        mov dword ptr [rsp+0x20], 0x41080000
        mov dword ptr [rsp+0x30], 0xbf800000
        mov dword ptr [rsp+0x40], 0x40000000
        mov dword ptr [rsp+0x48], 255
        call 0x24490
        {label('keytitle',33,34, -8)}
        {label('keypage',34,65,-8,0xff49bfff)}
        {label('keyextra',34,89,-8,0xff49bfff)}
        mov ecx, dword ptr {mem(keys)}
        call {key_name:#x}
        mov rcx, rax
        mov edx, 280; mov r8d, 65; mov r9d, 80; mov eax, 0xffffffff
        call {field:#x}
        mov ecx, dword ptr {mem(keys+4)}
        call {key_name:#x}
        mov rcx, rax
        mov edx, 280; mov r8d, 89; mov r9d, 80; mov eax, 0xffffffff
        call {field:#x}
        {label('keyinfo',240,150,7)}
        cmp byte ptr {mem(capture)}, 0
        je status
        {label('keywait',240,176,7,0xffffcf8d)}
        {label('keycancel',240,192,7,0xffffcf8d)}
        jmp hints
    status:
        cmp byte ptr {mem(error)}, 1
        jne write_error
        {label('keyduplicate',240,176,7,0xff8080ff)}
        jmp hints
    write_error:
        cmp byte ptr {mem(error)}, 2
        jne saved
        {label('keyerror',240,176,7,0xff8080ff)}
        jmp hints
    saved:
        {label('keydone',240,225,6,0xffd8bca0)}
    hints:
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
        mov r8d, 0x50
        {loc('select','r9')}
        mov dword ptr [rsp+0x20], 255
        call 0x21cbb0
        mov ecx, eax
        xor edx, edx
        mov r8d, 0x2000
        {loc('confirm','r9')}
        mov dword ptr [rsp+0x20], 255
        call 0x21cbb0
    done:
        add rsp, 0x58
        ret
    ''')
    return dict(input_rva=input_fn,draw_rva=draw,selection_rva=selection,
                capture_rva=capture,error_rva=error)
