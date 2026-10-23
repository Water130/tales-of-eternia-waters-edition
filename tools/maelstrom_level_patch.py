"""Local Undine level adjustment; retain the native extension and enemy rules."""


def emit_maelstrom_level(emit, jump, usage):
    # The original Spread branch has already resolved R9 to its caster and R8
    # to the Craymel state. Only the comparison changes. Leave its result flags
    # intact for the native JB; neither path writes registers, save data or TP.
    start = emit('maelstrom_undine_level', '''
        cmp byte ptr [r9+0x51], 0
        jne native_level
        cmp byte ptr [r8+0xbb9], 10
        jmp 0xc0f13
    native_level:
        cmp byte ptr [r8+0xbb9], 15
        jmp 0xc0f13
    ''')
    jump(0xc0f0b, 8, start, 'Maelstrom: Undine level 10 for party casters')
    from craymel_faculties import preserve
    eligibility = emit('maelstrom_party_eligibility', f'''
        cmp byte ptr [r9+0x51], 0
        jne native
        cmp word ptr [r8+0xbba], 0x5000
        jb 0xc10aa
        {preserve(f'movzx ecx, byte ptr [r9+0x4f]; mov edx, 71; call {usage["catchup"]["read_rva"]:#x}',result='rax')}
        cmp eax, 50
        jb 0xc10aa
        jmp 0xc0f80
    native:
        mov rax, qword ptr [r9+0xe8]
        jmp 0xc0f20
    ''')
    jump(0xc0f19, 7, eligibility,
         'Maelstrom: party 5/10 vitality replaces hidden water-resistance requirement')
    return dict(site=0xc0f0b, party_level=10, native_enemy_level=15,
                source_arte=71, source_effect=66, party_vitality=0x5000,credited_uses_required=50,
                party_water_resistance_required=False, native_cost_and_action_retained=True)
