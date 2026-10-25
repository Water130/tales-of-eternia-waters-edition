"""Optional Aurora controls and finite Reid mystic artes, original build 25190541.

Native usage, target geometry, story flags and cinematic timing remain.
Final Dragon Fang/Cyclone Seal accept held Arte, charge on successful dispatch,
and use Slash-based damage. Burning Phoenix keeps its previous rules.
The three counters are session battle state, never part of a game save.
"""
FLAG = 34
# 0x1ae0 belongs to settings_help's scrolling state. Battle quotas must not
# share it: opening a description used to overwrite all three counters.
COUNT_OFFSET = 0x1b80
MYSTIC_TP_COST = 100
# Descriptor RVA, native mode, native parameter, replacement percentage.
# These are impact strengths, not fixed final damage. The normal Slash,
# defense, variance, critical and elemental calculations still apply.
MYSTIC_IMPACTS = (
    (0x584a60, 3, 2000, 350),
    (0x584a76, 3, 500, 75),
    (0x584a8c, 3, 7650, 600),
    (0x584aa2, 3, 300, 50),
    (0x585410, 3, 2000, 200),
    (0x585426, 2, 10000, 800),
)


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
        cmp eax, 1
        je phoenix
        cmp byte ptr [r9+rax], 1
        pop r9
        jae denied
        cmp byte ptr {mem(0x12d0ef7)}, 6
        jne denied
        cmp word ptr {mem(0x12d0eaa)}, 0
        jne denied
        cmp word ptr [rcx+0x3c], 1
        jne denied
        cmp dword ptr [rcx+0x2c], 0
        jle denied
        cmp byte ptr [rcx+0x6d], dl
        jne denied
        movzx eax, byte ptr [rcx+0x57]
        dec eax
        cmp eax, 1
        ja denied
        cmp word ptr [rcx+0x34], {MYSTIC_TP_COST}
        jl denied
        mov rax, qword ptr [rcx+0xf0]
        test rax, rax
        je denied
        test byte ptr [rax], 0x40
        je denied
        mov eax, 1
        ret
    phoenix:
        cmp byte ptr [r9+rax], 3
        pop r9
        jb native
    denied:
        xor eax, eax
        ret
    native:
        mov qword ptr [rsp+8], rbx
        jmp 0x114025
    ''')
    jump(0x114020,5,admission,'Reid mystics: held Arte, one start per technique and 100 TP; Phoenix retains previous rules')

    # These are the initial successful dispatch sites, not the resource-loader
    # continuation. Count even while OFF to prevent toggling from resetting a
    # battle allowance. Failed allocation consumes no charge. Other actors do
    # not consume Reid's allowance (notably enemy Rising Phoenix).
    dispatch_assembly=f'''
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
        jmp mystic
    phoenix:
        mov esi, 1
        lea rdx, {mem(counters)}
        cmp byte ptr [rdx+rsi], 3
        jae done
        inc byte ptr [rdx+rsi]
        jmp done
    dragon:
        xor esi, esi
    mystic:
        cmp byte ptr {mem(flag)}, 0
        je count
        sub word ptr [rbx+0x34], {MYSTIC_TP_COST}
        inc byte ptr [rbx+0x6e]
        mov rcx, rbx
        call 0x8d520
        xor eax, eax
    count:
        lea rdx, {mem(counters)}
        cmp byte ptr [rdx+rsi], 1
        jae done
        inc byte ptr [rdx+rsi]
    done:
        add rsp, 0x28
        pop rsi
        pop rbx
        ret
    '''
    dispatch=emit('reid_hi_ougi_dispatch',dispatch_assembly)
    for site in (0xcbd53,0xce0e6,0xcf807):
        entry=emit(f'reid_hi_ougi_start_{site:x}',f'call {dispatch:#x}; jmp {site+5:#x}')
        jump(site,5,entry,'Count actual Reid hi-ougi start only once after native allocation succeeds')
    # Encounter 0xe6 can turn the attempted Dragon Fang back on Reid. The
    # cinematic is owned by the enemy but it is still Reid's paid attempt.
    mirror=emit('reid_hi_ougi_mirror_dispatch',dispatch_assembly.replace(
        'mov rbx, rcx','mov rbx, qword ptr [rcx]'))
    entry=emit('reid_hi_ougi_mirror_start',f'call {mirror:#x}; jmp 0xce020')
    jump(0xce01b,5,entry,'Count and pay Reid Dragon Fang when the native encounter reflects it')
    reset=emit('reid_specials_battle_reset',f'''
        mov dword ptr {mem(counters)}, 0
        mov dword ptr {mem(0x8c92c4)}, 0x78
        jmp 0x11c700
    ''')
    jump(0x11c6f6,10,reset,'Reset Reid hi-ougi allowances unconditionally at battle initialization')

    # Scope by the immutable native impact pointer, not the current action:
    # late cinematic hits may arrive after the actor has changed action.
    # No global descriptor changes, so OFF and enemy versions stay native.
    match=[]; strengths=[]
    for i,(descriptor,mode,power,percent) in enumerate(MYSTIC_IMPACTS):
        match.append(f'lea rax, {mem(descriptor+8)}; cmp r12, rax; je hit_{i}')
        strengths.append(f'hit_{i}: mov ecx, {percent}; jmp scale')
    damage=emit('reid_mystic_slash_damage',f'''
        cmp byte ptr {mem(flag)}, 0
        je native
        {chr(10).join(match)}
        jmp native
        {chr(10).join(strengths)}
    scale:
        cmp byte ptr [rbp+0x51], 0
        jne native
        cmp byte ptr [rbp+0x4f], 0
        jne native
        movsxd rax, esi
        imul rax, rcx
        cqo
        mov ecx, 100
        idiv rcx
        mov esi, eax
        jmp 0x8ed32
    native:
        movzx ecx, byte ptr [r12+2]
        jmp 0x8ecc2
    ''')
    jump(0x8ecbc,6,damage,'Final Dragon Fang and Cyclone Seal: native Slash-based impact scaling instead of fixed damage')
    return dict(flag=FLAG,flag_rva=flag,counters_rva=counters,limits=[1,3,1],
                counter_arte_ids=[19,20,21],counter_effect_ids=[40,39,41],
                held_arte_ids=[19,21],held_input_mask=0x40,tp_cost=MYSTIC_TP_COST,
                payment='additional TP, once at successful cinematic allocation',
                impact_scaling=[dict(descriptor_rva=d,native_mode=m,native_power=p,
                                     slash_percent=s) for d,m,p,s in MYSTIC_IMPACTS],
                aurora_hp_percent=25,native_aurora_hp_percent=12.5,
                aurora_input_mask=0x60,native_aurora_input_mask=0xe0,
                aurora_sword='native Attack press retained',reset=reset)
