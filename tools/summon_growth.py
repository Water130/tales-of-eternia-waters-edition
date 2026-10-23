"""Craymel level scaling, independently switchable from spell EXP.

Level one preserves native damage. These are initial balance coefficients, not
a claim of equal DPS: collision cadence, resistance and target movement still
matter. Undine's unusually small fixed damage needs a much steeper curve than
Sekundes's fixed 9600 total. Rem's healing is not multiplied.
"""
MAX_BONUS = (1900, 200, 300, 200, 200, 50, 0, 200, 100, 25)


def bonus(spirit, level):
    return MAX_BONUS[spirit] * (max(1, min(30, level))-1) // 29


def emit_summon_damage(emit, mem, data):
    # R10 = immutable origin record, ESI = post-resistance damage.
    # Caller has preserved all volatile registers; no critical roll here.
    return emit('summon_level_damage', f'''
        cmp byte ptr {mem(data+0x1a43)}, 0
        je done
        cmp esi, 0
        jle done
        movzx eax, word ptr [r10+8]
        sub eax, 43
        cmp eax, 9
        ja done
        mov ecx, dword ptr [r10+12]
        cmp ecx, 1900
        ja done
        add ecx, 100
        mov eax, esi
        imul rax, rcx
        xor edx, edx
        mov ecx, 100
        div rcx
        mov ecx, 30000
        cmp rax, rcx
        cmova rax, rcx
        mov esi, eax
    done:
        ret
    ''')


def emit_summon_capture(mem):
    # EDX arte, R11 output record, R12 owner. Shared native party master,
    # not whichever mage currently holds the partner Craymel.
    table='; '.join(f'cmp ecx, {i}; je spirit_{i}' for i in range(10))
    values='\n'.join(f'spirit_{i}: mov ecx, {v}; jmp coefficient' for i,v in enumerate(MAX_BONUS))
    return f'''
    summon:
        lea ecx, [rdx-43]
        mov r10, qword ptr {mem(0x12cea60)}
        test r10, r10
        je done
        cmp byte ptr [r10+rcx*8+0xbb8], 0
        je done
        mov word ptr [r11+8], dx
        movzx eax, byte ptr [r10+rcx*8+0xbb9]
        mov edx, 1
        cmp eax, edx
        cmovb eax, edx
        mov edx, 30
        cmp eax, edx
        cmova eax, edx
        mov word ptr [r11+10], ax
        dec eax
        {table}
        jmp done
        {values}
    coefficient:
        imul eax, ecx
        xor edx, edx
        mov ecx, 29
        div ecx
        mov dword ptr [r11+12], eax
        jmp store_owner
    '''
