"""Finite arte chains at native category admission and successful commit.

Only category sequencing changes. Caller timing/learned checks and downstream
TP admission/payment, animation, collision and aerial initialization stay native.
Transient records are observed even when faculties are disabled.
"""
from craymel_faculties import preserve


def emit_fighter_chains(emit,mem,jump,data,state,choices,expansion=None):
    family=emit('fighter_arte_family',f'''
        cmp edx, 130; jb native_id
        cmp edx, 135; ja native_id
        mov eax, 1; ret
    native_id:
        xor eax, eax
        cmp edx, 1; jb done
        cmp edx, 38; ja done
        cmp edx, 22; jb physical
        cmp edx, 25; jb done
    physical:
        imul r10d, edx, 24
        lea r11, {mem(0x562a50)}
        movzx eax, word ptr [r11+r10]
        shr eax, 10; and eax, 3
        test eax, eax; jne done
        mov eax, 3
    done: ret
    ''')
    record=emit('fighter_chain_record',f'''
        # RCX actor, EDX successfully admitted native arte ID. Before +6E++.
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx; mov esi, edx
        {f'call {expansion["commit"]:#x}; mov rcx, rbx; mov edx, esi' if expansion else ''}
        cmp byte ptr [rbx+0x51], 0; jne done
        movzx eax, byte ptr [rbx+0x4f]; cmp eax, 1; ja done
        shl eax, 5; lea rdi, {mem(state)}; add rdi, rax
        cmp qword ptr [rdi], rbx; jne fresh
        test byte ptr [rbx+0x64], 0xf0; je fresh
        mov al, byte ptr [rbx+0x6e]; cmp al, byte ptr [rdi+12]; jne fresh
        jmp append
    fresh:
        mov qword ptr [rdi], rbx
        mov qword ptr [rdi+8], 0
    append:
        call {family:#x}
        or byte ptr [rdi+9], al
        cmp byte ptr [rdi+8], 255; je serial
        inc byte ptr [rdi+8]
        mov r10, qword ptr {mem(0x12cea78)}
        movzx edx, byte ptr [r10+rsi*8+2]
        cmp edx, 1; jne arcane
        cmp byte ptr [rbx+0x4f], 0; jne basic
        cmp byte ptr [rbx+0x65], 2; jne basic
        mov byte ptr [rdi+13], 1
    basic:
        inc byte ptr [rdi+10]; or byte ptr [rdi+15], al; jmp serial
    arcane:
        cmp edx, 2; jne serial
        inc byte ptr [rdi+11]; or byte ptr [rdi+14], al
    serial:
        mov al, byte ptr [rbx+0x6e]; inc al; mov byte ptr [rdi+12], al
    done:
        add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    commit=emit('fighter_chain_commit',preserve(f'''
        mov rcx, rbx
        mov rdx, rdi; sub rdx, qword ptr {mem(0x12cea78)}; shr rdx, 3
        call {record:#x}
    ''')+'''; movzx eax, byte ptr [rdi+2]; shl al, 4; jmp 0x112c5f''')
    jump(0x112c58,7,commit,'Count successfully initialized physical artes, never failed input or TP admission')
    # EAX family mask; EDX level threshold; R8D first stable preference ID.
    # RCX actor retained. Return EAX boolean, all volatile regs may change.
    enabled=emit('fighter_chain_enabled',f'''
        mov r9, qword ptr {mem(0x12cea60)}; test r9, r9; je no
        cmp byte ptr [rcx+0x4f], 0; jne farah
        cmp byte ptr {mem(data+0x1a4f)}, 0; je no
        add r9, 0xc08; jmp levels
    farah:
        cmp byte ptr {mem(data+0x1a41)}, 0; je no
        add r9, 0xc18
    levels:
        test eax, 1; je second
        cmp byte ptr [r9], dl; jb no
        cmp byte ptr [r9], 30; ja no
    second:
        test eax, 2; je preference
        cmp byte ptr [r9+8], dl; jb no
        cmp byte ptr [r9+8], 30; ja no
    preference:
        movzx r10d, byte ptr [rcx+0x4f]; shl r10d, 8; add r10d, r8d
        lea r11, {mem(choices)}; bt dword ptr [r11], r10d; jc no
        mov eax, 1; ret
    no: xor eax, eax; ret
    ''')
    admit=emit('fighter_chain_admission',f'''
        # RCX actor, EDX requested native arte. -1 native, 0 refuse, 1 extend.
        push rbx; push rsi; push rdi; push r12; push r13; sub rsp, 0x20
        mov rbx, rcx; mov esi, edx
        cmp byte ptr {mem(0x12d0ef7)}, 6; jne native
        cmp byte ptr [rbx+0x51], 0; jne native
        cmp word ptr [rbx+0x3c], 1; jne native
        cmp dword ptr [rbx+0x2c], 0; jle native
        movzx eax, byte ptr [rbx+0x4f]; cmp eax, 1; ja native
        cmp byte ptr [rbx+0x52], 8; jne native
        test byte ptr [rbx+0x64], 0xf0; je native
        shl eax, 5; lea rdi, {mem(state)}; add rdi, rax
        cmp qword ptr [rdi], rbx; jne native
        mov al, byte ptr [rbx+0x6e]; cmp al, byte ptr [rdi+12]; jne native
        call {family:#x}; test eax, eax; je native
        mov r12d, eax
        cmp byte ptr [rbx+0x4f], 1; je farah
        cmp esi, 21; ja native
        cmp esi, 13; jae arcane
        # Two basics; one return after an arcane with Technical Return.
        cmp byte ptr [rbx+0x65], 1; je basic_pair
        cmp byte ptr [rbx+0x65], 2; jne native
        cmp byte ptr [rdi+13], 0; jne no
        {f'mov rcx, rbx; mov edx, 162; call {expansion["enabled"]:#x}' if expansion else 'xor eax, eax'}
        test eax, eax; je native
        cmp byte ptr [rdi+10], 2; jae no
        jmp grounded
    basic_pair:
        or r12b, byte ptr [rdi+15]
        mov edx, 10; mov r8d, 150; add r8d, r12d
        mov eax, r12d; mov rcx, rbx; call {enabled:#x}; test eax, eax; je native
        cmp byte ptr [rdi+10], 2; jae no
        jmp grounded
    arcane:
        # Returning through a basic must not reopen the arcane quota.
        cmp byte ptr [rdi+11], 2; jae no
        cmp byte ptr [rbx+0x65], 2; je arcane_requirements
        cmp byte ptr [rdi+13], 0; je native
        cmp byte ptr [rdi+11], 0; je native
        cmp byte ptr [rbx+0x65], 1; jne native
    arcane_requirements:
        or r12b, byte ptr [rdi+14]
        # Every involved arcane family needs its level-30 switch.
        test r12d, 1; je arcane_thrust
        mov eax, 1; mov edx, 30; mov r8d, 148; mov rcx, rbx
        call {enabled:#x}; test eax, eax; je native
    arcane_thrust:
        test r12d, 2; je arcane_count
        mov eax, 2; mov edx, 30; mov r8d, 149; mov rcx, rbx
        call {enabled:#x}; test eax, eax; je native
    arcane_count:
        cmp byte ptr [rdi+11], 2; jae no
    grounded:
        cmp word ptr [rbx+0x12], 0; jne no
        cmp word ptr [rbx+0x1a], 0; jne no
        jmp yes
    farah:
        cmp esi, 25; jb native
        or r12b, byte ptr [rdi+9]
        lea r13d, [r12*2+140]
        mov eax, r12d; mov edx, 30; lea r8d, [r13+1]; mov rcx, rbx
        call {enabled:#x}; test eax, eax; jne six
        mov eax, r12d; mov edx, 15; mov r8d, r13d; mov rcx, rbx
        call {enabled:#x}; test eax, eax; je native
        mov eax, 5; jmp count
    six: mov eax, 6
    count:
        cmp byte ptr [rdi+8], al; jae no
        mov r10, qword ptr {mem(0x12cea78)}
        movzx edx, byte ptr [r10+rsi*8+2]
        # Rising artes still only link to dives at native minimum height.
        cmp byte ptr [rbx+0x65], 2; je dive
        cmp edx, 4; je dive
        jmp grounded
    dive:
        cmp edx, 4; jne no
        cmp word ptr [rbx+0x12], -640; jge no
        jmp yes
    native: mov eax, -1; jmp done
    no: xor eax, eax; jmp done
    yes: mov eax, 1
    done: add rsp, 0x20; pop r13; pop r12; pop rdi; pop rsi; pop rbx; ret
    ''')
    for name,site,continuation,accepted in (('reid',0x113137,0x11313d,0x113174),('farah',0x113211,0x113217,0x113298)):
        hook=emit('fighter_chain_'+name,preserve(f'mov rcx, rbx; mov edx, ebp; call {admit:#x}',result='rax')+f'''
            cmp eax, 1; je {accepted:#x}
            test eax, eax; je 0x112dec
            movzx ecx, byte ptr [rcx+0x65]; test ecx, ecx
            jmp {continuation:#x}
        ''')
        jump(site,6,hook,'Finite '+name+' arte chains: native costs and aerial constraints retained')
    return dict(state_rva=state,size=64,admission=admit,commit=record,
                farah_limits={'15':5,'30':6},reid_arcane_limit=2,reid_basic_limit=2,
                preference_ids=list(range(142,150))+[151,152,153],runtime_validated=False)
