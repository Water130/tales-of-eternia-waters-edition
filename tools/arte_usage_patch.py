"""Usage display and per-character counters, without altering native save data.

Native physical counters remain authoritative. Casts are counted only after
the cast-completion dispatcher accepts them, not when incantation starts.
"""

SIZE = 7 * 128 * 2


def emit_usage(emit, mem, jump, state):
    live = state + 0x2000
    left = state + 0x3504
    # IDs 39..41 are Farah's healing spells: vanilla explicitly hides their
    # counters (metadata flag 1). The other IDs below 43 use native counters.
    increment = emit('arte_usage_increment', f'''
        cmp ecx, 6
        ja done
        cmp edx, 113
        ja done
        cmp edx, 39
        jb done
        cmp edx, 42
        je done
        shl ecx, 7
        add ecx, edx
        lea rax, {mem(live)}
        cmp word ptr [rax+rcx*2], 9999
        jae done
        inc word ptr [rax+rcx*2]
    done:
        ret
    ''')

    def preserve(body):
        # All call sites are in aligned native frames. Keep native volatile
        # registers too: several game routines use private calling conventions.
        return f'''
            pushfq
            push rax
            push rcx
            push rdx
            push r8
            push r9
            push r10
            push r11
            sub rsp, 0x20
            {body}
            add rsp, 0x20
            pop r11
            pop r10
            pop r9
            pop r8
            pop rdx
            pop rcx
            pop rax
            popfq
        '''

    cast = emit('arte_usage_cast_completed', preserve(f'''
        test eax, eax
        jne done
        cmp byte ptr [rbx+0x51], 0
        jne done
        movzx ecx, byte ptr [rbx+0x4f]
        movzx edx, byte ptr [rbx+0x6d]
        call {increment:#x}
    done:
    ''') + f'''
        cmp byte ptr {mem(0x12ceb7a)}, r12b
        jmp 0xd5555
    ''')
    # Original RIP target is 0x12ceb7a; keep the original post-dispatch test.
    jump(0xd554e, 7, cast, 'Count completed spell casts once after successful admission')

    menu = emit('arte_usage_menu_heal', preserve(f'''
        mov ecx, edi
        mov edx, ebp
        call {increment:#x}
    ''') + '''
        mov rbx, qword ptr [rsp+0x30]
        jmp 0x224648
    ''')
    jump(0x224643, 5, menu, 'Count a menu healing spell once after applying its effects')

    physical = emit('arte_usage_extra_physical', preserve(f'''
        cmp byte ptr [rdi+0x51], 0
        jne done
        movzx edx, byte ptr [rdi+0x6d]
        cmp edx, 43
        jb done
        cmp edx, 113
        ja done
        lea rax, {mem(0x551780)}
        cmp byte ptr [rax+rdx*8+1], 0
        jne done
        movzx ecx, byte ptr [rdi+0x4f]
        call {increment:#x}
    done:
    ''') + '''
        movzx ecx, byte ptr [rdi+0x6d]
        lea eax, [rcx-1]
        jmp 0x8e41f
    ''')
    jump(0x8e418, 7, physical, 'Count additional physical artes at the native first-hit site')

    start = emit('arte_usage_show_counter', f'''
        mov dword ptr {mem(left)}, 320
        cmp ebp, 1
        jb skipped
        cmp ebp, 113
        ja skipped
        mov r15d, ebp
        jmp 0x226fec
    skipped:
        jmp 0x227173
    ''')
    jump(0x226fbf, 9, start, 'Show native usage panel for spells and physical artes, including zero')
    value = emit('arte_usage_read_counter', f'''
        cmp ebp, 39
        jb native
        cmp ebp, 42
        je native
        mov ecx, dword ptr [rsp+0x68]
        cmp ecx, 6
        ja zero
        shl ecx, 7
        add ecx, ebp
        lea rax, {mem(live)}
        movzx ecx, word ptr [rax+rcx*2]
        cmp ecx, 9999
        jbe done
        mov ecx, 9999
        jmp done
    zero:
        xor ecx, ecx
        jmp done
    native:
        movzx ecx, word ptr [rax+r15*2+0x11cb048]
    done:
        jmp 0x22708c
    ''')
    jump(0x227083, 9, value, 'Read the selected caster usage count without indexing beyond native counters')
    layout = emit('arte_usage_counter_layout', f'''
        lea ecx, [r13-0x54]
        mov dword ptr {mem(left)}, ecx
        mov dword ptr [rsp+0x20], 0x22
        jmp 0x22706f
    ''')
    jump(0x227063, 12, layout, 'Locate elements relative to the localized native usage frame')
    for key, site, offset in (
        ('element_right', 0x22719a, 22), ('element_left', 0x2271c7, 41),
        ('summon_element', 0x22727c, 22),
        ('summon_vitality_back', 0x22720b, 21),
        ('summon_vitality_fill', 0x22722d, 21),
    ):
        target = emit('arte_usage_'+key, f'''
            mov ecx, dword ptr {mem(left)}
            sub ecx, {offset}
            jmp {site+5:#x}
        ''')
        jump(site, 5, target, 'Place '+key.replace('_', ' ')+' left of the usage counter')
    return dict(live_rva=live, size=SIZE, left_rva=left, limit=9999,
                per_character=True, native_physical_counters_preserved=True)


