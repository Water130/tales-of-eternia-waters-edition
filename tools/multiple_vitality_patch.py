"""Optional simultaneous MAX Craymel vitality, Steam build 25190541."""


def emit_multiple_vitality(emit, jump, edit):
    # Ordinary spells subtract half their gain from the opposing element.
    # Keep that native trade-off for incomplete gauges; lock only a ready MAX.
    opposite = emit('vitality_preserve_opposite_max', '''
        cmp word ptr [rdi-6], 0xa000
        jne original
        mov edx, 0xa000
        jmp 0x90413
    original:
        movzx ecx, word ptr [rdi-6]
        mov edx, r8d
        jmp 0x903fc
    ''')
    jump(0x903f5, 7, opposite, 'Vitality: preserve an opposing MAX gauge')

    # Previously unconditional in the summon input modules. All MAX protection
    # now belongs to this single switch, including the same-element 10 -> 5.
    edit(0x9041e, b'\x90'*8, 'Vitality: preserve same-element MAX on ordinary casts')

    # The native loop downgrades EVERY full gauge to nine before setting the
    # newly charged gauge to ten. Skip only the loop, after the ownership guard.
    jump(0x9046a, 9, 0x90487, 'Vitality: allow several owned gauges at MAX')
    return dict(option='MultipleMaxVitality', flag_index=9,
                max_value=0xa000, charge_routine=0x90380,
                sites=[0x903f5, 0x9041e, 0x9046a],
                preserved=['same-element MAX', 'opposing MAX', 'other MAX gauges'],
                unchanged=['partial charge and opposing loss', 'owner requirement',
                           'summon consumption', 'level-based vitality reset',
                           'element use counters', 'save format'],
                disabled='Original vitality rules on subsequent actions; no gauge rewrite on toggle')
