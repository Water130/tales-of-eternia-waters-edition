"""Skip presentation screens only, retaining native boot and options loading."""

def emit_startup(emit, mem, jump):
    draw = emit('startup_hide_logos', f'''
        cmp dword ptr {mem(0x119ea68)}, 1
        je 0x252d58
        jmp 0x252d68
    ''')
    jump(0x2528fb, 6, draw, 'Omit startup logo rendering, preserve render cleanup')
    done = emit('startup_after_resources', f'''
        mov dword ptr {mem(0x119ea68)}, 5
        mov dword ptr {mem(0x119ea60)}, 0
        jmp 0x2533a7
    ''')
    jump(0x253395, 10, done, 'Continue to native options loading after resource initialization')
    # State 4 is the timed informational screen AFTER options loading succeeds.
    # State 3 (load error/acknowledgement) and its input handling remain intact.
    jump(0x259340, 7, 0x2594e6, 'After options loading, request native opening movie 1 directly')
