"""Tag the native damage ring; keep its two low type bits and heal writers intact."""

# User-selected Symphonia palette in the engine's half-intensity RGB units.
# Eternia's element order places Ice before Lightning.
PAIRS = [(bytes.fromhex(a), bytes.fromhex(b)) for a,b in (
    ('808080','808080'), ('205080','102850'), ('308050','185030'),
    ('802810','501008'), ('705020','483010'), ('708080','385868'),
    ('805080','582858'), ('808058','585830'), ('301850','180828'),
    ('808080','808080'), ('147666','0c483e'))]
# Slot 9 is Maxwell's nonstandard "Elemental" family: display neutral white
# (Meteor Swarm / Shooting Star), independently of the casting-particle hue.
HEAL_PAIR = (bytes.fromhex('708070'),bytes.fromhex('508050'))


def emit_damage_colors(emit, mem, jump, data_rva):
    palette = b''.join(a+b'\0' for a,b in PAIRS)
    from damage_gradient import emit_gradient
    context = emit_gradient(emit,mem,jump,data_rva)
    # Store the secondary palette with code-local constants: the data after
    # 1340 already belongs to the combat HUD.
    rgba = lambda rgb: int.from_bytes(bytes(min(255,v*2) for v in rgb)+b'\xff','little')
    def pair_code(pair):
        return f'mov dword ptr {mem(context+4)}, {rgba(pair[0])}; mov dword ptr {mem(context+8)}, {rgba(pair[1])}'
    secondary = '\n'.join(f'cmp ecx, {i*4}; jne shade_{i}; {pair_code(pair)}; jmp pair_ready; shade_{i}:'
                          for i,pair in enumerate(PAIRS))
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
        mov byte ptr {mem(context)}, 0
        movzx eax, byte ptr [rbx+5]
        cmp eax, 0x40
        je received
        # Native low bit 1 denotes healing/TP recovery, not elemental damage.
        cmp eax, 1
        je healing
        cmp eax, 3
        je healing
        sub eax, 0x10
        cmp eax, 40
        ja original
        test eax, 3
        jne original
        lea r10, {mem(data_rva+0x1300)}
        mov ecx, eax
        mov eax, dword ptr [r10+rax]
        {secondary}
        jmp color
    pair_ready:
        # Route only tagged elemental damage through the original HP/TP
        # numeral strip. Same 48x48 cell, native spacing/animation retained.
        test ecx, ecx; je color
        mov byte ptr [rsp+0x40], 0
        mov byte ptr [rsp+0x48], 200
        jmp gradient
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
        jmp color
    healing:
        mov eax, 0x708070
        {pair_code(HEAL_PAIR)}
        # White source glyphs keep the native mint pair free of the French
        # recovery strip's baked pink edge. Numbers/spacing stay native.
        mov byte ptr [rsp+0x40], 0
        mov byte ptr [rsp+0x48], 200
    gradient:
        mov byte ptr {mem(context)}, 1
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
        mov byte ptr {mem(context)}, 0
        jmp 0x11cf45
    ''')
    jump(0x11cf40, 5, tint, 'Symphonia two-tone damage/healing palette and native elemental digit glyphs')
    return palette
