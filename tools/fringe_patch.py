"""Optional partner-location relaxation with bounded transient spell lists.

Native 32-byte save arrays must not be extended in place: the next four bytes
are battle assignments. Only readers are redirected; saved lists stay native.
"""
import capstone
from fringe_lists import CAPACITY, STRIDE


def emit_fringe(emit, mem, jump, pe, cs, relocate, data, info):
    state, refresh, available = (info[k] for k in ('state_rva','refresh','available'))
    flag = data+0x1a42
    save = 'pushfq\npush rax\npush rcx\npush rdx\npush r8\npush r9\npush r10\npush r11\nsub rsp, 0x20'
    restore = 'add rsp, 0x20\npop r11\npop r10\npop r9\npop r8\npop rdx\npop rcx\npop rax\npopfq'
    sites = []
    def hook(site, size, enabled, name):
        old=relocate(pe.get_data(site,size),site)
        target=emit('fringe_'+name,f'''
            pushfq
            cmp byte ptr {mem(flag)}, 0
            jne enabled
            cmp byte ptr {mem(data+0x1a63)}, 0
            je native
        enabled:
            popfq
            {enabled}
        native:
            popfq
            {old}
            jmp {site+size:#x}
        ''')
        jump(site,size,target,'Fringe: '+name)
        sites.append(dict(site=site,size=size,hook=target))

    # Refresh before the menu builds its row counts and selection indexes.
    hook(0x223200,5,f'''
        {save.replace('sub rsp, 0x20','sub rsp, 0x28')}
        lea rcx, {mem(0x11ca420)}
        call {refresh:#x}
        {restore.replace('add rsp, 0x20','add rsp, 0x28')}
        mov qword ptr [rsp+8], rbx
        jmp 0x223205
    ''','menu_refresh')
    hook(0x223290,8,f'''
        push rax
        push rdx
        push r8
        lea rax, {mem(state)}
        add rax, r9
        xor edx, edx
        xor r8d, r8d
    count:
        cmp byte ptr [rax+rdx], 0
        je empty
        lea r8d, [edx+1]
    empty:
        inc edx
        cmp edx, {CAPACITY}
        jb count
        mov word ptr [rcx+r11+8], r8w
        pop r8
        pop rdx
        pop rax
        jmp 0x22359f
    ''','menu_count')

    # All indexed list reads in the native Techniques menu, including both
    # list layouts, arte descriptions, auto toggles and assignment dialogs.
    reads=[]
    read_sites = [0x2235fc,0x223632,0x225032,0x225e2a,0x22651d,0x226cf3,
        0x2278ab,0x2290c3,0x22939b,0x2298cb,0x229a57,0x229a7d,0x22a338,
        0x22a621,0x22a6d2,0x22a95b,0x22aa20,0x22ab58,0x22aba2,0x22adaa,
        0x22ae4e,0x22b3d2,0x22b458,0x22b5d0,0x22b620,0x22b656,0x22b7cf,
        0x22b881,0x22b8c6,0x22b8fc,0x22be93,0x22bf53,0x22c09e]
    for site in read_sites:
        ins=next(cs.disasm(pe.get_data(site,15),site))
        assert any(o.type==capstone.x86.X86_OP_MEM and o.mem.disp==0x11ca49a for o in ins.operands)
        assert ins.mnemonic in ('movzx','movsx','cmp','lea'), (hex(ins.address),ins.mnemonic)
        new=('movzx' if ins.mnemonic=='movsx' else ins.mnemonic)+' '+ins.op_str.replace('0x11ca49a',hex(state))
        hook(ins.address,ins.size,new+f'\njmp {ins.address+ins.size:#x}',f'menu_read_{ins.address:x}')
        reads.append(ins.address)
    assert len(reads)>=20, reads

    # Native TP/status/target checks remain in force; replace membership only.
    hook(0x74592,6,f'''
        {save}
        movzx ecx, byte ptr [r11+0x4f]
        mov edx, ebx
        mov r8, qword ptr {mem(0x12cea60)}
        call {available:#x}
        test eax, eax
        je absent
        {restore}
        jmp 0x7459a
    absent:
        {restore}
        jmp 0x745f3
    ''','battle_membership')

    # AI can inspect all available spells, but its three candidate buckets
    # still hold 32 entries each. Keep their bound explicit.
    hook(0x73e09,7,f'''
        {save}
        mov rcx, r9
        call {refresh:#x}
        {restore}
        lea r15, {mem(state)}
        add r15, rcx
        jmp 0x73e10
    ''','ai_list')
    hook(0x73ebe,6,f'mov r12d, {CAPACITY}\njmp 0x73ec4','ai_count')
    hook(0x73f59,6,'''
        movzx eax, byte ptr [rdx]
        cmp eax, 32
        jae 0x73f65
        add rcx, rax
        jmp 0x73f5f
    ''','ai_bucket_bound')

    # Load-time shortcut repair must recognize enabled Fringe spells too.
    hook(0x38157,7,f'''
        {save}
        mov ecx, ebp
        mov edx, ebx
        mov r8, r14
        call {available:#x}
        test eax, eax
        je absent
        {restore}
        jmp 0x383a5
    absent:
        {restore}
        jmp 0x383b2
    ''','load_assignments')

    # Reassignment updates native lists first. Preserve only assignments which
    # remain valid under the optional rule, including primary ownership/levels.
    hook(0x21e0fa,7,f'''
        {save}
        push rbx
        push rsi
        push rdi
        push rbp
        sub rsp, 0x20
        mov rcx, r15
        call {refresh:#x}
        mov ebx, 2
    character:
        imul edi, ebx, {STRIDE}
        lea rsi, {mem(0x11ca4ba)}
        add rsi, rdi
        mov ebp, 4
    assignment:
        movzx edx, byte ptr [rsi]
        test edx, edx
        je next
        mov ecx, ebx
        mov r8, r15
        call {available:#x}
        test eax, eax
        jne next
        mov byte ptr [rsi], 0
    next:
        inc rsi
        dec ebp
        jne assignment
        inc ebx
        cmp ebx, 4
        jb character
        add rsp, 0x20
        pop rbp
        pop rdi
        pop rsi
        pop rbx
        {restore}
        jmp 0x21e281
    ''','refresh_assignments')
    for site,char in [(0x21e2c7,2),(0x21e45d,3)]:
        hook(site,7,f'''
            {save}
            mov ecx, {char}
            mov edx, r9d
            lea r8, {mem(0x11ca420)}
            call {available:#x}
            test eax, eax
            je absent
            {restore}
            jmp 0x21e5e7
        absent:
            {restore}
            jmp 0x21e5e2
        ''',f'ally_assignment_{char}')

    # Fringe screen's availability colour uses the same membership rule.
    hook(0x244180,8,f'''
        {save}
        mov ecx, 2
        mov edx, r9d
        lea r8, {mem(0x11ca420)}
        call {available:#x}
        test eax, eax
        jne found
        mov ecx, 3
        mov edx, dword ptr [rsp+0x30]
        lea r8, {mem(0x11ca420)}
        call {available:#x}
        test eax, eax
        je absent
    found:
        {restore}
        jmp 0x2441b4
    absent:
        {restore}
        jmp 0x2441a3
    ''','fringe_colour')
    info.update(hooks=sites,menu_reads=reads,ai_bucket_capacity=32)
    return info