def emit_usage_storage(emit, mem, data, state, string, fingerprint, usage, *,
                       record_name='arte_usage', section_name='ArteUsage-v1',
                       record_size=SIZE, layout=None, reset_extra=''):
    """Independent INI section; existing Artesphere-v1 records stay compatible."""
    native_emit, native_string = emit, string
    emit = lambda name, code: native_emit(name.replace('arte_usage', record_name), code)
    string = lambda name, value, wide=False: native_string(record_name+'_'+name, value, wide)
    SIZE = record_size
    assert 0 < SIZE <= 1792 and SIZE % 8 == 0
    section = string('usage_section', section_name, True)
    kernel = string('usage_kernel', 'kernel32.dll')
    get = string('usage_get', 'GetPrivateProfileStructW')
    put = string('usage_put', 'WritePrivateProfileStructW')
    live = usage['live_rva']
    snapshot, pending, workers = state+0x2700, state+0x2e00, state+0x3600
    valid, pending_ptr = state+0x3500, state+0x3508
    if layout:
        snapshot, pending, workers, valid, pending_ptr = [layout[k] for k in
            ('snapshot', 'pending', 'workers', 'valid', 'pending_ptr')]
    # 1800-byte record stays comfortably below a Windows guard page.
    io = emit('arte_usage_storage_io', f'''
        push rbx
        push rbp
        push rsi
        push rdi
        sub rsp, 0x788
        mov ebx, ecx
        mov ebp, edx
        mov rsi, r8
        mov rdi, r9
        cmp ebp, 20
        ja failed
        cmp byte ptr {mem(data+0x1a10)}, 1
        jne failed
        mov rcx, rsi
        call {fingerprint:#x}
        mov qword ptr [rsp+0x770], rax
        mov qword ptr [rsp+0x60], rax
        lea rcx, {mem(kernel)}
        call qword ptr {mem(0x2a9058)}
        test rax, rax
        je failed
        mov rcx, rax
        lea rdx, {mem(get)}
        test ebx, ebx
        je read_api
        lea rdx, {mem(put)}
    read_api:
        call qword ptr {mem(0x2a9060)}
        test rax, rax
        je failed
        mov qword ptr [rsp+0x778], rax
        mov dword ptr [rsp+0x40], 0x006c0053
        mov dword ptr [rsp+0x44], 0x0074006f
        mov eax, ebp
        xor edx, edx
        mov ecx, 10
        div ecx
        add eax, 48
        add edx, 48
        mov word ptr [rsp+0x48], ax
        mov word ptr [rsp+0x4a], dx
        mov word ptr [rsp+0x4c], 0
        test ebx, ebx
        je read_record
        xor eax, eax
    copy_out:
        mov rdx, qword ptr [rdi+rax]
        mov qword ptr [rsp+rax+0x68], rdx
        add eax, 8
        cmp eax, {SIZE}
        jb copy_out
    read_record:
        lea rcx, {mem(section)}
        lea rdx, [rsp+0x40]
        lea r8, [rsp+0x60]
        mov r9d, {SIZE+8}
        lea rax, {mem(data+0x3000)}
        mov qword ptr [rsp+0x20], rax
        call qword ptr [rsp+0x778]
        test eax, eax
        je failed
        test ebx, ebx
        jne success
        mov rax, qword ptr [rsp+0x770]
        cmp rax, qword ptr [rsp+0x60]
        jne failed
        xor eax, eax
    copy_in:
        mov rdx, qword ptr [rsp+rax+0x68]
        mov qword ptr [rdi+rax], rdx
        add eax, 8
        cmp eax, {SIZE}
        jb copy_in
    success:
        mov eax, 1
        jmp done
    failed:
        xor eax, eax
    done:
        add rsp, 0x788
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')

    def copy(src, dst):
        return f'''
            lea r10, {mem(src)}
            lea r11, {mem(dst)}
            xor eax, eax
        copy:
            mov r9, qword ptr [r10+rax]
            mov qword ptr [r11+rax], r9
            add eax, 8
            cmp eax, {SIZE}
            jb copy
        '''
    capture = emit('arte_usage_snapshot', copy(live, snapshot)+'ret')
    queue = emit('arte_usage_queue', f'''
        cmp rsi, 0x12d4
        jne done
        cmp r12d, 20
        ja done
        imul eax, r12d, {SIZE}
        lea r11, {mem(workers)}
        add r11, rax
        lea r10, {mem(snapshot)}
        xor eax, eax
    copy:
        mov r9, qword ptr [r10+rax]
        mov qword ptr [r11+rax], r9
        add eax, 8
        cmp eax, {SIZE}
        jb copy
    done:
        ret
    ''')
    # Import must keep RCX (native save source) and all incoming arguments.
    load = emit('arte_usage_import', f'''
        {reset_extra}
        lea r10, {mem(live)}
        xor eax, eax
    clear:
        mov qword ptr [r10+rax], 0
        add eax, 8
        cmp eax, {SIZE}
        jb clear
        cmp rcx, qword ptr {mem(pending_ptr)}
        jne done
        cmp byte ptr {mem(valid)}, 1
        jne done
        {copy(pending, live)}
    done:
        mov byte ptr {mem(valid)}, 0
        ret
    ''')
    reset = emit('arte_usage_new_game', f'''
        {reset_extra}
        lea r10, {mem(live)}
        xor eax, eax
    clear:
        mov qword ptr [r10+rax], 0
        add eax, 8
        cmp eax, {SIZE}
        jb clear
        mov byte ptr {mem(valid)}, 0
        ret
    ''')
    usage.update(snapshot_rva=snapshot, pending_rva=pending,
                 pending_valid_rva=valid, pending_ptr_rva=pending_ptr,
                 worker_profiles_rva=workers, section=section_name,
                 save_format_modified=False)
    return dict(capture=f'call {capture:#x}', queue=f'call {queue:#x}',
                load=f'sub rsp, 0x28; call {load:#x}; add rsp, 0x28',
                reset=f'call {reset:#x}', commit=f'''
                    mov ecx, 1
                    mov edx, r12d
                    mov r8, r15
                    imul eax, r12d, {SIZE}
                    lea r9, {mem(workers)}
                    add r9, rax
                    call {io:#x}
                    test eax, eax
                    sete al
                    or byte ptr {mem(state+7)}, al
                ''', read=f'''
                    mov byte ptr {mem(valid)}, 0
                    mov qword ptr {mem(pending_ptr)}, r15
                    xor ecx, ecx
                    mov edx, r12d
                    mov r8, rbx
                    lea r9, {mem(pending)}
                    call {io:#x}
                    mov byte ptr {mem(valid)}, al
                ''')
