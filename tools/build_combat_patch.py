"""Build a reversible, version-locked native combat experiment. Never installs it.

RVA addresses refer ONLY to Steam build 25190541 / ORIGINAL_SHA256.
x64 hooks are position independent.
"""
from pathlib import Path
import argparse, hashlib, json, re, struct, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(HERE/'pydeps'), str(HERE/'patchdeps')]
import pefile
import capstone
from keystone import Ks, KS_ARCH_X86, KS_MODE_64

ORIGINAL_SHA256 = '6488be2ce5ecc1dc9fc0216aa2462ec9aeba7a464468d5fd61ad3c2a8356849b'
GAME = ROOT/'backups/build-25190541/GameNative.dll'
OUT = ROOT/'build/combat-test'
BACKUP = ROOT/'backups/build-25190541/GameNative.dll'
KS = Ks(KS_ARCH_X86, KS_MODE_64)
CS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
CS.detail = True
align = lambda value, alignment: (value+alignment-1)//alignment*alignment
digest = lambda b: hashlib.sha256(b).hexdigest()

def build(features):
    if 'mod_settings' in features and 'combat_ui' not in features:
        raise ValueError('mod_settings requires combat_ui for its native panel renderer')
    if 'difficulty_rebalance' in features and 'mod_settings' not in features:
        raise ValueError('difficulty_rebalance requires mod_settings for its optional switch')
    if 'multiple_vitality' in features and 'mod_settings' not in features:
        raise ValueError('multiple_vitality requires mod_settings for its optional switch')
    if 'cast_defense' in features and 'mod_settings' not in features:
        raise ValueError('cast_defense requires mod_settings for its independent switches')
    source = BACKUP if BACKUP.exists() else GAME
    original = source.read_bytes()
    if digest(original) != ORIGINAL_SHA256:
        raise RuntimeError('Unsupported original DLL; nothing generated.')
    pe = pefile.PE(data=original)
    section_alignment = pe.OPTIONAL_HEADER.SectionAlignment
    code_rva = align(max(s.VirtualAddress + max(s.Misc_VirtualSize,s.SizeOfRawData) for s in pe.sections), section_alignment)
    code_capacity = 0xc000
    data_rva = code_rva + code_capacity
    credit = data_rva
    projectile_tags = data_rva+0x100  # one byte for each native 0x30 projectile slot
    code = bytearray()
    hooks, edits, symbols = [], [], {}
    references = {}
    active_gate = None
    gates = []

    def relocate(raw, rva):
        lines = []
        for ins in CS.disasm(raw, rva):
            operands = ins.op_str
            for op in ins.operands:
                if op.type == capstone.x86.X86_OP_MEM and op.mem.base == capstone.x86.X86_REG_RIP:
                    target = ins.address + ins.size + op.mem.disp
                    operands = re.sub(r'\[rip[^\]]*\]', mem(target), operands)
            lines.append(ins.mnemonic + ' ' + operands)
        return '\n'.join(lines)

    def mem(target):
        sentinel = 0x13500000 + len(references)*0x100
        references[sentinel] = target
        return f'[rip + {sentinel:#x}]'

    def emit(name, assembly):
        code.extend(b'\xcc' * (align(len(code),16)-len(code)))
        start = code_rva+len(code)
        encoded, _ = KS.asm(assembly, addr=start)
        buf = bytearray(encoded)
        for ins in CS.disasm(bytes(buf), start):
            for operand in ins.operands:
                if operand.type == capstone.x86.X86_OP_MEM and operand.mem.base == capstone.x86.X86_REG_RIP:
                    if operand.mem.disp in references:
                        target = references[operand.mem.disp]
                        offset = ins.address-start+ins.disp_offset
                        struct.pack_into('<i',buf,offset,target-(ins.address+ins.size))
        code.extend(buf)
        symbols[name] = start
        hooks.append({'name':name,'rva':start,'size':len(buf),'assembly':assembly})
        return start

    result = bytearray(original)

    def edit(rva, new, name, instruction=True):
        old = pe.get_data(rva,len(new))
        if instruction:
            decoded = list(CS.disasm(old,rva))
            if sum(i.size for i in decoded) != len(new):
                raise ValueError(f'Patch splits instruction: {name} {rva:x}')
        flag = active_gate
        if 'mod_settings' in features and flag is not None:
            if isinstance(flag, dict):flag = flag.get(rva)
            if flag is not None:
                assert instruction and len(new) >= 5
                # Preserve incoming flags (notably the conditional HP commit).
                # Both paths execute relocated instructions, never self-modify text.
                reset_camera = f'mov byte ptr {mem(data_rva+0x20)}, 0' if rva == 0x10d515 else ''
                gate = emit(f'option_gate_{rva:x}', f'''
                    pushfq
                    cmp byte ptr {mem(data_rva+0x1a00+flag)}, 0
                    je original
                    popfq
                    {relocate(new,rva)}
                    jmp {rva+len(new):#x}
                original:
                    {reset_camera}
                    popfq
                    {relocate(old,rva)}
                    jmp {rva+len(new):#x}
                ''')
                gates.append(dict(site=rva, flag=flag, gate=gate, size=len(new), enabled=new.hex(), original=old.hex()))
                new = b'\xe9'+struct.pack('<i',gate-rva-5)+b'\x90'*(len(new)-5)
        offset = pe.get_offset_from_rva(rva)
        result[offset:offset+len(new)] = new
        edits.append({'name':name,'rva':rva,'offset':offset,'original':old.hex(),'patched':new.hex()})

    def jump(rva, size, destination, name):
        edit(rva,b'\xe9'+struct.pack('<i',destination-rva-5)+b'\x90'*(size-5),name)

    if 'tp' in features:
        active_gate = 2
        # The same impact routine receives spells and artes. Identify the origin at
        # entry; award only at the native HP subtraction, never on effect creation.
        # Ordinary melee: native actor hitboxes + normal combo class (<0x0f).
        # Ranged: tags captured ONLY at actor animation projectile creation, not
        # inferred from the caster's later action (which could already have changed).
        start = emit('projectile_origin',f'''
            mov byte ptr [rax+0x20], r11b
            mov qword ptr [rax], rdx
            pushfq
            push rax
            push rcx
            push rdx
            push r10
            push r11
            mov r10, rax
            lea r11, {mem(0x12cee48)}
            sub r10, r11
            cmp r10, 0xb40
            jae tagged
            mov rax, r10
            xor edx, edx
            mov ecx, 0x30
            div rcx
            test edx, edx
            jne tagged
            lea r10, {mem(projectile_tags)}
            mov byte ptr [r10+rax], 0
            mov r11, qword ptr [rsp+48]
            lea rcx, {mem(0x70d3e)}
            cmp r11, rcx
            je animation
            lea rcx, {mem(0x70ef7)}
            cmp r11, rcx
            jne tagged
        animation:
            cmp byte ptr [r8+0x51], 0
            jne tagged
            cmp byte ptr [r8+0x52], 8
            jne tagged
            cmp byte ptr [r8+0x64], 0x0f
            jae tagged
            mov byte ptr [r10+rax], 1
        tagged:
            pop r11
            pop r10
            pop rdx
            pop rcx
            pop rax
            popfq
            jmp 0x116609
        ''')
        jump(0x116602,7,start,'Capture ordinary projectile origin')

        start = emit('damage_origin',f'''
            pushfq
            push rax
            push r10
            push r11
            mov qword ptr {mem(credit)}, 0
            test rcx, rcx
            je done
            cmp byte ptr [rcx+0x51], 0
            jne done
            cmp byte ptr [rdx+0x51], 1
            jne done
            cmp dword ptr [rdx+0x2c], 0
            jle done
            test byte ptr [r9], 0x80
            jne done
            mov rax, qword ptr [rsp+32]
            lea r10, {mem(0x822cd)}
            cmp rax, r10
            jne ranged
            lea r10, [rcx+0xd8]
            cmp r9, r10
            jne done
            cmp byte ptr [rcx+0x52], 8
            jne done
            cmp byte ptr [rcx+0x64], 0x0f
            jae done
            jmp owner
        ranged:
            lea r10, {mem(0x1164e3)}
            cmp rax, r10
            jne done
            lea r10, {mem(0x12cee48)}
            mov r11, rsi
            sub r11, r10
            cmp r11, 0xb40
            jae done
            push rdx
            push rcx
            mov rax, r11
            xor edx, edx
            mov r10d, 0x30
            div r10
            mov r11, rdx
            pop rcx
            pop rdx
            test r11, r11
            jne done
            lea r10, {mem(projectile_tags)}
            cmp byte ptr [r10+rax], 1
            jne done
        owner:
            mov r10, rcx
            cmp byte ptr [rcx+0x4f], 0x0b
            jne character
            mov r10, qword ptr {mem(0x12cecd8)}
            test r10, r10
            je done
            mov r11d, 4
        meredy:
            cmp byte ptr [r10+0x4f], 3
            je character
            add r10, 0x248
            dec r11d
            jne meredy
            jmp done
        character:
            cmp byte ptr [r10+0x4f], 6
            ja done
            cmp word ptr [r10+0x3c], 1
            jne done
            mov qword ptr {mem(credit)}, r10
        done:
            pop r11
            pop r10
            pop rax
            popfq
            mov qword ptr [rsp+8], rbx
            jmp 0x8e915
        ''')
        jump(0x8e910,5,start,'Identify basic hit origin')

        start = emit('tp_on_hp_commit',f'''
            jne no_commit
            sub dword ptr [rdi+0x2c], esi
            pushfq
            push rax
            push rcx
            push rdx
            test esi, esi
            jle finish
            mov rcx, qword ptr {mem(credit)}
            test rcx, rcx
            je finish
            mov rax, qword ptr [rcx+0xe8]
            test rax, rax
            je finish
            movsx edx, word ptr [rax+0x1c]
            test edx, edx
            jle finish
            movsx eax, word ptr [rcx+0x34]
            test eax, eax
            jns nonnegative
            xor eax, eax
        nonnegative:
            inc eax
            cmp byte ptr [rcx+0x4f], 2
            je mage
            cmp byte ptr [rcx+0x4f], 3
            jne capped
        mage:
            add eax, 1
        capped:
            cmp eax, edx
            cmovg eax, edx
            mov word ptr [rcx+0x34], ax
        finish:
            pop rdx
            pop rcx
            pop rax
            popfq
        no_commit:
            test bl, r15b
            jmp 0x8f0a1
        ''')
        jump(0x8f099,8,start,'Award bounded TP at HP commit')

    if 'camera' in features:
        active_gate = 0
        from camera_patch import emit_camera
        emit_camera(emit, mem, jump, data_rva, 'camera_floor' in features)
        from spread_visual_patch import emit_spread_visual
        emit_spread_visual(emit, mem, jump, data_rva)
        from ondine_visual_patch import emit_ondine_visual
        emit_ondine_visual(emit, mem, jump)
        from shadow_visual_patch import emit_shadow_visual
        emit_shadow_visual(emit, mem, jump, data_rva)

    active_gate = None
    if 'no_freeze' in features:
        start = emit('remove_spell_freeze',f'''
            movzx ecx, word ptr {mem(0x12d0eae)}
            push rax
            push rdx
            cmp byte ptr {mem(0x12d0ef7)}, 6
            jne freeze_done
            lea rdx, {mem(0x12cfca0)}
            mov eax, 16
        freeze_scan:
            cmp qword ptr [rdx], 0
            je freeze_next
            cmp byte ptr [rdx+0x33], 0
            je freeze_next
            xor ecx, ecx
            mov word ptr {mem(0x12d0eae)}, cx
            jmp freeze_done
        freeze_next:
            add rdx, 0x120
            dec eax
            jne freeze_scan
        freeze_done:
            pop rdx
            pop rax
            jmp 0xd2e68
        ''')
        jump(0xd2e61,7,start,'Remove spell cinematic delay without clearing menu pause')
        start = emit('skip_spell_freeze_command',f'''
            cmp byte ptr {mem(0x12d0ef7)}, 6
            je skip_freeze
            movzx eax, word ptr [r11+0x0a]
            jmp 0x866aa
        skip_freeze:
            jmp 0x866bc
        ''')
        jump(0x866a5,5,start,'Skip cinematic freeze opcode in battle')
        edit(0x114d30,b'\xb8\x00\x00\x00\x00','No initial 60-frame cinematic delay')

    if 'concurrent_spells' in features:
        # Deliberately partial: shared resource upload is serialized, same-effect
        # mutable static state is not reentered, summon/extension chains exclusive.
        # Different ordinary effects have their own native scripts and work data.
        allowed = list(range(1,26)) + [61,62,66]
        allowed_table = data_rva+0x200
        start = emit('guarded_spell_dispatch',f'''
            push rax
            push rcx
            push r8
            push r9
            push r10
            push r11
            cmp ebp, 99
            ja blocked
            cmp byte ptr {mem(0x12d0efb)}, 0
            jne chain
            lea r8, {mem(allowed_table)}
            movzx r9d, byte ptr [r8+rbp]
            lea r10, {mem(0x12cfca0)}
            mov r11d, 16
        scan:
            cmp qword ptr [r10], 0
            je next
            cmp byte ptr [r10+0x33], 0
            je next
            test r9d, r9d
            je blocked
            cmp word ptr [r10+0x3a], 2
            je blocked
            cmp word ptr [r10+0x3e], 0
            jne blocked
            movzx eax, byte ptr [r10+0x36]
            cmp eax, ebp
            je blocked
            cmp byte ptr [r8+rax], 0
            je blocked
        next:
            add r10, 0x120
            dec r11d
            jne scan
            mov word ptr {mem(0x12d0eaa)}, 0
            jmp allowed
        chain:
            cmp word ptr {mem(0x12d0eaa)}, 0
            jne blocked
        allowed:
            pop r11
            pop r10
            pop r9
            pop r8
            pop rcx
            pop rax
            jmp 0x1149a6
        blocked:
            pop r11
            pop r10
            pop r9
            pop r8
            pop rcx
            pop rax
            jmp 0x1149c6
        ''')
        jump(0x11499c,10,start,'Allow distinct ordinary spells after resource readiness')
        # Remove only the queue test on cast countdown; action submission still
        # uses the guarded dispatcher, native cost and resource readiness checks.
        edit(0xd5269,b'\x90'*6,'Casting progresses while another spell is active')
        start = emit('retain_active_spell_context',f'''
            mov qword ptr {mem(0x12d0ea0)}, r9
            pushfq
            push rax
            push rcx
            lea rcx, {mem(0x12cfca0)}
            mov eax, 16
        remaining:
            cmp rcx, rbx
            je next_remaining
            cmp qword ptr [rcx], 0
            je next_remaining
            cmp byte ptr [rcx+0x33], 0
            je next_remaining
            mov qword ptr {mem(0x12d0ea0)}, rcx
            mov word ptr {mem(0x12d0eaa)}, 0xffff
            jmp retained
        next_remaining:
            add rcx, 0x120
            dec eax
            jne remaining
        retained:
            pop rcx
            pop rax
            popfq
            jmp 0x115f3a
        ''')
        jump(0x115f33,7,start,'Retain context until the last large effect finishes')
    else:
        allowed = []

    if 'victory_tp' in features:
        active_gate = 1
        from recovery_summon_patch import emit_recovery
        emit_recovery(emit, jump)
        active_gate = None
    if 'summon_modifier' in features:
        from recovery_summon_patch import emit_summon
        emit_summon(emit, mem, jump, edit)
    if 'summon_hold' in features:
        if 'summon_modifier' in features:raise ValueError('Choose one summon input scheme')
        from cast_hold_patch import emit_cast_hold
        emit_cast_hold(emit, mem, jump, edit, data_rva, 'concurrent_spells' in features)
    color_data = b''
    if 'casting_colors' in features:
        from casting_color_patch import emit_casting_colors
        color_data = emit_casting_colors(emit, mem, jump, edit, data_rva)

    damage_palette, ui_info = b'', None
    if 'damage_colors' in features:
        active_gate = 3
        from damage_color_patch import emit_damage_colors
        damage_palette = emit_damage_colors(emit, mem, jump, data_rva)
        active_gate = None
    if 'combat_ui' in features:
        active_gate = {site:4 for site in (0xd1aa5,0xd1b38,0x80af8,0x80b1b,0xd1c23,0xd1cd4,0xd1d46,0xd53a5,0x11a449,0x11a48d)}
        active_gate.update({site:5 for site in (0x112ff8,0x8152f,0xd458e)})
        active_gate[0xd5ad4] = 6
        from combat_ui_patch import emit_combat_ui
        ui_info = emit_combat_ui(emit, mem, jump, edit, data_rva)
        active_gate = None
        if not color_data:
            from casting_color_patch import COLORS
            color_data = b''.join(bytes(rgb)+b'\0' for rgb in COLORS.values())

    floor_info, floor_data = None, b''
    if 'camera_floor' in features:
        active_gate = 0
        if 'camera' not in features:raise ValueError('camera_floor requires camera')
        from camera_floor_patch import emit_floor
        floor_info, floor_data = emit_floor(emit, mem, edit, data_rva)
        active_gate = None

    if 'startup_opening' in features:
        from startup_patch import emit_startup
        emit_startup(emit, mem, jump)

    settings_info, settings_data = None, b''
    logo_png = b''
    if 'mod_settings' in features:
        from mod_settings_patch import emit_settings
        settings_info, settings_data, logo_png = emit_settings(emit, mem, jump, data_rva, symbols)

    skit_info, skit_data = None, b''
    if 'skit_notice' in features:
        if not {'mod_settings', 'combat_ui'}.issubset(features):
            raise ValueError('skit_notice requires mod_settings and combat_ui rendering helpers')
        from skit_notice_patch import emit_skit_notice
        skit_info, skit_data = emit_skit_notice(emit, mem, jump, data_rva, symbols)

    artesphere_info, artesphere_data = None, b''
    artesphere_offset = align(0x4000+len(logo_png),0x1000)
    if 'artesphere' in features:
        if not {'mod_settings','combat_ui','summon_hold'}.issubset(features):
            raise ValueError('artesphere requires mod_settings, combat_ui and summon_hold')
        from artesphere_patch import emit_artesphere
        artesphere_info,artesphere_data=emit_artesphere(emit,mem,jump,edit,data_rva,symbols,data_rva+artesphere_offset)

    particle_info = None
    texture_info = None
    particle_offset = align(max(0x4000+len(logo_png), artesphere_offset+len(artesphere_data)),0x1000)
    if 'concurrent_spells' in features:
        from particle_capacity_patch import emit_particle_capacity
        particle_info = emit_particle_capacity(emit, mem, jump, data_rva+particle_offset)
        from spell_texture_patch import emit_spell_textures
        texture_offset = align(particle_offset+particle_info['size'],0x1000)
        texture_info = emit_spell_textures(emit, mem, jump, data_rva+texture_offset)

    difficulty_info = None
    if 'difficulty_rebalance' in features:
        active_gate = 8
        from difficulty_patch import emit_difficulty
        difficulty_info = emit_difficulty(emit, jump)
        active_gate = None

    vitality_info = None
    if 'multiple_vitality' in features:
        active_gate = 9
        from multiple_vitality_patch import emit_multiple_vitality
        vitality_info = emit_multiple_vitality(emit, jump, edit)
        active_gate = None

    defense_info = None
    if 'cast_defense' in features:
        from cast_defense_patch import emit_cast_defense
        defense_info = emit_cast_defense(emit, mem, jump, data_rva)

    if len(code)>code_capacity:
        raise RuntimeError('Hook code exceeds reserved section')
    # Two sections: executable code and nonexecutable writable state. Original
    # relocations remain valid, and all new references are RIP-relative.
    header_end = pe.sections[-1].get_file_offset()+40
    if header_end+80>pe.OPTIONAL_HEADER.SizeOfHeaders:
        raise RuntimeError('No PE header room')
    result.extend(b'\0'*(align(len(result),pe.OPTIONAL_HEADER.FileAlignment)-len(result)))
    raw_code = len(result)
    result.extend(code)
    result.extend(b'\xcc'*(code_capacity-len(code)))
    raw_data = len(result)
    state_size = 0x4000 if settings_info else (0x2000 if ui_info or damage_palette or color_data else (0x1000 if floor_info else 0x400))
    if logo_png:state_size=align(0x4000+len(logo_png),pe.OPTIONAL_HEADER.FileAlignment)
    if artesphere_data:state_size=artesphere_offset+len(artesphere_data)
    if particle_info:state_size=align(particle_offset+particle_info['size'],pe.OPTIONAL_HEADER.FileAlignment)
    if texture_info:state_size=align(texture_offset+texture_info['size'],pe.OPTIONAL_HEADER.FileAlignment)
    state = bytearray(state_size)
    if artesphere_data:state[artesphere_offset:artesphere_offset+len(artesphere_data)]=artesphere_data
    if logo_png:state[0x4000:0x4000+len(logo_png)] = logo_png
    if state_size >= 0x2000:
        from mod_settings_patch import FEATURES
        state[0x1a00:0x1a00+len(FEATURES)] = b'\1'*len(FEATURES)
    if settings_data:state[0x2000:0x2000+len(settings_data)] = settings_data
    if artesphere_info:
        kbui=artesphere_info['keyboard']['ui']
        struct.pack_into('<II',state,0x1a30,kbui['input_rva'],kbui['draw_rva'])
    if skit_data:state[0x3800:0x3800+len(skit_data)] = skit_data
    for effect in allowed:
        state[0x200+effect]=1
    state[0x700:0x700+len(color_data)] = color_data
    if 'casting_colors' in features:
        from casting_color_patch import profile_data
        profiles = profile_data()
        state[0x1700:0x1700+len(profiles)] = profiles
    state[0x800:0x800+len(floor_data)] = floor_data
    if damage_palette:state[0x1300:0x1300+len(damage_palette)] = damage_palette
    if ui_info:
        state[0x1340:0x134b] = b'OBJET\0ITEM\0'
        for vitality in range(11):
            text = ('MAX' if vitality == 10 else f'{vitality}/10').encode('ascii')+b'\0'
            state[0x1980+vitality*8:0x1980+vitality*8+len(text)] = text
    result.extend(state)
    for idx,(name,rva,raw,size,flags) in enumerate([
        (b'.tecode',code_rva,raw_code,code_capacity,0x60000020),
        (b'.tedata',data_rva,raw_data,state_size,0xc0000040),
    ]):
        struct.pack_into('<8sIIIIIIHHI',result,header_end+idx*40,
                         name.ljust(8,b'\0'),size,rva,size,raw,0,0,0,0,flags)
    struct.pack_into('<H',result,pe.FILE_HEADER.get_field_absolute_offset('NumberOfSections'),pe.FILE_HEADER.NumberOfSections+2)
    struct.pack_into('<I',result,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'),align(data_rva+state_size,section_alignment))
    struct.pack_into('<I',result,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfCode'),pe.OPTIONAL_HEADER.SizeOfCode+code_capacity)
    struct.pack_into('<I',result,pe.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfInitializedData'),pe.OPTIONAL_HEADER.SizeOfInitializedData+state_size)
    struct.pack_into('<I',result,pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),0)
    check_pe = pefile.PE(data=bytes(result))
    struct.pack_into('<I',result,pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum'),check_pe.generate_checksum())
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'GameNative.dll').write_bytes(result)
    manifest = {'version':'combat-test-0.12.13','steam_build':25190541,'original_sha256':ORIGINAL_SHA256,
                'patched_sha256':digest(result),'features':features,'edits':edits,'hooks':hooks,
                'symbols':symbols,'code_rva':code_rva,'data_rva':data_rva,
                'concurrent_effect_allowlist':allowed,'runtime_validated':False,
                'limits':['Distinct ordinary large effects only; same effect and special sequences remain serialized.',
                          'Dynamic camera bounds cover 82 audited rectangular stage grids. Unsupported grids retain their original camera rotation and position. Forest stages 6-8 additionally account for their offset backdrop at depth 576. New background behavior still requires in-game visual validation.',
                          'Twelve per-user title-screen switches, French for text language 3 and English otherwise, tested in emulation. Use controller or keyboard; custom mouse selection is not implemented. Title branding, panel layout and real settings persistence still need in-game validation.',
                          'Ordinary large effects 1-25, 61, 62 and 66 preserve battle pitch; special sequences retain native cameras. Spread retains its vanilla column with an added small textured top cap; the new cap needs in-game visual validation. Ondine perimeter and zoom-scaled shadows remain experimental. Other summon backdrops were not extended.',
                          'Craymel miniatures use an 8x8 quad and eight directional poses: the second half-turn mirrors the native half-turn atlas. New size and continuous rotation require visual confirmation.',
                          'Held Arte at cast completion selects learned owned summons; L1 holds ready casts. Steam controller slot zero only; other slots retain native controls.',
                          'TP origin recognition, controller ergonomics and rendering concurrency require in-game validation.']}
    if color_data:
        from casting_color_patch import COLORS
        manifest['casting_colors'] = COLORS
    if difficulty_info:manifest['difficulty_rebalance']=difficulty_info
    if vitality_info:manifest['multiple_vitality']=vitality_info
    if defense_info:manifest['cast_defense']=defense_info
    if floor_info:manifest['floor_extension']=floor_info
    if particle_info:manifest['particle_capacity']=particle_info
    if texture_info:manifest['spell_textures']=texture_info
    if ui_info:manifest['combat_ui']=ui_info
    if settings_info:manifest['mod_settings']=settings_info;manifest['option_gates']=gates
    if skit_info:manifest['skit_notice']=skit_info
    if artesphere_info:
        manifest['artesphere']=artesphere_info
        manifest['limits'].append('Artesphere: three pages of six commands, per-save sidecar stored locally beside mod preferences. L2 toggles B/A and R2 toggles C/A in the native six-row editor; hold L2 for B or R2 for C in battle, with C priority. F7/F8 are configurable foreground keyboard aliases. Legacy B assignments migrate; C initially copies B for legacy saves and A for new profiles. Only controller zero uses the extra pages. Runtime validation pending; copy the sidecar with saves when changing PCs.')
        manifest['limits'].append('Spell usage: new counters start at zero and are stored per character and save slot in ArteUsage-v1 beside mod preferences. Native physical counts remain authoritative. Casts count on successful release, menu healing after application; no reconstruction of past casts. Keep the INI sidecar with your saves. Offline verification does not replace in-game visual testing.')
    if damage_palette:manifest['damage_colors']='actual impact element; party received damage takes precedence; heal/TP recovery preserved'
    if 'concurrent_spells' in features:
        queue_names = ['Allow distinct ordinary spells after resource readiness',
                       'Casting progresses while another spell is active',
                       'Retain context until the last large effect finishes']
        queue_names += [e['name'] for e in edits if e['name'].startswith(('Particle capacity:', 'Spell textures:', 'Spell palettes:'))]
        fallback = bytearray(result)
        for change in edits:
            if change['name'] in queue_names:
                before = bytes.fromhex(change['original'])
                fallback[change['offset']:change['offset']+len(before)] = before
        checksum_offset = pe.OPTIONAL_HEADER.get_field_absolute_offset('CheckSum')
        checksum = pefile.PE(data=bytes(fallback)).generate_checksum()
        struct.pack_into('<I',fallback,checksum_offset,checksum)
        manifest['without_spell_overlap'] = dict(sha256=digest(fallback),
            checksum_offset=checksum_offset,checksum=checksum, reverted_edits=queue_names)
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    listing=[]
    for h in hooks:
        listing.append(f"\n; {h['name']}\n")
        offset=h['rva']-code_rva
        listing.extend(f'{i.address:08x}: {i.bytes.hex():24} {i.mnemonic} {i.op_str}\n'
                       for i in CS.disasm(bytes(code[offset:offset+h['size']]),h['rva']))
    (OUT/'hooks.asm').write_text(''.join(listing),encoding='utf-8')
    print(json.dumps({'output':str(OUT),'sha256':digest(result),'hooks':len(hooks),'code_bytes':len(code),'features':features}))
    return manifest

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--features',nargs='+',choices=['tp','camera','no_freeze','concurrent_spells','victory_tp','summon_modifier','summon_hold','casting_colors','camera_floor','damage_colors','combat_ui','startup_opening','mod_settings','skit_notice','artesphere','difficulty_rebalance','multiple_vitality','cast_defense'],
                    default=['tp','camera','no_freeze','concurrent_spells','victory_tp','summon_hold','casting_colors','camera_floor','damage_colors','combat_ui','startup_opening','mod_settings','skit_notice','artesphere','difficulty_rebalance','multiple_vitality','cast_defense'])
    build(ap.parse_args().features)
