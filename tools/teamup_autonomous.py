"""Standalone team-up entries, with bounded tables and sidecar-backed counters.

126..129 are virtual arte IDs, not effect IDs. Original save learned arrays and
the native 126-entry metadata table are never extended in place.
"""
import json
import struct
from pathlib import Path

SIZE = 0xb000
LAUNCH_OFFSET = 0xe00
RECIPES = (
    (126, 0, 4, 75, 134, 16595, 13, 'Flaming Sword'),
    (127, 1, 31, 87, 54, 16609, 36, 'Lightning Strike'),
    (128, 0, 5, 74, 64, 16615, 54, 'Earth Divide'),
    (129, 1, 30, 54, 104, 16594, 28, 'Serpent Knuckle'),
)
from farah_regulus_artes import ARTES, DESCRIPTIONS, prepare_payload, NAME_SITES
from custom_test_artes import RECIPES as CUSTOM_RECIPES, LAST_ID, unlock_assembly, DESCRIPTIONS as CUSTOM_DESCRIPTIONS
ALL_RECIPES = RECIPES + tuple((a,1,p,0,124,n,t,names[1]) for a,p,n,t,tree,level,pref,names in ARTES) + CUSTOM_RECIPES
SAVE = 'pushfq; push rax; push rcx; push rdx; push r8; push r9; push r10; push r11; sub rsp, 0x28'
RESTORE = 'add rsp, 0x28; pop r11; pop r10; pop r9; pop r8; pop rdx; pop rcx; pop rax; popfq'


def prepare(emit, mem, pe, data, state, usage):
    meta, launch = state, state+LAUNCH_OFFSET
    assert (LAST_ID+1)*24 <= LAUNCH_OFFSET
    assert LAUNCH_OFFSET+(LAST_ID+1)*8 <= 0x1ff0
    payload = bytearray(SIZE)
    for aid, char, physical, spell, effect, name, tp, _ in ALL_RECIPES:
        entry = bytearray(pe.get_data(0x562a50+physical*24,24))
        entry[0] = tp
        struct.pack_into('<I',entry,4,name)
        # +16 is Keele's casting-input sequence, an absolute relocated pointer.
        # The payload is outside the original PE relocation directory.
        entry[16:24] = bytes(8)
        payload[aid*24:aid*24+24] = entry
        entry = bytearray(pe.get_data(0x551780+physical*8,8))
        entry[0] = effect
        if aid in (130,131,133): entry[2]=8
        if aid in (134,135): entry[2]=2
        if aid==136: entry[1:4]=bytes((180,1,0))
        if aid==137: entry[1:4]=bytes((180,3,0))
        if aid==138: entry[1:4]=bytes((0,0,0))
        if aid==139: entry[1:4]=bytes((150,8,0))
        if aid>=140:
            from extra_test_magic import SPELLS
            from spirit_projectile_magic import SPELLS as SPIRIT_SPELLS
            spell=next(s for s in SPELLS+SPIRIT_SPELLS if s[0]==aid)
            entry[1:4]=bytes((spell[5],spell[6],0))
        # Native cooperative effects have their own voices; do not announce
        # the ingredient's name when launching the new standalone entry.
        entry[4:6] = b'\0\0'
        payload[LAUNCH_OFFSET+aid*8:LAUNCH_OFFSET+aid*8+8] = entry
    input_pointers = '\n'.join(
        f'mov rax, qword ptr {mem(0x562a50+p*24+16)}; '
        f'mov qword ptr {mem(meta+a*24+16)}, rax'
        for a,_,p,*_ in ALL_RECIPES)
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
        {input_pointers}
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
    farah_blocks=[]
    for aid,p,n,t,tree,level,pref,names in ARTES:
        levels=(0xc18,0xc20) if tree==6 else (0xc18,)
        farah_blocks.append(f'''cmp edx, {aid}; jne farah_{aid}
            {''.join(f'cmp byte ptr [r8+{off}], {level}; jb no; cmp byte ptr [r8+{off}], 30; ja no; ' for off in levels)}
            mov eax, dword ptr {mem(state+0x2ff0)}; test eax, eax; je no
            lea r9, {mem(0)}; add r9, rax
            mov r10d, {256+pref}; bt dword ptr [r9], r10d; jc no
            jmp yes
        farah_{aid}:''')
    unlocked=emit('teamup_unlocked',f'''
        test r8, r8; je no
        # Physical prototypes are suspended, including previously saved binds.
        cmp edx, 130; jb available
        cmp edx, 135; jbe no
        cmp edx, 138; je no
    available:
        {unlock_assembly(mem,data)}
        cmp edx, 130; jae farah
        cmp byte ptr {mem(data+0x1a63)}, 0
        je no
        {''.join(blocks)}
        jmp no
    farah:
        cmp ecx, 1; jne no
        cmp byte ptr {mem(data+0x1a41)}, 0; je no
        {''.join(farah_blocks)}
    no:
        xor eax, eax
        ret
    yes:
        mov eax, 1
        ret
    ''')
    from custom_test_artes import prepare_payload as custom_payload, TEST_ROSTER
    extra=custom_payload(pe,state,payload)
    from extra_test_magic import prepare as prepare_extra
    extra_magic=prepare_extra(pe,state,payload)
    from spirit_projectile_magic import prepare as prepare_spirit, prepare_spark
    spirit_magic=prepare_spirit(pe,state,payload)
    return dict(state_rva=state,size=SIZE,metadata=meta,launch=launch,
                frame_mem=(mem(state+0x5600),mem(state+0x5608),mem(0x12ceb74)),
                initialize=initialize,unlocked=unlocked,option_flag=35,
                usage_rva=usage,farah_artes=prepare_payload(pe,state,payload),
                approved_spark=prepare_spark(pe,state,payload),custom_artes=extra,extra_magic=extra_magic,spirit_magic=spirit_magic,test_roster=TEST_ROSTER,test_option_flag=36,
                recipes=[dict(id=a,character=c,physical=p,spell=s,
                    effect=e,name_message=n,tp=t,name=name) for a,c,p,s,e,n,t,name in ALL_RECIPES],
                native_test_entries=[dict(id=i,character=c) for c in (2,3) for i in (112,113)]), payload


