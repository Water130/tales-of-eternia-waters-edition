"""Expand local collision rectangles, never the stored projectile every frame."""
from spell_growth import PROJECTILE_CAPS


def emit_area(emit, mem, jump, state, data, usage, preserve):
    # RSI is the native collision object. RBX holds its packed int16 rectangle;
    # the following instruction copies it into this invocation's stack frame.
    # Thus repeated tests do not accumulate growth in persistent coordinates.
    body=emit('mastery_spell_area', preserve(f'''
        mov r11, qword ptr [rsi+8]
        test r11, r11
        je done
        cmp byte ptr [r11+0x51], 0
        jne done
        movzx ecx, byte ptr [r11+0x4f]
        sub ecx, 2
        cmp ecx, 1
        ja done
        add ecx, 2
        lea rax, {mem(0x12cf988)}
        cmp rsi, rax
        jne persistent
        mov r10, qword ptr {mem(state)}
        test r10, r10
        je done
        jmp tag
    persistent:
        mov rax, rsi
        lea r10, {mem(0x12cee48)}
        sub rax, r10
        cmp rax, 0xb40
        jae done
        xor edx, edx
        mov r10d, 0x30
        div r10
        test edx, edx
        jne done
        shl eax, 4
        lea r10, {mem(state+0x300)}
        add r10, rax
    tag:
        cmp qword ptr [r10], r11
        jne done
        movzx edx, word ptr [r10+8]
        cmp edx, 43
        jb done
        cmp edx, 52
        jbe summon
        cmp byte ptr {mem(data+0x1a0c)}, 0
        je done
        cmp edx, 70
        jb done
        cmp edx, 101
        jbe offensive
        cmp edx, 112
        jb done
        cmp edx, 113
        ja done
    offensive:
        {'; '.join(f'cmp edx, {aid}; je done' for aid in PROJECTILE_CAPS)}
        shl ecx, 8
        add ecx, edx
        lea r11, {mem(usage['preferences']['live_rva'])}
        bt dword ptr [r11], ecx
        jc done
        movzx eax, word ptr [r10+10]
        mov ecx, 999
        cmp eax, ecx
        cmova eax, ecx
        imul eax, eax, 50
        xor edx, edx
        div ecx
        test eax, eax
        je done
        mov r10d, eax
        # Decode a signed rectangle and grow equally around its center.
        # The native world rectangle uses pixels (actor coordinates /16).
        mov r8, rbx
        movsx eax, r8w
        shr r8, 32
        movsx ecx, r8w
        sub ecx, eax
        jle done
        mov eax, ecx
        imul eax, r10d
        xor edx, edx
        mov ecx, 200
        div ecx
        mov r9d, eax
        jmp height
    summon:
        cmp byte ptr {mem(data+0x1a43)}, 0
        je done
        movzx eax, word ptr [r10+10]
        cmp eax, 1
        jbe done
        cmp eax, 30
        ja done
        dec eax
        mov r10d, eax
        mov r8, rbx
        movsx eax, r8w
        shr r8, 32
        movsx ecx, r8w
        sub ecx, eax
        jle done
        mov eax, 720
        sub eax, ecx
        xor ecx, ecx
        cmp eax, ecx
        cmovl eax, ecx
        imul eax, r10d
        xor edx, edx
        mov ecx, 58
        div ecx
        mov r9d, eax
        imul eax, r10d, 50
        xor edx, edx
        mov ecx, 29
        div ecx
        mov r10d, eax
    height:
        mov r8, rbx
        shr r8, 16
        movsx eax, r8w
        shr r8, 32
        movsx ecx, r8w
        sub ecx, eax
        jle done
        mov eax, ecx
        imul eax, r10d
        xor edx, edx
        mov ecx, 200
        div ecx
        mov r10d, eax
        # Pack through a private stack temporary, saturating each boundary.
        push rbx
        xor r11d, r11d
    coordinate:
        movsx eax, word ptr [rsp+r11*2]
        mov ecx, r9d
        test r11b, 1
        je delta
        mov ecx, r10d
    delta:
        cmp r11d, 2
        jae positive
        neg ecx
    positive:
        add eax, ecx
        mov ecx, 32767
        cmp eax, ecx
        cmovg eax, ecx
        mov ecx, -32768
        cmp eax, ecx
        cmovl eax, ecx
        mov word ptr [rsp+r11*2], ax
        inc r11d
        cmp r11d, 4
        jb coordinate
        pop rbx
    done:
    ''')+'''
        mov qword ptr [rsp+0x38], rbx
        jmp 0x1162ba
    ''')
    jump(0x1162b5,5,body,'Spell/Craymel progression: centered non-cumulative collision growth, independent options')
    return body
