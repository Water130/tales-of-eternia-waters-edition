"""Keep controller-zero ally shortcuts with the hero, across all three pages.

The native four-controller layout is untouched. Only its first two commands
are exchanged. Older saves migrate their current assignments once; other
heroes start empty instead of inheriting someone else's commands.
"""
SIZE = 96
OFFSET = 0x1a000

def emit_shortcuts(emit, mem, jump, state, profile):
    live, owner = state+OFFSET, state+0x1aff0
    sync = emit('character_shortcuts_sync', f'''
        cmp ecx, 6; ja done
        lea r8, {mem(live)}
        lea r9d, [ecx+1]
        movzx eax, byte ptr {mem(owner)}
        cmp eax, r9d; je done
        test eax, eax; je restore
        dec eax; imul eax, eax, 12
        mov edx, dword ptr {mem(0x11cad3c)}; mov dword ptr [r8+rax+8], edx
        mov edx, dword ptr {mem(profile+28)}; mov dword ptr [r8+rax+12], edx
        mov edx, dword ptr {mem(profile+72)}; mov dword ptr [r8+rax+16], edx
    restore:
        imul eax, ecx, 12
        cmp dword ptr [r8], 0; jne existing
        # The first hero inherits the pre-update native assignments.
        mov edx, dword ptr {mem(0x11cad3c)}; mov dword ptr [r8+rax+8], edx
        mov edx, dword ptr {mem(profile+28)}; mov dword ptr [r8+rax+12], edx
        mov edx, dword ptr {mem(profile+72)}; mov dword ptr [r8+rax+16], edx
    existing:
        bts dword ptr [r8], ecx
        mov edx, dword ptr [r8+rax+8]; mov dword ptr {mem(0x11cad3c)}, edx
        mov edx, dword ptr [r8+rax+12]; mov dword ptr {mem(profile+28)}, edx
        mov edx, dword ptr [r8+rax+16]; mov dword ptr {mem(profile+72)}, edx
        mov byte ptr {mem(owner)}, r9b
    done: ret
    ''')
    flush = emit('character_shortcuts_flush', f'''
        movzx ecx, byte ptr {mem(owner)}; test ecx, ecx; je done
        dec ecx; imul ecx, ecx, 12; lea r8, {mem(live)}
        mov eax, dword ptr {mem(0x11cad3c)}; mov dword ptr [r8+rcx+8], eax
        mov eax, dword ptr {mem(profile+28)}; mov dword ptr [r8+rcx+12], eax
        mov eax, dword ptr {mem(profile+72)}; mov dword ptr [r8+rcx+16], eax
    done: ret
    ''')
    dispatch=emit('character_shortcuts_before_dispatch', f'''
        push rcx; sub rsp, 0x28
        cmp byte ptr [rcx+0x56], 0; jne done
        movzx ecx, byte ptr [rcx+0x4f]; call {sync:#x}
    done:
        add rsp, 0x28; pop rcx
        mov r10, qword ptr {mem(0x12cea60)}; jmp 0x113395
    ''')
    jump(0x11338e,7,dispatch,'Restore ally shortcuts belonging to the controlled hero')
    return dict(live_rva=live,size=SIZE,sync=sync,flush=flush,owner=owner)

def storage(emit,mem,data,state,string,fingerprint,info):
    from arte_usage_patch import emit_usage_storage
    hooks=emit_usage_storage(emit,mem,data,state,string,fingerprint,info,
        record_name='character_shortcuts',section_name='HeroShortcuts-v1',record_size=SIZE,
        layout=dict(snapshot=state+0x1a100,pending=state+0x1a200,workers=state+0x1a300,
                    valid=state+0x1a2f0,pending_ptr=state+0x1a2f8),
        reset_extra=f'mov byte ptr {mem(info["owner"])}, 0')
    hooks['capture']=f'call {info["flush"]:#x}\n'+hooks['capture']
    return hooks
