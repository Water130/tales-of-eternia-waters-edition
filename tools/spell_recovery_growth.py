"""Release the caster early without shortening effect scripts or projectile life."""


def emit_recovery(emit, mem, jump, state, data, usage, preserve, faculties=None):
    bonus=''
    if faculties:
        bonus=f'''
            push rcx; push r8; push r10; push r11; sub rsp, 0x28
            mov dword ptr [rsp+0x20], eax
            mov rcx, r11; call {faculties['tiers']['recovery']:#x}
            mov edx, 100; sub edx, eax
            mov eax, 100; sub eax, dword ptr [rsp+0x20]
            imul eax, edx; xor edx, edx; mov ecx, 100; div ecx
            mov edx, 100; sub edx, eax; mov eax, edx
            add rsp, 0x28; pop r11; pop r10; pop r8; pop rcx
        '''
    roots = state + 0xc00
    # RCX effect, context already established by the audited callback wrapper.
    # Script times are absolute; -2 repeats schedule child operations and do
    # not reset the parent's timer (114f50..1150b5). Read at most 256 entries.
    recovery = emit('mastery_spell_recovery', preserve(f'''
        cmp byte ptr {mem(data+0x1a0c)}, 0
        je done
        mov r10, qword ptr {mem(state)}
        test r10, r10
        je done
        mov r11, qword ptr [rcx]
        test r11, r11
        je done
        cmp qword ptr [r10], r11
        jne done
        cmp byte ptr [r11+0x51], 0
        jne done
        movzx eax, byte ptr [r11+0x4f]
        sub eax, 2
        cmp eax, 1
        ja done
        add eax, 2
        lea rdx, {mem(roots)}
        cmp qword ptr [rdx+rax*8], rcx
        jne done
        cmp byte ptr [r11+0x52], 10
        jne done
        cmp byte ptr [r11+0x77], 0
        je done
        cmp word ptr [r11+0x8c], 0
        jne done
        movzx edx, word ptr [r10+8]
        cmp dl, byte ptr [r11+0x6d]
        jne done
        cmp edx, 70
        jae offensive_id
        cmp edx, 54
        jb done
        cmp edx, 66
        jbe script
        jmp done
    offensive_id:
        cmp edx, 101
        jbe offensive
        cmp edx, 112
        jb done
        cmp edx, 113
        ja done
    offensive:
        shl eax, 8
        add eax, edx
        lea r8, {mem(usage['preferences']['live_rva'])}
        bt dword ptr [r8], eax
        # Per-spell EXP and Sylph faculties have independent toggles.
    script:
        mov r8, qword ptr [rcx+0x10]
        test r8, r8
        je manual
        lea r9, {mem(state+0x5000)}
        cmp r8, r9
        jb native_script
        lea r9, {mem(state+0x7000)}
        cmp r8, r9
        jb script_ready
    native_script:
        lea r9, {mem(0x2a9000)}
        cmp r8, r9
        jb done
        lea r9, {mem(0x12d2000-2048)}
        cmp r8, r9
        ja done
    script_ready:
        mov r9d, 256
    scan:
        cmp word ptr [r8+2], -1
        je end_time
        add r8, 8
        dec r9d
        jne scan
        jmp done
    end_time:
        movzx r8d, word ptr [r8]
        test r8d, r8d
        je done
        cmp r8d, 4096
        ja done
        jmp threshold
    manual:
        # Three small spells end from native timer comparisons rather than
        # scripts. Keep their vanilla Maxwell-powered variants' durations.
        mov r8d, 80
        cmp edx, 75
        je threshold
        cmp edx, 79
        je grave
        cmp edx, 82
        jne done
        mov r8d, 80
        jmp maxwell
    grave:
        mov r8d, 36
    maxwell:
        movzx eax, byte ptr [r11+0x4f]
        inc eax
        mov r9, qword ptr {mem(0x12cea60)}
        test r9, r9
        je threshold
        cmp al, byte ptr [r9+0xbd8]
        jne threshold
        cmp edx, 79
        jne ice
        cmp word ptr [r9+0xbca], 0x8000
        jb threshold
        mov r8d, 48
        jmp threshold
    ice:
        cmp word ptr [r9+0xbda], 0x8000
        jb threshold
        mov r8d, 100
    threshold:
        cmp word ptr [r10+8], 82
        jne reduction
        # Ice Needles emits one projectile every twenty ticks; mastery also
        # extends its real native loop, so measure recovery against that end.
        movzx eax, word ptr [r10+10]
        mov r9d, 500
        cmp eax, r9d
        cmova eax, r9d
        imul eax, eax, 3
        xor edx, edx
        div r9d
        imul eax, eax, 20
        add r8d, eax
    reduction:
        xor eax, eax
        cmp word ptr [r10+8], 70
        jb faculty_bonus
        movzx eax, byte ptr [r11+0x4f]
        shl eax, 8
        movzx edx, word ptr [r10+8]
        add eax, edx
        lea r9, {mem(usage['preferences']['live_rva'])}
        bt dword ptr [r9], eax
        mov eax, 0
        jc faculty_bonus
        movzx eax, word ptr [r10+10]
        mov r9d, 500
        cmp eax, r9d
        cmova eax, r9d
        imul eax, eax, 15
        xor edx, edx
        div r9d
    faculty_bonus:
        {bonus}
        test eax, eax
        je done
        mov r9d, 100
        sub r9d, eax
        mov eax, r8d
        imul eax, r9d
        add eax, 99
        xor edx, edx
        mov r9d, 100
        div r9d
        movzx edx, word ptr [rcx+0x38]
        cmp edx, eax
        jb done
        # Mirror only the caster-release portion of 115ee0. The effect, its
        # timer, scripts, textures and pending damage are left running.
        mov byte ptr [r11+0x77], 0
        cmp byte ptr [r11+0x23a], 7
        jne done
        mov byte ptr [r11+0x23d], 0xff
    done:
    ''')+'ret')
    guard = emit('mastery_spell_release_owner', f'''
        push rdx
        push r8
        cmp byte ptr [rcx+0x51], 0
        jne native
        movzx edx, byte ptr [rcx+0x4f]
        sub edx, 2
        cmp edx, 1
        ja native
        add edx, 2
        lea r8, {mem(roots)}
        cmp qword ptr [r8+rdx*8], 0
        je native
        cmp qword ptr [r8+rdx*8], rbx
        je native
        pop r8
        pop rdx
        jmp 0x115f14
    native:
        pop r8
        pop rdx
        cmp word ptr [rcx+0x8e], ax
        jne 0x115f14
        jmp 0x115efd
    ''')
    jump(0x115ef4,9,guard,'Released spell cannot unlock a newer cast with the same native effect ID')
    return recovery, roots
