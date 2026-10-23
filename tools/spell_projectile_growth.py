"""Extend audited native VFX loops, with bounded storage per effect instance."""


def emit_small_projectile_growth(emit, mem, jump, state, data, usage, preserve):
    extra=emit('mastery_extra_projectiles',f'''
        xor eax, eax
        cmp byte ptr {mem(data+0x1a0c)}, 0
        je done
        mov r10, qword ptr {mem(state)}
        test r10, r10
        je done
        cmp word ptr [r10+8], dx
        jne done
        mov r11, qword ptr [rcx]
        test r11, r11
        je done
        cmp qword ptr [r10], r11
        jne done
        cmp byte ptr [r11+0x51], 0
        jne done
        movzx edx, byte ptr [r11+0x4f]
        sub edx, 2
        cmp edx, 1
        ja done
        add edx, 2
        shl edx, 8
        movzx r9d, word ptr [r10+8]
        add edx, r9d
        lea r11, {mem(usage['preferences']['live_rva'])}
        bt dword ptr [r11], edx
        jc done
        movzx eax, word ptr [r10+10]
        mov r9d, 999
        cmp eax, r9d
        cmova eax, r9d
        imul eax, r8d
        xor edx, edx
        div r9d
    done:
        ret
    ''')
    for name,site,length,native,continuation,count,arte in (
        ('fireball',0xc9ba3,5,'cmp word ptr [rbx+0x38], 0',0xc9ba8,'ebp',75),
        ('ice_needles',0xce252,7,'mov rax, qword ptr [rbx+8]; xor r10d, r10d',0xce259,'edi',82),
    ):
        code=emit('mastery_'+name+'_count',preserve(f'''
            sub rsp, 0x20
            mov rcx, rbx
            mov edx, {arte}
            mov r8d, 3
            call {extra:#x}
            add {count}, eax
            add rsp, 0x20
        ''')+f'{native}; jmp {continuation:#x}')
        jump(site,length,code,'Spell EXP: '+name+' spawns up to three extra native projectiles')
    return extra


def emit_freeze_lancer_growth(emit, jump, extra):
    # The native callback emits sixteen independent VFX/collision objects at
    # t=0,4,...60. Insert at most six between these emissions (2,6,...22),
    # without extending the spell, reusing a sprite, or overrunning an array.
    body=emit('mastery_freeze_lancer_emission', f'''
        test eax, eax
        je native_emit
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        sub rsp, 0x20
        mov rcx, rdi
        mov edx, 83
        mov r8d, 6
        call {extra:#x}
        movzx ecx, word ptr [rdi+0x38]
        mov edx, ecx
        and edx, 3
        cmp edx, 2
        jne skip
        shr ecx, 2
        cmp ecx, eax
        setb al
        movzx eax, al
        jmp restore
    skip:
        xor eax, eax
    restore:
        add rsp, 0x20
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        test eax, eax
        je 0x932f7
    native_emit:
        jmp 0x931c9
    ''')
    jump(0x931c1,8,body,'Freeze Lancer: up to six extra native lances between the original emissions')
    return body


def emit_wind_blade_growth(emit, jump, extra):
    # The native spell emits its second pair of blade layers at t12 and
    # strikes at t32. Three extra blades can finish within its t88 lifetime:
    # emission t24/40/56, impact twenty ticks later. Each emission executes
    # the existing two-layer VFX construction; it is not an invisible hit.
    for name,site,size,native_tick,ticks,yes,no in (
        ('vfx',0xca2c5,6,12,(24,40,56),0xca2cb,0xca329),
        ('impact',0xca333,10,32,(44,60,76),0xca33d,0xca3f8),
    ):
        checks='\n'.join(f'cmp eax, {i+1}; jb absent; cmp word ptr [rbx+0x38], {t}; je found' for i,t in enumerate(ticks))
        target=emit('mastery_wind_blade_'+name,f'''
            cmp ax, {native_tick}
            je {yes:#x}
            push rax
            push rcx
            push rdx
            push r8
            push r9
            push r10
            push r11
            sub rsp, 0x28
            mov rcx, rbx
            mov edx, 72
            mov r8d, 3
            call {extra:#x}
            {checks}
        absent:
            add rsp, 0x28
            pop r11
            pop r10
            pop r9
            pop r8
            pop rdx
            pop rcx
            pop rax
            jmp {no:#x}
        found:
            add rsp, 0x28
            pop r11
            pop r10
            pop r9
            pop r8
            pop rdx
            pop rcx
            pop rax
            jmp {yes:#x}
        ''')
        jump(site,size,target,'Wind Blade: three extra visible blades, with their corresponding impacts ('+name+')')
    return dict(arte=72,additional_cap=3,emission_ticks=[24,40,56],impact_ticks=[44,60,76])


