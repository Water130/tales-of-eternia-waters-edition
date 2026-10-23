"""Finite grounded normal-chain extensions; native animations and timing remain."""





def emit_basic_attacks(emit,mem,jump,data,state,choices):

    native=emit('basic_mastery_native_init','mov r11, rsp; push rbx; push rbp; jmp 0x112725')

    # Private per-character transient record: actor pointer / spent extensions.

    # Family is taken from the native first-attack descriptor's mastery byte.

    entry=emit('basic_mastery_init',f'''

        push rbx

        push rbp

        push rsi

        push rdi

        push r12

        sub rsp, 0x20

        mov rbx, rcx

        mov ebp, edx

        xor edi, edi

        movzx r12d, byte ptr [rbx+0x6e]

        movzx eax, byte ptr [rbx+0x4f]

        cmp eax, 1

        ja original

        lea rsi, {mem(state)}

        shl eax, 4

        add rsi, rax

        cmp qword ptr [rsi], rbx

        jne reset_chain

        cmp byte ptr [rbx+0x52], 8

        je native_first

    reset_chain:

        mov qword ptr [rsi], rbx

        mov dword ptr [rsi+8], 0

    native_first:

        mov edi, 1

    original:

        mov rcx, rbx

        mov edx, ebp

        call {native:#x}

        test edi, edi

        je done

        cmp byte ptr [rbx+0x6e], r12b

        jne done

    option:

        cmp byte ptr [rbx+0x4f], 1

        jne reid_option

        cmp byte ptr {mem(data+0x1a41)}, 0

        je done

        jmp option_ready

    reid_option:

        cmp byte ptr {mem(data+0x1a4f)}, 0

        je done

    option_ready:

        cmp byte ptr {mem(0x12d0ef7)}, 6

        jne done

        cmp byte ptr [rbx+0x51], 0

        jne done

        cmp word ptr [rbx+0x3c], 1

        jne done

        cmp byte ptr [rbx+0x52], 8

        jne done

        cmp byte ptr [rbx+0x64], 15

        ja done

        cmp word ptr [rbx+0x12], 0

        jne done

        cmp dword ptr [rbx+0x2c], 0

        jle done

        cmp word ptr [rbx+0x44], 0

        jne done

        cmp ebp, 3

        ja done

        movzx eax, word ptr [rbx+0x238]

        movsx edx, word ptr [rbx+0x88]

        cmp eax, edx

        jl done

        movzx ecx, byte ptr [rbx+0x66]

        add ecx, edx

        cmp eax, ecx

        jge done

        mov r8, qword ptr {mem(0x12cea60)}

        test r8, r8

        je done

        lea rax, {mem(0x4e935c)}

        movzx ecx, byte ptr [rax+rbp]

        cmp ecx, 2

        ja done

        imul ecx, ecx, 5

        lea rax, {mem(0x551bb0)}

        cmp byte ptr [rbx+0x4f], 0

        je descriptor

        lea rax, {mem(0x551da8)}

    descriptor:

        movzx edx, byte ptr [rax+rcx+4]

        dec edx

        cmp edx, 1

        ja done

        movzx eax, byte ptr [rbx+0x4f]

        shl eax, 4

        movzx r9d, byte ptr [r8+rax+0xc08]

        movzx ecx, byte ptr [r8+rax+0xc10]

        cmp r9d, ecx

        cmova r9d, ecx

        # One shared faculty pair per character: min(Slash,Thrust)/min(Punch,Kick).

        mov ecx, 134

        movzx eax, byte ptr [rbx+0x4f]

        shl eax, 8

        add ecx, eax

        lea r8, {mem(choices)}

        xor edx, edx

        cmp r9d, 15

        jb done

        bt dword ptr [r8], ecx

        jc tier_two

        mov edx, 1

    tier_two:

        inc ecx

        cmp r9d, 30

        jb allowance

        bt dword ptr [r8], ecx

        jc allowance

        mov edx, 2

    allowance:

        cmp dword ptr [rsi+8], edx

        jae done

        movzx edi, byte ptr [rbx+0x64]

        mov byte ptr [rbx+0x64], 0

        mov rcx, rbx

        mov edx, ebp

        call {native:#x}

        # Every added attack ends in the terminal selector state. Replaying an

        # entire two-attack native subchain would otherwise double the allowance.

        mov byte ptr [rbx+0x64], dil

        cmp byte ptr [rbx+0x6e], r12b

        je done

        mov byte ptr [rbx+0x64], 15

        inc dword ptr [rsi+8]

    done:

        add rsp, 0x20

        pop r12

        pop rdi

        pop rsi

        pop rbp

        pop rbx

        ret

    ''')

    jump(0x112720,5,entry,'Optional +1/+2 grounded normal attacks at combined mastery 15/30')

    return dict(state_rva=state,size=32,flag_index=31,farah_flag_index=17,preference_bits=[134,135],combined_minimum=True,

                levels=[15,30],extra_attacks=[1,2],native_initializer=0x112720,

                native_chain_window_preserved=True,airborne_unchanged=True)
