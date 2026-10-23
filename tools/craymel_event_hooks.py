"""Audited battle entry points for Craymel faculties, native build 25190541."""
from craymel_faculties import preserve


def emit_events(emit,mem,jump,data,info):
    # 8FE50 never uses R11: retain its explicit arte argument through native
    # accessory cost modifiers. Do not infer it from an older actor action.
    cost_id=emit('craymel_cost_arte', '''
        mov r11d, edx
        movsxd rax, edx
        mov rbx, rcx
        jmp 0x8fe5c
    ''')
    jump(0x8fe56,6,cost_id,'Retain explicit arte identity for Craymel spell costs')
    for name,site,arte,original,end in (
        ('payment',0x8feae,'r11d','movsx ecx, word ptr [rbx+0x34]; cmp ecx, edx',0x8feb4),
        ('admission',0x112f34,'ebp','movsx eax, word ptr [rbx+0x34]; cmp eax, edx',0x112f3a)):
        fn=emit('craymel_cost_'+name,f'''
            cmp {arte}, 54; jb native
            cmp {arte}, 113; ja native
            {preserve(f'mov rcx, rbx; call {info["cost"]:#x}',result='rdx')}
        native:
            {original}
            jmp {end:#x}
        ''')
        jump(site,6,fn,'Craymel discount after native accessories, identical admission/payment rounding')
    paid=emit('craymel_tp_payment',f'''
        sub cx, dx
        mov word ptr [rbx+0x34], cx
        cmp r11d, 54; jb done
        cmp r11d, 113; ja done
        {preserve(f'movsx r8d, cx; add r8d, edx; mov rcx, rbx; call {info["spent"]:#x}')}
    done: jmp 0x8fec2
    ''')
    jump(0x8febb,7,paid,'Craymel mana events only after actual successful spell TP debit')
    evade=emit('craymel_evade_hit',f'''
        push rbx; sub rsp, 0x20; mov rbx, rcx
        cmp byte ptr {mem(data+0x1a60)}, 0; je no
        cmp byte ptr {mem(0x12d0ef7)}, 6; jne no
        test rcx, rcx; je no
        cmp byte ptr [rcx+0x51], 0; jne no
        cmp dword ptr [rcx+0x2c], 0; jle no
        call {info['slot']:#x}; test rax, rax; je no
        mov edx, dword ptr {mem(0x12cea40)}
        cmp edx, dword ptr [rax+48]; jae dodge
        mov rcx, rbx; mov edx, 4; mov r8d, 5; call {info['enabled']:#x}
        test eax, eax; jne done
    dodge:
        mov rcx, rbx; call {info['tiers']['dodge']:#x}
        test eax, eax; je no
        mov ecx, eax; call {info['roll']:#x}; jmp done
    no: xor eax, eax
    done: add rsp, 0x20; pop rbx; ret
    ''')
    # Origin tagging at 8E910 remains intact. Reject the incoming hit before
    # damage, ailment, interruption or native combat-stat writes can occur.
    dodge=emit('craymel_damage_admission',f'''
        {preserve(f'mov rcx, rdx; call {evade:#x}',result='rax',aligned=False)}
        test eax, eax; je native
        mov rax, qword ptr [rsp+0x28]
        test rax, rax; je empty
        mov dword ptr [rax], 0x40000000
    empty: xor eax, eax; ret
    native:
        mov qword ptr [rsp+0x18], r8
        jmp 0x8e91a
    ''')
    jump(0x8e915,5,dodge,'Perfect dodge and protective stasis skip the complete native hit')
    # Native callers invoke 8E320 even when damage is zero. Its flags contain
    # only native low bits; reserve one private bit for the rejected hit.
    ward=emit('craymel_interruption_ward',f'''
        # RCX victim, EDX native reaction index. Damage is already committed.
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx; mov esi, edx
        call {info['slot']:#x}; mov rdi, rax; test rdi, rdi; je no
        mov eax, dword ptr {mem(0x12cea40)}
        cmp eax, dword ptr [rdi+48]; jae casting
        mov rcx, rbx; mov edx, 4; mov r8d, 5; call {info['enabled']:#x}
        test eax, eax; je casting
        mov eax, 2; jmp done
    casting:
        cmp byte ptr [rbx+0x52], 10; jne no
        cmp word ptr [rbx+0x8c], 0; jle no
        cmp esi, 32; jae no
        lea rax, {mem(0x576fe0)}
        cmp word ptr [rax+rsi*4+2], 0; jne full
        mov rcx, rbx; call {info['tiers']['light_ward']:#x}; test eax, eax; je full
        mov edx, dword ptr {mem(0x12cea40)}
        cmp edx, dword ptr [rdi+96]; jb yes
        cmp edx, dword ptr [rdi+100]; jb full
        add eax, edx; mov dword ptr [rdi+100], eax
        add edx, 300; mov dword ptr [rdi+96], edx; jmp yes
    full:
        mov rcx, rbx; mov edx, 3; mov r8d, 6; call {info['enabled']:#x}
        test eax, eax; je no
        # The synergy needs Celsius recruited at 30, not an extra enabled node.
        mov rax, qword ptr {mem(0x12cea60)}; test rax, rax; je no
        cmp byte ptr [rax+0xbd8], 0; je no
        cmp byte ptr [rax+0xbd9], 30; jne no
        mov eax, dword ptr {mem(0x12cea40)}
        cmp eax, dword ptr [rdi+104]; jb yes
        cmp eax, dword ptr [rdi+108]; jb no
        lea edx, [rax+1200]; mov dword ptr [rdi+108], edx
        add eax, 300; mov dword ptr [rdi+104], eax
    yes: mov eax, 1; jmp done
    no: xor eax, eax
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    reaction=emit('craymel_hit_reaction',f'''
        test edx, 0x40000000; jne rejected
        {preserve(f'mov edx, ecx; mov rcx, qword ptr [rsp+0xf0]; call {ward:#x}',result='rax',aligned=False)}
        cmp eax, 2; je rejected
        test eax, eax; je native
        mov rdx, qword ptr [rsp+0x28]; mov rcx, r9
        jmp 0x8ded0
    native:
        push rbx; push rsi; push rdi; push r14
        jmp 0x8e326
    rejected: ret
    ''')
    jump(0x8e320,6,reaction,'A perfectly evaded hit cannot inflict ailments or interrupt actions')
    stun=emit('craymel_stun_duration',f'''
        {preserve(f'''
            mov rcx, rbx; call {info['tiers']['stun_reduction']:#x}
            mov ecx, 100; sub ecx, eax; imul eax, ecx, 240
            xor edx, edx; mov ecx, 100; div ecx
            mov rcx, qword ptr [rsp+0xa8]
            mov word ptr [rcx], ax
        ''')}
        jmp 0x8e66d
    ''')
    jump(0x8e668,5,stun,'Celsius Lucidity reduces a newly applied stun by its highest enabled milestone')
    stasis=emit('craymel_stasis_action',f'''
        {preserve(f'''
            call {info['slot']:#x}; test rax, rax; je allow
            mov edx, dword ptr {mem(0x12cea40)}
            cmp edx, dword ptr [rax+48]; jae allow
            mov edx, 4; mov r8d, 5; call {info['enabled']:#x}; jmp ready
        allow: xor eax, eax
        ready:
        ''',result='rax',aligned=False)}
        test eax, eax; jne blocked
        mov qword ptr [rsp+8], rbx
        jmp 0xd51f5
    blocked: ret
    ''')
    jump(0xd51f0,5,stasis,'Celsius stasis prevents actor actions for two battle seconds')
    info.update(cost_admission=0x112f34,cost_payment=0x8feae,evade=evade,ward=ward,stasis=stasis)
    return info
