"""Execute both sides of every generated native/off versus mod/on gate."""
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RIP, UC_X86_REG_RSP, UC_X86_REG_EFLAGS
from capstone import Cs, CS_ARCH_X86, CS_MODE_64


def check_gates(u,base,m,sp,put,get,reg,regs):
    from mod_settings_patch import FLAG_OFFSETS
    md=Cs(CS_ARCH_X86,CS_MODE_64)
    count=0
    for gate in m['option_gates']:
        entry=base+gate['gate']
        ins=list(md.disasm(bytes(u.mem_read(entry,40)),entry))
        assert ins[0].mnemonic=='pushfq' and ins[1].mnemonic=='cmp'
        assert ins[2].mnemonic in ('je','jz') and ins[3].mnemonic=='popfq'
        native=int(ins[2].op_str,16)
        # The camera gate also resets its private interpolation flag while OFF.
        native_code=list(md.disasm(bytes(u.mem_read(native,32)),native))
        pop=next(i for i in native_code if i.mnemonic=='popfq')
        off_end=pop.address+pop.size
        on_end=ins[3].address+ins[3].size
        flag=base+m['data_rva']+FLAG_OFFSETS[gate['flag']]
        saved=get(flag,'B')
        for enabled in (0,1):
            for flags in (0x202,0x246,0xa97):
                put(flag,'B',enabled)
                for i,name in enumerate(regs):reg(name,0x21000+i*16)
                before={name:u.reg_read(r) for name,r in regs.items()}
                u.reg_write(UC_X86_REG_RSP,sp)
                u.reg_write(UC_X86_REG_EFLAGS,flags)
                target=on_end if enabled else off_end
                def stop(_,address,size,data):
                    if address==target:u.emu_stop()
                h=u.hook_add(UC_HOOK_CODE,stop)
                try:u.emu_start(entry,target+16,count=20)
                finally:u.hook_del(h)
                assert u.reg_read(UC_X86_REG_RIP)==target,(gate,enabled)
                assert u.reg_read(UC_X86_REG_RSP)==sp
                assert u.reg_read(UC_X86_REG_EFLAGS)==flags
                assert before=={name:u.reg_read(r) for name,r in regs.items()}
                count+=1
        put(flag,'B',saved)
    return count
