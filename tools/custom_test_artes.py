"""Private level-one test roster; native saves and enemy versions stay intact."""
import struct
from build_profile import TEST_EDITION

FLAG_OFFSET = 0x1a64
LAST_ID = 145
# Virtual id, owner, metadata template, unused recipe field, effect, name, TP, English name.
RECIPES = (
    (134,0,14,0,124,15365,12,'Dragon Swarm'),
    (135,0,15,0,124,15368,16,'Dragon Flash'),
    (136,3,70,0,52,15381,48,'Tidal Wave'),
    (137,3,75,0,19,16597,24,'Fear Flare'),
    (138,1,25,0,124,17384,24,'Radiant Palm'),
    (139,3,91,0,60,16613,32,'Falling Finality'),
)
NAMES = {134:('Nuée de dragons','Dragon Swarm'),135:('Flash draconique','Dragon Flash'),
         136:('Lame de fond','Tidal Wave'),137:('Rafale ardente','Fear Flare'),
         138:('Paume rayonnante','Radiant Palm'),139:('Lame du néant','Falling Finality')}
DESCRIPTIONS = {
    134:("Avance en alternant des frappes de lame rapides. La puissance dépend du Tranchant de Reid.",
         "Advances with alternating rapid sword strikes. Power scales with Reid's Slash."),
    135:("Se rue vers l'ennemi avec une frappe éclair suivie d'un coup de lame. La puissance dépend du Tranchant de Reid.",
         "Dashes toward the enemy with a swift strike followed by a sword slash. Power scales with Reid's Slash."),
    136:("Une lame de fond balaie le terrain et frappe plusieurs fois les ennemis avec la puissance de l'eau.",
         "A tidal wave sweeps the battlefield, repeatedly striking enemies with water damage."),
    137:("Fait pleuvoir une rafale de projectiles ardents sur la zone ennemie. Chaque projectile inflige des dégâts de feu.",
         "Rains a barrage of burning projectiles over the enemy area. Each projectile deals fire damage."),
    138:("Projette trois sphères blanches depuis la paume. Chaque sphère inflige des dégâts neutres calculés sur le Poing de Farah.",
         "Fires three white spheres from the palm. Each sphere deals neutral damage scaling with Farah's Punch."),
    139:("Fait tomber une épée de ténèbres sur la cible. Un seul impact magique, sans les effets spéciaux de la Mystic Arte.",
         "Drops a dark sword onto the target. Deals one magic hit without the Mystic Arte's special effects."),
}
from extra_test_magic import RECIPES as EXTRA_RECIPES, NAMES as EXTRA_NAMES, DESCRIPTIONS as EXTRA_DESCRIPTIONS
RECIPES += EXTRA_RECIPES
NAMES.update(EXTRA_NAMES)
DESCRIPTIONS.update(EXTRA_DESCRIPTIONS)
from spirit_projectile_magic import RECIPES as SPIRIT_RECIPES, NAMES as SPIRIT_NAMES, DESCRIPTIONS as SPIRIT_DESCRIPTIONS
RECIPES += SPIRIT_RECIPES
NAMES.update(SPIRIT_NAMES)
DESCRIPTIONS.update(SPIRIT_DESCRIPTIONS)
MAGE_ROSTER=(113,136,139,140,141,142,143,144,145) if TEST_EDITION else ()
TEST_ROSTER = {0:(),1:(),2:MAGE_ROSTER,3:MAGE_ROSTER}
HELP = (
    "Accès de test dès le niveau 1, sans condition de maîtrise ni nombre d'utilisations.\nLes prototypes de Reid et Farah sont en suspens et ne sont plus ajoutés.\nKEELE ET MEREDY : Épée lumineuse, Lame de fond, Lame du néant, Invocation de Pluton, Éclat lumineux, Nuit nihiliste, Appel du démon, Aqualaser et Flèche du vent.\nLes coûts en PT et les règles de ciblage restent actifs. Les artes sont ajoutés temporairement à Techniques : désactivez cette option pour retrouver les conditions normales. Aucun niveau ni apprentissage de la sauvegarde n'est modifié.",
    "Level-one testing access, with no mastery or usage requirement.\nReid and Farah prototypes are paused and are no longer added.\nKEELE AND MEREDY: Prism Sword, Tidal Wave, Falling Finality, Summon Pluto, Shining Flare, Nihilistic Night, Summon Demon, Aqualaser and Wind Arrow.\nTP costs and targeting rules still apply. These artes are temporarily added to the Artes menu: turn this option off to restore normal requirements. No saved levels or learned lists are changed."
)