def emit_meteor_growth(emit, mem, jump, state, extra, preserve):
    arrays=state+0x2000
    # Eight original meteors plus six insertions use fourteen pointer slots.
    # Native storage has eight slots, so each effect gets a private 128 bytes.
    init=emit('mastery_meteor_storage',preserve(f'''
        mov rax, rbp
        lea r10, {mem(0x12cfca0)}
        sub rax, r10
        xor edx, edx
        mov ecx, 0x120
        div rcx
        shl eax, 7
        lea rsi, {mem(arrays)}
        add rsi, rax
        cmp word ptr [rbp+0x38], 0
        jne done
        xor eax, eax
        mov ecx, 16
    clear:
        mov qword ptr [rsi+rcx*8-8], rax
        dec ecx
        jne clear
        sub rsp, 0x20
        mov rcx, rbp
        mov edx, 93
        mov r8d, 6
        call {extra:#x}
        add eax, 8
        mov dword ptr [rsi+0x78], eax
        add rsp, 0x20
    done:
    ''')+'jmp 0x9cb94')
    jump(0x9cb8d,7,init,'Meteor Swarm: private bounded storage for fourteen meteors')
    emission=emit('mastery_meteor_emission','''
        cmp r8d, eax
        je 0x9cbca
        add eax, 12
        cmp r8d, eax
        jne 0x9cc4e
        cmp r8d, 144
        jae 0x9cc4e
        push rax
        lea eax, [ebx+8]
        cmp eax, dword ptr [rsi+0x78]
        pop rax
        jae 0x9cc4e
        add ebx, 8
        jmp 0x9cbd0
    ''')
    jump(0x9cbc1,9,emission,'Meteor Swarm: up to six additional native meteors between original launches')
    limit=emit('mastery_meteor_update_limit','mov r13d, dword ptr [rsi+0x78]; lea r13, [rsi+r13*8]; jmp 0x9cc55')
    jump(0x9cc4e,7,limit,'Meteor Swarm: update every allocated meteor without reading adjacent memory')
    return dict(arte=93,native_count=8,additional_cap=6,arrays_rva=arrays,stride=128,slots=16)


def emit_shooting_star_growth(emit, mem, jump, state, extra, preserve):
    markers=state+0x4050
    address=f'''
        mov rax, rdi
        lea r10, {mem(0x12cfca0)}
        sub rax, r10
        xor edx, edx
        mov ecx, 0x120
        div rcx
        lea r10, {mem(markers)}
        add r10, rax
    '''
    pushes='pushfq; push rax; push rcx; push rdx; push r8; push r9; push r10; push r11'
    pops='pop r11; pop r10; pop r9; pop r8; pop rdx; pop rcx; pop rax; popfq'
    begin=emit('mastery_shooting_star_emission',f'''
        {pushes}
        {address}
        mov byte ptr [r10], 0
        movzx eax, word ptr [rdi+0x38]
        sub eax, 44
        jb absent
        test eax, 7
        jne absent
        push r10
        sub rsp, 0x28
        mov rcx, rdi
        mov edx, 94
        mov r8d, 6
        call {extra:#x}
        add rsp, 0x28
        pop r10
        movzx ecx, word ptr [rdi+0x38]
        sub ecx, 44
        shr ecx, 3
        cmp ecx, eax
        jae absent
        mov byte ptr [r10], 1
        and ecx, 1
        lea ebx, [ecx*2-1]
        {pops}
        mov qword ptr [rsp+0x40], r14
        jmp 0xbce45
    absent:
        {pops}
        test eax, eax
        je 0xbce3b
        jmp 0xbcec4
    ''')
    jump(0xbce35,6,begin,'Shooting Star: six additional single impacts between native star showers')
    sprite=emit('mastery_shooting_star_sprite',preserve(address+f'''
        cmp byte ptr [r10], 0
        je done
        sub rsp, 0x20
        mov rcx, rdi
        lea rdx, {mem(0x58a650)}
        call 0x114e60
        test rax, rax
        je allocated
        mov rdx, qword ptr {mem(0x11ce620)}
        mov qword ptr [rax], rdx
    allocated:
        add rsp, 0x20
    done:
    ''')+f'mov r8, qword ptr [rdi+0x78]; lea rdx, {mem(0x11ce620)}; jmp 0xbce9c')
    jump(0xbce91,11,sprite,'Shooting Star: add a native star sprite at each new impact')
    end=emit('mastery_shooting_star_single',f'''
        {pushes}
        {address}
        cmp byte ptr [r10], 0
        je native
        mov byte ptr [r10], 0
        {pops}
        jmp 0xbcebf
    native:
        {pops}
        cmp ebx, 2
        jl 0xbce50
        jmp 0xbcebf
    ''')
    jump(0xbceba,5,end,'Shooting Star: one collision per additional star, retaining the two native shower regions')
    return dict(arte=94,additional_cap=6,emission_ticks=[44,52,60,68,76,84])


