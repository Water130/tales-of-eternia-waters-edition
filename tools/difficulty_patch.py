"""Optional enemy difficulty adjustments for Steam build 25190541."""


def emit_difficulty(emit, jump):
    # Enemy records are copied from the original resource before this block.
    # DEF is the signed word at +22 used by physical damage at 8e9b2.
    # ATK, INT, accuracy and all non-stat difficulty paths remain native.
    defense = emit('difficulty_defense', '''
        movzx ecx, byte ptr [rax+4]
        cmp ecx, 1
        jb original
        cmp ecx, 3
        ja original
        push rax
        push rdx
        push r8
        movsx eax, word ptr [rdi+0x22]
        lea r8d, [rcx+10]
        imul eax, r8d
        cdq
        mov r8d, 10
        idiv r8d
        mov r8d, 32767
        cmp eax, r8d
        cmovg eax, r8d
        mov word ptr [rdi+0x22], ax
        pop r8
        pop rdx
        pop rax
    original:
        cmp cl, 1
        jmp 0x82a46
    ''')
    jump(0x82a3f, 7, defense, 'Difficulty: physical defense +10/20/30 percent')

    # Enter after the native ATK/INT calculation, before HP multiplication.
    # Commit INT as the replaced native path does, then scale the original HP.
    # Wide arithmetic avoids intermediate overflow; saturate at the field limit.
    for name, site, size, numerator, denominator in (
        ('hard', 0x82a86, 7, 3, 2),
        ('extreme', 0x82adb, 6, 3, 1),
        ('unknown', 0x82b1f, 8, 5, 1),
    ):
        hp = emit('difficulty_hp_'+name, f'''
            mov word ptr [rdi+0x24], dx
            movsxd rax, dword ptr [rdi+0x18]
            imul rax, rax, {numerator}
            cqo
            mov ecx, {denominator}
            idiv rcx
            mov ecx, 0x7fffffff
            cmp rax, rcx
            cmovg rax, rcx
            mov rcx, -2147483648
            cmp rax, rcx
            cmovl rax, rcx
            mov edx, eax
            mov dword ptr [rdi+0x18], edx
            shr eax, 31
            jmp 0x82b3f
        ''')
        jump(site, size, hp, 'Difficulty: '+name+' enemy HP')

    fixed = emit('difficulty_fixed_damage', '''
        movzx ecx, byte ptr [rax+4]
        cmp ecx, 1
        jb original
        cmp ecx, 2
        ja original
        push rdx
        push r8
        mov eax, esi
        imul eax, ecx
        cdq
        mov r8d, 10
        idiv r8d
        add esi, eax
        pop r8
        pop rdx
        jmp 0x8ed32
    original:
        cmp cl, 1
        jmp 0x8ecef
    ''')
    # This is downstream of the native mode-3 and enemy-side guards.
    jump(0x8ece8, 7, fixed, 'Difficulty: enemy fixed damage x1.1/1.2/1.5')
    return dict(option='DifficultyRebalance', flag_index=8,
                enemy_hp_factors=[1, 1.5, 3, 5],
                enemy_defense_factors=[1, 1.1, 1.2, 1.3],
                enemy_fixed_damage_factors=[1, 1.1, 1.2, 1.5],
                defense_field=0x22, stat_record_entry=0x82a2e,
                applied_on_enemy_record_load=True,
                unchanged=['Normal', 'ATK', 'INT', 'accuracy', 'evasion',
                           'casting', 'AI delay', 'rewards', 'party stats'])
