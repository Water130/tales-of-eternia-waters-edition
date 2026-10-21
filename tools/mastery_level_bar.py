"""Read-only level 1..30 meter, with native fractional Craymel EXP."""


def emit_level_bar(emit,mem,value,text,line,tinted_line,string):
    progress=emit('mastery_level_progress',f'''
        push rbx
        push rsi
        push rdi
        sub rsp, 0x30
        mov rbx, rcx
        call {value:#x}
        test edx, edx
        je empty
        cmp eax, 1
        jb empty
        cmp eax, 30
        jae maximum
        mov esi, eax
        dec eax
        imul edi, eax, 1000
        cmp dword ptr [rbx], 0
        jne level_only
        # Native Craymel experience is cumulative; 928f0 is pure arithmetic.
        lea ecx, [rsi*2+3]
        call 0x928f0
        xor edx, edx
        cmp esi, 1
        cmove eax, edx
        mov dword ptr [rsp+0x28], eax
        lea ecx, [rsi*2+5]
        call 0x928f0
        sub eax, dword ptr [rsp+0x28]
        mov ecx, eax
        test ecx, ecx
        je level_only
        mov eax, dword ptr [rbx+4]
        lea rdx, {mem(0x11cafd8)}
        mov eax, dword ptr [rdx+rax*8+4]
        sub eax, dword ptr [rsp+0x28]
        jbe level_only
        cmp eax, ecx
        cmova eax, ecx
        imul rax, rax, 1000
        xor edx, edx
        div rcx
        add edi, eax
    level_only:
        mov eax, edi
        jmp done
    maximum:
        mov eax, 29000
        jmp done
    empty:
        xor eax, eax
    done:
        add rsp, 0x30
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
    return emit('mastery_level_bar',f'''
        push rbx
        sub rsp, 0x20
        call {progress:#x}
        imul eax, eax, 198
        xor edx, edx
        mov ecx, 29000
        div ecx
        mov ebx, eax
        lea rcx, {mem(string('1'))}
        mov edx, 98
        mov r8d, 49
        mov r9d, 12
        mov eax, 0xffeeeeee
        call {text:#x}
        lea rcx, {mem(string('30'))}
        mov edx, 311
        mov r8d, 49
        mov r9d, 13
        mov eax, 0xffeeeeee
        call {text:#x}
        mov ecx, 112
        mov edx, 54
        mov r8d, 198
        mov r9d, 3
        mov r10d, 65
        call {tinted_line:#x}
        test ebx, ebx
        je done
        mov ecx, 112
        mov edx, 54
        mov r8d, ebx
        mov r9d, 3
        call {line:#x}
    done:
        add rsp, 0x20
        pop rbx
        ret
    ''')
