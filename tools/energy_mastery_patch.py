"""Farah's optional Energy faculties, at the native healing application sites.

No new cast/effect allocations, TP charges or save fields. Secondary healing
uses the primary theoretical amount and the native green-number queue.
Preference IDs 128..133 in Farah's existing per-save disable-bit record.
"""
LEVELS = (10, 20, 30, 15, 25, 30)
PREFERENCE_IDS = tuple(range(128, 134))
FLAG_OFFSET = 0x1a41


def emit_energy(emit, mem, jump, data, usage):
    choices = usage['preferences']['live_rva']
    flag = data + FLAG_OFFSET
    tests = ''
    for i, level in enumerate(LEVELS):
        tests += f'''
            cmp r8d, {level}
            jb skip_{i}
            test byte ptr {mem(choices+32+16)}, {1<<i}
            jne skip_{i}
            or eax, {1<<i}
        skip_{i}:
        '''
    enabled = emit('energy_enabled_faculties', f'''
        xor eax, eax
        cmp byte ptr {mem(flag)}, 0
        je done
        movzx r8d, byte ptr {mem(0x11cb038)}
        movzx r9d, byte ptr {mem(0x11cb040)}
        cmp r8d, r9d
        cmova r8d, r9d
        cmp r8d, 30
        ja done
        {tests}
    done:
        ret
    ''')
    owner = emit('energy_battle_faculties', f'''
        xor eax, eax
        test rcx, rcx
        je done
        cmp byte ptr [rcx+0x4f], 1
        jne done
        cmp byte ptr [rcx+0x51], 0
        jne done
        jmp {enabled:#x}
    done:
        ret
    ''')
    # RCX actor/menu-character pointer, R8 mode (0 battle, 1 menu).
    # EAX current HP (zero if ineligible), R9D max HP. Full HP is excluded.
    candidate = emit('energy_candidate_stats', '''
        xor eax, eax
        xor r9d, r9d
        test rcx, rcx
        je done
        test r8d, r8d
        jne menu
        cmp byte ptr [rcx+0x51], 0
        jne done
        cmp byte ptr [rcx+0x4f], 6
        ja done
        cmp word ptr [rcx+0x3c], 1
        jne done
        mov r9, qword ptr [rcx+0xe8]
        test r9, r9
        je done
        mov r9d, dword ptr [r9+0x18]
        mov eax, dword ptr [rcx+0x2c]
        jmp check
    menu:
        test byte ptr [rcx+0x5b], 8
        jne done
        movzx r9d, word ptr [rcx+0x36]
        movzx eax, word ptr [rcx+0x38]
    check:
        test eax, eax
        jle invalid
        cmp eax, r9d
        jl done
    invalid:
        xor eax, eax
    done:
        ret
    ''')
    # Snapshot the two lowest HP ratios before any extra heal. Stable party
    # order resolves ties; 64-bit cross-products avoid integer truncation.
    select = emit('energy_secondary_targets', f'''
        push rbx
        push rsi
        push rdi
        push r12
        push r13
        push r14
        push r15
        sub rsp, 0x30
        mov r12, rcx
        mov r13d, edx
        xor esi, esi
        xor edi, edi
        xor r14d, r14d
        mov r15d, 6
        test edx, edx
        jne next
        movzx r15d, byte ptr {mem(0x12cece8)}
        cmp r15d, 8
        ja done
    next:
        cmp r14d, r15d
        jae done
        test r13d, r13d
        jne menu_pointer
        mov rbx, qword ptr {mem(0x12cecd8)}
        test rbx, rbx
        je done
        imul eax, r14d, 0x248
        add rbx, rax
        jmp consider
    menu_pointer:
        lea rax, {mem(0x11cad10)}
        movzx eax, word ptr [rax+r14*2]
        dec eax
        cmp eax, 6
        ja skip
        imul eax, eax, 0xd0
        lea rbx, {mem(0x11ca420)}
        add rbx, rax
    consider:
        cmp rbx, r12
        je skip
        cmp rbx, rdi
        je skip
        cmp rbx, rsi
        je skip
        mov rcx, rbx
        mov r8d, r13d
        call {candidate:#x}
        test eax, eax
        je skip
        mov dword ptr [rsp+0x20], eax
        mov dword ptr [rsp+0x24], r9d
        test rdi, rdi
        je first
        mov rcx, rdi
        call {candidate:#x}
        mov ecx, dword ptr [rsp+0x20]
        imul rcx, r9
        mov edx, dword ptr [rsp+0x24]
        imul rax, rdx
        cmp rcx, rax
        jb first
        test rsi, rsi
        je second
        mov rcx, rsi
        call {candidate:#x}
        mov ecx, dword ptr [rsp+0x20]
        imul rcx, r9
        mov edx, dword ptr [rsp+0x24]
        imul rax, rdx
        cmp rcx, rax
        jae skip
    second:
        mov rsi, rbx
        jmp skip
    first:
        mov rsi, rdi
        mov rdi, rbx
    skip:
        inc r14d
        jmp next
    done:
        mov rax, rdi
        mov rdx, rsi
        add rsp, 0x30
        pop r15
        pop r14
        pop r13
        pop r12
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
    # Same stack/locals as 8d5e0 at its HP-clamp and number-emission tail.
    # Only the source of EBX differs: an absolute amount instead of a percent.
    absolute = emit('energy_battle_heal_amount', '''
        test rcx, rcx
        je done
        cmp word ptr [rcx+0x3c], 1
        jne done
        cmp dword ptr [rcx+0x2c], 0
        jle done
        test edx, edx
        jle done
        mov qword ptr [rsp+0x18], rbp
        mov qword ptr [rsp+0x20], rsi
        push rdi
        sub rsp, 0x20
        mov qword ptr [rsp+0x38], rbx
        mov ebx, edx
        movzx esi, word ptr [rcx+0x82]
        sub si, word ptr [rcx+0x84]
        shl si, 3
        add si, word ptr [rcx+0x12]
        movzx ebp, word ptr [rcx+0x10]
        mov edi, 1
        add dword ptr [rcx+0x2c], ebx
        or word ptr [rcx+0x48], 8
        jmp 0x8d68b
    done:
        ret
    ''')
    menu_amount = emit('energy_menu_heal_amount', '''
        test rcx, rcx
        je done
        test byte ptr [rcx+0x5b], 8
        jne done
        movzx eax, word ptr [rcx+0x38]
        test eax, eax
        je done
        add eax, edx
        movzx r9d, word ptr [rcx+0x36]
        cmp eax, r9d
        cmova eax, r9d
        mov word ptr [rcx+0x38], ax
    done:
        ret
    ''')
    # RCX main target, EDX faculty bitset, R8D mode. Each sibling is applied
    # once here, without spawning another Healer effect or incrementing usage.
    healer = emit('energy_healer', f'''
        push rbx
        push rbp
        push rsi
        push rdi
        push r12
        push r13
        push r14
        sub rsp, 0x20
        mov rbx, rcx
        mov ebp, edx
        mov r12d, r8d
        mov r13d, 30
        test ebp, 1
        je percentage
        mov r13d, 40
    percentage:
        xor esi, esi
        xor edi, edi
        xor r14d, r14d
        test ebp, 6
        je primary
        test r12d, r12d
        jne menu_max
        cmp word ptr [rbx+0x3c], 1
        jne primary
        cmp dword ptr [rbx+0x2c], 0
        jle primary
        mov rax, qword ptr [rbx+0xe8]
        mov eax, dword ptr [rax+0x18]
        jmp nominal
    menu_max:
        test byte ptr [rbx+0x5b], 8
        jne primary
        cmp word ptr [rbx+0x38], 0
        je primary
        movzx eax, word ptr [rbx+0x36]
    nominal:
        imul eax, r13d
        xor edx, edx
        mov ecx, 100
        div ecx
        mov r14d, eax
        mov rcx, rbx
        mov edx, r12d
        call {select:#x}
        mov rdi, rax
        mov rsi, rdx
    primary:
        mov rcx, rbx
        mov edx, r13d
        test r12d, r12d
        jne menu_primary
        call 0x8d5e0
        jmp extras
    menu_primary:
        lea rax, {mem(0x11ca420)}
        sub rcx, rax
        mov rax, rcx
        xor edx, edx
        mov ecx, 0xd0
        div ecx
        mov ecx, eax
        mov edx, r13d
        call 0x21dcd0
    extras:
        test ebp, 2
        je third
        mov rcx, rdi
        mov edx, r14d
        shr edx, 1
        test r12d, r12d
        jne menu_second
        call {absolute:#x}
        jmp third
    menu_second:
        call {menu_amount:#x}
    third:
        test ebp, 4
        je done
        mov rcx, rsi
        # With the second-target faculty disabled, the third-target faculty
        # still adds one distinct ally at 25%, starting with the most injured.
        test ebp, 2
        jne third_target
        mov rcx, rdi
    third_target:
        mov edx, r14d
        shr edx, 2
        test r12d, r12d
        jne menu_third
        call {absolute:#x}
        jmp done
    menu_third:
        call {menu_amount:#x}
    done:
        add rsp, 0x20
        pop r14
        pop r13
        pop r12
        pop rdi
        pop rsi
        pop rbp
        pop rbx
        ret
    ''')
    detox = emit('energy_detoxify', f'''
        push rbx
        sub rsp, 0x20
        mov rbx, rcx
        test r8d, r8d
        jne menu
        and dword ptr [rcx+0x30], 0xfffffbfe
        cmp word ptr [rcx+0x3c], 1
        jne done
        test edx, 16
        je heal
        # Same mask and transient-ailment reset as Recover at cd58b/cd60d.
        and dword ptr [rcx+0x30], 0xfdff99fe
        mov word ptr [rcx+0x36], 0
        mov byte ptr [rcx+0x74], 0
        or word ptr [rcx+0x48], 0x20
    heal:
        test edx, 8
        je done
        mov edx, 25
        call 0x8d5e0
        jmp done
    menu:
        and byte ptr [rcx+0x5b], 0xfa
        test byte ptr [rcx+0x5b], 8
        jne done
        test edx, 16
        je menu_heal
        # Recover's persistent-state mask at 224828; KO bit 8 is retained.
        and byte ptr [rcx+0x5b], 0xe8
    menu_heal:
        test edx, 8
        je done
        movzx edx, word ptr [rcx+0x36]
        shr edx, 2
        call {menu_amount:#x}
    done:
        add rsp, 0x20
        pop rbx
        ret
    ''')

    def preserve(body, result_edx=False):
        # Native menu helpers also keep R10/R11 live across calls. Preserve
        # the entire volatile integer state at these instruction-site hooks.
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
            {'mov dword ptr [rsp+0x40], edx' if result_edx else ''}
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
    for name, site, size, continuation in (
        ('healer',0xcbee3,10,0xcbeed),('detoxify',0xccfb1,7,0xccfb8)):
        target=healer if name=='healer' else detox
        hook=emit('energy_battle_'+name, preserve(f'''
            mov rcx, qword ptr [rsi]
            call {owner:#x}
            mov edx, eax
            mov rcx, qword ptr [rsi+8]
            xor r8d, r8d
            call {target:#x}
        ''')+f'jmp {continuation:#x}')
        jump(site,size,hook,'Energy: Farah '+name+' at native application frame')
    for name,site,size,continuation in (
        ('healer',0x22459c,13,0x2245a9),('detoxify',0x2245bf,9,0x2245c8)):
        target=healer if name=='healer' else detox
        hook=emit('energy_menu_'+name,preserve(f'''
            xor eax, eax
            cmp edi, 1
            jne ready
            call {enabled:#x}
        ready:
            mov edx, eax
            imul ecx, esi, 0xd0
            lea rax, {mem(0x11ca420)}
            add rcx, rax
            mov r8d, 1
            call {target:#x}
        ''')+f'jmp {continuation:#x}')
        jump(site,size,hook,'Energy: '+name+' from the native field menu')
    for mode,site in (('battle',0xccca6),('menu',0x2245d4)):
        condition=(f'mov rcx, qword ptr [rsi]; call {owner:#x}' if mode=='battle' else
                   f'xor eax, eax; cmp edi, 1; jne percent; call {enabled:#x}')
        hook=emit('energy_'+mode+'_life',preserve(f'''
            {condition}
        percent:
            mov edx, 20
            test eax, 32
            je done
            mov edx, 35
        done:
        ''',True)+f'jmp {site+5:#x}')
        jump(site,5,hook,'Energy: Life 35% at level 30; native revival retained')
    eligible=emit('energy_menu_detoxify_eligible',f'''
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        sub rsp, 0x28
        lea rdx, [r9+r10+0x11ca420]
        call {enabled:#x}
        movzx ecx, byte ptr [rdx+0x5b]
        test ecx, 8
        jne rejected
        test eax, 16
        je healing
        test ecx, 0x17
        jne accepted
    healing:
        test eax, 8
        je native
        movzx eax, word ptr [rdx+0x38]
        test eax, eax
        je rejected
        cmp ax, word ptr [rdx+0x36]
        jb accepted
    native:
        mov eax, ecx
        and eax, 5
        jmp done
    accepted:
        mov eax, 1
        jmp done
    rejected:
        xor eax, eax
    done:
        add rsp, 0x28
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        ret
    ''')
    jump(0x2244e3,7,eligible,'Energy: allow injured or newly curable Detoxify menu targets')
    return dict(flag_rva=flag, levels=list(LEVELS), preference_ids=list(PREFERENCE_IDS),
                absolute_heal_rva=absolute, select_targets_rva=select,
                character=1, level_source='min(Punch, Kick)',
                battle_and_menu=True, secondary_basis='theoretical primary heal',
                secondary_selection='distinct living injured allies, lowest HP ratio first',
                detoxify_battle_mask=0x2006601, detoxify_menu_mask=0x17,
                detoxify_exceptions='KO and states outside native Recover purification',
                runtime_validated=False)
