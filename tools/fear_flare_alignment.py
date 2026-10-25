"""Attach native Fear Flare smoke to each live meteor, with its original subtractive palette."""
from craymel_faculties import preserve


def wire(emit, mem, jump, pe, relocate, info):
    state=info['state_rva'];script=state+0x3360;queues=state+0x6200
    # 16 effect slots, eight 16-byte live-meteor records (0x6200..0x6a00).
    # At most four are pending: one meteor every six ticks, 20 ticks to ground.
    address=emit('fear_landing_queue',f'''
        mov rax, rcx; lea r10, {mem(0x12cfca0)}; sub rax, r10
        cmp rax, 0x1200; jae invalid
        xor edx, edx; mov r10d, 0x120; div r10d; test edx, edx; jne invalid
        shl eax, 7; lea r10, {mem(queues)}; add rax, r10; ret
    invalid: xor eax, eax; ret
    ''')
    capture=emit('fear_landing_capture',f'''
        push rbx; sub rsp, 0x20
        mov rcx, rdi; call {address:#x}; test rax, rax; je done
        mov rbx, rax; mov ecx, 8
    slot: cmp word ptr [rbx+10], 0; je found
        add rbx, 16; dec ecx; jne slot; jmp done
    found:
        mov qword ptr [rbx], rsi
        mov ax, word ptr [rdi+0x38]; mov word ptr [rbx+8], ax
        mov word ptr [rbx+10], 1
    done: add rsp, 0x20; pop rbx; ret
    ''')
    hook=emit('fear_meteor_capture_hook',f'''
        {preserve(f'lea rax, {mem(script)}; cmp qword ptr [rdi+0x10], rax; jne done; call {capture:#x}; done:')}
        {relocate(pe.get_data(0x9d70a,9),0x9d70a)}
        jmp 0x9d713
    ''')
    jump(0x9d70a,9,hook,'Player Fear Flare: track the actual native meteor')
    ground=emit('fear_landing_ground',f'''
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rdi, rcx; call {address:#x}; test rax, rax; je done
        mov rbx, rax; mov esi, 8
        cmp word ptr [rdi+0x38], 0; jne scan
    clear: mov qword ptr [rbx], 0; mov qword ptr [rbx+8], 0
        add rbx, 16; dec esi; jne clear; jmp done
    scan:
        cmp word ptr [rbx+10], 0; je next
        movzx eax, word ptr [rdi+0x38]; sub ax, word ptr [rbx+8]
        cmp ax, 20; jb flying
        mov word ptr [rbx+10], 0; jmp next
    flying:
        test ax, 3; jne next
        mov rdx, qword ptr [rbx]; cmp byte ptr [rdx+8], 7; jne next
        lea rcx, {mem(0x57c82a)}; call 0x8b7e0
        test rax, rax; je next
        cmp rax, qword ptr {mem(0x12cec20)}; je next
        mov rdx, qword ptr [rbx]
        mov ecx, dword ptr [rdx]; mov dword ptr [rax], ecx
        mov cx, word ptr [rdx+4]; mov word ptr [rax+4], cx
        mov ecx, dword ptr [rdx+0x2a]; mov dword ptr [rax+0x2a], ecx
        # Retain the smoke's subtractive page and CLUT, not the glowing meteor's.
        cmp word ptr [rdi+0x38], 96; jbe lifetime
        dec word ptr [rax+0xe]; add word ptr [rax+0x10], -0x40
    lifetime:
        mov ecx, 160; sub cx, word ptr [rdi+0x38]
        cmp cx, 12; jae next
        mov word ptr [rax+0xc], cx
    next: add rbx, 16; dec esi; jne scan
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    hook=emit('fear_ground_hook',f'''
        lea rax, {mem(script)}; cmp qword ptr [rdi+0x10], rax; jne native
        mov rcx, rdi; call {ground:#x}; jmp 0x9d7a5
    native:
        {relocate(pe.get_data(0x9d746,7),0x9d746)}
        jmp 0x9d74d
    ''')
    jump(0x9d746,7,hook,'Player Fear Flare: original smoke follows each meteor')
    hook=emit('fear_last_meteor',f'''
        lea rax, {mem(script)}; cmp qword ptr [rdi+0x10], rax; jne native
        cmp word ptr [rdi+0x38], 140; ja 0x9d746
    native:
        {relocate(pe.get_data(0x9d676,9),0x9d676)}
        jmp 0x9d67f
    ''')
    jump(0x9d676,9,hook,'Player Fear Flare: last meteor lands before the effect releases')
    info['fear_alignment']=dict(queue=queues,size=0x800,address=address,
                               capture=capture,ground=ground,travel_ticks=20,
                               last_meteor_tick=138,runtime_validated=False)
