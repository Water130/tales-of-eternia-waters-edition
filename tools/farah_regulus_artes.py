"""Four player adaptations, using Farah motions and bounded shared effects.

No enemy actor, animation bank, AI script, fixed boss damage or scenario state
is copied. The names identify adaptations, not byte-identical boss sequences.
"""
import struct

# id, physical family template, message, TP, tree, level, preference, FR/EN
ARTES = (
    (130,25,17384,18,2,15,175,('Paume éclair','Palm Flash')),
    (131,27,16538,24,6,20,176,('Chaîne mirage','Mirage Chain')),
    (132,30,17385,32,2,25,177,('Poings du phénix','Phoenix Knuckles')),
    (133,31,17387,48,6,30,178,('Chaos divin','Divine Chaos')),
)
DESCRIPTIONS = {
    130:("Projette une sphère d’énergie droit devant Farah. La puissance dépend de son Poing.",
         'Fires a sphere of energy straight ahead. Its power scales with Farah’s Punch.'),
    131:("Avance en frappant rapidement, puis termine par une double paume. Sans extension automatique.",
         'Rushes forward with rapid strikes, finishing with a double palm. Has no automatic extension.'),
    132:("S’élève avec un poing embrasé et libère une sphère de feu ascendante. Peut être suivi d’un plongeon compatible.",
         'Rises with a flaming punch and releases an ascending fire sphere. Can link into a compatible dive.'),
    133:("Enchaîne paumes, frappes multiples et assaut rapide avant une paume finale puissante.",
         'Chains palm strikes, multiple blows and a rapid rush into a powerful final palm.'),
}
NAME_SITES = {
    0x222814:('rdi',24,'rcx',0x22285a),
    0x225188:('rax',3,'rcx',0x2251c4), 0x225234:('rax',3,'rcx',0x225270),
    0x225482:('rax',3,'rcx',0x2254be), 0x2255e9:('rax',3,'rcx',0x225625),
    0x225709:('rax',3,'rdx',0x225745), 0x2259d3:('rax',3,'rcx',0x225a0f),
    0x225fd7:('rcx',3,'rax',0x225fe4), 0x22605c:('rax',3,'rcx',0x226098),
    0x2278ce:('rax',3,'rcx',0x22790c),
    0x2442ae:('rax',3,'rcx',0x2442ea), 0x2447f7:('rax',3,'rcx',0x244833),
}

def command(phase,op,*args):
    return bytes((phase,op,*[x&255 for x in args]))

def scripts():
    c=command
    # Motion 25 can hold its last animation frame. The callback below owns
    # projectile/recovery timing; never wait for a nonexistent frame 5.
    palm=(c(255,5,25)+c(0,0,0,0)+c(254,255,28))
    # Each new motion resets its native phase counter. The interpreter then
    # continues at the following record, rather than restarting this script.
    mirage=(c(255,5,29)+c(0,0,-4,0)+c(0,12,8)+c(0,30,7)+
            c(2,13)+c(4,13)+c(6,13)+c(8,0,-2,0)+c(10,5,25)+
            c(0,0,-5,0)+c(0,13)+c(0,30,16)+c(2,18,4)+
            c(3,23,10)+c(4,0,0,0)+c(5,28))
    phoenix=(c(255,5,22)+c(0,7)+c(0,0,-8,0)+c(5,5,23)+
             c(2,22)+c(2,10,6)+c(2,18,6)+c(4,13)+c(4,30,14)+
             c(4,0,-2,-12)+c(4,14)+c(4,18,9)+c(4,23,30)+
             c(5,15,24)+c(5,1,0,5)+c(6,28))
    chaos=(c(255,5,25)+c(0,0,-4,0)+c(0,30,9)+c(0,12,12)+
           c(5,5,26)+c(0,13)+c(0,0,-4,0)+c(0,30,7)+c(0,12,8)+
           c(4,13)+c(8,13)+c(11,5,29)+c(0,13)+c(0,0,-4,0)+
           c(0,30,6)+c(2,13)+c(4,13)+c(6,13)+c(10,5,25)+
           c(0,13)+c(0,30,22)+c(0,12,24)+c(0,0,-5,0)+
           c(2,18,16)+c(3,23,10)+c(4,0,0,0)+c(5,28))
    return {130:palm,131:mirage,132:phoenix,133:chaos}

