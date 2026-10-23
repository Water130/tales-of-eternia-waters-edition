"""Skip presentation screens only, retaining native boot and options loading."""

def emit_startup(emit, mem, jump, data, initialize=None):
    # Settings normally load at the title, too late for this choice. Load the
    # same INI before *each* first startup decision (update or draw may run first).
    # Preserve native volatile state and incoming flags. These are interior
    # call sites with RSP aligned to 16, not function entries.
    def gate(native):
        if initialize is None:return ''
        return f'''
            pushfq
            push rax
            push rcx
            push rdx
            push r8
            push r9
            push r10
            push r11
            sub rsp, 0x80
            {chr(10).join(f'movdqu [rsp+{0x20+i*16}], xmm{i}' for i in range(6))}
            call {initialize:#x}
            {chr(10).join(f'movdqu xmm{i}, [rsp+{0x20+i*16}]' for i in range(6))}
            add rsp, 0x80
            pop r11
            pop r10
            pop r9
            pop r8
            pop rdx
            pop rcx
            pop rax
            cmp byte ptr {mem(data+0x1a4c)}, 0
            jne enabled
            popfq
            {native}
        enabled:
            popfq
        '''
    draw = emit('startup_hide_logos', f'''
        {gate(f'mov ecx, dword ptr {mem(0x119ea68)}; jmp 0x252901')}
        cmp dword ptr {mem(0x119ea68)}, 1
        je 0x252d58
        jmp 0x252d68
    ''')
    jump(0x2528fb, 6, draw, 'Omit startup logo rendering, preserve render cleanup')
    done = emit('startup_after_resources', f'''
        {gate(f'mov dword ptr {mem(0x119ea60)}, 2; jmp 0x25339f')}
        mov dword ptr {mem(0x119ea68)}, 5
        mov dword ptr {mem(0x119ea60)}, 0
        jmp 0x2533a7
    ''')
    jump(0x253395, 10, done, 'Continue to native options loading after resource initialization')
    # State 4 is the timed informational screen AFTER options loading succeeds.
    # State 3 (load error/acknowledgement) and its input handling remain intact.
    info=emit('startup_information',f'''
        {gate(f'mov rcx, qword ptr {mem(0x644a70)}; jmp 0x259347')}
        jmp 0x2594e6
    ''')
    jump(0x259340, 7, info, 'Optional skip of loaded startup information screen')
