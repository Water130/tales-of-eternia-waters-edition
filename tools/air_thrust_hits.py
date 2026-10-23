"""Per-effect, per-projectile Air Thrust hit cooldowns, build 25190541.

The original collision evaluator reads caster+0x5a[target slot]. All four
wind projectiles therefore suppress each other. Keep native hit geometry,
damage, guarding, immunity and cooldown durations; split only that history.
"""


def emit_air_hits(emit, mem, jump, ledger, data):
    # 16 effects * 256 bytes: ten rows, eight target expiry words per row.
    scope = ledger + 0x1000  # row Q, owner Q, effect tick Q; scoped to one call
    def saved(body):
        return f'''pushfq
            push rax
            push rdx
            push r10
            {body}
            pop r10
            pop rdx
            pop rax
            popfq'''

    reset = emit('air_hits_reset', saved(f'''
        mov eax, r8d
        shl eax, 8
        lea r10, {mem(ledger)}
        add r10, rax
        xor eax, eax
        mov edx, 32
    clear:
        mov qword ptr [r10], rax
        add r10, 8
        dec edx
        jne clear
    ''') + '\nret')

    scoped = emit('air_hits_collision', f'''
        push qword ptr {mem(scope)}
        push qword ptr {mem(scope+8)}
        push qword ptr {mem(scope+16)}
        sub rsp, 0x28
        mov qword ptr {mem(scope)}, 0
        cmp byte ptr {mem(data+0x1a4d)}, 0
        je collide
        cmp ebp, 10
        jae collide
        mov rax, rsi
        lea rdx, {mem(0x12cfca0)}
        sub rax, rdx
        cmp rax, 0x1200
        jae collide
        xor edx, edx
        mov r10d, 0x120
        div r10
        test edx, edx
        jne collide
        shl eax, 8
        mov edx, ebp
        shl edx, 4
        add eax, edx
        lea r10, {mem(ledger)}
        add r10, rax
        mov qword ptr {mem(scope)}, r10
        mov rax, qword ptr [rsi]
        mov qword ptr {mem(scope+8)}, rax
        movzx eax, word ptr [rsi+0x38]
        mov qword ptr {mem(scope+16)}, rax
    collide:
        lea rcx, {mem(0x12cf988)}
        call 0x116260
        add rsp, 0x28
        pop qword ptr {mem(scope+16)}
        pop qword ptr {mem(scope+8)}
        pop qword ptr {mem(scope)}
        jmp 0x9449f
    ''')
    jump(0x9449a, 5, scoped, 'Air Thrust: scope collision to this visible projectile')

    gate = emit('air_hits_gate', f'''
        push rdx
        push r10
        mov r10, qword ptr {mem(scope)}
        test r10, r10
        je native
        cmp rcx, 8
        jae native
        cmp rax, qword ptr {mem(scope+8)}
        jne native
        lea rdx, {mem(0x12cf988)}
        cmp rsi, rdx
        jne native
        movzx edx, word ptr [r10+rcx*2]
        cmp dx, word ptr {mem(scope+16)}
        # Native continuation uses JNE, so map expiry > tick to ZF=0.
        seta dl
        test dl, dl
        jmp done
    native:
        cmp byte ptr [rcx+rax+0x5a], 0
    done:
        pop r10
        pop rdx
        jmp 0x116313
    ''')
    jump(0x11630e, 5, gate, 'Air Thrust: independent target cooldown for each projectile')

    # Mirror real native cooldown writes (including a blocked hit's 32 ticks).
    # Leave the caster's native history intact for other attacks and option OFF.
    for site, size, owner, original, tail, guard in (
        (0x8e525, 8, 'rdi', 'mov byte ptr [rcx+rdi+0x5a], al',
         'cmp byte ptr [rbx+0x51], r15b', False),
        (0x8e6a7, 11, 'rdi', 'mov byte ptr [rcx+rdi+0x5a], al',
         'test dword ptr [rbx+0x30], 0x40000', False),
        (0x11645a, 5, 'rax', 'mov byte ptr [rcx+rax+0x5a], 32', '', True),
    ):
        writer = emit(f'air_hits_record_{site:x}', original+'\n'+saved(f'''
            mov r10, qword ptr {mem(scope)}
            test r10, r10
            je done
            cmp rcx, 8
            jae done
            cmp {owner}, qword ptr {mem(scope+8)}
            jne done
            {f'lea rdx, {mem(0x12cf988)}' if guard else f'mov rdx, qword ptr {mem(0x12cf9a0)}; add rdx, 8'}
            cmp rsi, rdx
            jne done
            {'mov edx, 32' if guard else 'movzx edx, al'}
            add dx, word ptr {mem(scope+16)}
            mov word ptr [r10+rcx*2], dx
        done:
        ''')+f'\n{tail}\njmp {site+size:#x}')
        jump(site, size, writer, 'Air Thrust: retain native hit/guard delay in projectile history')

    return reset, dict(ledger_rva=ledger, scope_rva=scope, size=0x1100,
                       effect_stride=256, projectile_stride=16, targets=8,
                       max_projectiles=10, option_flag=29)
