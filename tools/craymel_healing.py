"""Craymel healing, bounded regeneration and real recovery-item sharing."""
from craymel_faculties import preserve, FLAG_OFFSET


def emit_healing(emit,mem,jump,data,info,mastery):
    enabled,slot=info['enabled'],info['slot']
    heal=info['energy']['absolute_heal_rva']
    select=info['energy']['select_targets_rva']
    def q(spirit,node):
        return f'mov rcx, rbx; mov edx, {spirit}; mov r8d, {node}; call {enabled:#x}'
    def t(name):
        return f'mov rcx, rbx; call {info["tiers"][name]:#x}'
    apply=emit('craymel_heal_target',f'''
        # RCX caster, RDX target, R8D theoretical amount, R9D single target.
        push rbx; push rsi; push rdi; push rbp; push r12; push r13; push r14
        sub rsp, 0x30
        mov rbx, rcx; mov rdi, rdx; mov esi, r8d; mov r14d, r9d
        test rdi, rdi; je done
        cmp byte ptr [rdi+0x51], 0; jne done
        cmp word ptr [rdi+0x3c], 1; jne done
        cmp dword ptr [rdi+0x2c], 0; jle done
        mov rcx, rdi; call {slot:#x}; mov rbp, rax; test rbp, rbp; je done
        mov rcx, rbx; call {slot:#x}; mov r12, rax; test r12, r12; je done
        mov rax, qword ptr [rdi+0xe8]; test rax, rax; je done
        mov r13d, dword ptr [rax+0x18]; test r13d, r13d; jle done
        # Prepared healing has been snapshotted at completed-cast time.
        {t('prepared')}; cmp eax, dword ptr [r12+88]; cmova eax, dword ptr [r12+88]
        add eax, 100; imul eax, esi; xor edx, edx; mov ecx, 100; div ecx; mov esi, eax
        {q(6,5)}; test eax, eax; je shield
        cmp byte ptr [r12+44], 0; jne shield
        mov eax, dword ptr [rdi+0x2c]; shl eax, 2; cmp eax, r13d; jae shield
        mov byte ptr [r12+44], 1
        mov eax, dword ptr {mem(0x12cea40)}; add eax, 300; mov dword ptr [rbp+40], eax
        mov qword ptr [rbp+144], rbx
    shield:
        {q(0,5)}; test eax, eax; je purify
        mov eax, dword ptr [rdi+0x2c]; add eax, esi; sub eax, r13d; jle purify
        mov dword ptr [rsp+0x20], eax
        mov eax, r13d; imul eax, eax, 15; xor edx, edx; mov ecx, 100; div ecx
        cmp eax, dword ptr [rsp+0x20]; cmova eax, dword ptr [rsp+0x20]
        mov dword ptr [rbp+8], eax
        mov eax, dword ptr {mem(0x12cea40)}; add eax, 600; mov dword ptr [rbp+12], eax
        mov qword ptr [rbp+136], rbx
    purify:
        {t('purify')}; test eax, eax; je regen
        mov ecx, dword ptr {mem(0x12cea40)}; cmp ecx, dword ptr [r12+76]; jb regen
        mov edx, dword ptr [rdi+0x30]; and edx, 0x02006601; je regen
        add eax, ecx; mov dword ptr [r12+76], eax
        # Clear one compatible condition, never KO or unrelated state bits.
        mov eax, edx; neg eax; and eax, edx; not eax; and dword ptr [rdi+0x30], eax
        or word ptr [rdi+0x48], 1
    regen:
        {q(6,4)}; test eax, eax; je primary
        mov eax, esi; shr eax, 2; mov dword ptr [rbp+16], eax
        mov dword ptr [rbp+20], 5
        mov eax, dword ptr {mem(0x12cea40)}; add eax, 60; mov dword ptr [rbp+24], eax
        mov qword ptr [rbp+152], rbx
    primary:
        mov rcx, rdi; mov edx, esi; call {heal:#x}
        test r14d, r14d; je done
        {t('heal_share')}; test eax, eax; je done
        imul eax, esi; xor edx, edx; mov ecx, 100; div ecx; mov esi, eax
        mov rcx, rdi; xor edx, edx; call {select:#x}
        mov rcx, rax; mov edx, esi; call {heal:#x}
    done:
        add rsp, 0x30; pop r14; pop r13; pop r12; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    dispatch=emit('craymel_heal_dispatch',f'''
        push rbx; push rsi; sub rsp, 0x28
        mov rbx, rcx; mov esi, edx
        cmp byte ptr {mem(data+FLAG_OFFSET)}, 0; je native
        cmp byte ptr {mem(0x12d0ef7)}, 6; jne native
        test edx, edx; jle native
        test rcx, rcx; je native
        cmp byte ptr [rcx+0x51], 0; jne native
        mov rax, qword ptr {mem(mastery['context_rva'])}; test rax, rax; je native
        movzx r9d, word ptr [rax+8]; cmp r9d, 54; jb native
        cmp r9d, 58; ja native
        mov rcx, qword ptr [rax]; test rcx, rcx; je native
        cmp byte ptr [rcx+0x51], 0; jne native
        movzx eax, byte ptr [rcx+0x4f]; sub eax, 2; cmp eax, 1; ja native
        mov rax, qword ptr [rbx+0xe8]; test rax, rax; je native
        mov eax, dword ptr [rax+0x18]; imul eax, esi
        xor edx, edx; mov r8d, 100; div r8d; mov r8d, eax
        cmp r9d, 54; je single
        cmp r9d, 56; je single
        xor r9d, r9d; jmp apply
    single: mov r9d, 1
    apply:
        mov rdx, rbx; call {apply:#x}
        add rsp, 0x28; pop rsi; pop rbx; ret
    native:
        mov rcx, rbx; mov edx, esi
        add rsp, 0x28; pop rsi; pop rbx
        mov qword ptr [rsp+0x18], rbp
        jmp 0x8d5e5
    ''')
    jump(0x8d5e0,5,dispatch,'Craymel healing: scoped caster, prepared bonus, shield, purification and sharing')
    tick=emit('craymel_regeneration_tick',f'''
        push rbx; push rsi; push rdi; push rbp; push r12; sub rsp, 0x20
        cmp byte ptr {mem(data+FLAG_OFFSET)}, 0; je done
        movzx ebp, byte ptr {mem(0x12cece8)}; cmp ebp, 8; ja done
        mov rbx, qword ptr {mem(0x12cecd8)}; test rbx, rbx; je done
    next:
        test ebp, ebp; je done
        mov rcx, rbx; call {slot:#x}; mov rsi, rax; test rsi, rsi; je skip
        cmp dword ptr [rsi+20], 0; je skip
        cmp dword ptr [rbx+0x2c], 0; jle clear
        mov eax, dword ptr {mem(0x12cea40)}; cmp eax, dword ptr [rsi+24]; jb skip
        mov rcx, qword ptr [rsi+152]; mov edx, 6; mov r8d, 4; call {enabled:#x}
        test eax, eax; je clear
        mov eax, dword ptr [rsi+16]; xor edx, edx; div dword ptr [rsi+20]
        sub dword ptr [rsi+16], eax; dec dword ptr [rsi+20]
        add dword ptr [rsi+24], 60
        mov rcx, rbx; mov edx, eax; call {heal:#x}; jmp skip
    clear: mov dword ptr [rsi+16], 0; mov dword ptr [rsi+20], 0
    skip: add rbx, 0x248; dec ebp; jmp next
    done: add rsp, 0x20; pop r12; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    clock=emit('craymel_battle_tick',f'''
        inc dword ptr {mem(0x12cea40)}
        {preserve(f'call {tick:#x}')}
        jmp 0xd3297
    ''')
    jump(0xd3291,6,clock,'Craymel regeneration advances only on the native unpaused battle clock')
    # Native item completion is synchronous. Snapshot every party recipient;
    # compute all deltas before sharing, so one share can never feed another.
    item=emit('craymel_item_completed',f'''
        push rbx; push rsi; push rdi; push rbp; push r12; sub rsp, 0xa0
        mov r12, rcx; xor ebp, ebp
        mov rbx, qword ptr {mem(0x12cecd8)}
        movzx esi, byte ptr {mem(0x12cece8)}
        test rbx, rbx; je native_only
        cmp esi, 8; ja native_only
    before:
        cmp ebp, esi; jae native
        imul eax, ebp, 0x248
        mov edx, dword ptr [rbx+rax+0x2c]; mov dword ptr [rsp+rbp*8+0x20], edx
        movsx edx, word ptr [rbx+rax+0x34]; mov dword ptr [rsp+rbp*8+0x24], edx
        inc ebp; jmp before
    native:
        mov rcx, r12; call 0x91600; mov r12d, eax
        test eax, eax; je done
        cmp byte ptr {mem(data+FLAG_OFFSET)}, 0; je done
        xor ebp, ebp
    delta:
        cmp ebp, esi; jae share_begin
        imul eax, ebp, 0x248
        mov edx, dword ptr [rbx+rax+0x2c]; sub edx, dword ptr [rsp+rbp*8+0x20]
        mov dword ptr [rsp+rbp*8+0x20], edx
        movsx edx, word ptr [rbx+rax+0x34]; sub edx, dword ptr [rsp+rbp*8+0x24]
        mov dword ptr [rsp+rbp*8+0x24], edx
        inc ebp; jmp delta
    share_begin: xor ebp, ebp
    share_next:
        cmp ebp, esi; jae done
        imul edi, ebp, 0x248; add rdi, rbx
        mov rcx, rdi; mov edx, 8; mov r8d, 2; call {enabled:#x}
        test eax, eax; je skip_item
        mov edx, dword ptr [rsp+rbp*8+0x20]; test edx, edx; jle mana
        shr edx, 2; mov rcx, rdi; xor r8d, r8d; call {info['share']:#x}
    mana:
        mov edx, dword ptr [rsp+rbp*8+0x24]; test edx, edx; jle skip_item
        shr edx, 2; mov rcx, rdi; mov r8d, 1; call {info['share']:#x}
    skip_item: inc ebp; jmp share_next
    native_only: mov rcx, r12; call 0x91600; mov r12d, eax
    done: mov eax, r12d; add rsp, 0xa0; pop r12; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    bridge=emit('craymel_item_event',f'call {item:#x}; jmp 0xd5ab1')
    jump(0xd5aac,5,bridge,'Share actual recovery-item gains after successful native item completion')
    info.update(heal=apply,heal_dispatch=dispatch,tick=tick,item=item)
    return info
