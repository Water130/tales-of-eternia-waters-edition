"""Execute the actual injected x64 in Unicorn, with controlled native structures.
This is not a substitute for an in-game graphics/AI/concurrency test.
"""
import json, struct, sys
from pathlib import Path
from build_combat_patch import OUT, GAME, BACKUP, ORIGINAL_SHA256, digest, pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
from unicorn.x86_const import *

manifest=json.loads((OUT/'manifest.json').read_text())
binary=(OUT/'GameNative.dll').read_bytes()
pe=pefile.PE(data=binary)
assert digest(binary)==manifest['patched_sha256']
assert pe.verify_checksum()
assert pe.sections[-2].Characteristics==0x60000020
assert pe.sections[-1].Characteristics==0xc0000040
assert pe.OPTIONAL_HEADER.DATA_DIRECTORY[4].Size==0, 'Unexpected signature directory'
original=(BACKUP if BACKUP.exists() else GAME).read_bytes()
assert digest(original)==ORIGINAL_SHA256
for edit in manifest['edits']:
    pos=edit['offset']; old=bytes.fromhex(edit['original']); new=bytes.fromhex(edit['patched'])
    assert original[pos:pos+len(old)]==old
    assert binary[pos:pos+len(new)]==new
if 'without_spell_overlap' in manifest:
    fallback=bytearray(binary)
    profile=manifest['without_spell_overlap']
    for edit in manifest['edits']:
        if edit['name'] in profile['reverted_edits']:
            old=bytes.fromhex(edit['original']);pos=edit['offset']
            fallback[pos:pos+len(old)]=old
    struct.pack_into('<I',fallback,profile['checksum_offset'],profile['checksum'])
    assert pefile.PE(data=bytes(fallback)).verify_checksum()
    assert digest(fallback)==profile['sha256']

ACTORS=0x20000000
ENEMIES=0x20004000
STATS=0x20008000
IMPACT=0x20009000
STACK=0x30000000
SP=STACK+0xff08
REGS={'rax':UC_X86_REG_RAX,'rbx':UC_X86_REG_RBX,'rcx':UC_X86_REG_RCX,
      'rdx':UC_X86_REG_RDX,'rsi':UC_X86_REG_RSI,'rdi':UC_X86_REG_RDI,
      'rbp':UC_X86_REG_RBP,'r8':UC_X86_REG_R8,'r9':UC_X86_REG_R9,
      'r10':UC_X86_REG_R10,'r11':UC_X86_REG_R11,'r12':UC_X86_REG_R12,
      'r13':UC_X86_REG_R13,'r14':UC_X86_REG_R14,'r15':UC_X86_REG_R15}
passed=[]

