"""Bounded, transient Fringe lists. Native save lists are never enlarged.

The engine stores only 32 bytes per character, immediately followed by command
assignments. Keep those bytes native and build a separate 128-entry view with
the same character stride. The optional rule removes partner assignment only.
"""
STRIDE=0xd0
CAPACITY=128
SIZE=0x1000


def emit_lists(emit,mem,data,state,teamup=None):
    teamup_init = f"sub rsp, 0x20; call {teamup['initialize']:#x}; add rsp, 0x20" if teamup else ''
    teamup_append = ''
    if teamup:
        entries=teamup['recipes']+teamup.get('native_test_entries',[])
        entries=entries+[dict(r,character=2) for r in teamup['recipes'] if r['character']==3]
        for r in entries:
            aid, char = r['id'], r['character']
            block = f'''
                mov ecx, {char}
                mov edx, {aid}
                mov r8, r12
                sub rsp, 0x20
                call {teamup['unlocked']:#x}
                add rsp, 0x20
                test eax, eax
                je teamup_next_{aid}
                lea rdi, {mem(state+char*STRIDE)}
                xor eax, eax
            teamup_search_{aid}:
                cmp byte ptr [rdi+rax], {aid}
                je teamup_next_{aid}
                cmp byte ptr [rdi+rax], 0
                je teamup_store_{aid}
                inc eax
                cmp eax, {CAPACITY}
                jb teamup_search_{aid}
                jmp teamup_next_{aid}
            teamup_store_{aid}:
                mov byte ptr [rdi+rax], {aid}
            teamup_next_{aid}:
            '''
            for prefix in ('teamup_next_','teamup_search_','teamup_store_'):
                block=block.replace(prefix+str(aid),prefix+str(aid)+'_'+str(char))
            teamup_append += block
    # RCX master state -> refreshed lists. No external calls; no save writes.
    refresh=emit('fringe_refresh_lists',f'''
        push rbx
        push rsi
        push rdi
        push r12
        push r13
        mov r12, rcx
        {teamup_init}
        lea rdi, {mem(state)}
        lea rsi, [r12+0x7a]
        xor ebx, ebx
    character:
        xor r8d, r8d
    clear:
        mov byte ptr [rdi+r8], 0
        inc r8d
        cmp r8d, {CAPACITY}
        jb clear
        xor r8d, r8d
        xor r9d, r9d
    copy:
        xor eax, eax
        mov al, byte ptr [rsi+r8]
        test eax, eax
        je next_native
        # 112/113 are qualified additions; 114..125 are equipment passives.
        # The native row renderer suppresses
        # them but still counts their slots. Virtual attacks are added below.
        # Compact the view without changing equipment or saved learned lists.
        cmp eax, 112
        jae next_native
    store:
        mov byte ptr [rdi+r9], al
        inc r9d
    next_native:
        inc r8d
        cmp r8d, 32
        jb copy
        add rsi, {STRIDE}
        add rdi, {STRIDE}
        inc ebx
        cmp ebx, 7
        jb character
        cmp byte ptr {mem(data+0x1a42)}, 0
        je done
        lea rsi, {mem(0x564d40)}
        mov r13d, 48
    recipe:
        movzx ebx, byte ptr [rsi]
        cmp ebx, 255
        je done
        movzx eax, byte ptr [rsi+1]
        movzx edx, byte ptr [rsi+2]
        cmp eax, 9
        ja next
        cmp edx, 9
        ja next
        movzx ecx, byte ptr [r12+rax*8+0xbb8]
        sub ecx, 3
        cmp ecx, 1
        ja next
        cmp byte ptr [r12+rdx*8+0xbb8], 0
        je next
        mov r8b, byte ptr [rsi+3]
        cmp byte ptr [r12+rax*8+0xbb9], r8b
        jb next
        mov r8b, byte ptr [rsi+4]
        cmp byte ptr [r12+rdx*8+0xbb9], r8b
        jb next
        add ecx, 2
        imul ecx, ecx, {STRIDE}
        lea rdi, {mem(state)}
        add rdi, rcx
        xor eax, eax
        mov edx, {CAPACITY}
    search:
        cmp byte ptr [rdi+rax], bl
        je next
        cmp byte ptr [rdi+rax], 0
        jne occupied
        cmp edx, {CAPACITY}
        cmove edx, eax
    occupied:
        inc eax
        cmp eax, {CAPACITY}
        jb search
        cmp edx, {CAPACITY}
        jae next
        mov byte ptr [rdi+rdx], bl
    next:
        add rsi, 5
        dec r13d
        jne recipe
    done:
        {teamup_append}
        pop r13
        pop r12
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
    # ECX character, EDX arte, R8 master. Return membership in EAX. Rebuild
    # here so command validation remains correct after loading/reassigning.
    available=emit('fringe_available',f'''
        cmp ecx, 6
        ja no
        test edx, edx
        je no
        cmp edx, 255
        ja no
        test r8, r8
        je no
        push rcx
        push rdx
        sub rsp, 0x28
        mov rcx, r8
        call {refresh:#x}
        add rsp, 0x28
        pop rdx
        pop rcx
        imul r9d, ecx, {STRIDE}
        lea r8, {mem(state)}
        add r8, r9
        mov r9d, {CAPACITY}
    search:
        cmp byte ptr [r8], dl
        je yes
        inc r8
        dec r9d
        jne search
    no:
        xor eax, eax
        ret
    yes:
        mov eax, 1
        ret
    ''')
    return dict(state_rva=state,size=SIZE,stride=STRIDE,capacity=CAPACITY,
                refresh=refresh,available=available,option_flag=18,
                native_save_lists_unchanged=True,partner_assignment_only=True)
