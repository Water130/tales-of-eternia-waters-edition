"""Private player entries for four verified native spell resource pipelines.

Their native texture/visual lifetimes remain serialized by the effect queue.
Dedicated attack descriptors never modify the enemy versions or save records.
"""
import struct

# id, effect, template, message, TP, cast, element, init, script, length, damage
SPELLS = (
    (140,57,91,16611,56,180,8,0xbc540,0x58a2e0,224,0x589f10),
    (141,63,90,16614,44,150,7,0xbed50,0x58bb50,264,0x58b910),
    (142,67,79,16617,48,180,8,0xc1440,0x58ceb0,144,0x58cc90),
    (143,16,91,16596,48,180,8,0x9c670,0x57bee0,344,0x57bd08),
)
NAMES={140:('Invocation de Pluton','Summon Pluto'),141:('Éclat lumineux','Shining Flare'),
       142:('Nuit nihiliste','Nihilistic Night'),143:('Appel du démon','Summon Demon')}
DESCRIPTIONS={
140:("Invoque Pluton, qui frappe les ennemis et projette des sphères de ténèbres.",
     "Summons Pluto to strike enemies and unleash spheres of darkness."),
141:("Des flammes lumineuses convergent sur la zone ennemie et infligent des dégâts de feu et de lumière.",
     "Radiant flames converge on the enemy area, dealing fire and light damage."),
142:("Une nuée de projectiles obscurs s'abat sur les ennemis et leur inflige des dégâts de ténèbres.",
     "A swarm of dark projectiles descends on enemies, dealing darkness damage."),
143:("Appelle une apparition démoniaque qui frappe à plusieurs reprises la zone ennemie avec les ténèbres.",
     "Calls forth a demonic apparition that repeatedly strikes the enemy area with darkness."),
}
RECIPES=tuple((a,3,t,0,e,msg,tp,NAMES[a][1]) for a,e,t,msg,tp,*_ in SPELLS)

def prepare(pe,state,payload):
    rows=[]
    for i,(aid,effect,template,msg,tp,cast,element,init,script,size,impact) in enumerate(SPELLS):
        off=0x5800+i*0x200
        raw=pe.get_data(script,size)
        assert struct.unpack_from('<h',raw,len(raw)-6)[0]==-1
        payload[off:off+size]=raw
        if aid==142:
            # Initial -3 event: target X rather than the caster's X.
            struct.pack_into('<h',payload,off+4,1)
        count=2 if aid in (140,141) else 1
        for j in range(count):
            desc=bytearray(pe.get_data(impact+j*22,22))
            desc[8]=0x80;desc[10]=2
            if aid==142: desc[9]=8
            if aid==141:
                # Cover the luminous columns including their ground contact.
                struct.pack_into('<4h',desc,0,-48,-192,48,8)
                desc[11]=6
            # Preserve each visual's element. Remove boss status procs.
            # +17 indexes the native recoil table, not a hit cooldown. Keep
            # Shining Flare's two native reactions; Demon uses vertical lift.
            desc[15:17]=bytes((0,0))
            if aid==143: desc[17]=10  # Native (0, -128), no horizontal ejection.
            elif aid!=141: desc[17]=8
            struct.pack_into('<H',desc,18,{140:120 if j else 180,141:200,142:180,143:100}[aid])
            payload[off+0x180+j*22:off+0x196+j*22]=desc
        rows.append(dict(id=aid,effect=effect,initialize_native=init,script=state+off,
                         impact=state+off+0x180,script_size=size,runtime_validated=False))
    return rows

def wire(emit,mem,jump,pe,relocate,info):
    for r in info['extra_magic']:
        aid,site,script,impact=(r[k] for k in ('id','initialize_native','script','impact'))
        hook=emit(f'extra_magic_init_{aid}',f'''
            push rbx; sub rsp, 0x20; mov rbx, rcx
            call {info['identity']['lookup']:#x}
            cmp eax, {aid}; jne native
            call native_body
            lea rax, {mem(script)}; mov qword ptr [rbx+0x10], rax
            lea rax, {mem(impact)}; mov qword ptr [rbx+0x78], rax
            add rsp, 0x20; pop rbx; ret
        native:
            add rsp, 0x20; pop rbx
        native_body:
            {relocate(pe.get_data(site,7),site)}
            jmp {site+7:#x}
        ''')
        jump(site,7,hook,f'Private {aid}: retain native resource pipeline, independent scaled damage')
        r['initialize']=hook
    # Two native callbacks reference their damage table directly instead of
    # effect+78; select the corresponding private pair for player instances.
    for aid,site,register,fx,native in ((140,0xbcaa7,'r9','rdi',0x589f26),
                                       (141,0xbee7a,'r12','r14',0x58b910)):
        r=next(r for r in info['extra_magic'] if r['id']==aid)
        hook=emit(f'extra_magic_impact_{aid}',f'''
            pushfq; push rax
            lea {register}, {mem(native)}
            lea rax, {mem(r['script'])}; cmp qword ptr [{fx}+0x10], rax; jne done
            lea {register}, {mem(r['impact']+(22 if aid==140 else 0))}
        done: pop rax; popfq; jmp {site+7:#x}
        ''')
        jump(site,7,hook,f'Private {aid}: projectile and mixed-element damage descriptors')
    shining=next(r for r in info['extra_magic'] if r['id']==141)
    frame=info['state_rva']+0x5600
    gate=emit('shining_flare_collision_step',f'''
        push rax
        lea rax, {mem(shining['impact'])}; cmp r12, rax; jne native
        cmp qword ptr {mem(frame)}, r14; jne native
        cmp dword ptr {mem(frame+8)}, 1; pop rax; jmp 0xbeec0
    native:
        cmp byte ptr {mem(0x12ceb7a)}, 0; pop rax; jmp 0xbeec0
    ''')
    jump(0xbeeb9,7,gate,'Player Shining Flare: collisions follow the native effect tick during transitions')

    night=next(r for r in info['extra_magic'] if r['id']==142)
    # The script's target-centred initial event does not affect these two
    # callbacks: vanilla explicitly puts both lightning endpoints at X=0xac0.
    for site,size,endpoint in ((0xc16df,5,False),(0xc1748,6,True)):
        hook=emit(f'nihilistic_lightning_origin_{site:x}',f'''
            pushfq; push rdx
            lea rdx, {mem(night['script'])}
            cmp qword ptr [rsi+0x10], rdx; jne native
            {'push rax' if endpoint else ''}
            movsx eax, word ptr [rsi+0x20]
            {'mov word ptr [r8], ax; pop rax' if endpoint else ''}
            jmp done
        native:
            {'mov word ptr [r8], 0xac0' if endpoint else 'mov eax, 0xac0'}
        done:
            pop rdx; popfq; jmp {site+size:#x}
        ''')
        jump(site,size,hook,'Nihilistic Night: anchor background lightning to its eruption zone')
