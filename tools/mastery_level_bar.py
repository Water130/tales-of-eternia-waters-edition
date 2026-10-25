"""Native-style level meter; Craymels show EXP within their current level."""


def emit_level_bar(emit,mem,value,text,line,tinted_line,string,number,center,buffer):
    from mastery_exp_bar import emit_exp_bar
    gauge = emit_exp_bar(emit, mem)
    from craymel_experience import emit_exp_progress
    exp_progress=emit_exp_progress(emit,mem,'craymel_exp_progress_tree')
    fraction=emit('mastery_exp_fraction',f"""
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov ebx, edx; call {number:#x}
        mov rsi, rcx; lea rdi, {mem(buffer)}
    copy_first:
        lodsb; test al, al; je separator; stosb; jmp copy_first
    separator:
        mov al, 47; stosb
        mov eax, ebx; call {number:#x}; mov rsi, rcx
    copy_second:
        lodsb; stosb; test al, al; jne copy_second
        lea rcx, {mem(buffer)}
        add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    """)
    current=emit('craymel_current_level_bar',f'''
        push rbx; push rsi; push rdi; push rbp; sub rsp, 0x28
        mov ecx, dword ptr [rcx+4]; call {exp_progress:#x}
        mov ebx, eax; mov esi, edx; mov edi, r8d; mov ebp, r9d
        test ebp, ebp; je done
        cmp ebp, 30; je max_label
        mov eax, esi; mov edx, edi; call {fraction:#x}
        mov edx, 316; mov r8d, 51; mov r9d, 120; mov eax, 0xffeeeeee; call {text:#x}
        jmp bar
    max_label:
        lea rcx, {mem(string('MAX'))}
        mov edx, 316; mov r8d, 51; mov r9d, 24; mov eax, 0xffeeeeee; call {text:#x}
    bar:
        mov ecx, 112; mov edx, 53; mov r8d, 198; xor r10d, r10d; call {gauge:#x}
        imul eax, ebx, 198; xor edx, edx; mov ecx, 10000; div ecx
        test eax, eax; je done
        mov r8d, eax; mov ecx, 112; mov edx, 53; mov r10d, 1; call {gauge:#x}
    done: add rsp, 0x28; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
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
        # Physical branches keep the native level meter. Craymel rendering
        # exclusively uses current-level EXP in craymel_current_level_bar.
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
        cmp dword ptr [rcx], 0
        je {current:#x}
        push rbx
        sub rsp, 0x20
        call {progress:#x}
        imul eax, eax, 198
        xor edx, edx
        mov ecx, 29000
        div ecx
        mov ebx, eax
        mov ecx, 112
        mov edx, 57
        mov r8d, 198
        mov r9d, 3
        xor r10d, r10d
        call {gauge:#x}
        test ebx, ebx
        je done
        mov ecx, 112
        mov edx, 57
        mov r8d, ebx
        mov r9d, 3
        mov r10d, 1
        call {gauge:#x}
        cmp ebx, 198
        jne done
        lea rcx, {mem(string('MAX'))}
        mov edx, 201
        mov r8d, 45
        mov r9d, 24
        mov eax, 0xff90e05c
        call {text:#x}
    done:
        add rsp, 0x20
        pop rbx
        ret
    ''')