def emit_dark_force_growth(emit, mem, state, extra, preserve):
    scripts=state+0x5000
    prepare=emit('mastery_dark_force_script',preserve(f'''
        push rbx
        push rsi
        push rdi
        sub rsp, 0x20
        mov rbx, rcx
        cmp word ptr [rbx+0x38], 0
        jne done
        lea rax, {mem(0x5785d0)}
        cmp qword ptr [rbx+0x10], rax
        jne done
        mov edx, 91
        mov r8d, 6
        call {extra:#x}
        test eax, eax
        je done
        mov edi, eax
        mov rax, rbx
        lea rcx, {mem(0x12cfca0)}
        sub rax, rcx
        xor edx, edx
        mov ecx, 0x120
        div rcx
        shl eax, 9
        lea rsi, {mem(scripts)}
        add rsi, rax
        lea r10, {mem(0x5785d0)}
        xor ecx, ecx
    copy:
        mov rax, qword ptr [r10+rcx*8]
        mov qword ptr [rsi+rcx*8], rax
        inc ecx
        cmp ecx, 31
        jb copy
        # These four repetitions animate the same five orbs through their
        # launch, travelling and explosion stages. Grow every stage together.
        add word ptr [rsi+52], di
        add word ptr [rsi+76], di
        add word ptr [rsi+100], di
        add word ptr [rsi+148], di
        xor r9d, r9d
    impacts:
        imul eax, r9d, 6
        add eax, 122
        mov r11, 0x00010000fff90000
        or rax, r11
        mov qword ptr [rsi+rcx*8], rax
        inc ecx
        inc r9d
        cmp r9d, edi
        jb impacts
        # Let all added orbs explode before the native fade and completion.
        imul edi, edi, 6
        mov r9d, 31
    tail:
        mov rax, qword ptr [r10+r9*8]
        add ax, di
        mov qword ptr [rsi+rcx*8], rax
        inc ecx
        inc r9d
        cmp r9d, 34
        jb tail
        mov qword ptr [rbx+0x10], rsi
    done:
        add rsp, 0x20
        pop rdi
        pop rsi
        pop rbx
    ''')+'ret')
    return prepare,dict(arte=91,native_count=5,additional_cap=6,scripts_rva=scripts,stride=512,slots=16)


def emit_ray_growth(emit, mem, jump, state, extra, preserve):
    records=state+0x4010
    address=f'''
        mov rax, rsi
        lea r10, {mem(0x12cfca0)}
        sub rax, r10
        xor edx, edx
        mov ecx, 0x120
        div rcx
        lea r10, {mem(records)}
        lea r10, [r10+rax*4]
    '''
    init=emit('mastery_ray_count',preserve(address+f'''
        cmp word ptr [rsi+0x38], 0
        jne done
        mov dword ptr [r10], 0x00ffff00
        push r10
        sub rsp, 0x28
        mov rcx, rsi
        mov edx, 89
        mov r8d, 6
        call {extra:#x}
        add rsp, 0x28
        pop r10
        mov byte ptr [r10], al
    done:
    ''')+'mov r15d, 0xa0; jmp 0x947fb')
    jump(0x947f5,6,init,'Ray: freeze the extra-beam count for this effect')
    pushes='pushfq; push rax; push rcx; push rdx; push r8; push r9; push r10; push r11'
    pops='pop r11; pop r10; pop r9; pop r8; pop rdx; pop rcx; pop rax; popfq'
    emission=emit('mastery_ray_extra_beam',f'''
        {pushes}
        {address}
        cmp byte ptr [r10+3], 0
        je first_pass
        sub word ptr [rsi+0x38], 2
        mov byte ptr [r10+3], 0
        jmp done
    first_pass:
        movzx eax, word ptr [rsi+0x38]
        cmp ax, word ptr [r10+1]
        je done
        sub eax, 42
        jb done
        test eax, 7
        jne done
        shr eax, 3
        movzx ecx, byte ptr [r10]
        cmp eax, ecx
        jae done
        mov ax, word ptr [rsi+0x38]
        mov word ptr [r10+1], ax
        mov byte ptr [r10+3], 1
        # Native t%4==0 beams reach the battle plane and carry a collision.
        # The original beam at this tick has already been drawn. Use its
        # next phase for one extra beam, then restore the effect's clock.
        add word ptr [rsi+0x38], 2
        {pops}
        lea rbx, [rsi+0x38]
        mov r15d, 0xa0
        jmp 0x9498f
    done:
        {pops}
        mov r8, qword ptr {mem(0x863860)}
        jmp 0x94d0c
    ''')
    jump(0x94d05,7,emission,'Ray: up to six extra visible beams with native impact handling')
    return dict(arte=89,additional_cap=6,emission_ticks=[42,50,58,66,74,82],records_rva=records)


