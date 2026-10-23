"""Battle events for shared Craymel faculties. No recursive spell allocation."""
from craymel_faculties import preserve, FLAG_OFFSET


def emit_combat(emit, mem, jump, data, info):
    enabled, slot = info['enabled'], info['slot']
    state=info['state_rva']; tiers=info['tiers']
    heal=info['energy']['absolute_heal_rva']
    select=info['energy']['select_targets_rva']
    def q(spirit,node,actor='rbx'):
        return f'mov rcx, {actor}; mov edx, {spirit}; mov r8d, {node}; call {enabled:#x}'
    def t(name,actor='rbx'):
        return f'mov rcx, {actor}; call {tiers[name]:#x}'
    # Native TP numbers with explicit cap before the signed-word native add.
    tp=emit('craymel_restore_tp',f'''
        test rcx, rcx; je done
        cmp byte ptr [rcx+0x51], 0; jne done
        cmp word ptr [rcx+0x3c], 1; jne done
        cmp dword ptr [rcx+0x2c], 0; jle done
        test edx, edx; jle done
        mov r8, qword ptr [rcx+0xe8]; test r8, r8; je done
        movsx eax, word ptr [r8+0x1c]; movsx r8d, word ptr [rcx+0x34]
        sub eax, r8d; test eax, eax; jle done
        cmp edx, eax; cmovg edx, eax
        jmp 0x8fbf0
    done: ret
    ''')
    # RCX original recipient (excluded), EDX amount, R8D 0 HP / 1 TP.
    share=emit('craymel_share_resources',f'''
        push rbx; push rsi; push rdi; push rbp; push r12; sub rsp, 0x20
        mov rbx, rcx; mov esi, edx; mov edi, r8d; xor ebp, ebp
        cmp byte ptr {mem(0x12cece8)}, 8; ja done
    next:
        movzx eax, byte ptr {mem(0x12cece8)}; cmp ebp, eax; jae done
        imul eax, ebp, 0x248; mov r12, qword ptr {mem(0x12cecd8)}
        test r12, r12; je done
        add r12, rax; cmp r12, rbx; je skip
        cmp byte ptr [r12+0x51], 0; jne skip
        cmp byte ptr [r12+0x4f], 6; ja skip
        mov rcx, r12; mov edx, esi; test edi, edi; jne mana
        call {heal:#x}; jmp skip
    mana: call {tp:#x}
    skip: inc ebp; jmp next
    done: add rsp, 0x20; pop r12; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    # Called only after a real successful TP payment. EDX actual amount,
    # R8D old TP; admission checks never award TP or spend a per-battle charge.
    spent=emit('craymel_mana_spent',f'''
        push rbx; push rsi; push rdi; push rbp; sub rsp, 0x28
        mov rbx, rcx; mov esi, edx; mov edi, r8d
        test esi, esi; jle done
        call {slot:#x}; mov rbp, rax; test rbp, rbp; je done
        {t('mana_share')}; test eax, eax; je second_wind
        mov dword ptr [rsp+0x20], eax
        add dword ptr [rbp+52], esi
    sharing:
        cmp dword ptr [rbp+52], 50; jb second_wind
        sub dword ptr [rbp+52], 50
        mov rcx, rbx; mov edx, dword ptr [rsp+0x20]; mov r8d, 1; call {share:#x}
        jmp sharing
    second_wind:
        {q(8,3)}; test eax, eax; je done
        cmp byte ptr [rbp+46], 0; jne done
        mov rax, qword ptr [rbx+0xe8]; test rax, rax; je done
        movsx ecx, word ptr [rax+0x1c]; shr ecx, 2
        cmp edi, ecx; jb done
        movsx eax, word ptr [rbx+0x34]; cmp eax, ecx; jae done
        mov byte ptr [rbp+46], 1
        mov edx, ecx; mov rcx, rbx; call {tp:#x}
    done: add rsp, 0x28; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    # First completed offensive spell prepares a heal; subsequent successful
    # completions also drive Sekundes. Failed admission/cancellation do not.
    completed=emit('craymel_cast_completed',f'''
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx; mov esi, edx
        call {slot:#x}; mov rdi, rax; test rdi, rdi; je done
        {q(9,3)}; test eax, eax; je no_repeat
        cmp dword ptr [rdi+56], esi; jne restart
        cmp dword ptr [rdi+60], 3; jae remember
        inc dword ptr [rdi+60]; jmp remember
    restart: mov dword ptr [rdi+60], 1
    remember: mov dword ptr [rdi+56], esi; jmp prepared
    no_repeat: mov dword ptr [rdi+56], 0; mov dword ptr [rdi+60], 0
    prepared:
        mov dword ptr [rdi+88], 0
        cmp esi, 54; jb offensive_check
        cmp esi, 58; ja offensive_check
        cmp byte ptr [rdi+47], 0; je done
        {t('prepared')}; mov dword ptr [rdi+88], eax
        mov byte ptr [rdi+47], 0
        jmp done
    offensive_check:
        cmp esi, 70; jb done
        cmp esi, 101; jbe offensive
        cmp esi, 112; je offensive
        cmp esi, 113; jne done
    offensive:
        {t('prepared')}; test eax, eax; je done
        mov byte ptr [rdi+47], 1
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    cancel=emit('craymel_cast_cancelled',f'''
        push rbx; push rsi; sub rsp, 0x28
        mov rbx, rcx; call {slot:#x}; mov rsi, rax; test rsi, rsi; je done
        {t('memory')}; test eax, eax; je done
        movzx eax, word ptr [rbx+0x8c]; mov edx, dword ptr [rsi+72]
        sub edx, eax; jle done
        mov dword ptr [rsi+68], edx
        movzx eax, byte ptr [rbx+0x6d]; mov dword ptr [rsi+64], eax
    done: add rsp, 0x28; pop rsi; pop rbx; ret
    ''')
    # Volt critical status lives in the immutable origin word alongside the
    # ordinary EXP power coefficient. Child effects/projectiles inherit it.
    tag=emit('craymel_origin_critical',f'''
        push rbx; sub rsp, 0x20; mov rbx, rcx
        movzx eax, word ptr [rbx+8]; cmp eax, 70; jb done
        cmp eax, 101; jbe offensive
        cmp eax, 112; je offensive
        cmp eax, 113; jne done
    offensive:
        mov rcx, qword ptr [rbx]; call {tiers['critical']:#x}
        test eax, eax; je done
        mov ecx, eax; call {info['roll']:#x}; test eax, eax; je done
        or dword ptr [rbx+12], 0x10000
    done: add rsp, 0x20; pop rbx; ret
    ''')
    # Source record in RCX, incoming damage in EDX, native critical flag R8.
    power=emit('craymel_offensive_power',f'''
        push rbx; push rsi; push rdi; push rbp; sub rsp, 0x28
        mov rdi, rcx; mov esi, edx; mov ebp, r8d; mov rbx, qword ptr [rcx]
        mov dword ptr [rsp+0x24], 0
        {t('power')}; mov dword ptr [rsp+0x20], eax
        mov rax, qword ptr [rbx+0xe8]; test rax, rax; je apply
        mov ecx, dword ptr [rbx+0x2c]; add ecx, ecx
        cmp ecx, dword ptr [rax+0x18]; jae apply
        {t('fervor')}; add dword ptr [rsp+0x20], eax
    apply:
        mov eax, dword ptr [rsp+0x20]; add eax, 100
        imul eax, esi; xor edx, edx; mov ecx, 100; div ecx; mov esi, eax
        test ebp, 2; jne done
        test dword ptr [rdi+12], 0x10000; je done
        {t('critical')}; test eax, eax; je done
        mov eax, esi; shr eax, 1; add esi, eax
        mov dword ptr [rsp+0x24], 1
    done: mov eax, esi; mov edx, dword ptr [rsp+0x24]
        add rsp, 0x28; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    # Damage dealt uses HP actually lost (no overkill farming); each real
    # projectile hit can heal, but a dead target cannot pay a second reward.
    impact=emit('craymel_offensive_impact',f'''
        push rbx; push rsi; push rdi; push rbp; push r12; sub rsp, 0x20
        mov rbx, rcx; mov rdi, rdx; mov esi, r8d
        cmp byte ptr {mem(0x12d0ef7)}, 6; jne done
        test rdi, rdi; je done
        cmp byte ptr [rdi+0x51], 1; jne done
        cmp dword ptr [rdi+0x2c], 0; jle done
        cmp esi, 0; jle done
        cmp esi, 30000; jle cap_hp
        mov esi, 30000
    cap_hp:
        cmp esi, dword ptr [rdi+0x2c]; cmovg esi, dword ptr [rdi+0x2c]
        {t('hp_drain')}; imul eax, esi; xor edx, edx; mov ecx, 1000; div ecx
        mov edx, eax; mov rcx, rbx; call {heal:#x}
        {q(7,4)}; test eax, eax; je mana
        mov rcx, rbx; xor edx, edx; call {select:#x}; mov r12, rax
        mov eax, esi; xor edx, edx; mov ecx, 20; div ecx
        mov edx, eax; mov rcx, r12; call {heal:#x}
    mana:
        cmp esi, dword ptr [rdi+0x2c]; jb singularity
        {t('tp_drain')}; imul eax, esi; xor edx, edx; mov ecx, 1000; div ecx
        mov edx, eax; mov rcx, rbx; call {tp:#x}
    singularity:
        {q(8,4)}; test eax, eax; je done
        mov rcx, rbx; call {slot:#x}; mov rbp, rax
        mov eax, dword ptr {mem(0x12cea40)}; cmp eax, dword ptr [rbp+84]; jb done
        add eax, 600; mov dword ptr [rbp+84], eax
        # Conservative eligibility: normal grounded enemies only, native size
        # less than 48, no boss type; force is capped and never teleports.
        mov r12, qword ptr {mem(0x12cece0)}; test r12, r12; je done
        movzx ebp, byte ptr {mem(0x12cece9)}; cmp ebp, 8; ja done
    pull:
        test ebp, ebp; je done
        cmp r12, rdi; je next
        cmp word ptr [r12+0x3c], 1; jne next
        cmp dword ptr [r12+0x2c], 0; jle next
        cmp word ptr [r12+0x12], 0; jne next
        mov rax, qword ptr [r12+0xe8]; test rax, rax; je next
        cmp byte ptr [rax+0x5a], 0; jne next
        movzx eax, word ptr [r12+0x82]; cmp eax, 48; ja next
        movsx eax, word ptr [rdi+0x10]; movsx edx, word ptr [r12+0x10]; sub eax, edx
        cmp eax, 2560; jg next
        cmp eax, -2560; jl next
        sar eax, 5; mov edx, 32; cmp eax, edx; cmovg eax, edx
        mov edx, -32; cmp eax, edx; cmovl eax, edx
        mov word ptr [r12+0x18], ax
    next: add r12, 0x248; dec ebp; jmp pull
    done: add rsp, 0x20; pop r12; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    # RCX victim, EDX incoming damage, R8 magic flag. Reductions multiply;
    # mana bulwark spends only TP above the strict 25% reserve.
    defense=emit('craymel_incoming_damage',f'''
        push rbx; push rsi; push rdi; push rbp; sub rsp, 0x28
        mov rbx, rcx; mov esi, edx; mov edi, r8d
        cmp byte ptr {mem(0x12d0ef7)}, 6; jne done
        cmp byte ptr {mem(data+FLAG_OFFSET)}, 0; je done
        test rcx, rcx; je done
        cmp dword ptr [rcx+0x2c], 0; jle done
        cmp byte ptr [rcx+0x51], 0; jne done
        call {slot:#x}; mov rbp, rax; test rbp, rbp; je done
        mov eax, dword ptr {mem(0x12cea40)}
        cmp eax, dword ptr [rbp+48]; jae magic
        {q(4,5)}; test eax, eax; je magic
        xor esi, esi; jmp done
    magic:
        test edi, edi; je casting
        {t('magic_defense')}; mov ecx, 100; sub ecx, eax
        imul eax, esi, 100; imul esi, ecx; mov eax, esi
        add eax, 99; xor edx, edx; mov ecx, 100; div ecx; mov esi, eax
    casting:
        cmp byte ptr [rbx+0x52], 10; jne protect
        cmp word ptr [rbx+0x8c], 0; jle protect
        {t('cast_defense')}; mov ecx, 100; sub ecx, eax
        imul esi, ecx; mov eax, esi; add eax, 99; xor edx, edx; mov ecx, 100; div ecx; mov esi, eax
    protect:
        mov eax, dword ptr {mem(0x12cea40)}; cmp eax, dword ptr [rbp+40]; jae shield
        mov rcx, qword ptr [rbp+144]; mov edx, 6; mov r8d, 5; call {enabled:#x}
        test eax, eax; je shield
        inc esi; shr esi, 1
    shield:
        mov eax, dword ptr {mem(0x12cea40)}; cmp eax, dword ptr [rbp+12]; jae mana
        mov rcx, qword ptr [rbp+136]; xor edx, edx; mov r8d, 5; call {enabled:#x}
        test eax, eax; je mana
        mov eax, dword ptr [rbp+8]; cmp eax, esi; cmova eax, esi
        sub esi, eax; sub dword ptr [rbp+8], eax
    mana:
        {q(8,1)}; test eax, eax; je fatal
        mov rax, qword ptr [rbx+0xe8]; test rax, rax; je fatal
        movsx ecx, word ptr [rax+0x1c]; add ecx, 3; shr ecx, 2
        movsx edx, word ptr [rbx+0x34]; sub edx, ecx; jle fatal
        mov eax, esi; shr eax, 2; lea ecx, [rdx+rdx*4]
        cmp eax, ecx; cmova eax, ecx; test eax, eax; je fatal
        sub esi, eax; add eax, 4; xor edx, edx; mov ecx, 5; div ecx
        sub word ptr [rbx+0x34], ax; or word ptr [rbx+0x48], 0x20
    fatal:
        cmp esi, dword ptr [rbx+0x2c]; jb done
        cmp byte ptr [rbp+45], 0; jne done
        {q(4,5)}; test eax, eax; je done
        mov byte ptr [rbp+45], 1
        mov eax, dword ptr {mem(0x12cea40)}; add eax, 120; mov dword ptr [rbp+48], eax
        mov esi, dword ptr [rbx+0x2c]; dec esi
    done: mov eax, esi; add rsp, 0x28; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    info.update(tp=tp,share=share,spent=spent,completed=completed,cancel=cancel,
                tag=tag,power=power,impact=impact,defense=defense)
    return info
