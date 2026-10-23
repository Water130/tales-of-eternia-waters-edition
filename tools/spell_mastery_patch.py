"""Spell mastery, build 25190541; immutable per-effect/projectile provenance.

Counters already belong to ArteUsage-v1, keyed by character and native save.
Native buff lifetime/exclusivity is preserved; only recipient count changes.
Healing and summons use separate policies.
"""
SIZE = 0x8100
FLAG = 12
POOL = 0x12cfca0
PROJECTILES = 0x12cee48


def preserve(body):
    return f'''
        pushfq
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        {body}
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
        popfq
    '''


def emit_mastery(emit, mem, jump, data, state, usage, faculties=None):
    faculty_power=faculty_impact=faculty_defense=''
    if faculties:
        faculty_power=f'''
            sub rsp, 0x30; mov qword ptr [rsp+0x20], r10
            mov dword ptr [rsp+0x28], ecx
            mov rcx, r10; mov edx, esi; mov r8d, r15d
            call {faculties['power']:#x}; mov esi, eax
            test edx, edx; je no_faculty_critical
            or r15d, 2; or dword ptr [rsp+0xe8], 2
        no_faculty_critical:
            mov ecx, dword ptr [rsp+0x28]
            mov r10, qword ptr [rsp+0x20]; add rsp, 0x30
            movzx edx, word ptr [r10+8]
        '''
        faculty_impact=f'''
            sub rsp, 0x20; mov rcx, rbp; mov rdx, rdi; mov r8d, esi
            call {faculties['impact']:#x}; add rsp, 0x20
        '''
        faculty_defense=f'''
            sub rsp, 0x20; mov rcx, rdi; mov edx, esi
            movzx r8d, byte ptr [r12]; and r8d, 0x80
            call {faculties['defense']:#x}; mov esi, eax; add rsp, 0x20
        '''
    from spell_growth import emit_actor_uses, emit_cast_growth
    actor_uses = emit_actor_uses(emit, mem, data, usage)
    cast_growth = emit_cast_growth(emit, mem, jump, actor_uses, faculties)
    context = state
    effects, projectiles = state+0x100, state+0x300
    from spell_projectile_growth import emit_air_thrust_growth, emit_small_projectile_growth, emit_freeze_lancer_growth, emit_wind_blade_growth, emit_meteor_growth, emit_holy_lance_growth, emit_aqua_edge_growth, emit_ray_growth, emit_dark_force_growth, emit_shooting_star_growth
    air_growth = emit_air_thrust_growth(emit, mem, jump, state, effects, data, usage)
    extra_projectiles=emit_small_projectile_growth(emit,mem,jump,state,data,usage,preserve)
    emit_freeze_lancer_growth(emit,jump,extra_projectiles)
    wind_growth=emit_wind_blade_growth(emit,jump,extra_projectiles)
    meteor_growth=emit_meteor_growth(emit,mem,jump,state,extra_projectiles,preserve)
    holy_growth=emit_holy_lance_growth(emit,mem,jump,state,extra_projectiles,preserve)
    aqua_growth=emit_aqua_edge_growth(emit,mem,jump,state,extra_projectiles)
    ray_growth=emit_ray_growth(emit,mem,jump,state,extra_projectiles,preserve)
    dark_prepare,dark_growth=emit_dark_force_growth(emit,mem,state,extra_projectiles,preserve)
    star_growth=emit_shooting_star_growth(emit,mem,jump,state,extra_projectiles,preserve)
    from spell_recovery_growth import emit_recovery
    recovery, roots = emit_recovery(emit, mem, jump, state, data, usage, preserve, faculties)
    from spell_area_growth import emit_area
    area_growth = emit_area(emit, mem, jump, state, data, usage, preserve)
    from summon_growth import emit_summon_damage, emit_summon_capture, MAX_BONUS
    summon_damage = emit_summon_damage(emit, mem, data)
    # Record: owner Q, arte H, completed uses H, percentage D (16 bytes).
    # Allocation happens before the completed-cast counter increments.
    capture = emit('mastery_effect_capture', preserve(f'''
        mov rax, r14
        lea r10, {mem(POOL)}
        sub rax, r10
        cmp rax, 0x1200
        jae done
        xor edx, edx
        mov ecx, 0x120
        div rcx
        test edx, edx
        jne done
        shl eax, 4
        lea r11, {mem(effects)}
        add r11, rax
        mov qword ptr [r11], 0
        mov qword ptr [r11+8], 0
        test r12, r12
        je done
        cmp byte ptr [r12+0x51], 0
        jne done
        movzx ecx, byte ptr [r12+0x4f]
        cmp ecx, 2
        je mage
        cmp ecx, 3
        jne done
    mage:
        # Track the latest root even for healing/summons, so an older spell
        # cannot clear the casting lock of a newer action with the same ID.
        mov rax, qword ptr [rsp+0x98]
        lea r10, {mem(0xd554e)}
        cmp rax, r10
        jne not_root_owner
        lea r10, {mem(roots)}
        mov qword ptr [r10+rcx*8], r14
    not_root_owner:
        lea r10, {mem(0x115cef)}
        cmp rax, r10
        jne owner_done
        lea rax, [r15-0x3a]
        lea r10, {mem(roots)}
        cmp qword ptr [r10+rcx*8], rax
        jne owner_done
        mov qword ptr [r10+rcx*8], r14
    owner_done:
        mov r10, qword ptr {mem(context)}
        test r10, r10
        jne inherit
        # The native large-effect loading continuation reallocates the effect
        # outside its callbacks, immediately before releasing the old slot.
        mov rax, qword ptr [rsp+0x98]
        lea r10, {mem(0x115cef)}
        cmp rax, r10
        jne root
        lea rax, [r15-0x3a]
        lea r10, {mem(POOL)}
        sub rax, r10
        cmp rax, 0x1200
        jae done
        xor edx, edx
        mov r10d, 0x120
        div r10
        test edx, edx
        jne done
        shl eax, 4
        lea r10, {mem(effects)}
        add r10, rax
    inherit:
        cmp qword ptr [r10], r12
        jne root
        # A summon allocation is a new action, not an ordinary spell child.
        # Do not carry a preceding offensive spell's EXP into that root.
        lea eax, [rbp-26]
        cmp eax, 11
        ja inherit_record
        lea eax, [rbp+17]
        cmp ax, word ptr [r10+8]
        jne root
    inherit_record:
        # A child effect retains its parent's arte and mastery, not the
        # caster's next action. No extra usage increment for this effect.
        mov rax, qword ptr [r10+8]
        mov qword ptr [r11], r12
        mov qword ptr [r11+8], rax
        jmp done
    root:
        # Only the successful-cast dispatcher can create a new root record.
        # Other allocations must inherit a scoped parent, never infer a spell
        # from a caster who has since begun a different action.
        mov rax, qword ptr [rsp+0x98]
        lea r10, {mem(0xd554e)}
        cmp rax, r10
        jne done
        movzx edx, byte ptr [r12+0x6d]
        cmp edx, 43
        jb done
        cmp edx, 52
        jbe eligible
        cmp edx, 54
        jb done
        cmp edx, 66
        jbe eligible
        cmp edx, 70
        jb done
        cmp edx, 101
        jbe offensive
        cmp edx, 112
        je offensive
        cmp edx, 113
        jne done
    offensive:
    eligible:
        lea r10, {mem(0x551780)}
        cmp bpl, byte ptr [r10+rdx*8]
        jne done
        cmp byte ptr [r10+rdx*8+1], 0
        je done
        cmp edx, 52
        jbe summon
        mov word ptr [r11+8], dx
        sub rsp, 0x30
        mov qword ptr [rsp+0x20], r11
        call {usage['catchup']['next_rva']:#x}
        mov r11, qword ptr [rsp+0x20]
        add rsp, 0x30
        mov edx, 9999
        cmp eax, edx
        cmova eax, edx
        mov word ptr [r11+10], ax
        cmp word ptr [r11+8], 66
        jbe store_owner
        xor edx, edx
        mov ecx, 20
        div ecx
        mov edx, 25
        cmp eax, edx
        cmova eax, edx
        mov dword ptr [r11+12], eax
        jmp store_owner
        {emit_summon_capture(mem)}
    store_owner:
        mov qword ptr [r11], r12
        {f'sub rsp, 0x30; mov rcx, r11; call {faculties["tag"]:#x}; add rsp, 0x30' if faculties else ''}
    done:
    ''') + '''
        mov byte ptr [r14+0x36], bpl
        movzx eax, byte ptr [r12+0x53]
        jmp 0x114a4f
    ''')
    jump(0x114a45, 10, capture, 'Mastery: freeze caster, spell and usage on effect allocation')

    # Called only from the small-effect update, before the native buff callback.
    # Reproduce its four state writes and its native 0x18 aura allocation for
    # secondary recipients. No new timer, effect recursion or resource debit.
    share = emit('mastery_buff_share', preserve(f'''
        push rbx
        push rsi
        push rdi
        push rbp
        cmp byte ptr {mem(data+0x1a00+FLAG)}, 0
        je done
        cmp word ptr [rcx+0x38], 0
        jne done
        mov r11, qword ptr {mem(context)}
        test r11, r11
        je done
        mov rax, qword ptr [rcx]
        test rax, rax
        je done
        cmp qword ptr [r11], rax
        jne done
        cmp byte ptr [rax+0x51], 0
        jne done
        movzx edx, word ptr [r11+8]
        sub edx, 63
        cmp edx, 3
        ja done
        movzx r8d, byte ptr [rax+0x4f]
        cmp r8d, 6
        ja done
        shl r8d, 8
        lea r8d, [r8+rdx+63]
        lea r9, {mem(usage['preferences']['live_rva'])}
        bt dword ptr [r9], r8d
        jc done
        test dword ptr [r11+12], 0x80000000
        jne done
        or dword ptr [r11+12], 0x80000000
        movzx eax, word ptr [r11+10]
        xor ebp, ebp
        cmp eax, 100
        jb done
        inc ebp
        cmp eax, 250
        jb threshold
        inc ebp
        cmp eax, 500
        jb threshold
        inc ebp
    threshold:
        # Arte order: Sharpness, Resist, Concentrate, Barrier.
        mov r8d, 0x08041002
        mov r9d, 0x06050704
        mov rbx, qword ptr [rcx+8]
        mov ecx, edx
        shl ecx, 3
        shr r8d, cl
        shr r9d, cl
        movzx r8d, r8b
        movzx r9d, r9b
        mov rsi, qword ptr {mem(0x12cecd8)}
        test rsi, rsi
        je done
        movzx edi, byte ptr {mem(0x12cece8)}
        test edi, edi
        je done
        cmp edi, 8
        ja done
    candidate:
        cmp rsi, rbx
        je next
        cmp byte ptr [rsi+0x51], 0
        jne next
        cmp byte ptr [rsi+0x4f], 6
        ja next
        cmp word ptr [rsi+0x3c], 0
        je next
        cmp dword ptr [rsi+0x2c], 0
        jle next
        test dword ptr [rsi+0x30], r8d
        jne next
        and dword ptr [rsi+0x30], 0xffffffe1
        or dword ptr [rsi+0x30], r8d
        # The native buff aura is cosmetic and bounded to eight slots.
        # Pool exhaustion must never prevent the state from being applied.
        cmp byte ptr {mem(0x12ceb7a)}, 0
        jne applied
        lea r10, {mem(0x12ced48)}
        mov ecx, 8
    aura:
        cmp byte ptr [r10+0x18], 0
        je aura_free
        add r10, 0x20
        dec ecx
        jne aura
        jmp applied
    aura_free:
        mov byte ptr [r10+0x18], 0x18
        mov qword ptr [r10], rsi
        mov rax, qword ptr [rsi+0x128]
        mov qword ptr [r10+8], rax
        mov al, byte ptr [rsi+0x23f]
        mov byte ptr [r10+0x1a], al
        mov byte ptr [r10+0x19], r9b
        mov al, byte ptr [rsi+0x53]
        mov byte ptr [r10+0x1b], al
        mov rax, qword ptr [rsi+0x10]
        mov qword ptr [r10+0x10], rax
    applied:
        dec ebp
        je done
    next:
        add rsi, 0x248
        dec edi
        jne candidate
    done:
        pop rbp
        pop rdi
        pop rsi
        pop rbx
    ''') + 'ret')

    # RAX callback, RCX effect; every native callback uses this exact signature.
    # R8/R9/RDX are preserved before calling the original implementation.
    scoped = emit('mastery_effect_scope', f'''
        push rbx
        sub rsp, 0x30
        mov rbx, rax
        mov rax, qword ptr {mem(context)}
        mov qword ptr [rsp+0x20], rax
        {preserve(f'''
            mov qword ptr {mem(context)}, 0
            mov rax, rcx
            lea r10, {mem(POOL)}
            sub rax, r10
            cmp rax, 0x1200
            jae scoped
            xor edx, edx
            mov r10d, 0x120
            div r10
            test edx, edx
            jne scoped
            shl eax, 4
            lea r10, {mem(effects)}
            add r10, rax
            mov r11, qword ptr [rcx]
            cmp qword ptr [r10], r11
            jne scoped
            mov qword ptr {mem(context)}, r10
        scoped:
        ''')}
        # Buff propagation runs only for the audited native buff callbacks.
        lea rax, {mem(0xcab90)}
        cmp rbx, rax
        je buff
        lea rax, {mem(0xcac50)}
        cmp rbx, rax
        je buff
        lea rax, {mem(0xcad00)}
        cmp rbx, rax
        je buff
        lea rax, {mem(0xcada0)}
        cmp rbx, rax
        jne callback
    buff:
        call {share:#x}
    callback:
        call {dark_prepare:#x}
        call {recovery:#x}
        mov rax, rbx
        call rbx
        # MOV preserves the original callback's flags and return registers.
        push rax
        mov rax, qword ptr [rsp+0x28]
        mov qword ptr {mem(context)}, rax
        pop rax
        lea rsp, [rsp+0x30]
        pop rbx
        ret
    ''')
    for name, site, length, setup, end in (
        ('init', 0x1159c7, 13,
         'mov rax, qword ptr [rcx+rax*8+0x4e9420]; mov rcx, rsi', 0x1159d4),
        ('script', 0x1159fc, 5, 'lea rax, '+mem(0x114f50), 0x115a01),
        ('large', 0x115a33, 10,
         'mov rax, qword ptr [rdx+rax*8+0x4e9900]', 0x115a3d),
        ('small', 0x115d1c, 10,
         'mov rax, qword ptr [rdx+rax*8+0x4e9690]', 0x115d26),
    ):
        wrapper = emit('mastery_scope_'+name,
                       f'{setup}; call {scoped:#x}; jmp {end:#x}')
        jump(site, length, wrapper, 'Mastery: scope native '+name+' callback')

    born = emit('mastery_projectile_capture', preserve(f'''
        mov r10, rax
        lea r11, {mem(PROJECTILES)}
        sub r10, r11
        cmp r10, 0xb40
        jae done
        mov rax, r10
        xor edx, edx
        mov ecx, 0x30
        div rcx
        test edx, edx
        jne done
        shl eax, 4
        lea r11, {mem(projectiles)}
        add r11, rax
        mov qword ptr [r11], 0
        mov qword ptr [r11+8], 0
        mov r10, qword ptr {mem(context)}
        test r10, r10
        je done
        cmp qword ptr [r10], r8
        jne done
        mov rax, qword ptr [r10+8]
        mov qword ptr [r11], r8
        mov qword ptr [r11+8], rax
    done:
    ''') + '''
        mov qword ptr [rax+8], r8
        mov rcx, qword ptr [r8]
        jmp 0x116610
    ''')
    jump(0x116609, 7, born, 'Mastery: retain projectile origin until impact, clear on reuse')

    # The three native damage callers are melee, a special boss action, and the
    # projectile evaluator. Only the last can use our immutable projectile tag.
    # At this point the frame has pushed 7 registers and reserved 0x30 bytes:
    # saved RSI (projectile iterator) is +0x58; caller return address is +0x68.
    scale = emit('mastery_damage', f'''
        pushfq
        push rax
        push rcx
        push rdx
        push r8
        push r9
        push r10
        push r11
        cmp byte ptr [rbp+0x51], 0
        jne done
        cmp byte ptr [rdi+0x51], 1
        jne done
        mov rax, qword ptr [rsp+0xa8]
        lea r10, {mem(0x1164e3)}
        cmp rax, r10
        jne done
        mov rax, qword ptr [rsp+0x98]
        lea r10, {mem(0x12cf988)}
        cmp rax, r10
        je immediate
        lea r10, {mem(PROJECTILES)}
        sub rax, r10
        cmp rax, 0xb40
        jae done
        xor edx, edx
        mov ecx, 0x30
        div rcx
        test edx, edx
        jne done
        shl eax, 4
        lea r10, {mem(projectiles)}
        add r10, rax
        jmp tagged
    immediate:
        # Air Thrust and several area effects use the native scratch impact
        # inside the current effect callback. It has no persistent pool slot.
        # Only that exact object may inherit the scoped, immutable parent tag.
        cmp qword ptr [rax+8], rbp
        jne done
        mov r10, qword ptr {mem(context)}
        test r10, r10
        je done
    tagged:
        cmp qword ptr [r10], rbp
        jne done
        movzx ecx, byte ptr [rbp+0x4f]
        cmp ecx, 6
        ja done
        shl ecx, 8
        movzx edx, word ptr [r10+8]
        cmp edx, 43
        jb done
        cmp edx, 52
        ja ordinary_spell
        sub rsp, 0x28
        call {summon_damage:#x}
        add rsp, 0x28
        jmp done
    ordinary_spell:
        cmp byte ptr {mem(data+0x1a00+FLAG)}, 0
        je done
        cmp edx, 70
        jb done
        cmp edx, 101
        jbe offensive_tag
        cmp edx, 112
        jb done
        cmp edx, 113
        ja done
    offensive_tag:
        {faculty_power}
        add ecx, edx
        lea r11, {mem(usage['preferences']['live_rva'])}
        bt dword ptr [r11], ecx
        jc offense_done
        mov ecx, dword ptr [r10+12]
        and ecx, 0xffff
        cmp ecx, 25
        ja offense_done
        test esi, esi
        jle offense_done
        add ecx, 100
        mov eax, esi
        imul rax, rcx
        xor edx, edx
        mov ecx, 100
        div rcx
        mov ecx, 30000
        cmp rax, rcx
        cmova rax, rcx
        mov esi, eax
        test r15d, 2
        jne offense_done
        # Native physical criticals double damage and use display flag 2.
        # Magic has no native critical roll. Add it only to tagged offensive
        # spell impacts, never buffs, healing, allies, summons or melee.
        movzx eax, word ptr [r10+10]
        mov ecx, 500
        cmp eax, ecx
        cmova eax, ecx
        imul eax, eax, 15
        xor edx, edx
        div ecx
        test eax, eax
        je offense_done
        sub rsp, 0x90
        mov dword ptr [rsp+0x20], eax
        movdqu [rsp+0x30], xmm0
        movdqu [rsp+0x40], xmm1
        movdqu [rsp+0x50], xmm2
        movdqu [rsp+0x60], xmm3
        movdqu [rsp+0x70], xmm4
        movdqu [rsp+0x80], xmm5
        call 0x283090
        xor edx, edx
        mov ecx, 100
        div ecx
        cmp edx, dword ptr [rsp+0x20]
        movdqu xmm0, [rsp+0x30]
        movdqu xmm1, [rsp+0x40]
        movdqu xmm2, [rsp+0x50]
        movdqu xmm3, [rsp+0x60]
        movdqu xmm4, [rsp+0x70]
        movdqu xmm5, [rsp+0x80]
        lea rsp, [rsp+0x90]
        jae offense_done
        add esi, esi
        or r15d, 2
        or dword ptr [rsp+0xb8], 2
    offense_done:
        {faculty_impact}
    done:
        {faculty_defense}
        pop r11
        pop r10
        pop r9
        pop r8
        pop rdx
        pop rcx
        pop rax
        popfq
        mov eax, 30000
        jmp 0x8f02a
    ''')
    jump(0x8f025, 5, scale, 'Mastery: scale offensive spell damage before native cap and display')
    return dict(state_rva=state, size=SIZE, context_rva=context,
                effects_rva=effects, projectiles_rva=projectiles,
                record_size=16, option_flag=FLAG, usage=usage,
                uses_per_percent=20, maximum_percent=25,
                actor_uses_rva=actor_uses, cast_growth_rva=cast_growth,
                recovery_rva=recovery, current_roots_rva=roots,
                recovery_reduction_percent=15,
                area_growth_rva=area_growth, area_extent_percent=50,
                cast_reduction_percent=15, critical_chance_points=15,
                critical_damage_multiplier=2, common_track_max_casts=500,
                projectile_growth=[air_growth,wind_growth,meteor_growth,holy_growth,aqua_growth,ray_growth,dark_growth,star_growth,dict(arte=75,additional_cap=3),dict(arte=82,additional_cap=3),
                                   dict(arte=83,native_count=16,additional_cap=6)],
                extra_projectiles_rva=extra_projectiles,
                offensive_arte_ids=list(range(70, 102))+[112, 113],
                buff_arte_ids=[63,64,65,66],
                buff_extra_targets={'100':1,'250':2,'500':3},
                buff_target_order='living party order, excluding primary and same buff',
                buff_duration='native, no timer added',
                buff_exclusivity='native replacement of other buffs preserved',
                healing_unchanged=True, summons_unchanged=False,
                summons=dict(option_flag=19, damage_rva=summon_damage,
                             maximum_bonus=list(MAX_BONUS), level_cap=30,
                             area_width_at_cap=720, area_height_bonus=50,
                             balance_status='initial coefficients; live balance pending'))