def unlock_assembly(mem,data):
    # Always qualify the approved additions, never via the testing override.
    approved = """cmp edx, 112; je volt
        cmp edx, 137; je efreet; jmp prototypes
    volt: mov eax, 5; mov r9d, 5; jmp spirit
    efreet: mov eax, 2; mov r9d, 10
    spirit:
        cmp ecx, 2; jb no; cmp ecx, 3; ja no
        lea r10d, [rcx+1]
        cmp byte ptr [r8+rax*8+0xbb8], r10b; jne no
        cmp byte ptr [r8+rax*8+0xbb9], r9b; jb no
        cmp byte ptr [r8+rax*8+0xbb9], 30; ja no
        jmp yes
    prototypes:
    """
    if not TEST_EDITION:
        return approved + 'normal_unlock:'
    blocks=[]
    for char,ids in TEST_ROSTER.items():
        blocks.append(f'cmp ecx, {char}; jne test_owner_{char}')
        blocks.extend(f'cmp edx, {aid}; je yes' for aid in ids)
        blocks.append(f'test_owner_{char}:')
    return approved + f'cmp byte ptr {mem(data+FLAG_OFFSET)}, 0; je normal_unlock\n'+ '\n'.join(blocks)+'\nnormal_unlock:'


def prepare_payload(pe,state,payload):
    from farah_regulus_artes import command as c
    # Reid motions 21 and 23 are the native Neosonic Swarm sword movements.
    swarm=(c(255,5,21)+c(0,13)+c(0,0,-5,0)+c(0,30,7)+c(5,5,23)+
           c(0,13)+c(0,30,7)+c(0,0,-4,0)+c(6,5,21)+c(0,13)+
           c(0,30,10)+c(0,0,-4,0)+c(5,5,23)+c(0,13)+c(0,30,14)+
           c(0,0,-3,0)+c(6,0,0,0)+c(6,23,10)+c(8,28))
    flash=(c(255,5,21)+c(0,13)+c(0,0,-12,0)+c(0,30,16)+
           c(4,5,23)+c(0,13)+c(0,0,-4,0)+c(0,30,22)+
           c(5,0,0,0)+c(5,23,10)+c(7,28))
    rows=[];cursor=0x3500
    for aid,owner,template,_,effect,message,tp,name in RECIPES:
        row=dict(id=aid,character=owner,runtime_validated=False)
        addresses=[]
        for s in NAMES[aid]:
            raw=(s+'\0').encode('utf8');addresses.append(state+cursor)
            payload[cursor:cursor+len(raw)]=raw;cursor+=len(raw)
        row['names']=addresses
        if owner==0:
            off=0x3000+(aid-134)*0x100;script={134:swarm,135:flash}[aid]
            assert len(script)<0xc0
            payload[off:off+len(script)]=script
            impact=bytearray(pe.get_data(0x5937c0,14))
            impact[0]=0x10;impact[1]=0;impact[2]=2
            struct.pack_into('<H',impact,10,70 if aid==134 else 160)
            payload[off+0xc0:off+0xce]=impact
            row.update(script=state+off,impact=state+off+0xc0,motion_bank='Reid')
        if aid==138:
            off=0x5000;script=c(255,5,25)+c(0,0,0,0)+c(254,255,28)
            payload[off:off+len(script)]=script
            impact=bytearray(pe.get_data(0x593580,14))
            impact[0]=0x10;impact[1]=0;impact[2]=2;impact[3]=12
            struct.pack_into('<H',impact,10,80)
            payload[off+0x40:off+0x4e]=impact
            payload[off+0x60:off+0x76]=struct.pack('<4h',-12,-12,12,12)+impact
            row.update(script=state+off,impact=state+off+0x40,projectile_impact=state+off+0x60,motion_bank='Farah')
        rows.append(row)
    # Lifetime script for the water-only effect. No Chat movement/hammer event.
    # Keep the instance marker until its frame callback releases it at 192.
    # The event VM clears +0x10 on -1, before dispatching the frame callback.
    payload[0x3300:0x3310]=struct.pack('<HhhhHhhh',0,-3,8,0,512,-1,0,0)
    impact=bytearray(pe.get_data(0x57d968,22))
    struct.pack_into('<4h',impact,0,-2048,-256,2048,64)
    impact[8]=0x80;impact[9]=1;impact[10]=2
    struct.pack_into('<H',impact,18,160)
    payload[0x3320:0x3336]=impact
    payload[0x3340:0x3356]=pe.get_data(0x58f390,22)
    struct.pack_into("<H",payload,0x3340+18,80)  # 18 meteors: 1440 nominal power; Explode: 1890.
    # An independent script identifies this instance without borrowing any
    # of the native resource/impact slots (0x48..0x78) or event slots (0x80+).
    payload[0x3360:0x3390]=pe.get_data(0x57c7a8,48)
    struct.pack_into('<H',payload,0x3388,512)
    # The dark blade keeps native resource 182, but has its own empty event
    # lifetime and ordinary INT-scaled impact. No 1999 fixed damage survives.
    payload[0x5100:0x5110]=struct.pack('<HhhhHhhh',0,-3,8,0,512,-1,0,0)
    blade=bytearray(pe.get_data(0x58b34e,0x4a))
    struct.pack_into('<4h',blade,0,0,0,0,0)
    struct.pack_into('<H',blade,0xc,28)
    struct.pack_into('<3b',blade,0x26,0,0,0)
    # Native 60 Hz mesh physics applies half the stored velocity per update.
    struct.pack_into('<4h',blade,0x2a,-128,256,0,0)
    struct.pack_into('<4h',blade,0x32,0,0,0,0)
    struct.pack_into('<4h',blade,0x3a,2048,512,0,0)
    payload[0x5140:0x518a]=blade
    impact=bytearray(pe.get_data(0x57c878,22))
    struct.pack_into('<4h',impact,0,-384,-768,384,64)
    impact[8]=0x80;impact[9]=8;impact[10]=2;impact[11]=12
    struct.pack_into('<H',impact,18,320)
    payload[0x51a0:0x51b6]=impact
    assert cursor<0x3800
    return rows

