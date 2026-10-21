"""Configurable keyboard trigger aliases, polled only for this foreground PID."""

def emit_keyboard(emit,mem,jump,data,state,string,initialize,skit_shortcut=None):
    section=string('keys_section','ArtesphereControls',True)
    page=string('keys_page','PageKey',True)
    extra=string('keys_c','PageCKey',True)
    legacy=string('keys_legacy','ShortcutKey',True)
    kernel=string('keys_kernel','kernel32.dll')
    user=string('keys_user','user32.dll')
    apis={name:string('keys_'+name,name) for name in (
        'GetAsyncKeyState','GetForegroundWindow','GetWindowThreadProcessId','GetCurrentProcessId')}
    table=state+0x300
    flag=state+0x320
    keys=state+0x324
    previous=state+0x32c
    resolve=''
    for i,(name,address) in enumerate(apis.items()):
        resolve+=f'''
            lea rcx, {mem(kernel if name=='GetCurrentProcessId' else user)}
            call qword ptr {mem(0x2a9058)}
            test rax, rax
            je done
            mov rcx, rax
            lea rdx, {mem(address)}
            call qword ptr {mem(0x2a9060)}
            test rax, rax
            je done
            mov qword ptr {mem(table+i*8)}, rax
        '''
    load=''
    for i,(key,default) in enumerate(((page,118),(extra,119))):
        # Preserve an existing keyboard binding for the retired seventh slot.
        fallback = f'''
            lea rcx, {mem(section)}
            lea rdx, {mem(legacy)}
            mov r8d, {default}
            lea r9, {mem(data+0x3000)}
            call qword ptr {mem(data+0x1b08)}
            mov r8d, eax
        ''' if i == 1 else f'mov r8d, {default}'
        load+=f'''
            {fallback}
            lea rcx, {mem(section)}
            lea rdx, {mem(key)}
            lea r9, {mem(data+0x3000)}
            call qword ptr {mem(data+0x1b08)}
            cmp eax, 1
            jb default_{i}
            cmp eax, 254
            jbe key_{i}
        default_{i}:
            mov eax, {default}
        key_{i}:
            mov dword ptr {mem(keys+i*4)}, eax
        '''
    update=emit('artesphere_keyboard',f'''
        push rbx
        push rsi
        sub rsp, 0x38
        call {initialize:#x}
        cmp byte ptr {mem(flag)}, 1
        je ready
        cmp byte ptr {mem(data+0x1a10)}, 1
        jne done
        {resolve}
        {load}
        mov eax, dword ptr {mem(keys)}
        cmp eax, dword ptr {mem(keys+4)}
        jne distinct
        mov dword ptr {mem(keys)}, 118
        mov dword ptr {mem(keys+4)}, 119
    distinct:
        mov byte ptr {mem(flag)}, 1
    ready:
        cmp byte ptr {mem(data+0x1a11)}, 2
        je unfocused
        call qword ptr {mem(table+8)}
        test rax, rax
        je unfocused
        mov rcx, rax
        lea rdx, [rsp+0x20]
        mov dword ptr [rsp+0x20], 0
        call qword ptr {mem(table+16)}
        call qword ptr {mem(table+24)}
        cmp eax, dword ptr [rsp+0x20]
        jne unfocused
        xor ebx, ebx
        mov esi, 0x40000
    next:
        lea rax, {mem(keys)}
        mov ecx, dword ptr [rax+rbx*4]
        call qword ptr {mem(table)}
        test ax, 0x8000
        setne dl
        lea rcx, {mem(previous)}
        test dl, dl
        je released
        or dword ptr {mem(0x8c9180)}, esi
        cmp byte ptr [rcx+rbx], 0
        jne released
        or dword ptr {mem(0x8c9184)}, esi
        or dword ptr {mem(0x8c9188)}, esi
    released:
        mov byte ptr [rcx+rbx], dl
        shl esi, 1
        inc ebx
        cmp ebx, 2
        jb next
        jmp done
    unfocused:
        mov word ptr {mem(previous)}, 0
    done:
        add rsp, 0x38
        pop rsi
        pop rbx
        ret
    ''')
    bridge=emit('artesphere_keyboard_frame',f'''
        push rax
        sub rsp, 0x28
        call {update:#x}
        {f'mov rcx, rbx; call {skit_shortcut:#x}' if skit_shortcut else ''}
        add rsp, 0x28
        pop rax
        mov rbx, qword ptr [rsp+0x30]
        jmp 0x19df42
    ''')
    jump(0x19df3d,5,bridge,'Poll configurable foreground keyboard aliases after native input')
    return dict(section='ArtesphereControls',page_b_key=118,page_c_key=119,
                keys_rva=keys,api_rva=table,initialized_rva=flag,previous_rva=previous,
                section_rva=section,page_name_rva=page,page_c_name_rva=extra)
