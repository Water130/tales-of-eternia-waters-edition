"""Standalone team-up entries, with bounded tables and sidecar-backed counters.

126..129 are virtual arte IDs, not effect IDs. Original save learned arrays and
the native 126-entry metadata table are never extended in place.
"""
import json
import struct
from pathlib import Path

SIZE = 0x2000
RECIPES = (
    (126, 0, 4, 75, 134, 16595, 13, 'Flaming Sword'),
    (127, 1, 31, 87, 54, 16609, 36, 'Lightning Strike'),
    (128, 0, 5, 74, 64, 16615, 54, 'Earth Divide'),
    (129, 1, 30, 54, 104, 16594, 28, 'Serpent Knuckle'),
)
SAVE = 'pushfq; push rax; push rcx; push rdx; push r8; push r9; push r10; push r11; sub rsp, 0x28'
RESTORE = 'add rsp, 0x28; pop r11; pop r10; pop r9; pop r8; pop rdx; pop rcx; pop rax; popfq'


def prepare(emit, mem, pe, data, state, usage):
    meta, launch = state, state+0xd00
    payload = bytearray(SIZE)
    for aid, char, physical, spell, effect, name, tp, _ in RECIPES:
        entry = bytearray(pe.get_data(0x562a50+physical*24,24))
        entry[0] = tp
        struct.pack_into('<I',entry,4,name)
        payload[aid*24:aid*24+24] = entry
        entry = bytearray(pe.get_data(0x551780+physical*8,8))
        entry[0] = effect
        # Native cooperative effects have their own voices; do not announce
        # the ingredient's name when launching the new standalone entry.
        entry[4:6] = b'\0\0'
        payload[0xd00+aid*8:0xd00+aid*8+8] = entry
    initialize = emit('teamup_tables_initialize', f'''
        cmp byte ptr {mem(state+0x1ff0)}, 1
        je done
        push rsi
        push rdi
        lea rsi, {mem(0x562a50)}
        lea rdi, {mem(meta)}
        mov ecx, {126*24//8}
        rep movsq
        lea rsi, {mem(0x551780)}
        lea rdi, {mem(launch)}
        mov ecx, 114
        rep movsq
        pop rdi
        pop rsi
        mov byte ptr {mem(state+0x1ff0)}, 1
    done:
        ret
    ''')
    # ECX owner, EDX virtual ID, R8 master -> EAX bool. Original physical
    # counters and one mage's individual successful-cast counter must qualify.
    blocks=[]
    for aid,char,physical,spell,*_ in RECIPES:
        blocks.append(f'''
            cmp edx, {aid}
            jne next_{aid}
            cmp ecx, {char}
            jne no
            cmp word ptr [r8+{0xc28+physical*2}], 50
            jb no
            movzx eax, word ptr {mem(usage+(2*128+spell)*2)}
            movzx r9d, word ptr {mem(usage+0xd000+(2*128+spell)*2)}
            add eax, r9d
            cmp eax, 50
            jae yes
            movzx eax, word ptr {mem(usage+(3*128+spell)*2)}
            movzx r9d, word ptr {mem(usage+0xd000+(3*128+spell)*2)}
            add eax, r9d
            cmp eax, 50
            jae yes
            jmp no
        next_{aid}:
        ''')
    unlocked=emit('teamup_unlocked',f'''
        cmp byte ptr {mem(data+0x1a63)}, 0
        je no
        test r8, r8
        je no
        {''.join(blocks)}
    no:
        xor eax, eax
        ret
    yes:
        mov eax, 1
        ret
    ''')
    return dict(state_rva=state,size=SIZE,metadata=meta,launch=launch,
                initialize=initialize,unlocked=unlocked,option_flag=35,
                usage_rva=usage,recipes=[dict(id=a,character=c,physical=p,spell=s,
                    effect=e,name_message=n,tp=t,name=name) for a,c,p,s,e,n,t,name in RECIPES]), payload


