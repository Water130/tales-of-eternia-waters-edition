"""Build 25190541: victory TP and explicit Guard + elemental spell invocation.

Only the two player command dispatchers choose a replacement; AI launch code is
untouched. Ownership, learned summons and vitality are checked before replacing
the requested ID. Native execution retains costs, targets and consumption.
"""

def emit_recovery(emit, jump):
    start = emit('victory_tp_bonus', '''
        add edx, 3
        movsx ecx, word ptr [rax+0x1c]
        imul edx, ecx
        jmp 0x118b3d
    ''')
    jump(0x118b36, 7, start, 'Add three percentage points to native victory TP recovery: 8% baseline')


def emit_summon(emit, mem, jump, edit):
    # EAX = requested arte; RCX = recipient; RDX = issuing controller's input.
    # Private leaf ABI: only EAX and flags may change, no native calls or writes.
    helper = emit('choose_elemental_summon', f'''
        push r8
        push r9
        push r10
        push r11
        cmp eax, 70
        jb unchanged
        cmp eax, 95
        ja unchanged
        test rcx, rcx
        je unchanged
        test rdx, rdx
        je unchanged
        test byte ptr [rdx], 0x80
        je unchanged
        cmp byte ptr [rcx+0x51], 0
        jne unchanged
        movzx r10d, byte ptr [rcx+0x4f]
        cmp r10d, 2
        jb unchanged
        cmp r10d, 3
        ja unchanged
        mov r9, qword ptr {mem(0x12cea78)}
        test r9, r9
        je unchanged
        movzx r8d, byte ptr [r9+rax*8+2]
        test r8b, 0x10
        jne unchanged
        and r8d, 0x0f
        dec r8d
        cmp r8d, 9
        ja unchanged
        mov r9, qword ptr {mem(0x12cea60)}
        test r9, r9
        je unchanged
        lea r11d, [r10d+1]
        cmp byte ptr [r9+r8*8+0xbb8], r11b
        jne unchanged
        cmp byte ptr [r9+r8*8+0xbb9], 0
        je unchanged
        cmp word ptr [r9+r8*8+0xbba], 0xa000
        jne unchanged
        add r8d, 43
        imul r10, r10, 0xd0
        lea r10, [r9+r10+0x7a]
        mov r11d, 32
    learned:
        cmp byte ptr [r10], r8b
        je accepted
        inc r10
        dec r11d
        jne learned
        jmp unchanged
    accepted:
        mov eax, r8d
    unchanged:
        pop r11
        pop r10
        pop r9
        pop r8
        ret
    ''')

    # 114296 has EBX = final player-selected arte, before manual/semi-auto split.
    # Helper has a private leaf ABI, so it needs no Windows shadow space.
    start = emit('summon_player_command', f'''
        push rax
        push rcx
        push rdx
        mov eax, ebx
        mov rcx, rbp
        mov rdx, qword ptr [rbp+0xf0]
        call {helper:#x}
        mov ebx, eax
        pop rdx
        pop rcx
        pop rax
        test ebx, ebx
        je 0x1142e7
        test r13d, r13d
        jne 0x1142ae
        jmp 0x11429f
    ''')
    jump(0x114296, 9, start, 'Choose invocation for an explicit player arte command')

    # Change EBP before native learned/cost validation and all subsequent uses.
    # R14 is the issuer, RBX the recipient: holding Guard never affects other AI.
    start = emit('summon_ally_shortcut', f'''
        push rax
        push rcx
        push rdx
        mov eax, ebp
        mov rcx, rbx
        mov rdx, qword ptr [r14+0xf0]
        call {helper:#x}
        mov ebp, eax
        pop rdx
        pop rcx
        pop rax
        mov edx, ebp
        mov rcx, rbx
        jmp 0x1134cc
    ''')
    jump(0x1134c7, 5, start, 'Choose invocation before validating an ally shortcut')

    # Native guard state omits the arte reader. Permit a new arte press by the
    # controlled mage while Guard is held; normal idle handling already permits
    # simultaneous Guard + Arte. Keep native target selection and stun blocking.
    save = 'pushfq; push rax; push rcx; push rdx; push r8; push r9; push r10; push r11'
    restore = 'pop r11; pop r10; pop r9; pop r8; pop rdx; pop rcx; pop rax; popfq'
    start = emit('guarded_mage_arte_input', f'''
        {save}
        cmp byte ptr [rbx+0x51], 0
        jne normal
        cmp byte ptr [rbx+0x57], 1
        jb normal
        cmp byte ptr [rbx+0x57], 2
        ja normal
        movzx eax, byte ptr [rbx+0x4f]
        cmp eax, 2
        jb normal
        cmp eax, 3
        ja normal
        cmp word ptr [rbx+0x44], 0
        jne normal
        mov rax, qword ptr [rbx+0xf0]
        test rax, rax
        je normal
        test byte ptr [rax], 0x80
        je normal
        test word ptr [rax], 0x200
        jne normal
        test byte ptr [rax+4], 0x40
        je normal
        sub rsp, 0x20
        mov rcx, rbx
        mov edx, 1
        call 0x1140f0
        add rsp, 0x20
        test eax, eax
        je normal
        {restore}
        jmp 0x72627
    normal:
        {restore}
        mov rax, qword ptr [rbx+0xf0]
        jmp 0x7272a
    ''')
    jump(0x72723, 7, start, 'Read a mage arte command while already holding Guard')

    # Ordinary spell charging has a separate 10 -> 5 case. Summon consumption in
    # d55db..d5637 is untouched (native level / 10 fixed-point vitality).
    edit(0x9041e, b'\x90'*8, 'Keep full vitality when casting an ordinary same-element spell')
