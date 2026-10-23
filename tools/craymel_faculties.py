"""Optional shared Craymel faculties for Keele/Meredy, native build 25190541.

Preferences retain mage-only IDs 128..207, with overflow at 208..247.
Transient shields, cooldowns and cast memory are never written to save files.
Every event rechecks ownership, level, global option and individual preference.
"""
SIZE = 0x2000
FLAG_OFFSET = 0x1a60
from craymel_milestones import LEVELS, TIERS, faculty_id
# Sylph's perfect dodge replaces the conditional casting-movement proposal.
PREVIEW = set()


def preserve(body, result=None, aligned=True):
    # These hooks sit inside native functions, where even caller-saved SIMD
    # registers may still be live. Reserve shadow space plus XMM0..XMM5.
    reserve = 0x80 if aligned else 0x88
    save = '; '.join(f'movdqu xmmword ptr [rsp+{0x20+i*16}], xmm{i}' for i in range(6))
    restore = '; '.join(f'movdqu xmm{i}, xmmword ptr [rsp+{0x20+i*16}]' for i in range(6))
    output = '' if result is None else f'mov dword ptr [rsp+{reserve+dict(rax=48,rcx=40,rdx=32,r8=24,r9=16,r10=8,r11=0)[result]}], eax'
    return f'''pushfq; push rax; push rcx; push rdx; push r8; push r9; push r10; push r11
        sub rsp, {reserve}; {save}; {body}; {output}; {restore}; add rsp, {reserve}
        pop r11; pop r10; pop r9; pop r8; pop rdx; pop rcx; pop rax; popfq'''


