"""Freeze virtual arte identity before native loading/actor recovery can change it."""
from spell_mastery_patch import preserve

TAG_OFFSET = 0x5400  # 16 * 16: owner Q, arte D, reserved D
REQUEST_OFFSET = 0x5500  # 7 * 16: actor Q, requested arte D
FRAME_OFFSET = 0x5600  # active callback Q, native tick decision D


def step_guard(info, label):
    """Use the dispatcher's decision, not its already-transformed fade byte."""
    mem = info['frame_mem']
    return f'''cmp qword ptr {mem[0]}, 0; je step_fallback
        cmp dword ptr {mem[1]}, 0; je {label}; jmp step_allowed
    step_fallback: cmp byte ptr {mem[2]}, 0; jne {label}
    step_allowed:'''


def wire(emit, mem, jump, info):
    state = info['state_rva']
    tags = state + TAG_OFFSET
    requests = state + REQUEST_OFFSET
    rows = info['recipes'] + [dict(id=112,effect=24)]
    match = []
    for row in rows:
        aid, effect = row['id'], row['effect']
        match.append(f'cmp edx, {aid}; jne id_{aid}; cmp ebp, {effect}; je store; jmp done; id_{aid}:')
    capture = emit('custom_effect_identity_capture', preserve(f'''
        mov rax, r14; lea r10, {mem(0x12cfca0)}; sub rax, r10
        xor edx, edx; mov r10d, 0x120; div r10
        test edx, edx; jne done; cmp eax, 16; jae done
        shl eax, 4; lea r11, {mem(tags)}; add r11, rax
        mov qword ptr [r11], 0; mov qword ptr [r11+8], 0
        cmp byte ptr [r12+0x51], 0; jne done
        movzx ecx, byte ptr [r12+0x4f]; cmp ecx, 6; ja done
        # Native loading continuations retain the old instance identity.
        mov rax, qword ptr [rsp+0x98]
        lea r10, {mem(0x115cef)}; cmp rax, r10; jne root
        lea rax, [r15-0x3a]; lea r10, {mem(0x12cfca0)}; sub rax, r10
        cmp rax, 0x1200; jae root
        xor edx, edx; mov r10d, 0x120; div r10
        test edx, edx; jne root
        shl eax, 4; lea r10, {mem(tags)}; add r10, rax
        cmp qword ptr [r10], r12; jne root
        mov edx, dword ptr [r10+8]; jmp match
    root:
        movzx edx, byte ptr [r12+0x6d]
        cmp ebp, 124; jne match
        shl ecx, 4; lea r10, {mem(requests)}; add r10, rcx
        cmp qword ptr [r10], r12; jne match
        mov edx, dword ptr [r10+8]
    match:
        {''.join(match)}
        jmp done
    store:
        mov qword ptr [r11], r12; mov dword ptr [r11+8], edx
    done:
    ''') + 'mov byte ptr [r14+0x30], al; mov qword ptr [r14+0x10], rdi; jmp 0x114a57')
    jump(0x114a4f, 8, capture, 'Freeze custom arte identity across asynchronous resource loading')
    lookup = emit('custom_effect_identity', f'''
        push rdx; push r10; push r11
        mov rax, rcx; lea r10, {mem(0x12cfca0)}; sub rax, r10
        cmp rax, 0x1200; jae absent
        xor edx, edx; mov r10d, 0x120; div r10
        test edx, edx; jne absent
        shl eax, 4; lea r10, {mem(tags)}; add r10, rax
        mov r11, qword ptr [rcx]; cmp qword ptr [r10], r11; jne absent
        mov eax, dword ptr [r10+8]; jmp done
    absent: xor eax, eax
    done: pop r11; pop r10; pop rdx; ret
    ''')
    info['identity'] = dict(tags=tags, requests=requests, capture=capture, lookup=lookup)
    return lookup
