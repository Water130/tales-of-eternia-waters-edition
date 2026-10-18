"""Extend only Ondine's projected water-decor perimeter, never actors/hitboxes.

a0460 builds a 7x10 water grid on its stack, then reuses the first row for
the waterfall's lower edge. Overscan both edges in projected coordinates;
interior points, scrolling UVs, camera scripts and effect state remain native.
"""


def emit_ondine_visual(emit, mem, jump):
    edge = emit('ondine_water_perimeter', f'''
        pushfq
        push rdx
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne native
        test ebx, ebx
        jne right
        movsx eax, word ptr {mem(0x8c9720)}
        mov edx, -16
        cmp eax, edx
        cmovg eax, edx
        mov word ptr {mem(0x8c9720)}, ax
    right:
        cmp ebx, 9
        jne bottom
        movsx eax, word ptr {mem(0x8c9720)}
        mov edx, 336
        cmp eax, edx
        cmovl eax, edx
        mov word ptr {mem(0x8c9720)}, ax
    bottom:
        cmp ebp, 6
        jne native
        movsx eax, word ptr {mem(0x8c9724)}
        mov edx, 224
        cmp eax, edx
        cmovl eax, edx
        mov word ptr {mem(0x8c9724)}, ax
    native:
        pop rdx
        popfq
        movzx eax, word ptr {mem(0x8c9720)}
        jmp 0xa07df
    ''')
    jump(0xa07d8,7,edge,'Cover Ondine water decor sides and foreground at its native camera')
