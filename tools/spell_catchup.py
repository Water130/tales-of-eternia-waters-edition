"""Earned catch-up EXP is separate from real cast counts and native saves.

Old profiles have zero extra EXP: existing ranks therefore migrate unchanged.
One successful cast earns one base EXP plus at most two catch-up EXP, capped
at the other mage's current EXP. Six innate starter spells stay independent.
"""
from spell_growth import OFFENSIVE

STARTERS = (70, 72, 75, 79, 82, 86)
ELIGIBLE = tuple(range(63, 67)) + tuple(a for a in OFFENSIVE if a not in STARTERS)
SIZE = 1792
OFFSET = 0xf000
STATE_SIZE = 0x1a000


def emit_catchup(emit, mem, state, data, raw):
    bonus = state + OFFSET
    # ECX character, EDX spell. R8-R11 are volatile; ECX/EDX remain intact.
    read = emit('spell_exp_read', f'''
        xor eax, eax
        cmp ecx, 6; ja done
        cmp edx, 127; ja done
        mov r8d, ecx; shl r8d, 7; add r8d, edx
        lea r9, {mem(raw)}
        movzx eax, word ptr [r9+r8*2]
        lea r9, {mem(bonus)}
        movzx r10d, word ptr [r9+r8*2]
        add eax, r10d
    done:
        ret
    ''')
    next_exp = emit('spell_exp_next', f'''
        sub rsp, 0x28
        call {read:#x}
        add rsp, 0x28
        inc eax
        cmp byte ptr {mem(data+0x1a0c)}, 0; je done
        cmp ecx, 2; jb done
        cmp ecx, 3; ja done
        {'; '.join(f'cmp edx, {a}; je eligible' for a in ELIGIBLE)}
        jmp done
    eligible:
        # Do not accrue optional bonuses while this spell is disabled.
        mov r8d, ecx; shl r8d, 8; add r8d, edx
        lea r9, {mem(state+0xd000)}
        bt dword ptr [r9], r8d; jc done
        mov r11d, 999
        cmp edx, 66; ja cap_current
        mov r11d, 500
    cap_current:
        cmp eax, r11d; jae done
        mov r8d, ecx; xor r8d, 1
        shl r8d, 7; add r8d, edx
        lea r9, {mem(raw)}
        movzx r10d, word ptr [r9+r8*2]
        lea r9, {mem(bonus)}
        movzx r11d, word ptr [r9+r8*2]
        add r10d, r11d
        mov r11d, 999
        cmp edx, 66; ja cap_peer
        mov r11d, 500
    cap_peer:
        cmp r10d, r11d; cmova r10d, r11d
        cmp eax, r10d; jae done
        add eax, 2
        cmp eax, r10d; cmova eax, r10d
    done:
        ret
    ''')
    award = emit('spell_exp_award', f'''
        push rbx
        sub rsp, 0x20
        mov ebx, ecx; shl ebx, 7; add ebx, edx
        call {next_exp:#x}
        lea r9, {mem(raw)}
        movzx r10d, word ptr [r9+rbx*2]
        inc r10d
        sub eax, r10d
        lea r9, {mem(bonus)}
        mov word ptr [r9+rbx*2], ax
        add rsp, 0x20
        pop rbx
        ret
    ''')
    return dict(live_rva=bonus, size=SIZE, read_rva=read, next_rva=next_exp,
                award_rva=award, eligible=list(ELIGIBLE), multiplier=3,
                cap=999, raw_casts_unchanged=True)


def storage_layout(state):
    return dict(snapshot=state+0xf700, pending=state+0xfe00,
                valid=state+0x10500, pending_ptr=state+0x10508,
                workers=state+0x10600)