def wire(emit,mem,jump,edit,pe,cs,relocate,data,info):
    meta,launch,initialize,unlocked=(info[k] for k in ('metadata','launch','initialize','unlocked'))
    # Redirect each audited metadata reader, including UI details and labels.
    refs=json.loads((Path(__file__).resolve().parents[1]/'audit/build-25190541/teamup-autonomous/table_refs.json').read_text())
    # This leaf function is absent from the PE unwind-function index used by
    # the original audit. Its unredirected cost lookup made valid artes red.
    redirected=[]
    for r in refs:
        site,target=int(r['site'],16),int(r['target'],16)
        if r['kind']!='indexed' or not 0x562a50<=target<0x563620 or site in (0x224396,0x227421,0x2277dd) or site in NAME_SITES:
            continue
        ins=next(cs.disasm(pe.get_data(site,15),site))
        new=bytearray(ins.bytes)
        struct.pack_into('<i',new,ins.disp_offset,meta+target-0x562a50)
        edit(site,bytes(new),'Standalone team-up metadata reader')
        redirected.append(site)
    old=relocate(pe.get_data(0x224396,9),0x224396)
    target=emit('teamup_menu_cost',f'''
        pushfq
        cmp rdx, {126*3}
        jb native_cost
        cmp rdx, {LAST_ID*3}
        ja native_cost
        popfq
        movzx r8d, byte ptr [r9+rdx*8+{meta:#x}]
        jmp 0x22439f
    native_cost:
        popfq
        {old}
        jmp 0x22439f
    ''')
    jump(0x224396,9,target,'Read virtual TP costs without changing native costs before table initialization')
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
    # The copied native entries 112/113 belong to Shizel. Select Meredy's
    # generic casting voice for her adaptations only; preserve the side CMP
    # flags consumed by the native branch at 113097 and all enemy voices.
    target=emit('custom_meredy_cast_voice',f'''
        movzx ecx, word ptr [rax+rbp*8+4]
        pushfq
        cmp byte ptr [rbx+0x51], 0; jne done
        cmp byte ptr [rbx+0x4f], 2; je mage
        cmp byte ptr [rbx+0x4f], 3; jne done
    mage:
        cmp ebp, 112; je personal
        cmp ebp, 113; je personal
        cmp ebp, 136; je personal
        cmp ebp, 137; je personal
        cmp ebp, 139; jb done
        cmp ebp, {LAST_ID}; ja done
    personal: mov ecx, 0x19c
        cmp byte ptr [rbx+0x4f], 3; je done
        movsx ecx, word ptr {mem(0x4e9290+2*2)}
    done: popfq; jmp 0x113094
    ''')
    jump(0x11308f,5,target,'Meredy adaptations use her generic cast voice, never Shizel')
    # Standalone arte admission remains checked even for an old page-A command
    # while the option is disabled. Native TP/target/ground rules follow.
    for site,size in ((0x112d10,8),(0x73790,5)):
        old=relocate(pe.get_data(site,size),site)
        target=emit(f'teamup_admit_{site:x}',f'''
            cmp edx, 112; je native_added
            cmp edx, 113; jne virtual_added
        native_added:
            cmp byte ptr [rcx+0x51], 0; jne native
            jmp validate_added
        virtual_added:
            cmp edx, 126
            jb native
            cmp edx, {LAST_ID}
            ja native
        validate_added:
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
            {f'''mov rcx, qword ptr [rsp+0x50]
            movzx eax, byte ptr [rcx+0x4f]; shl eax, 4
            lea r10, {mem(info['state_rva']+0x5500)}; add r10, rax
            mov qword ptr [r10], rcx; mov dword ptr [r10+8], edx''' if site==0x112d10 else ''}
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
        cmp ecx, {LAST_ID}
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
        cmp ebx, {LAST_ID}
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
        cmp r8d, {LAST_ID}
        ja native
        mov ecx, r8d
        sub ecx, 126
        mov edx, 1
        shl edx, cl
        xor dword ptr {mem(auto)}, edx
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
        cmp edi, {LAST_ID}
        ja native
        push rdx
        mov edx, edi
        sub edx, 126
        mov eax, dword ptr {mem(auto)}
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
        cmp ebx, {LAST_ID}
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
        cmp ebx, {LAST_ID}
        ja native
        mov ecx, ebx
        sub ecx, 126
        mov eax, dword ptr {mem(auto)}
        bt eax, ecx
        jc 0x73f6c
        mov edx, ebx
        jmp 0x73f21
    native:
        {old}
        jmp 0x73f0f
    ''')
    jump(0x73f09,6,target,'Use standalone AI preferences without native bitset access')
    # The native icon renderer has its own 126-entry category table. Resolve
    # only virtual IDs to their physical family before that lookup (all menus).
    mapping='\n'.join(f'cmp ecx, {aid}; jne icon_{aid}; mov ecx, {physical}; jmp icon_ready; icon_{aid}:'
                      for aid,_,physical,*_ in ALL_RECIPES)
    target=emit('teamup_icon',f'''
        {mapping}
    icon_ready:
        mov qword ptr [rsp+8], rbx
        jmp 0x42575
    ''')
    jump(0x42570,5,target,'Use native physical arte icons for standalone team-ups')

    # Virtual artes have no native learned/achievement bits. Both list layouts
    # must retain the availability/TP/Auto color already computed above.
    for site,aidreg,end in ((0x22511d,'ebx',0x22517b),(0x225f63,'edi',0x225fca)):
        old=relocate(pe.get_data(site,7),site)
        target=emit(f'teamup_known_colour_{site:x}',f'''
            cmp byte ptr {mem(data+0x1a64)}, 0
            je virtual_colour
            cmp {aidreg}, 112; je {end:#x}
            cmp {aidreg}, 113; je {end:#x}
        virtual_colour:
            cmp {aidreg}, 126
            jb native
            cmp {aidreg}, {LAST_ID}
            jbe {end:#x}
        native:
            {old}
            jmp {site+7:#x}
        ''')
        jump(site,7,target,'Retain standalone arte availability colors without native learned-bit reads')

    # Native Serpent Knuckle heals its caster by 50%. The standalone arte uses
    # 5%; the cooperative version and all other healing calls remain native.
    target=emit('teamup_serpent_heal',f'''
        mov edx, 50
        cmp byte ptr [rcx+0x4f], 1
        jne native_heal
        cmp byte ptr [rcx+0x51], 0
        jne native_heal
        cmp byte ptr [rcx+0x6d], 129
        jne native_heal
        mov edx, 5
    native_heal:
        jmp 0xca1a3
    ''')
    jump(0xca19e,5,target,'Standalone Serpent Knuckle: heal 5% of Farah max HP')
    info['serpent_heal_percent']=5

    # The native description pointer is resolved THREE times: cache check,
    # layout input and cache update. Replacing only the first loses our text.
    cursor=0x7000
    branches=[]
    for aid,_,_,_,_,_,_,name in ALL_RECIPES:
        fr,en={**DESCRIPTIONS,**CUSTOM_DESCRIPTIONS,126:("Abat une lame embrasée sur l'ennemi et le frappe avec la puissance du feu.","Brings a blazing blade down on the enemy, striking with the power of fire."),
               127:("Déchaîne la foudre sur l'ennemi dans une puissante attaque de paume.","Unleashes lightning on the enemy through a powerful palm strike."),
               128:("Projette une attaque tournoyante qui emporte l'ennemi dans un violent tourbillon.","Unleashes a spinning attack that engulfs the enemy in a fierce whirlwind."),
               129:("Frappe l'ennemi avec une onde d'énergie et rend à Farah 5 % de ses PV max.","Strikes the enemy with a wave of energy and restores 5% of Farah's max HP.")}[aid]
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
    assert cursor<0xa000
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
    for site,size,dest,continuation,original in (
        (0x22777e,6,'rcx',0x2277ab,'cmp r9d, -1; je 0x2277a8'),
        (0x2277dd,8,'rax',0x22781b,f'movsxd rax, dword ptr [rdi+rax*8+{meta+12:#x}]'),
    ):
        body=''.join(branches).replace('lea rax,','lea '+dest+',')
        target=emit(f'teamup_description_{site:x}',f'''
            {body}
            {original}
            jmp {site+size:#x}
        shown:
            jmp {continuation:#x}
        ''')
        jump(site,size,target,'Keep standalone effect descriptions through native layout and cache')
    info['metadata_readers']=redirected
    from custom_effect_identity import wire as wire_identity
    wire_identity(emit,mem,jump,info)
    from farah_regulus_artes import wire as wire_farah
    wire_farah(emit,mem,jump,info,pe,cs)
    from custom_test_artes import wire_magic
    wire_magic(emit,mem,jump,pe,relocate,info)
