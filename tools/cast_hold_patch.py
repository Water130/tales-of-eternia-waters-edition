"""Build 25190541: resolve held commands at cast completion; L1 retains casts.

Uses the native issuer/mask fields, so autonomous AI does not read player input.
No native bindings or save structures are enlarged. Garde is no longer involved.
"""


def emit_cast_hold(emit, mem, jump, edit, data_rva, overlap, artesphere=False):
    choose = emit('held_summon_choice', f'''
        push r8
        push r9
        push r10
        push r11
        cmp eax, 70
        jb unchanged
        cmp eax, 95
        ja unchanged
        cmp byte ptr [rcx+0x51], 0
        jne unchanged
        movzx r10d, byte ptr [rcx+0x4f]
        sub r10d, 2
        cmp r10d, 1
        ja unchanged
        add r10d, 2
        mov r9, qword ptr {mem(0x12cea78)}
        test r9, r9
        je unchanged
        movzx r8d, byte ptr [r9+rax*8+2]
        test r8b, 0x10
        jne unchanged
        and r8d, 0x0f
        dec r8d
        cmp r8d, 9
        ja unchanged
        mov r9, qword ptr {mem(0x12cea60)}
        test r9, r9
        je unchanged
        lea r11d, [r10d+1]
        cmp byte ptr [r9+r8*8+0xbb8], r11b
        jne unchanged
        cmp byte ptr [r9+r8*8+0xbb9], 0
        je unchanged
        cmp word ptr [r9+r8*8+0xbba], 0xa000
        jne unchanged
        add r8d, 43
        imul r10, r10, 0xd0
        lea r10, [r9+r10+0x7a]
        mov r11d, 32
    learned:
        cmp byte ptr [r10], r8b
        je accepted
        inc r10
        dec r11d
        jne learned
        jmp unchanged
    accepted:
        mov eax, r8d
    unchanged:
        pop r11
        pop r10
        pop r9
        pop r8
        ret
    ''')

    save = 'pushfq; push rax; push rcx; push rdx; push r8; push r9; push r10; push r11'
    restore = 'pop r11; pop r10; pop r9; pop r8; pop rdx; pop rcx; pop rax; popfq'
    extra_caster = f'''
        cmp word ptr [rbx+0xa4], 0x100
        jne original
        cmp word ptr [rbx+0xa2], 0
        jne original
        test dword ptr {mem(0x8c9180)}, 0x80100
        jne hold_l1
        jmp release
    ''' if artesphere else 'jmp original'
    extra_branch = 'cmp edx, 0x100; je extra_button' if artesphere else ''
    extra_button = f'''
    extra_button:
        test dword ptr {mem(0x8c9180)}, 0x80000
        je release
        jmp choose
    ''' if artesphere else ''
    start = emit('cast_hold_resolution', f'''
        {save}
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne original
        cmp byte ptr [rbx+0x51], 0
        jne original
        movzx eax, byte ptr [rbx+0x4f]
        sub eax, 2
        cmp eax, 1
        jbe mage
        {extra_caster}
    mage:
        movzx edx, word ptr [rbx+0xa4]
        test edx, edx
        je original
        movzx ecx, word ptr [rbx+0xa2]
        test ecx, ecx
        jne original
        test dword ptr {mem(0x8c9180)}, 0x100
        jne hold_l1
        {extra_branch}
        cmp edx, 0x40
        je arte_button
        cmp edx, 0x400
        je attack_button
        cmp edx, 0x800
        jne original
        jmp arte_button
        {extra_button}
    arte_button:
        cmp byte ptr {mem(0x8c9230)}, 0
        je release
        jmp choose
    attack_button:
        cmp byte ptr {mem(0x8c922f)}, 0
        je release
    choose:
        movzx eax, byte ptr [rbx+0x6d]
        mov rcx, rbx
        call {choose:#x}
        cmp al, byte ptr [rbx+0x6d]
        je release
        mov byte ptr [rbx+0x6d], al
        mov r8, qword ptr {mem(0x12cea78)}
        movzx edx, byte ptr [r8+rax*8]
        mov word ptr [rbx+0x8e], dx
        movzx edx, byte ptr [r8+rax*8+2]
        and edx, 15
        shl edx, 2
        mov byte ptr [rbx+0x6c], dl
        movzx edx, word ptr [r8+rax*8+4]
        cmp byte ptr [rbx+0x4f], 3
        jne voice
        add edx, 0x9c
    voice:
        mov word ptr [rbx+0x4c], dx
        mov word ptr [rbx+0xa4], 0x2000
        {restore}
        jmp 0xd571d
    release:
        {restore}
        movsx edx, word ptr [rbx+0xa4]
        jmp 0xd53f0
    hold_l1:
        mov word ptr [rbx+0x8c], 4
        {restore}
        jmp 0xd571d
    original:
        {restore}
        movsx edx, word ptr [rbx+0xa4]
        jmp 0xd53c4
    ''')
    jump(0xd53bd, 7, start, 'Hold Arte chooses invocation at cast completion; L1 retains ready spell')
    if artesphere:
        # R2 belongs to the ally-shortcut family for native healing target
        # selection too (First Aid/Recover/etc. are handled at this branch).
        edit(0xd5408, b'\xb8\x00\x0d\x00\x00', 'R2 retains native ally-healing target selection')
    edit(0x9041e, b'\x90'*8, 'Keep full vitality when casting an ordinary same-element spell')

    # Read-only mirror of the dispatcher admission checks. Queue retries must
    # happen BEFORE TP/vitality are spent, especially now that summons are chosen
    # after incantation. Includes exhausted effect pools and loading records.
    policy = f'''
        cmp byte ptr {mem(0x12d0efb)}, 0
        jne serial
        lea r10, {mem(data_rva+0x200)}
        movzx r11d, byte ptr [r10+rdx]
        jmp scan
    serial:
    ''' if overlap else ''
    check_active = '''
        test r11d, r11d
        je blocked
        cmp word ptr [r8+0x3a], 2
        je blocked
        cmp word ptr [r8+0x3e], 0
        jne blocked
        movzx eax, byte ptr [r8+0x36]
        cmp eax, edx
        je blocked
        cmp byte ptr [r10+rax], 0
        je blocked
    ''' if overlap else 'jmp blocked'
    ready = emit('cast_dispatch_ready', f'''
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne blocked
        xor ecx, ecx
        xor r11d, r11d
        cmp edx, 100
        jae scan
        {policy}
        cmp word ptr {mem(0x12d0eaa)}, 0
        jne blocked
    scan:
        lea r8, {mem(0x12cfca0)}
        mov r9d, 16
    next_slot:
        cmp qword ptr [r8], 0
        je free_slot
        cmp edx, 100
        jae next
        cmp byte ptr [r8+0x33], 0
        je next
        {check_active}
        jmp next
    free_slot:
        mov ecx, 1
    next:
        add r8, 0x120
        dec r9d
        jne next_slot
        mov eax, ecx
        jmp done
    blocked:
        xor eax, eax
    done:
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        ret
    ''')
    start = emit('cast_precommit', f'''
        {save}
        cmp word ptr [rbx+0xa4], 0x2000
        jne ready
        movzx eax, byte ptr [rbx+0x6d]
        sub eax, 43
        cmp eax, 9
        ja cancel
        mov r8, qword ptr {mem(0x12cea60)}
        test r8, r8
        je cancel
        movzx edx, byte ptr [rbx+0x4f]
        inc edx
        cmp byte ptr [r8+rax*8+0xbb8], dl
        jne cancel
        cmp word ptr [r8+rax*8+0xbba], 0xa000
        jne cancel
    ready:
        movzx edx, word ptr [rbx+0x8e]
        call {ready:#x}
        test eax, eax
        je wait_slot
        cmp word ptr [rbx+0xa4], 0x2000
        jne admitted
        mov word ptr [rbx+0xa4], 0
    admitted:
        {restore}
        cmp byte ptr [rbx+0x51], r12b
        jne 0xd5452
        jmp 0xd5436
    wait_slot:
        mov word ptr [rbx+0x8c], 1
        {restore}
        jmp 0xd571d
    cancel:
        mov byte ptr [rbx+0x52], 0
        mov word ptr [rbx+0x8c], 0
        mov word ptr [rbx+0xa4], 0
        {restore}
        jmp 0xd571d
    ''')
    jump(0xd5430, 6, start, 'Check effect admission and selected summon vitality before any resource debit')
