"""Scale native shadow thickness with its sprite's actual projected depth.

80090 already scales shadow width to the rendered sprite bounds, but keeps
height=10 and ground offset=8 screen units. Wide camera views therefore make
shadows disproportionately thick. Keep native texture, opacity, width and ground.
"""


def emit_shadow_visual(emit, mem, jump, data_rva):
    size=emit('battle_shadow_height', f'''
        pushfq
        push rcx
        push rdx
        push r8
        mov eax, 10
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne done
        cmp byte ptr {mem(data_rva+0x20)}, 1
        jne done
        # Native sprite frame stores projection-Z minus 512 at original RSP+c0.
        movsx ecx, word ptr [rsp+0xe0]
        add ecx, 512
        cmp ecx, 512
        jle done
        cmp ecx, 4096
        jg done
        mov eax, 4096
        xor edx, edx
        div ecx
        movsx r8d, word ptr {mem(0x11ce662)}
        add r8d, 8
        sub r8d, eax
        mov word ptr {mem(0x11ce662)}, r8w
        mov eax, 5120
        xor edx, edx
        div ecx
        mov edx, 2
        cmp eax, edx
        cmovb eax, edx
    done:
        pop r8
        pop rdx
        pop rcx
        popfq
        jmp 0x80637
    ''')
    jump(0x80632,5,size,'Scale battlefield shadow thickness and ground offset with sprite depth')