def prepare_payload(pe,state,payload):
    rows=[]
    cursor=0x2a00
    for aid,physical,message,tp,tree,level,pref,names in ARTES:
        off=0x2000+(aid-130)*0x200
        script=scripts()[aid];assert len(script)<0xc0
        payload[off:off+len(script)]=script
        impact=bytearray(pe.get_data(0x593580,14))
        impact[1]=3 if aid==132 else 0  # native element 3 = fire
        impact[3]=12
        impact[9]=1
        struct.pack_into('<H',impact,10,{130:80,131:70,132:140,133:90}[aid])
        payload[off+0xc0:off+0xce]=impact
        projectile=bytearray(struct.pack('<4h',-12,-12,12,12)+impact)
        projectile[8+3]=24
        struct.pack_into('<H',projectile,8+10,180 if aid==130 else 120)
        payload[off+0xd0:off+0xe6]=projectile
        name_ptrs=[]
        for name in names:
            raw=(name+'\0').encode('utf8');name_ptrs.append(state+cursor)
            payload[cursor:cursor+len(raw)]=raw;cursor+=len(raw)
        rows.append(dict(id=aid,names=name_ptrs,script=state+off,script_hex=script.hex(),impact=state+off+0xc0,
                         projectile_impact=state+off+0xd0,tree=tree,level=level,preference=pref,
                         motion_bank='Farah',runtime_validated=False))
    assert cursor<0x2ff0
    return rows

def extend_catalog(rows,node):
    trees={r['key']:r for r in rows if r['kind']==1}
    for aid,physical,message,tp,tree,level,pref,names in ARTES:
        row=trees[tree];used={n['lane'] for n in row['nodes'] if n['required']==level}
        lane=next(i for i in range(4) if i not in used)
        row['nodes'].append(node(level,(f'Arte · {tp} TP',f'Arte · {tp} TP'),names,
                                DESCRIPTIONS[aid],implemented=True,lane=lane,preference=pref))
        assert len(row['nodes'])<=12