for BASE in [0x180000000,0x7ffb00000000]:
    uc=Uc(UC_ARCH_X86,UC_MODE_64)
    uc.mem_map(BASE,pe.OPTIONAL_HEADER.SizeOfImage)
    uc.mem_write(BASE,pe.get_memory_mapped_image())
    uc.mem_map(ACTORS,0x10000)
    uc.mem_map(STACK,0x10000)
    DATA=BASE+manifest['data_rva']
    POOL=BASE+0x12cfca0
    PROJECTILES=BASE+0x12cee48
    def put(addr,fmt,*values):uc.mem_write(addr,struct.pack('<'+fmt,*values))
    def get(addr,fmt):return struct.unpack('<'+fmt,uc.mem_read(addr,struct.calcsize('<'+fmt)))[0]
    def reg(name,value):uc.reg_write(REGS[name],value)
    def reset():
        uc.mem_write(ACTORS,b'\0'*0x10000)
        uc.mem_write(BASE+0x12cea40,b'\0'*0x26c0)
        uc.mem_write(DATA,b'\0'*0x200) # keep allowlist
        for i,(name,number) in enumerate(REGS.items()):uc.reg_write(number,0x111000+i)
        uc.reg_write(UC_X86_REG_RSP,SP)
        uc.reg_write(UC_X86_REG_EFLAGS,0x202)
        put(BASE+0x12cecd8,'Q',ACTORS)
        put(BASE+0x12cece0,'Q',ENEMIES)
        put(BASE+0x12cece8,'BB',5,2)
        put(BASE+0x12d0ef7,'B',6)
        for i in range(5):
            a=ACTORS+i*0x248
            put(a+0x3c,'H',1);put(a+0x4f,'B',i if i<4 else 11)
            put(a+0x52,'B',8);put(a+0x64,'B',1)
            put(a+0xe8,'Q',STATS);put(a+0x2c,'i',1000);put(a+0x34,'h',10)
        put(STATS+0x1c,'h',100)
        put(ENEMIES+0x3c,'H',1);put(ENEMIES+0x51,'B',1);put(ENEMIES+0x2c,'i',1000)
    def run(name,stops):
        targets={BASE+s for s in stops}; reached=[]
        def stop(uc,address,size,user):
            if address in targets:
                reached.append(address-BASE);uc.emu_stop()
        handle=uc.hook_add(UC_HOOK_CODE,stop)
        uc.emu_start(BASE+manifest['symbols'][name],BASE+pe.OPTIONAL_HEADER.SizeOfImage,count=10000)
        uc.hook_del(handle)
        assert reached,(name,'no continuation reached')
        assert uc.reg_read(UC_X86_REG_RSP)==SP,(name,'stack imbalance')
        return reached[0]
    def impact_origin(char=0,action=1,side=0,magic=False,return_rva=0x822cd,ranged_tag=0):
        reset();actor=ACTORS+char*0x248
        put(actor+0x64,'B',action);put(actor+0x51,'B',side)
        put(actor+0xd8,'B',0x80 if magic else 0)
        reg('rcx',actor);reg('rdx',ENEMIES);reg('r9',actor+0xd8)
        put(SP,'Q',BASE+return_rva)
        if return_rva==0x1164e3:
            reg('rsi',PROJECTILES+0x30*5);reg('r9',IMPACT)
            put(IMPACT,'B',0x80 if magic else 0);put(DATA+0x100+5,'B',ranged_tag)
        saved={r:uc.reg_read(v) for r,v in REGS.items()}
        run('damage_origin',[0x8e915])
        assert saved=={r:uc.reg_read(v) for r,v in REGS.items()},'entry register corruption'
        return get(DATA,'Q')

    if 'spell_textures' in manifest:
        from test_spell_palette_patch import check_spell_palettes
        n=check_spell_palettes(uc,BASE,manifest,SP,put,get,reg,REGS)
        passed.append(f'{BASE:x}: {n} native CLUT load/draw cases; Air Thrust then Spread, reverse/repeat loads and unrelated fallback')
        from test_spell_texture_patch import check_spell_textures
        n=check_spell_textures(uc,BASE,manifest,ACTORS,SP,reset,put,get,reg,REGS)
        passed.append(f'{BASE:x}: {n} native spell texture cases; overlapping loads retain per-spell descriptors, part links, binding and UV scale')
    if 'particle_capacity' in manifest:
        from test_particle_capacity_patch import check_particle_capacity
        n=check_particle_capacity(uc,BASE,manifest,SP,reset,put,get,reg,REGS)
        passed.append(f'{BASE:x}: {n} native particle allocations/updates; capacity, pause, reuse, clear and battle reset')

    if 'tp' in manifest['features']:
        for ch in range(4):assert impact_origin(ch)==ACTORS+ch*0x248
        assert impact_origin(4)==ACTORS+3*0x248,'Quickie owner'
        for action in [15,31,47,255]:assert impact_origin(action=action)==0
        assert impact_origin(side=1)==0
        assert impact_origin(magic=True)==0
        assert impact_origin(return_rva=0x976a9)==0
        assert impact_origin(return_rva=0x1164e3,ranged_tag=0)==0
        assert impact_origin(return_rva=0x1164e3,ranged_tag=1)==ACTORS
        assert impact_origin(action=31,return_rva=0x1164e3,ranged_tag=1)==ACTORS,'basic projectile retains provenance'
        assert impact_origin(magic=True,return_rva=0x1164e3,ranged_tag=1)==0
        passed.append(f'{BASE:x}: basic/arte/magic/enemy/projectile origin and Quickie attribution')
        for ch,gain in [(0,1),(1,1),(2,2),(3,2),(4,1),(5,1),(6,1)]:
            for initial,maximum,damage,battle in [(10,100,30,True),(99,100,30,True),(100,100,30,True),(10,100,0,True),(10,100,30,False)]:
                reset();put(ACTORS+0x4f,'B',ch);put(ACTORS+0x34,'h',initial);put(STATS+0x1c,'h',maximum)
                put(DATA,'Q',ACTORS);reg('rdi',ENEMIES);reg('rsi',damage)
                uc.reg_write(UC_X86_REG_EFLAGS,0x242 if battle else 0x202)
                saved={r:uc.reg_read(v) for r,v in REGS.items()}
                run('tp_on_hp_commit',[0x8f0a1])
                assert saved=={r:uc.reg_read(v) for r,v in REGS.items()}
                expected=min(initial+gain,maximum) if damage>0 and battle else initial
                assert get(ACTORS+0x34,'h')==expected,(ch,initial,damage,battle)
                assert get(ENEMIES+0x2c,'i')==1000-(damage if battle else 0)
        reset();reg('rdi',ENEMIES);reg('rsi',50);uc.reg_write(UC_X86_REG_EFLAGS,0x242)
        run('tp_on_hp_commit',[0x8f0a1]);assert get(ACTORS+0x34,'h')==10
        passed.append(f'{BASE:x}: 35 HP/TP commit cases, caps, no damage and no credit')
        for caller,action,side,tag in [(0x70d3e,1,0,1),(0x70ef7,1,0,1),(0x70d3e,31,0,0),(0x70d3e,1,1,0),(0x941e0,1,0,0)]:
            reset();put(ACTORS+0x64,'B',action);put(ACTORS+0x51,'B',side)
            reg('rax',PROJECTILES+5*0x30);reg('r8',ACTORS);reg('rdx',IMPACT);reg('r11',5)
            put(SP,'Q',BASE+caller);put(DATA+0x100+5,'B',1)
            saved={r:uc.reg_read(v) for r,v in REGS.items()}
            run('projectile_origin',[0x116609])
            assert get(DATA+0x100+5,'B')==tag
            assert get(PROJECTILES+5*0x30,'Q')==IMPACT
            assert saved=={r:uc.reg_read(v) for r,v in REGS.items()}
        passed.append(f'{BASE:x}: projectile provenance captured and stale tags cleared')

    if 'camera' in manifest['features']:
        from test_camera_patch import check_camera
        count=check_camera(uc,BASE,DATA,ACTORS,ENEMIES,STATS,IMPACT,SP,
                           reset,put,get,reg,run,REGS,
                           (UC_HOOK_CODE,UC_X86_REG_RSP,UC_X86_REG_EFLAGS))
        passed.append(f'{BASE:x}: {count} adaptive camera cases; native projection, changing targets, effect overwrite and transitions')

    if 'no_freeze' in manifest['features']:
        for active,large,battle,expected in [(True,1,6,0),(True,0,6,60),(False,0,6,60),(True,1,0,60)]:
            reset();put(BASE+0x12d0ef7,'B',battle);put(BASE+0x12d0eae,'H',60)
            put(BASE+0x12ceb7a,'B',1);put(BASE+0x12cea58,'H',90)
            if active:put(POOL,'Q',ACTORS);put(POOL+0x33,'B',large)
            run('remove_spell_freeze',[0xd2e68])
            assert get(BASE+0x12d0eae,'H')==expected
            assert get(BASE+0x12ceb7a,'B')==1,'menu pause changed'
            assert get(BASE+0x12cea58,'H')==90,'Time Stop timer changed'
        reset();assert run('skip_spell_freeze_command',[0x866aa,0x866bc])==0x866bc
        reset();put(BASE+0x12d0ef7,'B',0);reg('r11',IMPACT);put(IMPACT+10,'H',30)
        assert run('skip_spell_freeze_command',[0x866aa,0x866bc])==0x866aa
        assert uc.reg_read(UC_X86_REG_RAX)==30
        passed.append(f'{BASE:x}: spell cinematic freeze removed; menu and Time Stop state preserved')

    if 'concurrent_spells' in manifest['features']:
        # Exercise every pair in the supported list, plus loading and special cases.
        reset();reg('rbp',0xffffffffffffffff)
        assert run('guarded_spell_dispatch',[0x1149a6,0x1149c6])==0x1149c6
        for new in manifest['concurrent_effect_allowlist']:
            for active in manifest['concurrent_effect_allowlist']+[26,34,58,70]:
                reset();reg('rbp',new);put(POOL,'Q',ACTORS);put(POOL+0x33,'B',1)
                put(POOL+0x36,'B',active);put(POOL+0x3a,'H',1);put(BASE+0x12d0eaa,'H',0xffff)
                expected=0x1149a6 if active!=new and active in manifest['concurrent_effect_allowlist'] else 0x1149c6
                assert run('guarded_spell_dispatch',[0x1149a6,0x1149c6])==expected,(new,active)
        for state,init in [(2,0),(1,1)]:
            reset();reg('rbp',2);put(POOL,'Q',ACTORS);put(POOL+0x33,'B',1)
            put(POOL+0x36,'B',1);put(POOL+0x3a,'H',state);put(POOL+0x3e,'H',init)
            assert run('guarded_spell_dispatch',[0x1149a6,0x1149c6])==0x1149c6
        reset();reg('rbp',26);assert run('guarded_spell_dispatch',[0x1149a6,0x1149c6])==0x1149a6
        reset();reg('rbx',POOL);reg('r9',0);put(POOL,'Q',ACTORS);put(POOL+0x33,'B',1)
        put(POOL+0x120,'Q',ACTORS+0x248);put(POOL+0x153,'B',1)
        run('retain_active_spell_context',[0x115f3a]);assert get(BASE+0x12d0ea0,'Q')==POOL+0x120
        assert get(BASE+0x12d0eaa,'H')==0xffff
        reset();reg('rbx',POOL);reg('r9',0)
        run('retain_active_spell_context',[0x115f3a]);assert get(BASE+0x12d0ea0,'Q')==0
        passed.append(f'{BASE:x}: 896 effect pairs, loader serialization, same-ID/special exclusion, final context cleanup')

    if 'camera_floor' in manifest['features']:
        from test_camera_floor_patch import check_floor
        count = check_floor(uc,BASE,DATA,manifest,ACTORS,SP,reset,put,get,reg,REGS)
        passed.append(f'{BASE:x}: {count} native ground renderer cases; viewport coverage, unchanged backdrop/interior/camera/gameplay, no black bottom fill, guarded fallback')

    if 'camera' in manifest['features']:
        from test_spread_visual_patch import check_spread
        count=check_spread(uc,BASE,manifest,ACTORS,SP,reset,put,get,reg,REGS)
        passed.append(f'{BASE:x}: {count} native Spread meshes; vanilla body vertices/UVs preserved, closed textured upper rim, restored scratch, capacity/phase guards')
        from test_ondine_visual_patch import check_ondine
        count=check_ondine(uc,BASE,manifest,ACTORS,SP,reset,put,get,reg,REGS)
        passed.append(f'{BASE:x}: {count} native Ondine water-decor cases; actual projected mesh and submitted edge polygons, unchanged interior/world mesh/camera/gameplay')
        from test_shadow_visual_patch import check_shadow
        count=check_shadow(uc,BASE,DATA,ACTORS,SP,reset,put,get,reg,REGS)
        passed.append(f'{BASE:x}: {count} native shadow layout cases; depth-scaled thickness and offset, native width/texture/phase guards, no gameplay writes')

    if 'victory_tp' in manifest['features'] or 'summon_modifier' in manifest['features']:
        from test_recovery_summon_patch import check_recovery_summon
        checks, count = check_recovery_summon(uc,BASE,manifest,ACTORS,ENEMIES,STATS,IMPACT,SP,
                                             reset,put,get,reg,REGS)
        passed.extend(f'{BASE:x}: {check}' for check in checks)
        passed.append(f'{BASE:x}: {count} recovery/summon native execution cases')

    if 'summon_hold' in manifest['features'] or 'casting_colors' in manifest['features']:
        from test_cast_hold_patch import check_cast_hold
        checks, count = check_cast_hold(uc,BASE,manifest,ACTORS,ENEMIES,STATS,IMPACT,SP,
                                       reset,put,get,reg,REGS)
        passed.extend(f'{BASE:x}: {check}' for check in checks)
        passed.append(f'{BASE:x}: {count} held-cast and casting-color execution cases')

    if 'startup_opening' in manifest['features']:
        from test_startup_patch import check_startup
        count=check_startup(uc,BASE,manifest,SP,reset,put,get,reg,REGS)
        passed.append(f'{BASE:x}: {count} native startup transitions; resource/options loading and load-error acknowledgement retained; opening index 0 then title')

    if 'combat_ui' in manifest['features'] or 'damage_colors' in manifest['features']:
        from test_combat_ui_patch import check_combat_ui
        checks, count = check_combat_ui(uc,BASE,manifest,ACTORS,ENEMIES,STATS,IMPACT,SP,
                                       reset,put,get,reg,REGS)
        passed.extend(f'{BASE:x}: {check}' for check in checks)
        passed.append(f'{BASE:x}: {count} damage-color and gauge native execution cases')
        if 'combat_ui' in manifest['features']:
            from test_spirit_icon_patch import check_spirit_icons
            count=check_spirit_icons(uc,BASE,manifest,SP,reset,put,get,reg,REGS)
            passed.append(f'{BASE:x}: {count} native spirit atlas cases; ten palette assets, four party slots, command binding, resource lookup, UVs, capacity and missing-manager guards')

    if 'mod_settings' in manifest['features']:
        from test_title_logo_patch import check_title_logo
        count=check_title_logo(uc,BASE,manifest,SP,reset,put,get,reg,REGS)
        passed.append(f'{BASE:x}: {count} title logo cases; actual native PNG registration, deferred load, one-time cache, destruction, transparent quad UVs, allocation/capacity/load failure fallback')
        from test_mod_settings_patch import check_settings
        count=check_settings(uc,BASE,manifest,ACTORS,ENEMIES,STATS,SP,reset,put,get,reg,REGS)
        passed.append(f'{BASE:x}: {count} mod settings cases; native title navigation, French/English fallback, per-feature switches, Unicode per-user INI persistence, errors and ABI')

    if 'skit_notice' in manifest['features']:
        from test_skit_notice_patch import check_skit_notice
        count=check_skit_notice(uc,BASE,manifest,ACTORS,SP,reset,put,get,reg,REGS)
        passed.append(f'{BASE:x}: {count} camp-skit notice cases; world/field native selector differential, 264 seen slots, no save writes, transition guards, original global submission, both HUD callsites/ABI, four-corner collision/fallback, native window/font queue, French/English, GPU/font state restoration without scene reset')

    if 'artesphere' in manifest['features']:
        from test_artesphere_patch import check_artesphere
        count,checks=check_artesphere(uc,BASE,manifest,ACTORS,SP,reset,put,get,reg,REGS)
        passed.extend(f'{BASE:x}: {check}' for check in checks)
        passed.append(f'{BASE:x}: {count} artesphere native execution cases')

report={'passed':True,'patched_sha256':digest(binary),'checks':passed,
        'runtime_validated':False,'note':'Actual x64 hook execution in an emulator; rendering, engine concurrency, Quickie routing and gameplay still require user testing.'}
(OUT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
