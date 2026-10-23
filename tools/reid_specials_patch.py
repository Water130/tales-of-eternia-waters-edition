"""Optional Aurora controls and finite Reid mystic artes, original build 25190541.

Only HP eligibility and requested inputs change. Native arte usage, timing,
target geometry, story flags, TP payment and cinematic dispatch remain.
The three counters are session battle state, never part of a game save.
"""
FLAG = 34
COUNT_OFFSET = 0x1ae0


def emit_reid_specials(emit, mem, jump, data):
    flag=data+0x1a62
    counters=data+COUNT_OFFSET
    hp=emit('reid_aurora_hp',f'''
        cmp byte ptr {mem(flag)}, 0
        je native
        cmp byte ptr [rbx+0x51], 0
        jne native
        cdq
        and edx, 3
        add eax, edx
        sar eax, 2
        jmp 0x111f9e
    native:
        cdq
        and edx, 7
        add eax, edx
        sar eax, 3
        jmp 0x111f9e
    ''')
    jump(0x111f95,9,hp,'Optional Aurora Wall: 25 percent HP instead of native 12.5 percent')
    # Aurora Wall, the Dark Aurora counter, and Aurora Wave against Eternal
    # Finality. Aurora Sword already requires Attack alone: leave it native.
    for name,site,size,register,compare in (
            ('wall',0x11201d,9,'ecx','cl'),
            ('dark_counter',0xabf02,7,'eax','al'),
            ('wave',0xbddc5,6,'cl','cl')):
        entry=emit('reid_aurora_'+name,f'''
            cmp byte ptr {mem(flag)}, 0
            je native
            and {register}, 0x60
            cmp {compare}, 0x60
            jmp {site+size:#x}
        native:
            and {register}, 0xe0
            cmp {compare}, 0xe0
            jmp {site+size:#x}
        ''')
        jump(site,size,entry,'Optional Aurora '+name+': mapped Attack + Arte; Guard no longer required')

    # Final Dragon Fang checks EVERY live nearby enemy's HP against
    # 2000 + Omega Demon Chaos uses. Keep the proximity and usage checks.
    final=emit('reid_final_dragon_hp',f'''
        cmp byte ptr {mem(flag)}, 0
        je native
        cmp byte ptr [rdi+0x51], 0
        jne native
        cmp byte ptr [rdi+0x4f], 0
        jne native
        jmp 0xcdf44
    native:
        movzx eax, word ptr [r9+0xc4e]
        jmp 0xcdf37
    ''')
    jump(0xcdf2f,8,final,'Optional Final Dragon Fang: remove enemy HP ceiling, retain range and usage')
    infinity=emit('reid_infinity_hp',f'''
        cmp byte ptr {mem(flag)}, 0
        je native
        push rax
        mov rax, qword ptr [rdi]
        cmp byte ptr [rax+0x51], 0
        jne restore_native
        cmp byte ptr [rax+0x4f], 0
        jne restore_native
        pop rax
        jmp 0xcf2c0
    restore_native:
        pop rax
    native:
        cmp dword ptr [rcx+0x2c], 20000
        jmp 0xcf2be
    ''')
    jump(0xcf2b7,7,infinity,'Optional Infinity: remove target HP ceiling, retain target and execution rules')

    admission=emit('reid_hi_ougi_admission',f'''
        cmp byte ptr {mem(flag)}, 0
        je native
        cmp byte ptr [rcx+0x51], 0
        jne native
        cmp byte ptr [rcx+0x4f], 0
        jne native
        lea eax, [rdx-19]
        cmp eax, 2
        ja native
        push r9
        lea r9, {mem(counters)}
        cmp byte ptr [r9+rax], 3
        pop r9
        jb native
        xor eax, eax
        ret
    native:
        mov qword ptr [rsp+8], rbx
        jmp 0x114025
    ''')
    jump(0x114020,5,admission,'Optional Reid hi-ougi: three successful starts per technique before TP debit')

    # These are the initial successful dispatch sites, not the resource-loader
    # continuation. Count even while OFF to prevent toggling from resetting a
    # battle allowance. Failed allocation consumes no charge. Other actors do
    # not consume Reid's allowance (notably enemy Rising Phoenix).
    dispatch=emit('reid_hi_ougi_dispatch',f'''
        push rbx
        push rsi
        sub rsp, 0x28
        mov rbx, rcx
        mov esi, edx
        call 0x114980
        test eax, eax
        jne done
        cmp byte ptr [rbx+0x51], 0
        jne done
        cmp byte ptr [rbx+0x4f], 0
        jne done
        cmp esi, 39
        je phoenix
        cmp esi, 40
        je dragon
        cmp esi, 41
        jne done
        mov esi, 2
        jmp count
    phoenix:
        mov esi, 1
        jmp count
    dragon:
        xor esi, esi
    count:
        lea rdx, {mem(counters)}
        cmp byte ptr [rdx+rsi], 3
        jae done
        inc byte ptr [rdx+rsi]
    done:
        add rsp, 0x28
        pop rsi
        pop rbx
        ret
    ''')
    for site in (0xcbd53,0xce0e6,0xcf807):
        entry=emit(f'reid_hi_ougi_start_{site:x}',f'call {dispatch:#x}; jmp {site+5:#x}')
        jump(site,5,entry,'Count actual Reid hi-ougi start only once after native allocation succeeds')
    reset=emit('reid_specials_battle_reset',f'''
        mov dword ptr {mem(counters)}, 0
        mov dword ptr {mem(0x8c92c4)}, 0x78
        jmp 0x11c700
    ''')
    jump(0x11c6f6,10,reset,'Reset Reid hi-ougi allowances unconditionally at battle initialization')
    return dict(flag=FLAG,flag_rva=flag,counters_rva=counters,limit=3,
                counter_arte_ids=[19,20,21],counter_effect_ids=[40,39,41],
                aurora_hp_percent=25,native_aurora_hp_percent=12.5,
                aurora_input_mask=0x60,native_aurora_input_mask=0xe0,
                aurora_sword='native Attack press retained',reset=reset)
