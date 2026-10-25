"""Read-only ZARC v2 reader. Layout/hash reference: DaZombieKiller/TalesOfTools (MIT)."""
import argparse
import os
import hashlib
import json
import lzma
import re
import struct
from pathlib import Path

ROOT = Path(os.environ.get('TOE_GAME_DIR', 'local/game')).resolve()
ARCHIVE = ROOT / 'Tales of Eternia Remastered_Data/StreamingAssets/Archive/DATA.zarc'
OUT = Path(__file__).resolve().parents[1] / 'audit/build-25190541'

def name_hash(name):
    low = high = 0xffffffff
    for b in name.lower().encode('ascii'):
        low ^= b
        high ^= b
        for _ in range(8):
            low = (low >> 1) ^ (0x56811021 if low & 1 else 0)
            high = (high >> 1) ^ (0x10215681 if high & 1 else 0)
    return (~(low | high << 32)) & 0xffffffffffffffff

class Archive:
    def __init__(self, path=ARCHIVE):
        self.path = path
        self.f = path.open('rb')
        head = self.f.read(40)
        magic, version, end, stride, count, unknown, enc, self.block, self.align, case = struct.unpack('>4s9I', head)
        assert magic == b'ZARC' and version == 2 and stride == 24 and case == 1
        self.entries=[]
        for i in range(count):
            b=self.f.read(24)
            self.entries.append(dict(index=i, hash=f'{int.from_bytes(b[:8],"big"):016x}', size=int.from_bytes(b[8:13],'big'), block_index=int.from_bytes(b[17:20],'big'), offset=int.from_bytes(b[20:24],'big')*self.align))
        width=((self.block-1).bit_length()+7)//8
        self.blocks=[int.from_bytes(self.f.read(width),'big') for _ in range((end-self.f.tell())//width)]
        self.by_hash={int(e['hash'],16):e for e in self.entries}
    def read(self,e,limit=None):
        self.f.seek(e['offset'])
        target=min(e['size'],limit) if limit is not None else e['size']
        parts=[]; done=0
        for idx in range(e['block_index'],e['block_index']+(e['size']+self.block-1)//self.block):
            compressed=self.blocks[idx]
            expected=min(self.block,e['size']-done)
            if compressed:
                # This build's size includes the 13-byte LZMA-alone header.
                packed=self.f.read(compressed)
                dec=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
                chunk=dec.decompress(packed,max_length=expected)
            else:
                chunk=self.f.read(expected)
            assert len(chunk)==expected,(e['index'],idx,len(chunk),expected)
            parts.append(chunk); done+=len(chunk)
            if done>=target: break
        return b''.join(parts)[:target]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--extract',nargs='*',type=int);args=parser.parse_args()
    arc=Archive()
    if args.extract is not None:
        dest=OUT/'extracted';dest.mkdir(exist_ok=True)
        for i in args.extract:
            e=arc.entries[i]
            assert e['size']<32*1024*1024,'Use targeted ranges for large entries'
            content=arc.read(e)
            path=dest/f'{i:04d}_{e["hash"]}.bin'
            path.write_bytes(content)
            print(path.name,len(content),hashlib.sha256(content).hexdigest())
        return
    candidates=set()
    native=(OUT/'GameNative.dll.strings.txt').read_text(encoding='utf-8')
    for line in native.splitlines():
        value=line.split('\t',1)[1]
        if '/' in value or re.search(r'\.(bin|dat|d|o|prx|msg)$',value,re.I):
            candidates.add(value)
    for language in ['english','french','japanese','en','fr','ja']:
        for p in [f'Border/Message/{language}/Message.bin',f'Border/Message/{language}.bin',f'Border/Message/Message_{language}.bin']:
            candidates.add(p)
    for c in candidates:
        if name_hash(c) in arc.by_hash: arc.by_hash[name_hash(c)]['name']=c
    results=[]
    for e in arc.entries:
        data=arc.read(e,65536)
        strings=[m.group().decode('ascii') for m in re.finditer(rb'[\x20-\x7e]{6,}',data)]
        hits=[s for s in strings if re.search(r'(spark|prism|maelstrom|thunder|spell|magic|skill|shining|fear.?flare|\.bin|\.dat|\.d\b|USRDIR)',s,re.I)]
        results.append(dict(e,magic=data[:16].hex(),hits=hits[:30],strings=strings[:4]))
    (OUT/'zarc_index.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print('entries',len(results),'uncompressed bytes',sum(e['size'] for e in results),'matched names',sum('name' in e for e in results))
    for e in results:
        if e['hits'] or 'name' in e: print(json.dumps(e))

if __name__=='__main__':main()