def wire_magic(emit,mem,jump,pe,relocate,info):
    from custom_effect_identity import step_guard
    from spirit_projectile_magic import wire as spirit_wire
    spirit_wire(emit,mem,jump,pe,relocate,info)
    from extra_test_magic import wire as extra_wire
    extra_wire(emit,mem,jump,pe,relocate,info)
    from falling_finality import wire
    wire(emit,mem,jump,pe,relocate,info)
    state=info['state_rva']
    from tidal_wave_presentation import wire as tidal_presentation
    water=tidal_presentation(emit,mem,jump,pe,relocate,state)
    info['tidal_presentation']=water
    def owned(aid,native):
        return f'''sub rsp, 0x20; call {info['identity']['lookup']:#x}; add rsp, 0x20
            test eax, eax; jne identified_{aid}
            mov rax, qword ptr [rcx]; test rax, rax; je {native}
            cmp byte ptr [rax+0x51], 0; jne {native}
            cmp byte ptr [rax+0x4f], 2; je mage_{aid}
            cmp byte ptr [rax+0x4f], 3; jne {native}
        mage_{aid}:
            movzx eax, byte ptr [rax+0x6d]
        identified_{aid}: cmp eax, {aid}; jne {native}'''
    # Replace only the player's water init. Resource 174 is still loaded and
    # released by the native large-effect dispatcher, with normal queueing.
    init=emit('custom_tidal_initialize',f'''
        push rax
        {owned(136,'native')}
        pop rax
        push rbx; sub rsp, 0x20; mov rbx, rcx
        call native_body
        mov rcx, rbx
        lea rax, {mem(state+0x3300)}; mov qword ptr [rcx+0x10], rax
        add rsp, 0x20; pop rbx; ret
    native: pop rax
    native_body:
        {relocate(pe.get_data(0xb7330,7),0xb7330)}
        jmp 0xb7337
    ''')
    jump(0xb7330,7,init,'Player Tidal Wave: water-only lifetime, no Chat commands')
    frame=emit('custom_tidal_frame',f'''
        push rax
        sub rsp, 0x20; call {info['identity']['lookup']:#x}; add rsp, 0x20
        cmp eax, 136; je custom
        lea rax, {mem(state+0x3300)}
        cmp qword ptr [rcx+0x10], rax; jne native_pop
    custom:
        pop rax
        cmp word ptr [rcx+0x3a], 2; je not_ready
        push rbx; sub rsp, 0x20; mov rbx, rcx
        call {water['render']:#x}
        {step_guard(info,'done')}
        cmp word ptr [rbx+0x38], 192; jae release
        movzx eax, word ptr [rbx+0x38]
        cmp eax, 32; jb done; cmp eax, 160; ja done
        test eax, 31; jne done
        mov rcx, rbx; lea rdx, [rbx+0x22]; lea r8, {mem(state+0x3320)}
        call 0x8f6e0
        # Native area collisions otherwise choose recoil from the centre of
        # the huge rectangle. Force the wave's direction, away from its mage.
        mov rax, qword ptr [rbx]
        mov al, byte ptr [rax+0x53]
        mov byte ptr {mem(0x12cf9ac)}, al
        lea rcx, {mem(0x12cf988)}; call 0x116260
        jmp done
    release: mov rcx, rbx; call 0x115ee0
    done: add rsp, 0x20; pop rbx; ret
    not_ready: ret
    native_pop: pop rax
    native:
        {relocate(pe.get_data(0xb7c90,11),0xb7c90)}
        jmp 0xb7c9b
    ''')
    jump(0xb7c90,11,frame,'Player Tidal Wave: native water renderer and five water impacts')
    # Fear Flare leaves live projectiles retaining this private descriptor.
    # Restore the shared pointer after the original frame, including enemies.
    tidal_frame=frame
    fear_init=emit('custom_fear_flare_initialize',f'''
        push rax
        {owned(137,'native')}
        pop rax
        push rbx; sub rsp, 0x20; mov rbx, rcx
        call native_body
        lea rax, {mem(state+0x3360)}; mov qword ptr [rbx+0x10], rax
        add rsp, 0x20; pop rbx; ret
    native: pop rax
    native_body:
        {relocate(pe.get_data(0x9d590,7),0x9d590)}
        jmp 0x9d597
    ''')
    jump(0x9d590,7,fear_init,'Remember player Fear Flare ownership for its whole lifetime')
    frame=emit('custom_fear_flare_frame',f'''
        push rax
        lea rax, {mem(state+0x3360)}
        cmp qword ptr [rcx+0x10], rax; jne native
        pop rax
        cmp word ptr [rcx+0x3a], 2; je not_ready
        {step_guard(info,'not_ready')}
        push rbx; sub rsp, 0x20
        mov rbx, qword ptr {mem(0x12ced28)}
        lea rax, {mem(state+0x3340)}
        mov qword ptr {mem(0x12ced28)}, rax
        call native_body
        mov qword ptr {mem(0x12ced28)}, rbx
        add rsp, 0x20; pop rbx; ret
    not_ready: ret
    native: pop rax
    native_body:
        {relocate(pe.get_data(0x9d630,6),0x9d630)}
        jmp 0x9d636
    ''')
    jump(0x9d630,6,frame,'Player Fear Flare: stable private projectile damage descriptor')
    from fear_flare_alignment import wire as align_fear
    align_fear(emit,mem,jump,pe,relocate,info)
    names=[]
    for row in info['custom_artes']:
        if row['character']!=3:continue
        fr,en=row['names'];aid=row['id']
        names.append(f'''cmp byte ptr [rbx+0x6d], {aid}; jne next_{aid}
            lea rcx, {mem(en)}; cmp byte ptr {mem(0x11c9ce8)}, 3; jne named
            lea rcx, {mem(fr)}; jmp named
        next_{aid}:''')
    hook=emit('custom_spell_announcement',f'''
        cmp byte ptr [rbx+0x51], 0; jne native
        cmp byte ptr [rbx+0x4f], 2; je mage
        cmp byte ptr [rbx+0x4f], 3; jne native
    mage:
        {''.join(names)}
    native:
        {relocate(pe.get_data(0xd56ba,8),0xd56ba)}
        jmp 0xd56c2
    named: jmp 0xd56f8
    ''')
    jump(0xd56ba,8,hook,'Announce custom magic after successful casting, in the selected language')
    info['custom_magic']=dict(tidal_initialize=init,tidal_frame=tidal_frame,fear_initialize=fear_init,
                             fear_frame=frame,resource_policy='native admission, lifetime and texture isolation',
                             runtime_validated=False)
