"""Tag the native damage ring; keep its two low type bits and heal writers intact."""
from casting_color_patch import COLORS


def emit_damage_colors(emit, mem, jump, data_rva):
    palette = bytes((128, 128, 128, 0)) + b''.join(
        bytes((v+1)//2 for v in rgb)+b'\0' for rgb in COLORS.values())
    tag = emit('tag_damage_color', f'''
        push rax
        mov eax, 0x40
        cmp byte ptr [rdi+0x51], 0
        je tagged
        movzx eax, byte ptr [r12+1]
        cmp eax, 10
        jbe element
        xor eax, eax
    element:
        lea eax, [rax*4+0x10]
    tagged:
        mov byte ptr [rcx+7], al
        pop rax
        and edx, 0x8000000f
        jmp 0x8f07c
    ''')
    jump(0x8f072, 10, tag, 'Tag actual impact element and party damage in native number record')
    tint = emit('draw_damage_color', f'''
        pushfq
        push rax
        push rcx
        push r10
        movzx eax, byte ptr [rbx+5]
        cmp eax, 0x40
        je received
        sub eax, 0x10
        cmp eax, 40
        ja original
        test eax, 3
        jne original
        lea r10, {mem(data_rva+0x1300)}
        mov eax, dword ptr [r10+rax]
        jmp color
    received:
        mov eax, 56
        sub eax, ebp
        cmp eax, 56
        ja original
        shr eax, 1
        add eax, 76
        mov ecx, eax
        shl eax, 16
        shl ecx, 8
        or eax, ecx
        or eax, 128
    color:
        mov word ptr {mem(0x11ce670)}, ax
        shr eax, 16
        mov byte ptr {mem(0x11ce672)}, al
    original:
        pop r10
        pop rcx
        pop rax
        popfq
        call 0x1114a0
        jmp 0x11cf45
    ''')
    jump(0x11cf40, 5, tint, 'Tint damage numbers without changing healing or TP recovery')
    return palette
