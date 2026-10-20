"""Extra native-format particle storage; no changes to effect scale or timing.

Native constructors discard requests once their fixed arrays are full. Keep the
original arrays first, then use three additional banks. Each bank is advanced by
the original updater exactly once per native call, including pause/render paths.
Only the four ordinary particle types are extended; full-screen fades stay native.
"""

BANK_SIZE = 0x5600
BANKS = 3
TYPES = [
    # name, pool offset, stride, count, active byte, protected flags, full site,
    # displaced size, native copy continuation, updater, prologue size/assembly
    ('sprite', 0, 0x58, 50, 0x49, 0x4c, 0x8b581, 7, 0x8b588,
     0x88ba0, 5, 'mov qword ptr [rsp+8], rbx'),
    ('line', 0x1130, 0x2c, 50, 8, 0xe, 0x8b637, 7, 0x8b63e,
     0x87be0, 7, 'mov rax, rsp; mov qword ptr [rax+0x10], rbx'),
    ('quad', 0x36b0, 0x6a, 48, 8, 0x5e, 0x8b6e1, 7, 0x8b6e8,
     0x86d90, 5, 'mov qword ptr [rsp+0x20], rbx'),
    ('mesh', 0x19c8, 0x4a, 100, 8, 0xa, 0x8b81c, 11, 0x8b82a,
     0x85810, 7, 'mov rax, rsp; push rbx; push rdi; push r14'),
]


def emit_particle_capacity(emit, mem, jump, data):
    for name, off, stride, count, active, flags, site, size, continuation, updater, pro_size, pro in TYPES:
        # The mesh free-slot branch targets 8b82a. Hook the preceding scan
        # tail rather than overwriting that incoming branch target.
        select = emit('particle_overflow_'+name, f'''
            {'inc ecx; add rax, 0x4a; cmp ecx, 100; jl 0x8b816' if name=='mesh' else ''}
            push r10
            push r11
            lea rax, {mem(data+off)}
            mov r10d, {BANKS}
        bank:
            mov r11d, {count}
            {'cmp byte ptr [rdx+8], 6; je scan; dec r11d' if name=='line' else ''}
        scan:
            cmp byte ptr [rax+{active}], 0
            je found
            add rax, {stride}
            dec r11d
            jne scan
            add rax, {BANK_SIZE-stride*count}
            {'cmp byte ptr [rdx+8], 6; je next_bank; add rax, 0x2c; next_bank:' if name=='line' else ''}
            dec r10d
            jne bank
            mov rax, qword ptr {mem(0x12cec20)}
        found:
            pop r11
            pop r10
            jmp {continuation:#x}
        ''')
        jump(site, size, select, 'Particle capacity: overflow '+name)
        native = emit('particle_native_update_'+name, f'{pro}; jmp {updater+pro_size:#x}')
        update = emit('particle_update_'+name, f'''
            push rbx
            push rsi
            push rdi
            sub rsp, 0x30
            mov rbx, qword ptr {mem(0x12cecf0)}
            call {native:#x}
            mov qword ptr [rsp+0x20], rax
            lea rsi, {mem(data)}
            mov edi, {BANKS}
        bank:
            mov qword ptr {mem(0x12cecf0)}, rsi
            call {native:#x}
            add rsi, {BANK_SIZE}
            dec edi
            jne bank
            mov qword ptr {mem(0x12cecf0)}, rbx
            mov rax, qword ptr [rsp+0x20]
            add rsp, 0x30
            pop rdi
            pop rsi
            pop rbx
            ret
        ''')
        jump(updater, pro_size, update, 'Particle capacity: update '+name)

    reset = emit('particle_reset_battle', f'''
        mov qword ptr {mem(0x12cecf0)}, rbx
        pushfq
        push rax
        push rcx
        push rdi
        lea rdi, {mem(data)}
        xor eax, eax
        mov ecx, {BANKS*BANK_SIZE//8}
        cld
        rep stosq
        pop rdi
        pop rcx
        pop rax
        popfq
        jmp 0xd6512
    ''')
    jump(0xd650b, 7, reset, 'Particle capacity: reset on battle initialization')
    loops = []
    for name, off, stride, count, active, flags, *_ in TYPES:
        loops.append(f'''
            lea rax, {mem(data+off)}
            mov r10d, {BANKS}
        clear_bank_{name}:
            mov r11d, {count}
        clear_{name}:
            test byte ptr [rax+{flags}], 8
            jne keep_{name}
            mov byte ptr [rax+{active}], 0
        keep_{name}:
            add rax, {stride}
            dec r11d
            jne clear_{name}
            add rax, {BANK_SIZE-stride*count}
            dec r10d
            jne clear_bank_{name}
        ''')
    clear = emit('particle_clear_effects', f'''
        pushfq
        push r10
        push r11
        {''.join(loops)}
        pop r11
        pop r10
        popfq
        mov rax, qword ptr {mem(0x12cecf0)}
        jmp 0x83231
    ''')
    jump(0x8322a, 7, clear, 'Particle capacity: preserve native protected particles during clear')
    return dict(state_rva=data, size=BANK_SIZE*BANKS, extra_banks=BANKS,
                sprite_capacity=200, line_capacity=200, quad_capacity=192,
                mesh_capacity=400, runtime_validated=False)