def emit_faculties(emit, mem, jump, data, state, usage, energy):
    choices = usage['preferences']['live_rva']
    # Private leaf ABI: RCX actor, EDX spirit, R8D faculty. EAX boolean;
    # RCX/EDX/R8 unchanged; R9/R10/R11 scratch. Only recruited spirits count,
    # regardless of which mage holds their cage.
    cases=''
    for spirit,levels in enumerate(LEVELS):
        for i,level in enumerate(levels):
            if (spirit,i) in PREVIEW:continue
            cases += f'cmp r9d, {spirit*12+i}; jne next_{spirit}_{i}; cmp r10d, {level}; jb no; mov r9d, {faculty_id(spirit,i)}; jmp preference; next_{spirit}_{i}:\n'
    enabled=emit('craymel_faculty_enabled',f'''
        xor eax, eax
        cmp byte ptr {mem(data+FLAG_OFFSET)}, 0
        je no
        test rcx, rcx
        je no
        cmp byte ptr [rcx+0x51], 0
        jne no
        movzx r9d, byte ptr [rcx+0x4f]
        sub r9d, 2
        cmp r9d, 1
        ja no
        cmp edx, 9
        ja no
        cmp r8d, 11
        ja no
        mov r11, qword ptr {mem(0x12cea60)}
        test r11, r11
        je no
        cmp byte ptr [r11+rdx*8+0xbb8], 0
        je no
        movzx r10d, byte ptr [r11+rdx*8+0xbb9]
        cmp r10d, 30
        ja no
        imul r9d, edx, 12
        add r9d, r8d
        {cases}
        jmp no
    preference:
        movzx eax, byte ptr [rcx+0x4f]
        shl eax, 8
        lea eax, [rax+r9]
        lea r11, {mem(choices)}
        bt dword ptr [r11], eax
        setnc al
        movzx eax, al
        ret
    no:
        xor eax, eax
        ret
    ''')
    # Actor state is keyed by character, but pointer changes also clear it.
    slot=emit('craymel_actor_state',f'''
        xor eax, eax
        test rcx, rcx
        je done
        cmp byte ptr [rcx+0x51], 0
        jne done
        movzx eax, byte ptr [rcx+0x4f]
        cmp eax, 6
        ja none
        shl eax, 8
        lea r9, {mem(state+0x100)}
        add rax, r9
        cmp qword ptr [rax], rcx
        je done
        mov r9, rax
        lea r10, [rax+256]
    clear:
        mov qword ptr [r9], 0
        add r9, 8
        cmp r9, r10
        jb clear
        mov qword ptr [rax], rcx
        ret
    none:
        xor eax, eax
    done:
        ret
    ''')
    # All numerical tiers independently togglable; highest enabled tier wins.
    tier_functions={}
    for name,(spirit,tiers) in TIERS.items():
        checks=''
        for i,v in reversed(tiers):
            checks+=f'mov r8d, {i}; call {enabled:#x}; test eax, eax; je next_{i}; mov eax, {v}; jmp done; next_{i}:\n'
        tier_functions[name]=emit('craymel_'+name,f'''
            sub rsp, 0x28; mov edx, {spirit}; {checks}
        done: add rsp, 0x28; ret''')
    def query(spirit,node,actor='rbx'):
        return f'mov rcx, {actor}; mov edx, {spirit}; mov r8d, {node}; call {enabled:#x}'
    def tier(name,actor='rbx'):
        return f'mov rcx, {actor}; call {tier_functions[name]:#x}'

    # Input RCX actor, EDX native cost; same integer result for admission/payment.
    cost=emit('craymel_discount_cost',f'''
        push rbx; sub rsp, 0x20; mov ebx, edx
        call {tier_functions['cost']:#x}
        mov ecx, 100; sub ecx, eax; imul eax, ebx, 100
        imul ebx, ecx; mov eax, ebx; add eax, 99
        xor edx, edx; mov ecx, 100; div ecx
        add rsp, 0x20; pop rbx; ret
    ''')
    # Preserve all scalar and XMM registers across the native random generator.
    roll=emit('craymel_roll_percent',f'''
        push rbx; sub rsp, 0x80; mov ebx, ecx
        movdqu [rsp+0x20], xmm0; movdqu [rsp+0x30], xmm1
        movdqu [rsp+0x40], xmm2; movdqu [rsp+0x50], xmm3
        movdqu [rsp+0x60], xmm4; movdqu [rsp+0x70], xmm5
        call 0x283090; xor edx, edx; mov ecx, 100; div ecx
        xor eax, eax; cmp edx, ebx; setb al
        movdqu xmm0, [rsp+0x20]; movdqu xmm1, [rsp+0x30]
        movdqu xmm2, [rsp+0x40]; movdqu xmm3, [rsp+0x50]
        movdqu xmm4, [rsp+0x60]; movdqu xmm5, [rsp+0x70]
        add rsp, 0x80; pop rbx; ret
    ''')
    # RCX caster, EDX arte, R8D cast duration after ordinary spell EXP.
    cast=emit('craymel_cast_duration',f'''
        push rbx; push rsi; push rdi; push rbp; sub rsp, 0x28
        mov rbx, rcx; mov esi, edx; mov edi, r8d
        cmp esi, 54; jb done
        cmp esi, 113; ja done
        mov edx, 9; xor r8d, r8d; call {enabled:#x}
        mov rcx, rbx; call {slot:#x}; mov rbp, rax
        test rbp, rbp; je done
        {tier('haste')}
        mov ecx, 100; sub ecx, eax; imul eax, edi, 100
        imul edi, ecx; mov eax, edi; add eax, 99; xor edx, edx
        mov ecx, 100; div ecx; mov edi, eax
        {query(4,3)}
        test eax, eax; je repetition
        test dword ptr [rbx+0x30], 0x2000000; je repetition
        # Native mental delay doubles casting; halve only that extra duration.
        lea eax, [rdi+rdi*2+3]; shr eax, 2; mov edi, eax
    repetition:
        {query(9,3)}
        test eax, eax; je memory
        cmp esi, dword ptr [rbp+56]; jne memory
        mov eax, dword ptr [rbp+60]; mov ecx, 3
        cmp eax, ecx; cmova eax, ecx; imul eax, eax, 5
        mov ecx, 100; sub ecx, eax; imul edi, ecx
        mov eax, edi; add eax, 99; xor edx, edx; mov ecx, 100; div ecx; mov edi, eax
    memory:
        cmp esi, dword ptr [rbp+64]; jne forget
        {tier('memory')}
        test eax, eax; je forget
        imul eax, dword ptr [rbp+68]; xor edx, edx; mov ecx, 100; div ecx
        sub edi, eax; mov ecx, 2; cmp edi, ecx; cmovl edi, ecx
    forget:
        mov dword ptr [rbp+64], 0; mov dword ptr [rbp+68], 0
        {query(5,3)}
        test eax, eax; je store
        mov ecx, 5; call {roll:#x}; test eax, eax; je store
        xor edi, edi
    store:
        mov dword ptr [rbp+72], edi
    done:
        mov eax, edi; add rsp, 0x28; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    return dict(state_rva=state,size=SIZE,flag_rva=data+FLAG_OFFSET,
        enabled=enabled,slot=slot,tiers=tier_functions,cost=cost,cast=cast,roll=roll,
        energy=energy,choices=choices,levels=LEVELS,preview=list(PREVIEW))