def wire(emit,mem,jump,info,pe,cs):
    from custom_effect_identity import step_guard
    rows=info['farah_artes']
    extra=info['custom_artes']
    names_rows=rows+extra
    physical_rows=rows+[r for r in extra if r['character'] in (0,1)]
    spheres=next(r for r in extra if r['id']==138)
    def names(index,scale,dest,end):
        result=''
        for row in names_rows:
            aid=row['id'];fr,en=row['names']
            result+=f'''cmp {index}, {aid*scale}; jne name_{aid}
                lea {dest}, {mem(en)}
                cmp byte ptr {mem(0x11c9ce8)}, 3; jne name_done
                lea {dest}, {mem(fr)}
            name_done: jmp {end:#x}
            name_{aid}:'''.replace('name_done',f'name_done_{aid}')
        return result
    for site,(index,scale,dest,end) in NAME_SITES.items():
        ins=next(cs.disasm(pe.get_data(site,15),site))
        original=ins.mnemonic+' '+ins.op_str.replace('0x562a54',hex(info['metadata']+4))
        hook=emit(f'farah_arte_name_{site:x}',names(index,scale,dest,end)+
                  f'{original}; jmp {site+ins.size:#x}')
        jump(site,ins.size,hook,'Localized Farah adaptation names across native lists, details and shortcuts')
    announce=[]
    for row in names_rows:
        aid=row['id'];fr,en=row['names']
        announce.append(f'''lea rax, {mem(info['launch']+aid*8)}
            cmp rdi, rax; jne announce_{aid}
            lea rcx, {mem(en)}; cmp byte ptr {mem(0x11c9ce8)}, 3; jne announce
            lea rcx, {mem(fr)}; jmp announce
        announce_{aid}:''')
    hook=emit('farah_arte_announcement',f'''
        {''.join(announce)}
        sub rsp, 0x20; call 0x114dd0; add rsp, 0x20; jmp 0x112c58
    announce:
        mov qword ptr {mem(0x12cea88)}, rcx
        mov byte ptr {mem(0x12ceb90)}, 60
        mov byte ptr {mem(0x12ceb91)}, dl
        mov edx, 0x2c0; mov r8d, 0x1f0
        sub rsp, 0x20; call 0x2506e0; add rsp, 0x20; jmp 0x112c58
    ''')
    jump(0x112c53,5,hook,'Announce the selected Farah arte, retaining native Palm Strike for ordinary casts')
    # The Serpent Knuckle particle template is shared by all small effects
    # (114d8a -> 591de0, ca017 -> +151a). It needs no enemy texture bank.
    # Reserve a free collision slot first: native 116580 returns a dummy on
    # exhaustion, so never launch a damaging visual without a real slot.
    projectile=emit('farah_regulus_projectile',f'''
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx; mov rdi, rdx; mov esi, r8d
        {step_guard(info,'done')}
        test rdi, rdi; je create
        lea rax, {mem(0x12cee48)}; mov ecx, 60
    free: cmp byte ptr [rax+0x20], 0; je create
        add rax, 0x30; dec ecx; jne free; jmp done
    create:
        lea rcx, {mem(0x5932fa)}; call 0x8b7e0
        test rax, rax; je done
        cmp rax, qword ptr {mem(0x12cec20)}; je done
        mov rdx, rax
        movsx ecx, byte ptr [rbx+0x53]; imul ecx, -192
        mov word ptr [rdx+0x2a], cx
        mov ax, word ptr [rbx+0x10]; add ax, cx; mov word ptr [rdx], ax
        mov ax, word ptr [rbx+0x12]; sub ax, 640; mov word ptr [rdx+2], ax
        mov word ptr [rdx+0xc], 48
        mov word ptr [rdx+0x2c], 0; mov dword ptr [rdx+0x32], 0
        mov word ptr [rdx+0x26], 0; mov byte ptr [rdx+0x28], 0
    hyades:
        # Original Hyades sphere frames, copied into a managed embedded atlas.
        # Its lifetime is independent of the enemy actor/texture bank.
        mov byte ptr [rdx+8], 1; mov byte ptr [rdx+9], 1
        mov word ptr [rdx+0xe], 0x20
        mov word ptr [rdx+0xa], 0x10
        xor eax, eax
        cmp byte ptr [rbx+0x53], 0; jge orb_uv
        add eax, 384
    orb_uv:
        mov word ptr [rdx+0x12], ax; mov word ptr [rdx+0x14], 3840
        mov dword ptr [rdx+0x16], 0x008000c0
        mov dword ptr [rdx+0x1c], 0x00020002; mov word ptr [rdx+0x20], 12
        mov dword ptr [rdx+0x22], 0x28808080
        mov dword ptr [rdx+0x26], 0x00e0e0e0
        mov dword ptr [rdx+0x3a], 0x02000300
        mov dword ptr [rdx+0x3e], 0
        mov word ptr [rdx+0x42], 0x6000
        mov dword ptr [rdx+0x44], 0x10000400
        mov word ptr [rdx+0x48], 0
        cmp esi, 1; jne maybe_pulse
        mov word ptr [rdx+0x2c], -96
        mov byte ptr [rdx+0x23], 72; mov byte ptr [rdx+0x24], 24
    maybe_pulse:
        cmp esi, 2; jne collision
        mov word ptr [rdx+0xc], 12; mov word ptr [rdx+0x2a], 0
        mov dword ptr [rdx+0x3a], 0x01000180
        mov byte ptr [rdx+0x25], 0
        mov word ptr [rdx+0x26], 0xf8f8; mov byte ptr [rdx+0x28], 0xf8
    collision:
        test rdi, rdi; je done
        mov ecx, 5; mov r8, rbx; mov r9, rdi; call 0x116580
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    choices=[]
    for r in physical_rows:
        aid=r['id']
        choices.append(f'''cmp eax, {aid}; jne next_{aid}
            lea rdx, {mem(r['script'])}; lea r8, {mem(r['impact'])}
            jmp selected
        next_{aid}:''')
    callback=emit('farah_regulus_frame',f'''
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx; mov rsi, qword ptr [rcx]
        {step_guard(info,'done')}
        mov rax, rbx; lea rdi, {mem(0x12cfca0)}; sub rax, rdi
        cmp rax, 0x1200; jae release
        xor edx, edx; mov ecx, 0x120; div ecx
        test edx, edx; jne release
        lea rdi, {mem(info['state_rva']+0x3200)}; lea rdi, [rdi+rax*4]
        test rsi, rsi; je release
        cmp word ptr [rsi+0x3c], 1; jne release
        cmp dword ptr [rsi+0x2c], 0; jle release
        cmp byte ptr [rsi+0x52], 7; je release
        cmp byte ptr [rsi+0x52], 2; je release
        cmp word ptr [rbx+0x38], 0; je first_frame
        mov al, byte ptr [rsi+0x6e]; cmp al, byte ptr [rdi+1]; jne release
        cmp word ptr [rsi+0x8e], 124; jne release
        cmp qword ptr [rsi+0x230], 0; je release
        jmp initialize
    first_frame:
        mov dword ptr [rdi], 0
        mov al, byte ptr [rsi+0x6e]; mov byte ptr [rdi+1], al
        # The borrowed container schedules a native event at tick 18. Our
        # actor script owns the whole action; do not run that unrelated event.
        mov qword ptr [rbx+0x10], 0
        mov byte ptr [rbx+0x35], 0
    initialize:
        mov rcx, rbx; call {info['identity']['lookup']:#x}
        test eax, eax; jne has_identity
        movzx eax, byte ptr [rsi+0x6d]
    has_identity:
        {''.join(choices)}
        jmp release
    selected:
        mov rcx, rbx; call 0x116090
        # Native motion processing can temporarily enter recovery 5/6.
        # 116090 restores action 8; validate AFTER that native normalization.
        cmp byte ptr [rsi+0x52], 8; jne release
        cmp qword ptr [rsi+0x230], 0; je release
        cmp word ptr [rbx+0x38], 360; jae timeout
        cmp byte ptr [rsi+0x6d], 138; je triple_palm
        cmp byte ptr [rsi+0x6d], 130; jne other_visuals
        cmp word ptr [rbx+0x38], 30; jae timeout
        cmp byte ptr [rdi], 0; jne done
        cmp word ptr [rbx+0x38], 12; jae palm
        cmp byte ptr [rsi+0x23c], 2; jb done
        jmp palm
    triple_palm:
        cmp word ptr [rbx+0x38], 42; jae timeout
        movzx eax, byte ptr [rdi]; cmp eax, 3; jae done
        imul ecx, eax, 6; add ecx, 12
        movzx edx, word ptr [rbx+0x38]; cmp edx, ecx; jb done
        and eax, 1; lea r8d, [rax+3]
        inc byte ptr [rdi]
        lea rdx, {mem(spheres['projectile_impact'])}
        mov rcx, rsi; call {projectile:#x}; jmp done
    other_visuals:
        movzx eax, byte ptr [rsi+0x6d]
        cmp eax, 131; je pulse_check
        cmp eax, 133; je pulse_check
        jmp projectile_check
    pulse_check:
        mov ax, word ptr [rsi+0x23a]
        mov ah, byte ptr [rsi+0x23c]
        cmp ax, word ptr [rdi+2]; je done
        mov word ptr [rdi+2], ax
        cmp ah, 2; jb done
        test ah, 1; jne done
        mov rcx, rsi; xor edx, edx; mov r8d, 2
        call {projectile:#x}; jmp done
    projectile_check:
        cmp byte ptr [rdi], 0; jne done
        cmp byte ptr [rsi+0x23c], 2; jb done
        movzx eax, byte ptr [rsi+0x6d]
        cmp eax, 130; je palm
        cmp eax, 132; jne done
        cmp byte ptr [rsi+0x23a], 23; jne done
        cmp byte ptr [rsi+0x23c], 4; jb done
        lea rdx, {mem(rows[2]['projectile_impact'])}; mov r8d, 1; jmp spawn
    palm:
        lea rdx, {mem(rows[0]['projectile_impact'])}; xor r8d, r8d
    spawn:
        mov byte ptr [rdi], 1
        mov rcx, rsi; call {projectile:#x}; jmp done
    timeout:
        mov qword ptr [rsi+0x230], 0
        and byte ptr [rsi+0x62], 0xc5
        mov word ptr [rsi+0x18], 0
        mov byte ptr [rsi+0x52], 6; mov word ptr [rsi+0x44], 12
    release:
        mov rcx, rbx; call 0x115ee0
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx; ret
    ''')
    wrapper=emit('farah_regulus_dispatch',f'''
        push rax
        sub rsp, 0x20; call {info['identity']['lookup']:#x}; add rsp, 0x20
        cmp eax, 138; je custom
        cmp eax, 130; jb legacy
        cmp eax, 135; jbe custom
    legacy:
        mov rax, qword ptr [rcx]; test rax, rax; je native
        cmp byte ptr [rax+0x51], 0; jne native
        cmp byte ptr [rax+0x4f], 1; je farah
        cmp byte ptr [rax+0x4f], 0; jne native
        movzx eax, byte ptr [rax+0x6d]
        cmp eax, 134; jb native; cmp eax, 135; ja native; jmp custom
    farah:
        movzx eax, byte ptr [rax+0x6d]
        cmp eax, 138; je custom
        cmp eax, 130; jb native; cmp eax, 133; ja native
    custom:
        pop rax; jmp {callback:#x}
    native:
        pop rax; push rbx; sub rsp, 0x20; jmp 0xcaf36
    ''')
    jump(0xcaf30,6,wrapper,'Farah adaptations: independent finite scripts, shared native effect container')
    info['farah_callback']=callback;info['farah_projectile']=projectile
