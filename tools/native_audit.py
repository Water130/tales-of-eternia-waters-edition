"""Static PE inspection and disassembly only; never loads or executes game code."""
import argparse, os
import bisect
import hashlib
import json
import re
import struct
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'pydeps'))
import capstone
import pefile

OUT=Path(__file__).resolve().parents[1]/'audit/build-25190541'
GAME=Path(__file__).resolve().parents[1]/'backups/build-25190541/GameNative.dll'
BACKUP=Path(os.environ.get('TOE_NATIVE_ORIGINAL', str(Path(__file__).resolve().parents[1]/'backups/build-25190541/GameNative.dll')))
SOURCE=BACKUP if BACKUP.exists() else GAME
data=SOURCE.read_bytes()
if hashlib.sha256(data).hexdigest() != '6488be2ce5ecc1dc9fc0216aa2462ec9aeba7a464468d5fd61ad3c2a8356849b':
    raise RuntimeError('Native audit requires the verified original build 25190541 DLL.')
pe=pefile.PE(data=data);base=pe.OPTIONAL_HEADER.ImageBase
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
functions=[(e.struct.BeginAddress,e.struct.EndAddress) for e in pe.DIRECTORY_ENTRY_EXCEPTION]
starts=[x[0] for x in functions]
def containing(rva):
    i=bisect.bisect_right(starts,rva)-1
    return functions[i] if i>=0 and rva<functions[i][1] else (rva,rva+160)
def code(start,end):return pe.get_data(start,end-start)
def disasm(rva, explicit_end=None):
    start,end=(rva,explicit_end) if explicit_end else containing(rva)
    lines=[f'; function RVA {start:#x}..{end:#x}, image base {base:#x}']
    for ins in md.disasm(code(start,end),base+start):
        lines.append(f'{ins.address-base:08x}: {ins.bytes.hex():24} {ins.mnemonic:8} {ins.op_str}')
    return '\n'.join(lines)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--rva',nargs='*',type=lambda x:int(x,0));ap.add_argument('--end',type=lambda x:int(x,0));ap.add_argument('--index',action='store_true');args=ap.parse_args()
    if args.rva is not None:
        for rva in args.rva:
            s=disasm(rva,args.end);(OUT/f'fn_{rva if args.end else containing(rva)[0]:08x}.asm').write_text(s,encoding='utf-8');print(s)
        return
    targets=[15300,15332,15334,15336,15338,15383,15385,16581,16597,16598,16605,16614]
    for t in targets:
        matches=[]
        for m in re.finditer(re.escape(struct.pack('<I',t)),data):
            try: rva=pe.get_rva_from_offset(m.start())
            except Exception: continue
            matches.append(hex(rva))
        print('message',t,'u32 matches',matches[:45])
    if args.index:
        refs=[];calls=[];indexed=[]
        for start,end in functions:
            for ins in md.disasm(code(start,end),base+start):
                for op in ins.operands:
                    if op.type==capstone.x86.X86_OP_MEM and op.mem.base==capstone.x86.X86_REG_RIP:
                        refs.append([ins.address-base,start,ins.address+ins.size+op.mem.disp-base,ins.mnemonic,ins.op_str])
                    elif op.type==capstone.x86.X86_OP_MEM and 0x2a0000<=op.mem.disp<0x1300000:
                        indexed.append([ins.address-base,start,op.mem.disp,ins.mnemonic,ins.op_str])
                if ins.mnemonic in ('call','jmp') and ins.operands and ins.operands[0].type==capstone.x86.X86_OP_IMM:
                    calls.append([ins.address-base,start,ins.operands[0].imm-base])
        (OUT/'native_refs.json').write_text(json.dumps(refs),encoding='utf-8')
        (OUT/'native_calls.json').write_text(json.dumps(calls),encoding='utf-8')
        (OUT/'native_indexed.json').write_text(json.dumps(indexed),encoding='utf-8')
        print('functions',len(functions),'RIP refs',len(refs),'direct calls/jumps',len(calls))
if __name__=='__main__':main()
