"""Dedicated mage spell page summary: exact count, bonus and next milestone."""


def emit_spell_progress(emit, mem, value):
    # RCX spell row -> EAX bonus, EDX next absolute threshold (zero at max),
    # R8D progress within the next step (0..100), R9D remaining casts.
    progress=emit('mastery_spell_progress',f'''
        push rbx
        sub rsp, 0x20
        mov ebx, dword ptr [rcx+4]
        call {value:#x}
        cmp ebx, 63
        jb excluded
        cmp ebx, 66
        jbe buff
        cmp ebx, 70
        jb excluded
        cmp eax, 500
        jae offensive_max
        xor edx, edx
        mov ecx, 20
        div ecx
        imul r8d, edx, 5
        mov r9d, 20
        sub r9d, edx
        lea edx, [rax+1]
        imul edx, edx, 20
        jmp done
    offensive_max:
        mov eax, 25
        jmp maximum
    buff:
        mov r10d, eax
        cmp eax, 500
        jae buff_max
        mov ebx, 100
        xor r11d, r11d
        mov ecx, 100
        cmp eax, 100
        jb buff_step
        sub eax, 100
        mov ebx, 250
        mov r11d, 1
        mov ecx, 150
        cmp r10d, 250
        jb buff_step
        sub eax, 150
        mov ebx, 500
        mov r11d, 2
        mov ecx, 250
    buff_step:
        imul eax, eax, 100
        xor edx, edx
        div ecx
        mov r8d, eax
        mov eax, r11d
        mov edx, ebx
        mov r9d, ebx
        sub r9d, r10d
        jmp done
    buff_max:
        mov eax, 3
    maximum:
        xor edx, edx
        mov r8d, 100
        xor r9d, r9d
        jmp done
    excluded:
        xor eax, eax
        xor edx, edx
        xor r8d, r8d
        xor r9d, r9d
    done:
        add rsp, 0x20
        pop rbx
        ret
    ''')
    return progress
