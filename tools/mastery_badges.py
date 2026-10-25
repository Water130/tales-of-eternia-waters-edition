"""Native elemental discs and healing glyphs for the mastery menus."""


def emit_badges(emit, mem, native):
    # Keep the original localized disc renderer for headings. The spell-list
    # copy only changes geometry/font size; all palettes, UVs, localization,
    # null checks and register restoration remain native.
    import struct
    pe, cs, relocate = native
    def scalar(register, value):
        bits=struct.unpack('<I',struct.pack('<f',value))[0]
        return f'mov r11d, {bits}; movd {register}, r11d'
    changes={
        0x251945: scalar('xmm0',10.),
        0x2519da: scalar('xmm4',13.5*10/14),
        0x2519eb: scalar('xmm0',6.*10/14),
        0x251a1e: scalar('xmm5',16.+4.*10/14)+'; addss xmm2, xmm5',
        0x251a26: scalar('xmm5',80.+7.1*10/14)+'; addss xmm1, xmm5',
    }
    lines=[];replaced=set()
    for ins in cs.disasm(pe.get_data(0x2518a0,0x1b8),0x2518a0):
        line=relocate(ins.bytes,ins.address)
        if ins.address in changes:
            line=changes[ins.address];replaced.add(ins.address)
        elif ins.mnemonic.startswith('j') and ins.op_str.startswith('0x'):
            target=int(ins.op_str,16)
            if 0x2518a0<=target<0x251a58:line=f'{ins.mnemonic} badge_{target:x}'
        lines.append(f'badge_{ins.address:x}: {line}')
    assert replaced==set(changes)
    small_native=emit('mastery_compact_element_native','\n'.join(lines))
    small_element=emit('mastery_compact_element_badge',f'''
        sub rsp, 0x28
        mov dword ptr [rsp+0x20], r9d
        mov r9d, ecx
        lea ecx, [rdx-80]
        lea edx, [r8-16]
        mov r8d, 0x601
        call {small_native:#x}
        add rsp, 0x28
        ret
    ''')
    # Same native green reticle/atlas region as Heal (54), at 10x10.
    heal=emit('mastery_compact_heal_badge','''
        push rsi; push rdi; sub rsp, 0x68
        mov esi, edx; mov edi, r8d
        mov ecx, r9d; shl ecx, 24; or ecx, 0xffffff
        call 0x6c550
        mov r9d, esi
        mov dword ptr [rsp+0x20], edi
        mov dword ptr [rsp+0x28], 0
        mov dword ptr [rsp+0x30], 10
        mov dword ptr [rsp+0x38], 10
        mov dword ptr [rsp+0x40], 448
        mov dword ptr [rsp+0x48], 272
        mov dword ptr [rsp+0x50], 512
        mov dword ptr [rsp+0x58], 336
        call 0x131c0
        add rsp, 0x68; pop rdi; pop rsi; ret
    ''')
    # ECX element 0..10, EDX/R8D screen coordinates, R9D opacity.
    element = emit('mastery_element_badge', '''
        sub rsp, 0x28
        mov dword ptr [rsp+0x20], r9d
        mov r9d, ecx
        lea ecx, [rdx-80]
        lea edx, [r8-16]
        mov r8d, 0x601
        call 0x2518a0
        add rsp, 0x28
        ret
    ''')
    # The native spell descriptor carries the actual element in its low
    # nibble. Healing/restoration spells use the original green support icon.
    spell = emit('mastery_spell_badge', f'''
        cmp ecx, 54; jb elemental
        cmp ecx, 60; jbe healing
        cmp ecx, 67; je healing
    elemental:
        cmp ecx, 113; ja done
        lea rax, {mem(0x551780)}
        movzx ecx, byte ptr [rax+rcx*8+2]
        and ecx, 15
        cmp ecx, 10; ja done
        jmp {small_element:#x}
    healing:
        jmp {heal:#x}
    done:
        ret
    ''')
    return dict(element=element, spell=spell)


def emit_text_width(emit, mem):
    # Same seven-point font, locale adjustment and width cap as menu text.
    return emit('mastery_text_width', f'''
        push rbx
        sub rsp, 0x30
        mov ebx, r9d
        mov eax, 0x40e00000
        movd xmm1, eax
        cmp qword ptr {mem(0x644a18)}, 0; je measure
        movzx eax, byte ptr {mem(0x11c9ce8)}
        lea edx, [rax-1]
        cmp edx, 5; jbe adjusted
        cmp eax, 10; jb measure
    adjusted:
        addss xmm1, dword ptr {mem(0x524860)}
    measure:
        xor r8d, r8d; xor r9d, r9d
        mov dword ptr [rsp+0x20], 0
        mov dword ptr [rsp+0x28], -1
        call 0xb240
        cvtsi2ss xmm2, ebx
        minss xmm0, xmm2
        cvttss2si eax, xmm0
        inc eax
        add rsp, 0x30
        pop rbx
        ret
    ''')