def wire(emit,mem,jump,edit,pe,cs,relocate,data,info):
    meta,launch,initialize,unlocked=(info[k] for k in ('metadata','launch','initialize','unlocked'))
    # Redirect each audited metadata reader, including UI details and labels.
    refs=json.loads((Path(__file__).resolve().parents[1]/'audit/build-25190541/teamup-autonomous/table_refs.json').read_text())
    redirected=[]
    for r in refs:
        site,target=int(r['site'],16),int(r['target'],16)
        if r['kind']!='indexed' or not 0x562a50<=target<0x563620 or site==0x227421:
            continue
        ins=next(cs.disasm(pe.get_data(site,15),site))
        new=bytearray(ins.bytes)
        struct.pack_into('<i',new,ins.disp_offset,meta+target-0x562a50)
        edit(site,bytes(new),'Standalone team-up metadata reader')
        redirected.append(site)
    target=emit('teamup_battle_tables',f'''
        {SAVE.replace('0x28','0x20')}
        call {initialize:#x}
        {RESTORE.replace('0x28','0x20')}
        lea r13, {mem(meta)}
        jmp 0x11c615
    ''')
    jump(0x11c60e,7,target,'Initialize extended arte metadata before battle')
    target=emit('teamup_launch_table',f'lea rax, {mem(launch)}; jmp 0x11c74d')
    jump(0x11c746,7,target,'Use bounded extended launch descriptors')
    # Standalone arte admission remains checked even for an old page-A command
    # while the option is disabled. Native TP/target/ground rules follow.
    for site,size in ((0x112d10,8),(0x73790,5)):
        old=relocate(pe.get_data(site,size),site)
        target=emit(f'teamup_admit_{site:x}',f'''
            cmp edx, 126
            jb native
            cmp edx, 129
            ja native
            {SAVE}
            cmp byte ptr [rcx+0x51], 0
            jne denied
            movzx ecx, byte ptr [rcx+0x4f]
            mov r8, qword ptr {mem(0x12cea60)}
            call {unlocked:#x}
            test eax, eax
            je denied
            cmp byte ptr {mem(0x12d0ef7)}, 6
            jne denied
            mov edx, dword ptr [rsp+0x48]
            lea rax, {mem(launch)}
            cmp byte ptr [rax+rdx*8], 100
            jae pool
            cmp word ptr {mem(0x12d0eaa)}, 0
            jne denied
        pool:
            lea rax, {mem(0x12cfca0)}
            mov ecx, 16
        slot:
            cmp qword ptr [rax], 0
            je admitted
            add rax, 0x120
            dec ecx
            jne slot
            jmp denied
        admitted:
            {RESTORE}
        native:
            {old}
            jmp {site+size:#x}
        denied:
            {RESTORE}
            xor eax, eax
            ret
        ''')
        jump(site,size,target,'Standalone team-up owner and unlock admission')
    # Native combined large effects set state 0x40 after allocation. Apply that
    # state only after successful allocation, never by cancelling a mage cast.
    target=emit('teamup_large_state',f'''
        push rax
        lea rax, {mem(launch+126*8)}
        cmp rdi, rax
        jb native
        add rax, 32
        cmp rdi, rax
        jae native
        cmp byte ptr [rdi], 100
        jae native
        mov byte ptr [rbx+0x58], 0x40
    native:
        pop rax
        test esi, esi
        je 0x112c58
        movzx edx, byte ptr [rbx+0x51]
        jmp 0x112c50
    ''')
    jump(0x112c48,8,target,'Preserve native large cooperative effect state after successful allocation')
    # The native achievement collection is bounded to its own IDs. Virtual
    # entries must not write a bit past that save/achievement structure.
    old=relocate(pe.get_data(0x38040,7),0x38040)
    target=emit('teamup_collection_guard',f'''
        cmp ecx, 126
        jb native
        cmp ecx, 129
        ja native
        ret
    native:
        {old}
        jmp 0x38047
    ''')
    jump(0x38040,7,target,'Keep virtual arte IDs out of native achievement bits')
    # Avoid even reading beyond the native automatic-use bitset for IDs >127.
    old=relocate(pe.get_data(0x7455a,8),0x7455a)
    target=emit('teamup_auto_bits_guard',f'''
        cmp ebx, 126
        jb native
        cmp ebx, 129
        ja native
        xor eax, eax
        jmp 0x74562
    native:
        {old}
        jmp 0x74562
    ''')
    jump(0x7455a,8,target,'Bound native automatic-use bitset reads')
    # Auto-use choices live in unused sidecar word 4, not the native 128-bit
    # mask. Zero means enabled, so newly unlocked entries are usable by AI.
    auto=info['usage_rva']+8
    info['auto_disabled_rva']=auto
    target=emit('teamup_auto_toggle',f'''
        cmp r8d, 126
        jb native
        cmp r8d, 129
        ja native
        mov ecx, r8d
        sub ecx, 126
        mov edx, 1
        shl edx, cl
        xor word ptr {mem(auto)}, dx
        mov ebx, 0x8e
        jmp 0x22b6c9
    native:
        mov ecx, r8d
        mov eax, r8d
        jmp 0x22b681
    ''')
    jump(0x22b67b,6,target,'Persist standalone arte Auto Yes/No outside native masks')
    old=relocate(pe.get_data(0x225ede,8),0x225ede)
    target=emit('teamup_auto_colour',f'''
        cmp edi, 126
        jb native
        cmp edi, 129
        ja native
        push rdx
        mov edx, edi
        sub edx, 126
        movzx eax, word ptr {mem(auto)}
        bt eax, edx
        mov eax, 0
        jc ready
        bts eax, ecx
    ready:
        pop rdx
        jmp 0x225ee6
    native:
        {old}
        jmp 0x225ee6
    ''')
    jump(0x225ede,8,target,'Show standalone arte automatic-use status')
    target=emit('teamup_ai_id',f'''
        cmp ebx, 126
        jb native
        cmp ebx, 129
        jbe 0x73edd
    native:
        cmp bl, 0x72
        jae 0x73f6c
        jmp 0x73edd
    ''')
    jump(0x73ed4,9,target,'Allow virtual arte IDs into bounded AI candidates')
    old=relocate(pe.get_data(0x73f09,6),0x73f09)
    target=emit('teamup_ai_auto',f'''
        cmp ebx, 126
        jb native
        cmp ebx, 129
        ja native
        mov ecx, ebx
        sub ecx, 126
        movzx eax, word ptr {mem(auto)}
        bt eax, ecx
        jc 0x73f6c
        mov edx, ebx
        jmp 0x73f21
    native:
        {old}
        jmp 0x73f0f
    ''')
    jump(0x73f09,6,target,'Use standalone AI preferences without native bitset access')
    # Localized descriptions explicitly identify standalone behavior.
    cursor=0x1200
    branches=[]
    for aid,_,_,_,_,_,_,name in RECIPES:
        fr,en={126:("Lame enflammée autonome. Frappe de feu issue de Fendoir démoniaque et Boule de feu.","Standalone Flaming Sword. A fire strike combining Demon Hammer and Fireball."),
               127:("Coup foudroyant autonome. Combine Double coup de paume et Lame du tonnerre.","Standalone Lightning Strike. Combines Twin Palm Strike and Thunder Blade."),
               128:("Faille terrestre autonome. Combine Lame tournoyante et Cyclone.","Standalone Earth Divide. Combines Spiral Attack and Cyclone."),
               129:("Poing du serpent autonome. Combine Coup ascendant du dragon et Soins ; conserve son soin natif.","Standalone Serpent Knuckle. Combines Rising Dragon Strike and Heal; retains its native healing.")}[aid]
        addresses=[]
        for s in (fr,en):
            blob=(s+'\0').encode('utf8');addresses.append(info['state_rva']+cursor)
            info.setdefault('strings',[]).append((cursor,blob.hex()));cursor+=len(blob)
        branches.append(f'''cmp ebp, {aid}; jne next_{aid}
            lea rax, {mem(addresses[1])}
            cmp byte ptr {mem(0x11c9ce8)}, 3
            jne shown
            lea rax, {mem(addresses[0])}
            jmp shown
        next_{aid}:''')
    assert cursor<0x1ff0
    ins=next(cs.disasm(pe.get_data(0x227421,15),0x227421))
    original=ins.mnemonic+' '+ins.op_str.replace('0x562a5c',hex(meta+12))
    target=emit('teamup_description',f'''
        {''.join(branches)}
        {original}
        jmp {0x227421+ins.size:#x}
    shown:
        jmp 0x227771
    ''')
    jump(0x227421,ins.size,target,'Describe autonomous team-up artes')
    info['metadata_readers']=redirected