def emit_aqua_edge_growth(emit, mem, jump, state, extra):
    counts=state+0x4000
    native=emit('mastery_aqua_edge_native','push rdi; sub rsp, 0x20; jmp 0xcefa6')
    # Aqua Edge builds its projectile and collision from the effect's phase on
    # every frame. Draw extra independent phases through the SAME native path.
    # Positive phase offsets let all projectiles finish within the native life;
    # no duplicate script events, cast counters or owner-lock mutations.
    wrapper=emit('mastery_aqua_edge_projectiles',f'''
        cmp qword ptr [rcx+0x10], 0
        je {native:#x}
        push rbx
        push rsi
        push rdi
        push r12
        push r13
        sub rsp, 0x20
        mov rsi, rcx
        movzx edi, word ptr [rcx+0x38]
        mov rax, rcx
        lea r10, {mem(0x12cfca0)}
        sub rax, r10
        xor edx, edx
        mov ecx, 0x120
        div rcx
        lea r12, {mem(counts)}
        add r12, rax
        test edi, edi
        jne count_ready
        mov rcx, rsi
        mov edx, 70
        mov r8d, 3
        call {extra:#x}
        mov byte ptr [r12], al
    count_ready:
        movzx ebx, byte ptr [r12]
        xor r13d, r13d
    projectile:
        lea eax, [rdi+r13*8]
        cmp eax, 112
        ja done
        mov word ptr [rsi+0x38], ax
        mov rcx, rsi
        call {native:#x}
        inc r13d
        cmp r13d, ebx
        jbe projectile
    done:
        mov word ptr [rsi+0x38], di
        add rsp, 0x20
        pop r13
        pop r12
        pop rdi
        pop rsi
        pop rbx
        ret
    ''')
    jump(0xcefa0,6,wrapper,'Aqua Edge: up to four visible native projectiles with separate flight phases and collisions')
    return dict(arte=70,native_count=1,additional_cap=3,counts_rva=counts,phase_stride=8,lifetime=112)


def emit_holy_lance_growth(emit, mem, jump, state, extra, preserve):
    arrays=state+0x3000
    address=f'''
        mov rax, r14
        lea r10, {mem(0x12cfca0)}
        sub rax, r10
        xor edx, edx
        mov ecx, 0x120
        div rcx
        shl eax, 8
        lea r10, {mem(arrays)}
        add rax, r10
    '''
    init=emit('mastery_holy_lance_storage',preserve(address+f'''
        mov rbp, rax
        cmp word ptr [r14+0x38], 0
        jne done
        xor eax, eax
        mov ecx, 32
    clear:
        mov qword ptr [rbp+rcx*8-8], rax
        dec ecx
        jne clear
        sub rsp, 0x20
        mov rcx, r14
        mov edx, 90
        mov r8d, 3
        call {extra:#x}
        lea eax, [rax*2+16]
        mov dword ptr [rbp+0xf8], eax
        add rsp, 0x20
    done:
    ''')+'jmp 0x9bad4')
    jump(0x9bacd,7,init,'Holy Lance: private storage for eleven two-layer lances')
    # Keep all eight original launches, including their global-clock phase.
    # Insert at the opposite phase in the first three eight-tick windows.
    emission=emit('mastery_holy_lance_emission',f'''
        test byte ptr {mem(0x12ceb40)}, 7
        je 0x9bb00
        push rax
        push rdx
        mov eax, dword ptr {mem(0x12ceb40)}
        and eax, 7
        cmp eax, 4
        jne absent
        lea eax, [ecx-16]
        shr eax, 3
        add eax, 8
        lea edx, [eax*2]
        cmp edx, dword ptr [rbp+0xf8]
        jae absent
        # Continue after native index division, preserving the same VFX,
        # trajectory, collision and impact code for the extra lance.
        pop rdx
        add rsp, 8
        lea rcx, [r15+0x6a]
        jmp 0x9bb10
    absent:
        pop rdx
        pop rax
        jmp 0x9bc71
    ''')
    jump(0x9baf3,7,emission,'Holy Lance: insert three complete native lances between original launches')
    limit=emit('mastery_holy_lance_update_limit',f'''
        push rax
        push rcx
        push rdx
        push r10
        {address}
        cmp r12d, dword ptr [rax+0xf8]
        pop r10
        pop rdx
        pop rcx
        pop rax
        jl 0x9bc93
        jmp 0x9bf71
    ''')
    jump(0x9bf67,10,limit,'Holy Lance: update every native and added layer within its private array')
    cleanup=emit('mastery_holy_lance_cleanup',preserve(address+'''
        mov r10, rax
        mov ecx, dword ptr [r10+0xf8]
        mov word ptr [r14+0x38], 126
    loop:
        mov rax, qword ptr [r10+rcx*8-8]
        test rax, rax
        je next
        dec word ptr [rax+0x5a]
        add word ptr [rax+0x5c], -64
    next:
        dec ecx
        jne loop
    ''')+'jmp 0x9c26d')
    jump(0x9c116,7,cleanup,'Holy Lance: retire all allocated layers, including extra lances')
    return dict(arte=90,native_count=8,additional_cap=3,arrays_rva=arrays,stride=256,slots=16)


