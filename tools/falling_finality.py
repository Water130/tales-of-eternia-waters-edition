"""One ordinary dark sword: no original MA event/frame or fixed damage path."""

def wire(emit,mem,jump,pe,relocate,info):
    from custom_effect_identity import step_guard
    state=info['state_rva'];script=state+0x5100;blade=state+0x5140;impact=state+0x51a0
    sidecar=state+0x5200 # 16 effects * 0x20, bounded independently of native slots
    init=emit('falling_finality_initialize',f'''
        push rax
        sub rsp, 0x20; call {info['identity']['lookup']:#x}; add rsp, 0x20
        cmp eax, 139; je identified
        mov rax, qword ptr [rcx]; test rax, rax; je native
        cmp byte ptr [rax+0x51], 0; jne native
        cmp byte ptr [rax+0x4f], 2; je mage
        cmp byte ptr [rax+0x4f], 3; jne native
    mage:
        cmp byte ptr [rax+0x6d], 139; jne native
    identified:
        lea rax, {mem(script)}; mov qword ptr [rcx+0x10], rax
        lea rax, {mem(impact)}; mov qword ptr [rcx+0x78], rax
        # Dispatcher clears +3E after initialization. Keep the texture index
        # in an unused resource pointer slot of this fully private effect.
        movzx eax, word ptr [rcx+0x3e]; mov qword ptr [rcx+0x70], rax
        pop rax; ret
    native: pop rax
        {relocate(pe.get_data(0xbd7a0,7),0xbd7a0)}
        jmp 0xbd7a7
    ''')
    jump(0xbd7a0,7,init,'Private Falling Finality: ordinary sword initialization only')
    frame=emit('falling_finality_frame',f'''
        push rax; lea rax, {mem(script)}
        cmp qword ptr [rcx+0x10], rax; jne native
        pop rax
        cmp word ptr [rcx+0x3a], 2; je early
        {step_guard(info,'early')}
        push rbx; push rsi; push rdi; sub rsp, 0x20
        mov rbx, rcx
        lea rdi, {mem(0x12cfca0)}; mov rax, rcx; sub rax, rdi
        cmp rax, 0x1200; jae release_native
        xor edx, edx; mov ecx, 0x120; div ecx; test edx, edx; jne release_native
        shl eax, 5; lea rdi, {mem(sidecar)}; add rdi, rax
        cmp word ptr [rbx+0x38], 0; jne alive
        mov qword ptr [rdi], 0; mov qword ptr [rdi+8], 0
        mov dword ptr [rdi+16], 0
        mov ax, word ptr [rbx+0x22]; mov word ptr [rdi+16], ax
        mov ax, word ptr [rbx+0x2a]; mov word ptr [rdi+18], ax
        mov rax, rbx; lea rcx, {mem(0x12cfca0)}; sub rax, rcx
        xor edx, edx; mov ecx, 0x120; div ecx
        add ax, 0x5fe0; mov word ptr [rdi+22], ax
        mov rax, qword ptr [rbx]
        test rax, rax; je release
        mov al, byte ptr [rax+0x6e]; mov byte ptr [rdi+20], al
    alive:
        mov rsi, qword ptr [rbx]; test rsi, rsi; je release
        cmp word ptr [rsi+0x3c], 1; jne release
        cmp dword ptr [rsi+0x2c], 0; jle release
        cmp byte ptr [rsi+0x52], 7; je release
        cmp byte ptr [rsi+0x52], 2; je release
        mov al, byte ptr [rsi+0x6e]; cmp al, byte ptr [rdi+20]; jne release
        cmp word ptr [rbx+0x38], 48; jae release
        cmp word ptr [rbx+0x38], 8; jne impact_tick
        cmp byte ptr [rdi+8], 0; jne done
        lea rcx, {mem(blade)}; call 0x8b7e0
        test rax, rax; je done
        cmp rax, qword ptr {mem(0x12cec20)}; je done
        mov qword ptr [rdi], rax; mov byte ptr [rdi+8], 1
        mov dx, word ptr [rdi+22]; mov word ptr [rax+0x42], dx
        mov dx, word ptr [rbx+0x70]; mov word ptr [rax+0x48], dx
        # 8B7E0 mirrors velocity, angle and UVs for a left-facing emitter.
        # This sword has a world-space trajectory, independent of the mage.
        mov word ptr [rax+0x2a], -128; mov word ptr [rax+0x2c], 256
        mov word ptr [rax+0x1c], -512; mov word ptr [rax+0x1e], 0
        mov word ptr [rax+0x12], 0; mov word ptr [rax+0x14], 112
        mov word ptr [rax+0x16], 255; mov word ptr [rax+0x18], 63
        mov dx, word ptr [rdi+16]; add dx, 1024; mov word ptr [rax], dx
        mov dx, word ptr [rdi+18]; sub dx, 2048; mov word ptr [rax+2], dx
        jmp done
    impact_tick:
        cmp word ptr [rbx+0x38], 24; jne done
        cmp byte ptr [rdi+8], 1; jne done
        mov byte ptr [rdi+8], 2
        mov rcx, rbx; lea rdx, [rdi+16]; lea r8, {mem(impact)}
        call 0x8f770
        jmp done
    release:
        mov rax, qword ptr [rdi]; test rax, rax; je release_native
        mov dx, word ptr [rdi+22]
        cmp word ptr [rax+0x42], dx; jne release_native
        mov byte ptr [rax+8], 0
        mov qword ptr [rdi], 0
    release_native:
        mov rcx, rbx; call 0x115ee0
    done: add rsp, 0x20; pop rdi; pop rsi; pop rbx
    early: ret
    native:
        pop rax
        {relocate(pe.get_data(0xbd8b0,7),0xbd8b0)}
        jmp 0xbd8b7
    ''')
    jump(0xbd8b0,7,frame,'Private Falling Finality: sword particle and one normal dark impact')
    info['falling_finality']=dict(initialize=init,frame=frame,script=script,blade=blade,impact=impact,
        sidecar=sidecar,resource=182,spawn_tick=8,impact_tick=24,end_tick=48,
        damage_mode=2,damage_percent=320,runtime_validated=False)
