"""Approved fighter faculties. Transient battle records, stable save switches.

Only native successful commits/hits/heals award preparations. Admission queries
never consume them. Buffs are cleared by the native battle-start reset.
"""
from craymel_faculties import preserve

SIZE = 0x800
# key: (stable preference, character, mastery family mask, minimum level)
GATES = {
    'R2': (154,0,1,15), 'R3': (155,0,1,20), 'R4': (156,0,1,25),
    'R5': (157,0,2,10), 'R6': (158,0,2,15), 'R7': (159,0,2,20),
    'R9': (160,0,3,10), 'R11': (161,0,3,20), 'R12': (162,0,3,25),
    'R14': (163,0,3,30), 'F1': (164,1,1,5), 'F2': (165,1,1,10),
    'F3': (166,1,1,20), 'F4': (167,1,1,25), 'F6': (168,1,2,20),
    'F8': (169,1,3,10), 'F10': (170,1,3,25), 'F11': (171,1,3,15),
    'F12': (172,1,3,20), 'F13': (173,1,3,25), 'F14': (174,1,3,10),
}


def emit_expansion(emit, mem, jump, data, state, choices):
    checks = ''
    for key,(pref,char,family,level) in GATES.items():
        levels = ''.join(f'cmp byte ptr [r9+{0xc08+char*16+8*i}], {level}; jb no; '
                         f'cmp byte ptr [r9+{0xc08+char*16+8*i}], 30; ja no; '
                         for i in range(2) if family & (1<<i))
        checks += f'''cmp edx, {pref}; jne next_{key}
            cmp byte ptr [rcx+0x4f], {char}; jne no
            cmp byte ptr {mem(data+(0x1a4f if char==0 else 0x1a41))}, 0; je no
            {levels}
            mov r10d, {char*256+pref}; jmp preference
        next_{key}:
        '''
    enabled=emit('fighter_expansion_enabled',f'''
        test rcx, rcx; je no
        cmp byte ptr {mem(0x12d0ef7)}, 6; jne no
        cmp byte ptr [rcx+0x51], 0; jne no
        cmp word ptr [rcx+0x3c], 1; jne no
        cmp dword ptr [rcx+0x2c], 0; jle no
        mov r9, qword ptr {mem(0x12cea60)}; test r9, r9; je no
        {checks}
        jmp no
    preference:
        lea r9, {mem(choices)}; bt dword ptr [r9], r10d; jc no
        mov eax, 1; ret
    no: xor eax, eax; ret
    ''')
    def gate(key, actor='rbx'):
        return f'mov rcx, {actor}; mov edx, {GATES[key][0]}; call {enabled:#x}'
    slot=emit('fighter_expansion_slot',f'''
        test rcx, rcx; je no
        cmp byte ptr [rcx+0x51], 0; jne no
        movzx eax, byte ptr [rcx+0x4f]; cmp eax, 6; ja no
        shl eax, 8; lea r9, {mem(state)}; add rax, r9
        cmp qword ptr [rax], rcx; je done
        mov r9, rax; lea r10, [rax+256]
    clear: mov qword ptr [r9], 0; add r9, 8; cmp r9, r10; jb clear
        mov qword ptr [rax], rcx
    done: ret
    no: xor eax, eax; ret
    ''')
    # Per-character offsets: 8 guard start+1, 12 held-direction latch,
    # 16 prepared-punch expiry, 20 protected arte serial+1, 24 heal-ready,
    # 28 emergency next clock, 32 heal rebate, 36 early recovery expiry,
    # 40/44 detox mask/expiry, 48/52 revival expiry/caster preference owner,
    # 56 last block source pointer, 64 block source serial,
    # 72 current chain serial, 73 previous family, 74 arte count,
    # 75 mixed rebate spent, 76 distinct punch mask, 80 actual TP sum,
    # 84 refund spent, 88 hit serial+1, 92 alternating successful count,
    # 96 alternating last family, 100 hitstun spent, 104 guard-break ready,
    # 108 normal successful count, 112 last normal serial+1,
    # 120 last cast serial+1, 124 reserved.
    tp=emit('fighter_expansion_tp', '''
        test edx, edx; jle done
        mov r8, qword ptr [rcx+0xe8]; test r8, r8; je done
        movsx eax, word ptr [r8+0x1c]; movsx r8d, word ptr [rcx+0x34]
        sub eax, r8d; test eax, eax; jle done
        cmp edx, eax; cmovg edx, eax
        jmp 0x8fbf0
    done: ret
    ''')
    family=emit('fighter_expansion_family',f'''
        cmp edx, 130; jb native_id
        cmp edx, 135; ja native_id
        mov eax, 1; ret
    native_id:
        xor eax, eax
        cmp edx, 1; jb done
        cmp edx, 38; ja done
        cmp edx, 22; jb table
        cmp edx, 25; jb done
    table:
        imul r10d, edx, 24; lea r11, {mem(0x562a50)}
        movzx eax, word ptr [r11+r10]; shr eax, 10; and eax, 3
        test eax, eax; jne done; mov eax, 3
    done: ret
    ''')
    # Actual admitted physical arte, called before the native serial advances.
    commit=emit('fighter_expansion_commit',f'''
        push rbx; push rsi; push rdi; push rbp; sub rsp, 0x28
        mov rbx, rcx; mov esi, edx
        call {family:#x}; test eax, eax; je done; mov ebp, eax
        mov rcx, rbx; call {slot:#x}; test rax, rax; je done; mov rdi, rax
        cmp byte ptr [rbx+0x4f], 1; ja done
        mov al, byte ptr [rbx+0x6e]
        cmp al, byte ptr [rdi+72]; jne fresh
        cmp byte ptr [rbx+0x52], 8; jne fresh
        test byte ptr [rbx+0x64], 0xf0; jne append
    fresh:
        mov qword ptr [rdi+72], 0; mov dword ptr [rdi+84], 0
        mov qword ptr [rdi+88], 0; mov qword ptr [rdi+96], 0
        mov dword ptr [rdi+140], 0
    append:
        mov dword ptr [rdi+144], 0
        cmp byte ptr [rbx+0x4f], 1; je farah
        cmp ebp, 1; jne reid_count
        cmp dword ptr [rdi+108], 3; jb reid_count
        {gate('R4')}; test eax, eax; je reid_count
        mov al, byte ptr [rbx+0x6e]; inc al; movzx eax, al; inc eax
        mov dword ptr [rdi+144], eax
        mov dword ptr [rdi+108], 0
    reid_count:
        cmp byte ptr [rdi+74], 2; jne remember
        mov byte ptr [rdi+75], 1; jmp remember
    farah:
        mov byte ptr [rdi+32], 0
        cmp esi, 31; jne prepared_punch
        cmp byte ptr [rdi+104], 0; je prepared_punch
        {gate('F4')}; test eax, eax; je prepared_punch
        mov byte ptr [rdi+104], 0
        mov dword ptr [rdi+140], 0
        mov al, byte ptr [rbx+0x6e]; inc al; movzx eax, al; inc eax
        mov dword ptr [rdi+144], eax
    prepared_punch:
        cmp ebp, 1; jne remember
        {gate('F1')}; test eax, eax; je varied
        mov eax, dword ptr {mem(0x12cea40)}
        cmp eax, dword ptr [rdi+16]; jae varied
        mov al, byte ptr [rbx+0x6e]; inc al; movzx eax, al; inc eax
        mov dword ptr [rdi+20], eax; mov dword ptr [rdi+16], 0
    varied:
        mov ecx, esi; cmp ecx, 130; jb native_varied
        sub ecx, 116; jmp varied_bit
    native_varied: sub ecx, 25
    varied_bit: bts dword ptr [rdi+76], ecx
    remember:
        # family 3 cannot establish a strict slash/thrust alternation.
        movzx eax, byte ptr [rdi+73]; xor eax, ebp
        cmp eax, 3; sete al; and al, 1
        cmp byte ptr [rdi+74], 1; jne no_pair
        mov byte ptr [rdi+127], al
    no_pair:
        mov byte ptr [rdi+73], bpl
        cmp byte ptr [rdi+74], 255; je serial
        inc byte ptr [rdi+74]
    serial:
        mov al, byte ptr [rbx+0x6e]; inc al; mov byte ptr [rdi+72], al
    done: add rsp, 0x28; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    cost=emit('fighter_expansion_cost',f'''
        # RCX caster, EDX arte, R8D cost after accessories -> EAX cost.
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx; mov esi, r8d
        call {family:#x}; test eax, eax; je done
        mov rcx, rbx; call {slot:#x}; test rax, rax; je done; mov rdi, rax
        cmp byte ptr [rbx+0x4f], 0; jne farah
        {gate('R9')}; test eax, eax; je done
        cmp byte ptr [rbx+0x52], 8; jne done
        mov al, byte ptr [rbx+0x6e]; cmp al, byte ptr [rdi+72]; jne done
        cmp byte ptr [rdi+74], 2; jne done
        cmp byte ptr [rdi+127], 1; jne done
        cmp byte ptr [rdi+75], 0; jne done; jmp discount
    farah:
        {gate('F14')}; test eax, eax; je done
        cmp byte ptr [rdi+32], 0; je done
    discount:
        imul eax, esi, 80; add eax, 99; xor edx, edx
        mov ecx, 100; div ecx; mov esi, eax
    done: mov eax, esi; add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    # Cost must match both native admission paths and the AI payment helper.
    for site,tail in ((0x1131d1,0x1131d7),(0x1132f5,0x1132fb)):
        hook=emit(f'fighter_cost_{site:x}',preserve(
            f'mov r8d, edx; mov edx, ebp; mov rcx, rbx; call {cost:#x}',result='rdx')+
            f'; movsx ecx, word ptr [rbx+0x34]; cmp ecx, edx; jmp {tail:#x}')
        jump(site,6,hook,'Approved physical arte discount after native accessories')
    paid=emit('fighter_expansion_paid',f'''
        # RCX caster, EDX arte, R8D actual debit. Never called on admission.
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx; mov esi, r8d
        call {family:#x}; cmp eax, 1; jne done
        cmp byte ptr [rbx+0x4f], 1; jne done
        mov rcx, rbx; call {slot:#x}; test rax, rax; je done; mov rdi, rax
        cmp byte ptr [rbx+0x52], 8; jne fresh
        mov al, byte ptr [rbx+0x6e]; cmp al, byte ptr [rdi+72]; je add_cost
    fresh: mov dword ptr [rdi+80], 0
    add_cost: add dword ptr [rdi+80], esi
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    hook=emit('fighter_physical_paid',f'''
        sub cx, dx; mov word ptr [rbx+0x34], cx
        {preserve(f'mov r8d, edx; mov edx, ebp; mov rcx, rbx; call {paid:#x}')}
        jmp 0x113304
    ''')
    jump(0x1132fd,7,hook,'Observe actual physical arte payment for finite chain rewards')
    ward=emit('fighter_expansion_ward',f'''
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx; mov esi, edx
        cmp byte ptr [rbx+0x52], 8; jne no
        cmp byte ptr [rbx+0x4f], 0; jne farah
        cmp byte ptr [rbx+0x65], 2; jne no
        cmp byte ptr [rbx+0x6d], 13; jb no
        cmp byte ptr [rbx+0x6d], 21; ja no
        {gate('R14')}; jmp done
    farah:
        {gate('F1')}; test eax, eax; je no
        cmp esi, 32; jae no
        lea rax, {mem(0x576fe0)}; cmp word ptr [rax+rsi*4+2], 0; jne no
        mov rcx, rbx; call {slot:#x}; mov rdi, rax
        movzx eax, byte ptr [rbx+0x6e]; inc eax
        cmp eax, dword ptr [rdi+20]; jne no
        mov dword ptr [rdi+20], 0; mov eax, 1; jmp done
    no: xor eax, eax
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    cast=emit('fighter_expansion_cast',f'''
        # Query only. Consumption is done when state 10 is actually observed.
        push rbx; push rsi; push rdi; push rbp; sub rsp, 0x28
        mov rbx, rcx; mov esi, edx; mov ebp, r8d
        cmp esi, 39; jb done; cmp esi, 41; ja done
        cmp byte ptr [rcx+0x4f], 1; jne done
        call {slot:#x}; test rax, rax; je done; mov rdi, rax
        {gate('F8')}; test eax, eax; je emergency
        cmp byte ptr [rdi+24], 0; je emergency
        add ebp, 3; shr ebp, 2; jmp minimum
    emergency:
        cmp esi, 39; jne done
        {gate('F11')}; test eax, eax; je done
        mov eax, dword ptr {mem(0x12cea40)}; cmp eax, dword ptr [rdi+28]; jb done
        mov rax, qword ptr [rbx+0xe8]; test rax, rax; je done
        mov ecx, dword ptr [rbx+0x2c]; shl rcx, 2
        cmp ecx, dword ptr [rax+0x18]; jae done
        inc ebp; shr ebp, 1
    minimum: cmp ebp, 2; jae done; mov ebp, 2
    done: mov eax, ebp; add rsp, 0x28; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    action=emit('fighter_expansion_action',f'''
        push rbx; push rsi; push rdi; push rbp; sub rsp, 0x28
        mov rbx, rcx
        cmp byte ptr {mem(0x12d0ef7)}, 6; jne done
        cmp byte ptr [rcx+0x4f], 1; ja done
        call {slot:#x}; test rax, rax; je done; mov rdi, rax
        mov ebp, dword ptr {mem(0x12cea40)}
        cmp byte ptr [rbx+0x52], 8; je active
        mov dword ptr [rdi+108], 0; mov dword ptr [rdi+112], 0
        mov byte ptr [rdi+104], 0
    active:
        cmp word ptr [rbx+0x3c], 1; jne clear_guard
        cmp dword ptr [rbx+0x2c], 0; jle clear_guard
        cmp byte ptr [rbx+0x52], 10; jne recovery
        cmp byte ptr [rbx+0x4f], 1; jne clear_guard
        cmp byte ptr [rbx+0x6d], 39; jb clear_guard
        cmp byte ptr [rbx+0x6d], 41; ja clear_guard
        movzx eax, byte ptr [rbx+0x6e]; inc eax
        cmp eax, dword ptr [rdi+120]; je clear_guard
        mov dword ptr [rdi+120], eax
        {gate('F8')}; test eax, eax; je consume_emergency
        cmp byte ptr [rdi+24], 0; je consume_emergency
        mov byte ptr [rdi+24], 0; jmp clear_guard
    consume_emergency:
        cmp byte ptr [rbx+0x6d], 39; jne clear_guard
        {gate('F11')}; test eax, eax; je clear_guard
        cmp ebp, dword ptr [rdi+28]; jb clear_guard
        mov rax, qword ptr [rbx+0xe8]; test rax, rax; je clear_guard
        mov ecx, dword ptr [rbx+0x2c]; shl rcx, 2
        cmp ecx, dword ptr [rax+0x18]; jae clear_guard
        lea eax, [rbp+900]; mov dword ptr [rdi+28], eax
        jmp clear_guard
    recovery:
        cmp byte ptr [rbx+0x57], 1; jb clear_guard
        cmp byte ptr [rbx+0x57], 2; ja clear_guard
        mov rsi, qword ptr [rbx+0xf0]; test rsi, rsi; je clear_guard
        test word ptr [rsi], 0x200; jne clear_guard
        cmp word ptr [rbx+0x12], 0; jne clear_guard
        cmp byte ptr [rbx+0x74], 0; jne clear_guard
        test dword ptr [rbx+0x30], 0x4000; jne clear_guard
        cmp byte ptr [rbx+0x52], 6; jne guard
        cmp ebp, dword ptr [rdi+36]; jae clear_guard
        test byte ptr [rsi+4], 0x20; je clear_guard
        {gate('F10')}; test eax, eax; je clear_guard
        mov word ptr [rbx+0x44], 0; mov byte ptr [rbx+0x52], 0
        mov byte ptr [rbx+0x64], 0; mov dword ptr [rdi+36], 0
        mov rcx, rbx; xor edx, edx; call 0x112720; jmp clear_guard
    guard:
        cmp byte ptr [rbx+0x52], 2; jne clear_guard
        test byte ptr [rsi], 0x80; je clear_guard
        cmp dword ptr [rdi+8], 0; jne guarding
        lea eax, [rbp+1]; mov dword ptr [rdi+8], eax
    guarding:
        cmp byte ptr [rbx+0x4f], 0; je step
        cmp word ptr [rbx+0x18], 0; jne done
        test byte ptr [rsi+0x10], 0xf; jne done
        mov eax, ebp; inc eax; sub eax, dword ptr [rdi+8]
        cmp eax, 20; jb done
        {gate('F1')}; test eax, eax; je done
        lea eax, [rbp+180]; mov dword ptr [rdi+16], eax; jmp done
    step:
        # Require a fresh toward direction; Guard+Up keeps native priority.
        movzx eax, byte ptr [rsi+0x10]; test eax, 1; jne clear_latch
        and eax, 10; cmp eax, 2; je direction
        cmp eax, 8; jne clear_latch
    direction:
        cmp byte ptr [rdi+12], 0; jne done
        mov byte ptr [rdi+12], 1
        cmp word ptr [rbx+0x44], 0; jne done
        mov esi, eax
        {gate('R7')}; test eax, eax; je done
        mov rax, qword ptr [rbx]; test rax, rax; je done
        cmp byte ptr [rax+0x51], 1; jne done
        cmp dword ptr [rax+0x2c], 0; jle done
        movsx edx, word ptr [rax+0x10]; movsx eax, word ptr [rbx+0x10]
        sub edx, eax; test edx, edx; je done
        mov eax, 48; jg right
        cmp esi, 2; jne done; neg eax; jmp move
    right: cmp esi, 8; jne done
    move:
        # A native movement state, not a teleport: collision integrates +18.
        mov word ptr [rbx+0x18], ax; mov byte ptr [rbx+0x52], 5
        or byte ptr [rbx+0x62], 1
        mov word ptr [rbx+0x44], 8
        mov rcx, rbx; mov edx, 10; call 0x7fe70
        mov byte ptr [rbx+0x23a], 10; jmp done
    clear_latch: mov byte ptr [rdi+12], 0; jmp done
    clear_guard:
        mov dword ptr [rdi+8], 0
        mov rax, qword ptr [rbx+0xf0]; test rax, rax; je release_step
        test byte ptr [rax], 0x80; je release_step
        test byte ptr [rax+0x10], 10; jne done
    release_step: mov byte ptr [rdi+12], 0
    done: add rsp, 0x28; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    block=emit('fighter_expansion_block',f'''
        # RCX guarding actor, RDX actual attacking actor.
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx; mov rsi, rdx
        {gate('R5')}; test eax, eax; je done
        test rsi, rsi; je done; cmp byte ptr [rsi+0x51], 1; jne done
        mov rcx, rbx; call {slot:#x}; mov rdi, rax
        cmp dword ptr [rdi+8], 0; je done
        mov eax, dword ptr {mem(0x12cea40)}; inc eax; sub eax, dword ptr [rdi+8]
        cmp eax, 8; ja done
        movzx eax, byte ptr [rsi+0x6e]
        cmp qword ptr [rdi+56], rsi; jne reward
        cmp dword ptr [rdi+64], eax; je done
    reward:
        mov qword ptr [rdi+56], rsi; mov dword ptr [rdi+64], eax
        mov rcx, rbx; mov edx, 3; call {tp:#x}
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    defense=emit('fighter_expansion_defense',f'''
        # RCX victim, EDX incoming damage, R8D nonzero magic flag.
        push rbx; push rsi; push rdi; push rbp; push r12; sub rsp, 0x20
        mov rbx, rcx; mov esi, edx; mov ebp, r8d
        cmp byte ptr {mem(0x12d0ef7)}, 6; jne done
        cmp byte ptr [rcx+0x51], 0; jne done
        cmp word ptr [rcx+0x3c], 1; jne done
        test esi, esi; jle done
        call {slot:#x}; test rax, rax; je done; mov rdi, rax
        mov eax, dword ptr {mem(0x12cea40)}; cmp eax, dword ptr [rdi+48]; jae rempart
        mov rcx, qword ptr [rdi+136]; mov edx, {GATES['F13'][0]}; call {enabled:#x}
        test eax, eax; je rempart
        imul eax, esi, 75; add eax, 99; xor edx, edx; mov ecx, 100; div ecx; mov esi, eax
    rempart:
        test ebp, ebp; jne done
        movzx r12d, byte ptr {mem(0x12cece8)}; cmp r12d, 8; ja done
        mov rdi, qword ptr {mem(0x12cecd8)}; test rdi, rdi; je done
    next:
        test r12d, r12d; je done
        cmp rdi, rbx; je skip
        cmp byte ptr [rdi+0x52], 2; jne skip
        {gate('R11','rdi')}; test eax, eax; je skip
        movsx eax, word ptr [rdi+0x10]; movsx edx, word ptr [rbx+0x10]; sub eax, edx
        add eax, 3200; cmp eax, 6400; ja skip
        movsx eax, word ptr [rdi+0x12]; movsx edx, word ptr [rbx+0x12]; sub eax, edx
        add eax, 1600; cmp eax, 3200; ja skip
        imul eax, esi, 90; add eax, 99; xor edx, edx; mov ecx, 100; div ecx; mov esi, eax; jmp done
    skip: add rdi, 0x248; dec r12d; jmp next
    done: mov eax, esi; add rsp, 0x20; pop r12; pop rbp; pop rdi; pop rsi; pop rbx; ret
    ''')
    healed=emit('fighter_expansion_healed',f'''
        # RCX caster, RDX recipient, R8D actual HP restored (>0 only).
        push rbx; push rsi; sub rsp, 0x28
        mov rbx, rcx
        mov esi, r8d
        test rdx, rdx; je done; cmp byte ptr [rdx+0x51], 0; jne done
        {gate('F10')}; test eax, eax; je rebate
        mov rcx, rbx; call {slot:#x}
        mov edx, dword ptr {mem(0x12cea40)}; add edx, 180; mov dword ptr [rax+36], edx
    rebate:
        test esi, esi; jle done
        {gate('F14')}; test eax, eax; je done
        mov rcx, rbx; call {slot:#x}; mov byte ptr [rax+32], 1
    done: add rsp, 0x28; pop rsi; pop rbx; ret
    ''')
    # Snapshot callback from Detoxify after removing actual conditions.
    purified=emit('fighter_expansion_purified',f'''
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx; mov rsi, rdx; mov edi, r8d
        and edi, 0x02006601; je done
        {gate('F12')}; test eax, eax; je done
        mov rcx, rsi; call {slot:#x}; test rax, rax; je done
        mov dword ptr [rax+40], edi
        mov edx, dword ptr {mem(0x12cea40)}; add edx, 600; mov dword ptr [rax+44], edx
        mov qword ptr [rax+128], rbx
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    revived=emit('fighter_expansion_revived',f'''
        push rbx; push rsi; sub rsp, 0x28
        mov rbx, rcx; mov rsi, rdx
        test rsi, rsi; je done
        cmp word ptr [rsi+0x3c], 1; jne done
        cmp dword ptr [rsi+0x2c], 0; jle done
        {gate('F13')}; test eax, eax; je done
        mov rcx, rsi; call {slot:#x}; test rax, rax; je done
        mov edx, dword ptr {mem(0x12cea40)}; add edx, 300; mov dword ptr [rax+48], edx
        mov qword ptr [rax+136], rbx
    done: add rsp, 0x28; pop rsi; pop rbx; ret
    ''')
    # Native status switch IDs are decoded from its verified jump table.
    from tables_audit import get
    import struct
    # Switch entries point at each case's resistance check, not its OR.
    masks_by_entry={0x8e0e4:1,0x8e0fe:0x200,0x8e11b:0x4000,
                    0x8e1fc:0x2000000,0x8e21d:0x400}
    branches=''
    for i,entry in enumerate(struct.unpack('<22I',get(0x8e2c4,88)),1):
        if entry in masks_by_entry:
            branches+=f'cmp esi, {i}; jne status_{i}; mov esi, {masks_by_entry[entry]}; jmp mapped; status_{i}:\n'
    immunity=emit('fighter_expansion_immunity',f'''
        # RCX recipient, EDX native ailment enum -> EAX reject this ailment.
        push rbx; push rsi; sub rsp, 0x28
        mov rbx, rcx; mov esi, edx
        {branches}
        jmp no
    mapped:
        call {slot:#x}; test rax, rax; je no
        mov edx, dword ptr {mem(0x12cea40)}; cmp edx, dword ptr [rax+44]; jae no
        test dword ptr [rax+40], esi; je no
        mov rcx, qword ptr [rax+128]; mov edx, {GATES['F12'][0]}
        call {enabled:#x}; jmp done
    no: xor eax, eax
    done: add rsp, 0x28; pop rsi; pop rbx; ret
    ''')
    hook=emit('fighter_status_immunity',preserve(
        f'mov rcx, rbx; movzx edx, byte ptr [rsi+7]; call {immunity:#x}',result='rax')+'''
        test eax, eax; jne 0x8e293
        movzx eax, byte ptr [rsi+7]; dec eax; jmp 0x8e0bc
    ''')
    jump(0x8e0b6,6,hook,'Detoxify immunity: suppress only a recently removed ailment, after native chance checks')
    info=dict(state_rva=state,size=SIZE,enabled=enabled,slot=slot,family=family,tp=tp,
                commit=commit,cost=cost,paid=paid,ward=ward,cast=cast,action=action,
                block=block,defense=defense,healed=healed,purified=purified,revived=revived,
                immunity=immunity,gates=GATES,runtime_validated=False)
    from fighter_expansion_impacts import emit_impacts
    return emit_impacts(emit,mem,jump,data,info)