def emit_air_thrust_growth(emit, mem, jump, state, effects, data, usage):
    from air_thrust_hits import emit_air_hits
    reset_hits, hits = emit_air_hits(emit, mem, jump, state+0x7000, data)
    # Four original position records at 863830 and angles at 863850 are shared
    # globals. Ten records need separate storage; never overwrite adjacent data.
    # Each effect gets 128 bytes: ten positions (80), angles (20), count (+112).
    arrays=state+0x1000
    init=emit('mastery_air_projectile_storage', f'''
        pushfq
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        mov rax, rsi
        lea r10, {mem(0x12cfca0)}
        sub rax, r10
        xor edx, edx
        mov ecx, 0x120
        div rcx
        # RSI is a native effect-pool entry at this fixed callback site.
        mov r8d, eax
        shl eax, 7
        lea r14, {mem(arrays)}
        add r14, rax
        # The count is frozen at the first VFX update. Changing an option
        # during flight cannot expose position records never initialized.
        cmp word ptr [rsi+0x38], 0
        jne done
        sub rsp, 0x20
        call {reset_hits:#x}
        add rsp, 0x20
        mov dword ptr [r14+0x70], 4
        cmp byte ptr {mem(data+0x1a0c)}, 0
        je done
        shl r8d, 4
        lea r10, {mem(effects)}
        add r10, r8
        cmp word ptr [r10+8], 73
        jne done
        mov rax, qword ptr [rsi]
        cmp qword ptr [r10], rax
        jne done
        test rax, rax
        je done
        cmp byte ptr [rax+0x51], 0
        jne done
        movzx ecx, byte ptr [rax+0x4f]
        cmp ecx, 3
        ja done
        cmp ecx, 2
        jb done
        shl ecx, 8
        add ecx, 73
        lea r11, {mem(usage['preferences']['live_rva'])}
        bt dword ptr [r11], ecx
        jc done
        movzx eax, word ptr [r10+10]
        mov ecx, 999
        cmp eax, ecx
        cmova eax, ecx
        imul eax, eax, 6
        xor edx, edx
        div ecx
        add dword ptr [r14+0x70], eax
    done:
        add r14, 2
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
        popfq
        jmp 0x9423b
    ''')
    jump(0x94234,7,init,'Air Thrust: ten bounded VFX records per effect instead of shared globals')
    angles=emit('mastery_air_projectile_angles','lea r15, [r14+0x4e]; jmp 0x94246')
    jump(0x9423f,7,angles,'Air Thrust: private angles for every visible projectile')
    end=emit('mastery_air_projectile_count',f'''
        push rax
        push rcx
        push rdx
        mov rax, rsi
        lea rcx, {mem(0x12cfca0)}
        sub rax, rcx
        xor edx, edx
        mov ecx, 0x120
        div rcx
        shl eax, 7
        lea rcx, {mem(arrays)}
        cmp ebp, dword ptr [rcx+rax+0x70]
        pop rdx
        pop rcx
        pop rax
        jl 0x94251
        jmp 0x9451e
    ''')
    jump(0x94515,9,end,'Air Thrust: four native projectiles plus up to six at 999 casts')
    return dict(arte=73,native_count=4,additional_cap=6,max_casts=999,
                arrays_rva=arrays,stride=128,slots=16,independent_hits=hits)
