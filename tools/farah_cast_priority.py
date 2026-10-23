"""Keep a completed Deadly Force from starving behind concurrent large spells.

Effect 75 owns a cinematic and a native follow-up window, so it remains
exclusive. Read the live cast state instead of retaining a reservation that
could survive cancellation, death, a held input, or the end of the battle.
"""


def emit_farah_priority(emit, mem, data):
    # EDX = requested large effect. Preserve every GPR except the boolean EAX.
    return emit('farah_cast_priority', f'''
        push rcx
        push r8
        push r9
        xor eax, eax
        cmp byte ptr {mem(data+0x1a45)}, 0
        je done
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne done
        cmp byte ptr {mem(0x12d0efb)}, 0
        jne done
        cmp edx, 99
        ja done
        lea r8, {mem(data+0x200)}
        cmp byte ptr [r8+rdx], 0
        je done
        mov r8, qword ptr {mem(0x12cecd8)}
        test r8, r8
        je done
        movzx r9d, byte ptr {mem(0x12cece8)}
        test r9d, r9d
        je done
        cmp r9d, 8
        ja done
    actor:
        cmp word ptr [r8+0x3c], 1
        jne next
        cmp byte ptr [r8+0x51], 0
        jne next
        cmp byte ptr [r8+0x4f], 1
        jne next
        cmp dword ptr [r8+0x2c], 0
        jle next
        cmp byte ptr [r8+0x52], 10
        jne next
        cmp byte ptr [r8+0x6d], 42
        jne next
        cmp word ptr [r8+0x8e], 75
        jne next
        cmp word ptr [r8+0x8c], 1
        ja next
        cmp word ptr [r8+0x44], 0
        jne next
        cmp byte ptr [r8+0x74], 0
        jne next
        test dword ptr [r8+0x30], 0x4000
        jne next
        mov eax, 1
        jmp done
    next:
        add r8, 0x248
        dec r9d
        jne actor
    done:
        pop r9
        pop r8
        pop rcx
        ret
    ''')
