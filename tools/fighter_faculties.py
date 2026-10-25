"""Four opt-in-per-faculty additions on verified native action boundaries.

8e51e is reached only for an accepted block; 8e5d9 only for an actual
hit reaction. d6231 is the grounded recovery calculation, before state 6.
The native initializers retain costs, arte eligibility and chain limits.
"""
from craymel_faculties import preserve


def emit_fighter_faculties(emit, mem, jump, data, state, choices, expansion=None):
    enabled=emit('fighter_faculty_enabled',f'''
        # RCX actor, EDX stable faculty ID 138..141. All other inputs retained.
        xor eax, eax
        test rcx, rcx; je done
        cmp byte ptr {mem(0x12d0ef7)}, 6; jne done
        cmp byte ptr [rcx+0x51], 0; jne done
        cmp word ptr [rcx+0x3c], 1; jne done
        cmp dword ptr [rcx+0x2c], 0; jle done
        mov r9, qword ptr {mem(0x12cea60)}; test r9, r9; je done
        movzx r10d, byte ptr [rcx+0x4f]
        cmp edx, 141; je farah
        test r10d, r10d; jne done
        cmp byte ptr {mem(data+0x1a4f)}, 0; je done
        cmp edx, 138; je slash
        cmp edx, 139; je thrust
        cmp edx, 140; jne done
        cmp byte ptr [r9+0xc10], 20; jb done
    slash: cmp byte ptr [r9+0xc08], 20; jb done
        jmp preference
    thrust: cmp byte ptr [r9+0xc10], 25; jb done
        jmp preference
    farah:
        cmp r10d, 1; jne done
        cmp byte ptr {mem(data+0x1a41)}, 0; je done
        cmp byte ptr [r9+0xc18], 20; jb done
        cmp byte ptr [r9+0xc20], 20; jb done
    preference:
        shl r10d, 8; add r10d, edx
        lea r9, {mem(choices)}
        bt dword ptr [r9], r10d; jc done
        mov eax, 1
    done: ret
    ''')
    # Actor pointer, last block clock, one pending retaliation, heavy-hit spent.
    block=emit('fighter_block_record',f'''
        cmp byte ptr [rcx+0x4f], 0; jne done
        cmp byte ptr [rcx+0x51], 0; jne done
        cmp word ptr [rcx+0x12], 0; jne done
        mov qword ptr {mem(state)}, rcx
        mov eax, dword ptr {mem(0x12cea40)}
        mov dword ptr {mem(state+8)}, eax
        mov byte ptr {mem(state+12)}, 1
    done: ret
    ''')
    hook=emit('fighter_block_hook',f'''
        mov byte ptr [rbx+0x70], al
        {preserve(f'mov rcx, rbx; call {block:#x}')}
        {preserve(f'mov rcx, rbx; mov rdx, rdi; call {expansion["block"]:#x}') if expansion else ''}
        movzx eax, byte ptr [rsi+3]
        jmp 0x8e525
    ''')
    jump(0x8e51e,7,hook,'Record an accepted grounded Reid block, without changing native block recovery')
    action=emit('fighter_guard_action',f'''
        push rbx; push rsi; sub rsp, 0x28
        mov rbx, rcx
        {f'call {expansion["action"]:#x}; mov rcx, rbx' if expansion else ''}
        cmp byte ptr [rbx+0x4f], 0; jne done
        cmp byte ptr [rbx+0x51], 0; jne done
        cmp byte ptr [rbx+0x52], 8; je keep_heavy
        mov byte ptr {mem(state+13)}, 0
    keep_heavy:
        cmp qword ptr {mem(state)}, rbx; jne done
        cmp byte ptr {mem(state+12)}, 0; je done
        mov eax, dword ptr {mem(0x12cea40)}
        sub eax, dword ptr {mem(state+8)}
        cmp eax, 24; ja expire
        cmp byte ptr [rbx+0x52], 2; jne expire
        cmp byte ptr [rbx+0x57], 1; jb done
        cmp byte ptr [rbx+0x57], 2; ja done
        cmp word ptr [rbx+0x12], 0; jne done
        cmp word ptr [rbx+0x44], 0; jne done
        cmp byte ptr [rbx+0x74], 0; jne done
        test dword ptr [rbx+0x30], 0x4000; jne done
        cmp qword ptr [rbx+0xe8], 0; je done
        mov rsi, qword ptr [rbx+0xf0]; test rsi, rsi; je done
        test word ptr [rsi], 0x200; jne done
        test byte ptr [rsi+4], 0x40; jne arte
        test byte ptr [rsi+4], 0x20; je done
        mov edx, 139; call {enabled:#x}; test eax, eax; je done
        # Direction 3 selects native first thrust (selector 1, family 2).
        mov rcx, rbx; mov edx, 3; call 0x112720
        cmp byte ptr [rbx+0x52], 8; jne done
        jmp expire
    arte:
        mov edx, 140; call {enabled:#x}; test eax, eax; je done
        mov rcx, rbx; xor edx, edx; call 0x1140f0
        # Native Reid basic artes only; forbid arcane/secret/collaboration.
        cmp eax, 1; jb done
        cmp eax, 6; ja done
        mov edx, eax; mov rcx, rbx
        cmp byte ptr [rbx+0x57], 2; jne semi
        call 0x112d10; jmp started
    semi: call 0x73790
    started:
        cmp byte ptr [rbx+0x52], 8; jne done
    expire: mov byte ptr {mem(state+12)}, 0
    done: add rsp, 0x28; pop rsi; pop rbx; ret
    ''')
    impact=emit('fighter_heavy_impact',f'''
        push rbx; push rsi; sub rsp, 0x28
        mov rbx, rcx; mov rsi, rdx
        mov edx, 138; call {enabled:#x}; test eax, eax; je done
        cmp byte ptr [rbx+0x52], 8; jne done
        cmp byte ptr [rbx+0x64], 15; jne done
        cmp word ptr [rbx+0x12], 0; jne done
        cmp byte ptr {mem(state+13)}, 0; jne done
        test rsi, rsi; je done
        cmp byte ptr [rsi+0x51], 1; jne done
        cmp word ptr [rsi+0x3c], 1; jne done
        cmp word ptr [rsi+0x12], 0; jne done
        mov rax, qword ptr [rsi+0xe8]; test rax, rax; je done
        # Respect native heavy/immune targets as well as all upstream checks.
        cmp byte ptr [rax+0x2e], 5; jae done
        test byte ptr [rax+0x4e], 0x14; jne done
        movsx eax, word ptr [rsi+0x44]; test eax, eax; jle done
        imul eax, eax, 110; add eax, 99
        xor edx, edx; mov ecx, 100; div ecx
        mov ecx, 32767; cmp eax, ecx; cmova eax, ecx
        mov word ptr [rsi+0x44], ax
        mov byte ptr {mem(state+13)}, 1
    done: add rsp, 0x28; pop rsi; pop rbx; ret
    ''')
    hook=emit('fighter_heavy_hit_hook',f'''
        mov word ptr [rbx+0x44], cx
        {preserve(f'mov rcx, rdi; mov rdx, rbx; call {impact:#x}')}
        {preserve(f'mov rcx, rdi; mov rdx, rbx; call {expansion["reaction"]:#x}') if expansion else ''}
        mov byte ptr [rbx+0x70], r15b
        jmp 0x8e5e1
    ''')
    jump(0x8e5d9,8,hook,'Impact lourd: +10% accepted grounded terminal normal hit recovery, once per chain')
    landing=emit('fighter_active_landing',f'''
        # Native R10B is the pre-landing action. SI is final recovery time.
        cmp r10b, 8; jne done
        cmp byte ptr [rbx+0x64], 16; jb done
        cmp word ptr [rbx+0x12], 0; jne done
        mov rcx, rbx; mov edx, 141
        sub rsp, 0x28; call {enabled:#x}; add rsp, 0x28
        test eax, eax; je done
        test si, si; jle done
        inc si; shr si, 1
    done: ret
    ''')
    hook=emit('fighter_landing_hook',f'''
        mov al, 6
        add si, r8w
        {preserve(f'call {landing:#x}')}
        jmp 0xd6237
    ''')
    # d621e branches directly to d623b for fast landings (state 5).
    # Keep that shared entry intact: only detour the state-6 calculation.
    jump(0xd6231,6,hook,'Farah active landing: half recovery after aerial arte, native landing and chain state retained')
    return dict(state_rva=state,size=16,action_callback=action,preference_bits=[138,139,140,141],
                block_window_frames=24,heavy_impact_percent=10,landing_recovery_percent=50,
                native_block_hook=0x8e51e,native_landing_hook=0xd6231,
                runtime_validated=False)
