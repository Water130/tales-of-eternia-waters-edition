"""Native collision, successful damage and physical chain event integration."""
from craymel_faculties import preserve


def emit_impacts(emit,mem,jump,data,info):
    enabled,slot,family=(info[k] for k in ('enabled','slot','family'))
    def gate(id,actor='rbx'):
        return f'mov rcx, {actor}; mov edx, {info["gates"][id][0]}; call {enabled:#x}'
    hit=emit('fighter_expansion_hit',f'''
        # Called after the native damage cap, before actual HP subtraction.
        push rbx; push rsi; push rdi; push rbp; sub rsp, 0x28
        mov rbx, rcx; mov rsi, rdx; mov ebp, r9d
        test rcx, rcx; je done; test rsi, rsi; je done
        cmp byte ptr {mem(0x12d0ef7)}, 6; jne done
        test r8d, r8d; jle done
        test ebp, 1; jne done
        cmp byte ptr [rsi+0x51], 1; jne done
        cmp dword ptr [rsi+0x2c], 0; jle done
        cmp byte ptr [rbx+0x4f], 1; ja done
        cmp byte ptr [rbx+0x52], 8; jne done
        mov rcx, rbx; call {slot:#x}; test rax, rax; je done; mov rdi, rax
        movzx eax, byte ptr [rbx+0x6e]; inc eax
        cmp byte ptr [rbx+0x64], 15; ja arte
        cmp dword ptr [rdi+112], eax; je done
        mov dword ptr [rdi+112], eax
        {gate('R4')}; test eax, eax; je done
        cmp dword ptr [rdi+108], 3; jae done
        inc dword ptr [rdi+108]; jmp done
    arte:
        cmp byte ptr [rbx+0x4f], 1; jne done
        cmp dword ptr [rdi+88], eax; je done
        mov dword ptr [rdi+88], eax
        movzx edx, byte ptr [rbx+0x6d]; call {family:#x}
        mov ebp, eax; test eax, eax; je done
        cmp eax, 3; je reset_alternating
        cmp eax, dword ptr [rdi+96]; je reset_alternating
        mov dword ptr [rdi+96], eax
        inc dword ptr [rdi+92]
        cmp dword ptr [rdi+92], 3; jb punch
        {gate('F8')}; test eax, eax; je punch
        mov byte ptr [rdi+24], 1; mov dword ptr [rdi+92], 0; jmp punch
    reset_alternating:
        mov dword ptr [rdi+96], eax; mov dword ptr [rdi+92], 1
    punch:
        cmp ebp, 1; jne done
        movzx ecx, byte ptr [rbx+0x6d]
        cmp ecx, 130; jb native_punch
        cmp ecx, 133; ja done
        sub ecx, 116; jmp punch_bit
    native_punch:
        sub ecx, 25; cmp ecx, 13; ja done
    punch_bit:
        bts dword ptr [rdi+140], ecx
        mov eax, dword ptr [rdi+140]
        # At least three distinct successful Punch artes, no POPCNT dependency.
        lea ecx, [rax-1]; and eax, ecx; je done
        lea ecx, [rax-1]; and eax, ecx; je done
        {gate('F4')}; test eax, eax; je refund
        mov byte ptr [rdi+104], 1
    refund:
        {gate('F2')}; test eax, eax; je done
        cmp dword ptr [rdi+84], 0; jne done
        mov dword ptr [rdi+84], 1
        mov eax, dword ptr [rdi+80]; xor edx, edx; mov ecx, 10; div ecx
        mov edx, eax; mov rcx, rbx; call {info['tp']:#x}
    done: add rsp, 0x28; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    hook=emit('fighter_damage_applied',f'''
        mov word ptr [rdi+0x96], si
        {preserve(f'mov rcx, rbp; mov rdx, rdi; mov r8d, esi; mov r9d, r15d; call {hit:#x}')}
        jmp 0x8f08c
    ''')
    jump(0x8f085,7,hook,'Record actual positive unguarded physical damage for finite fighter preparations')
    reaction=emit('fighter_expansion_reaction',f'''
        # RCX attacker, RDX victim. Native knockback/hitstun already assigned.
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx; mov rsi, rdx
        test rbx, rbx; je done; test rsi, rsi; je done
        cmp byte ptr [rsi+0x51], 1; jne done
        cmp word ptr [rsi+0x3c], 1; jne done
        cmp word ptr [rsi+0x12], 0; jne done
        mov rax, qword ptr [rsi+0xe8]; test rax, rax; je done
        cmp byte ptr [rax+0x2e], 5; jae done
        test byte ptr [rax+0x4e], 0x14; jne done
        cmp byte ptr [rax+0x5a], 0; jne done
        cmp byte ptr [rbx+0x52], 8; jne done
        cmp byte ptr [rbx+0x4f], 0; jne palm
        {gate('R6')}; test eax, eax; je done
        movzx edx, byte ptr [rbx+0x6d]; call {family:#x}; cmp eax, 2; jne done
        cmp word ptr [rsi+0x1a], 0; jne done
        sar word ptr [rsi+0x18], 1; jmp done
    palm:
        {gate('F3')}; test eax, eax; je done
        cmp byte ptr [rbx+0x6d], 31; jne done
        # Twin Palm script 593590 switches to reaction 16 at phase 2,
        # retaining it for its final palm until the phase-5 terminator.
        cmp byte ptr [rbx+0xe1], 16; jne done
        cmp byte ptr [rbx+0x23c], 2; jb done
        mov rcx, rbx; call {slot:#x}; mov rdi, rax
        cmp dword ptr [rdi+100], 0; jne done
        movsx eax, word ptr [rsi+0x44]; test eax, eax; jle done
        add eax, 6; mov edx, 32767; cmp eax, edx; cmovg eax, edx
        mov word ptr [rsi+0x44], ax; mov dword ptr [rdi+100], 1
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    breaking=emit('fighter_expansion_guard_break',f'''
        # Consume on the first collision of the prepared arte, not each target.
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx; mov rsi, rdx
        cmp byte ptr [rbx+0x52], 8; jne no
        cmp byte ptr [rbx+0x64], 16; jb no
        mov rcx, rbx; call {slot:#x}; test rax, rax; je no; mov rdi, rax
        movzx eax, byte ptr [rbx+0x6e]; inc eax
        cmp eax, dword ptr [rdi+144]; jne no
        mov dword ptr [rdi+144], 0
        cmp byte ptr [rbx+0x4f], 0; jne farah
        {gate('R4')}; test eax, eax; je no; jmp target
    farah: {gate('F4')}; test eax, eax; je no
    target:
        cmp byte ptr [rsi+0x51], 1; jne no
        cmp word ptr [rsi+0x3c], 1; jne no
        cmp byte ptr [rsi+0x52], 2; jne no
        cmp byte ptr [rsi+0x59], 0; jne no
        cmp word ptr [rsi+0x12], 0; jne no
        mov rax, qword ptr [rsi+0xe8]; test rax, rax; je no
        cmp byte ptr [rax+0x5a], 0; jne no
        test byte ptr [rax+0x4e], 0x14; jne no
        mov eax, 1; jmp done
    no: xor eax, eax
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    hook=emit('fighter_melee_guard_break',preserve(
        f'mov rcx, rsi; mov rdx, rdi; call {breaking:#x}',result='rax')+'''
        test eax, eax; je native
        xor ebx, ebx; mov dword ptr [rsp+0x30], ebx; jmp 0x822a3
    native: cmp byte ptr [rdi+0x70], 0
        mov dword ptr [rsp+0x30], ebx; jmp 0x82248
    ''')
    jump(0x82240,8,hook,'Prepared physical arte breaks one ordinary guard, preserving protected enemies')
    # Late rising-input window remains bounded by Farah's native altitude and
    # chain-category checks downstream; the requested arte still must be a dive.
    window=emit('fighter_expansion_window',f'''
        push rbx; sub rsp, 0x20; mov rbx, rcx
        {gate('F6')}; test eax, eax; je no
        cmp byte ptr [rbx+0x52], 8; jne no
        cmp byte ptr [rbx+0x65], 2; jne no
        cmp word ptr [rbx+0x12], -640; jge no
        movzx eax, word ptr [rbx+0x238]; movsx edx, word ptr [rbx+0x88]
        cmp eax, edx; jl no
        movzx ecx, byte ptr [rbx+0x66]; add edx, ecx; add edx, 6
        cmp eax, edx; jge no
        mov eax, 1; jmp done
    no: xor eax, eax
    done: add rsp, 0x20; pop rbx; ret
    ''')
    hook=emit('fighter_rising_window',preserve(f'call {window:#x}',result='rax',aligned=False)+'''
        test eax, eax; jne 0x1121d8
        cmp byte ptr [rcx+0x52], 4; jbe 0x1121d8; jmp 0x1121b6
    ''')
    jump(0x1121b0,6,hook,'Farah rising-to-dive input window: six extra frames, native minimum altitude retained')
    # Temporarily widen only collision queries, never persistent animation data.
    native=emit('fighter_native_melee_collision','mov qword ptr [rsp+0x10], rbx; jmp 0x82035')
    wide=emit('fighter_wide_slash',f'''
        push rbx; push rsi; push rdi; sub rsp, 0xa0
        mov rbx, rcx; xor esi, esi
        {gate('R2')}; test eax, eax; je invoke
        cmp byte ptr [rbx+0x52], 8; jne invoke
        cmp byte ptr [rbx+0x64], 15; jne invoke
        cmp byte ptr [rbx+0xab], 1; jne invoke
        movzx esi, byte ptr [rbx+0x241]; cmp esi, 15; ja invalid
        xor edi, edi
    widen:
        cmp edi, esi; jae invoke
        mov rax, qword ptr [rbx+rdi*8+0x1b8]; mov qword ptr [rsp+rdi*8+0x20], rax
        movsx edx, word ptr [rbx+rdi*8+0x1bc]
        movsx eax, word ptr [rbx+rdi*8+0x1b8]; sub edx, eax
        test edx, edx; jle next
        shr edx, 3; sub eax, edx
        mov ecx, -32768; cmp eax, ecx; cmovl eax, ecx
        mov word ptr [rbx+rdi*8+0x1b8], ax
        movsx eax, word ptr [rbx+rdi*8+0x1bc]; add eax, edx
        mov ecx, 32767; cmp eax, ecx; cmovg eax, ecx
        mov word ptr [rbx+rdi*8+0x1bc], ax
    next: inc edi; jmp widen
    invalid: xor esi, esi
    invoke:
        mov rcx, rbx; call {native:#x}; xor edi, edi
    restore:
        cmp edi, esi; jae done
        mov rdx, qword ptr [rsp+rdi*8+0x20]; mov qword ptr [rbx+rdi*8+0x1b8], rdx
        inc edi; jmp restore
    done: add rsp, 0xa0; pop rdi; pop rsi; pop rbx; ret
    ''')
    jump(0x82030,5,wide,'Terminal slash normal collision width +25%, original boxes restored after every query')
    # Sonic Blade dissipates when particle X scale +3A reaches 0xC0
    # (116AF3), with decay +3E integrated by 86314. Slower decay extends
    # travel without changing velocity, collision or the one-hit termination.
    sonic=emit('fighter_expansion_sonic',f'''
        # RCX owner, RDX newly allocated particle; called once on allocation.
        push rbx; push rsi; sub rsp, 0x28
        mov rbx, rcx; mov rsi, rdx
        test rsi, rsi; je done
        {gate('R3')}; test eax, eax; je done
        cmp byte ptr [rbx+0x6d], 1; jne done
        cmp word ptr [rsi+0x3a], 0xc0; jle done
        movsx eax, word ptr [rsi+0x3e]; cmp eax, -1; jge done
        imul eax, eax, 4; cdq; mov ecx, 5; idiv ecx
        mov word ptr [rsi+0x3e], ax
        movsx eax, word ptr [rsi+0x40]; cmp eax, -1; jge lifetime
        imul eax, eax, 4; cdq; mov ecx, 5; idiv ecx
        mov word ptr [rsi+0x40], ax
    lifetime:
        movsx eax, word ptr [rsi+0xc]; test eax, eax; jle done
        imul eax, eax, 5; add eax, 3; shr eax, 2
        mov edx, 32767; cmp eax, edx; cmovg eax, edx
        mov word ptr [rsi+0xc], ax
    done: add rsp, 0x28; pop rsi; pop rbx; ret
    ''')
    hook=emit('fighter_sonic_spawn',preserve(
        f'mov rcx, r8; call {sonic:#x}')+'''
        call 0x116580; jmp 0xc9b1a
    ''')
    jump(0xc9b15,5,hook,'Lame prolongee: slow only Sonic Blade dissipation, retain velocity and hit termination')
    info.update(hit=hit,reaction=reaction,guard_break=breaking,window=window,wide_slash=wide,sonic=sonic)
    return info
