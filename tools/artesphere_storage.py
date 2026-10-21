"""Per-slot sidecar, committed only after native save success.

An FNV-1a fingerprint ties each record to the exact 0x12d4-byte native snapshot.
Windows profile-struct checksum additionally rejects damaged mod records.
Loading previews only updates a pending record; the live profile changes at the
actual native import. The original game file is never extended or rewritten.
"""

def emit_storage(emit,mem,jump,data,state,profile,string,symbols,usage):
    section=string('storage_section','Artesphere-v2',True)
    legacy=string('storage_legacy','Artesphere-v1',True)
    kernel=string('storage_kernel','kernel32.dll')
    get=string('storage_get','GetPrivateProfileStructW')
    put=string('storage_put','WritePrivateProfileStructW')
    snapshot,pending,pending_ptr,valid=state+0x200,state+0x280,state+0x2e0,state+0x2e8
    workers=state+0x400 # 21 independent immutable profiles, 96 bytes each.
    # RCX native serialized buffer -> RAX fingerprint (not a security digest).
    fingerprint=emit('artesphere_fingerprint','''
        mov rax, 0xcbf29ce484222325
        mov r9, 0x100000001b3
        mov edx, 0x12d4
    next:
        movzx r8d, byte ptr [rcx]
        xor rax, r8
        imul rax, r9
        inc rcx
        dec edx
        jne next
        ret
    ''')
    from arte_usage_patch import emit_usage_storage
    usage_hooks = emit_usage_storage(emit,mem,data,state,string,fingerprint,usage)
    # Independent, zero-default disable bits: 256 stable faculty IDs per hero.
    # A legacy/missing record enables everything without changing usage counts.
    preferences = dict(live_rva=state+0xd000, size=224, ui_state_rva=state+0xe600)
    pref_hooks = emit_usage_storage(emit,mem,data,state,string,fingerprint,preferences,
        record_name='mastery_preferences', section_name='MasteryChoices-v1', record_size=224,
        layout=dict(snapshot=state+0xd100,pending=state+0xd200,workers=state+0xd300,
                    valid=state+0xd2f0,pending_ptr=state+0xd2f8),
        reset_extra=f'mov dword ptr {mem(state+0xe600)}, 0')
    for key in usage_hooks:
        usage_hooks[key] += '\n' + pref_hooks[key]
    usage['preferences'] = preferences
    # ECX write flag, EDX slot, R8 serialized buffer, R9 96-byte mod profile.
    io=emit('artesphere_storage_io',f'''
        push rbx
        push rbp
        push rsi
        push rdi
        sub rsp, 0xe8
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
        mov qword ptr [rsp+0xd0], rax
        mov qword ptr [rsp+0x60], rax
        lea rax, {mem(kernel)}
        mov rcx, rax
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
        mov qword ptr [rsp+0xd8], rax
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
        cmp eax, 96
        jb copy_out
    read_record:
        mov dword ptr [rsp+0x50], 0
        lea rcx, {mem(section)}
        lea rdx, [rsp+0x40]
        lea r8, [rsp+0x60]
        mov r9d, 104
        lea rax, {mem(data+0x3000)}
        mov qword ptr [rsp+0x20], rax
        call qword ptr [rsp+0xd8]
        test eax, eax
        jne record_ready
        test ebx, ebx
        jne failed
        # Read legacy records only as a fallback; never overwrite them.
        lea rcx, {mem(legacy)}
        lea rdx, [rsp+0x40]
        lea r8, [rsp+0x60]
        mov r9d, 104
        lea rax, {mem(data+0x3000)}
        mov qword ptr [rsp+0x20], rax
        call qword ptr [rsp+0xd8]
        test eax, eax
        je failed
        mov dword ptr [rsp+0x50], 1
    record_ready:
        test ebx, ebx
        jne success
        mov rax, qword ptr [rsp+0xd0]
        cmp rax, qword ptr [rsp+0x60]
        jne failed
        cmp dword ptr [rsp+0x50], 0
        je migrated
        # Keep B's 44 bytes; C starts as B, not the obsolete seventh slots.
        xor eax, eax
    migrate:
        mov edx, dword ptr [rsp+rax+0x68]
        mov dword ptr [rsp+rax+0x94], edx
        add eax, 4
        cmp eax, 44
        jb migrate
        mov qword ptr [rsp+0xc0], 0
    migrated:
        xor eax, eax
    copy_in:
        mov rdx, qword ptr [rsp+rax+0x68]
        mov qword ptr [rdi+rax], rdx
        add eax, 8
        cmp eax, 96
        jb copy_in
    success:
        mov eax, 1
        jmp done
    failed:
        xor eax, eax
    done:
        add rsp, 0xe8
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
    capture=emit('artesphere_save_snapshot',f'''
        call {symbols['artesphere_initialize']:#x}
        xor eax, eax
        lea rcx, {mem(profile)}
        lea rdx, {mem(snapshot)}
    next:
        mov r8, qword ptr [rcx+rax]
        mov qword ptr [rdx+rax], r8
        add eax, 8
        cmp eax, 96
        jb next
        {usage_hooks['capture']}
        mov rbx, qword ptr [rsp+0x30]
        jmp 0x24db28
    ''')
    jump(0x24db23,5,capture,'Capture mod assignments alongside native serialization')
    # 3f310 joins its previous writer BEFORE this point. Freeze the captured
    # profile here: the main thread can serialize a later save while this write
    # is running. The worker must not read the mutable serialization snapshot.
    queue=emit('artesphere_queue_profile',f'''
        cmp rsi, 0x12d4
        jne done
        cmp r12d, 20
        ja done
        imul eax, r12d, 96
        lea rdx, {mem(workers)}
        add rdx, rax
        lea rcx, {mem(snapshot)}
        xor eax, eax
    next:
        mov r8, qword ptr [rcx+rax]
        mov qword ptr [rdx+rax], r8
        add eax, 8
        cmp eax, 96
        jb next
    done:
        {usage_hooks['queue']}
        mov rax, qword ptr [rbp+0x10]
        lea rcx, [rbp+0x10]
        jmp 0x3f3a8
    ''')
    jump(0x3f3a0,8,queue,'Freeze per-slot assignments after joining the previous writer')
    save=emit('artesphere_save_commit',f'''
        sub rsp, 0x28
        call 0x594d0
        mov byte ptr [rsp+0x20], al
        test al, al
        je done
        cmp qword ptr [rsp+0x80], 0x12d4
        jne done
        cmp r12d, 20
        ja done
        mov ecx, 1
        mov edx, r12d
        mov r8, r15
        imul eax, r12d, 96
        lea r9, {mem(workers)}
        add r9, rax
        call {io:#x}
        test eax, eax
        sete byte ptr {mem(state+7)}
        {usage_hooks['commit']}
    done:
        movzx eax, byte ptr [rsp+0x20]
        add rsp, 0x28
        ret
    ''')
    # At this call site RSP is aligned; an ordinary replacement CALL is required.
    save_site=emit('artesphere_save_site',f'''
        call {save:#x}
        jmp 0x3fce0
    ''')
    jump(0x3fcdb,5,save_site,'Write sidecar only after successful native save')
    read=emit('artesphere_read_stage',f'''
        call 0x2a41e0
        cmp r14, 0x12d4
        jne done
        mov byte ptr {mem(valid)}, 0
        mov qword ptr {mem(pending_ptr)}, r15
        xor ecx, ecx
        mov edx, r12d
        mov r8, rbx
        lea r9, {mem(pending)}
        call {io:#x}
        mov byte ptr {mem(valid)}, al
        {usage_hooks['read']}
    done:
        jmp 0x40172
    ''')
    jump(0x4016d,5,read,'Read pending mod profile without changing the active game')
    # Native load import mutates localized name IDs in its source buffer. The
    # sidecar was already fingerprinted before this mutation in the read thread.
    load=emit('artesphere_import_profile',f'''
        {usage_hooks['load']}
        mov byte ptr {mem(state)}, 0
        mov byte ptr {mem(state+1)}, 0
        mov byte ptr {mem(state+2)}, 0
        mov byte ptr {mem(state+3)}, 0
        lea r10, {mem(profile)}
        xor eax, eax
    clear:
        mov qword ptr [r10+rax], 0
        add eax, 8
        cmp eax, 96
        jb clear
        cmp rcx, qword ptr {mem(pending_ptr)}
        jne done
        cmp byte ptr {mem(valid)}, 1
        jne done
        lea r11, {mem(pending)}
        xor eax, eax
    copy:
        mov r9, qword ptr [r11+rax]
        mov qword ptr [r10+rax], r9
        add eax, 8
        cmp eax, 96
        jb copy
        mov byte ptr {mem(state)}, 1
    done:
        mov byte ptr {mem(valid)}, 0
        push r15
        sub rsp, 0x30
        jmp 0x24db46
    ''')
    jump(0x24db40,6,load,'Apply matching profile only when a save is actually imported')
    reset=emit('artesphere_new_game',f'''
        call 0x2a41e0
        {usage_hooks['reset']}
        mov dword ptr {mem(state)}, 0
        mov byte ptr {mem(valid)}, 0
        lea r10, {mem(profile)}
        xor eax, eax
    clear:
        mov qword ptr [r10+rax], 0
        add eax, 8
        cmp eax, 96
        jb clear
        jmp 0x258f96
    ''')
    jump(0x258f91,5,reset,'Reset mod assignments with native new-game state')
    return dict(kind='per-slot INI sidecar with native-snapshot fingerprint',
                profile_size=96,snapshot_rva=snapshot,pending_rva=pending,
                pending_ptr_rva=pending_ptr,pending_valid_rva=valid,
                worker_profiles_rva=workers,section='Artesphere-v2',
                legacy_section='Artesphere-v1',migration='Preserve B; initialize C from B; retain legacy record',
                save_format_modified=False)
