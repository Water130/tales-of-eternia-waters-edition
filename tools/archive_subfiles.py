"""Read embedded headers and enemy records without extracting full archives."""
import json
import lzma
import struct
from zarc_audit import Archive, OUT
from tales_block_reader import decode

class Ranges:
    def __init__(self, arc, entry):
        self.arc,self.entry=arc,entry
        self.positions=[];self.cache={}
        offset=entry['offset']
        for block in range((entry['size']+arc.block-1)//arc.block):
            self.positions.append(offset)
            packed=arc.blocks[entry['block_index']+block]
            offset+=packed or min(arc.block,entry['size']-block*arc.block)
    def read(self,start,size):
        assert 0<=start<=start+size<=self.entry['size']
        if not size:return b''
        chunks=[]
        for b in range(start//self.arc.block,(start+size-1)//self.arc.block+1):
            if b not in self.cache:
                expected=min(self.arc.block,self.entry['size']-b*self.arc.block)
                packed=self.arc.blocks[self.entry['block_index']+b]
                self.arc.f.seek(self.positions[b])
                data=self.arc.f.read(packed or expected)
                if packed:
                    data=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(data,max_length=expected)
                assert len(data)==expected
                self.cache[b]=data
            lo=max(start-b*self.arc.block,0);hi=min(start+size-b*self.arc.block,self.arc.block)
            chunks.append(self.cache[b][lo:hi])
        return b''.join(chunks)

class MemoryRanges:
    def __init__(self,data):self.data=data
    def read(self,start,size):
        assert 0<=start<=start+size<=len(self.data)
        return self.data[start:start+size]

def main():
    arc=Archive();rows=[];enemies=[]
    def inspect(ranges,entry,start,size,path,depth=0):
        if size<9 or depth>4:return
        head=ranges.read(start,min(64,size))
        method,packed,unpacked=struct.unpack_from('<BII',head)
        row=dict(entry=entry['index'],hash=entry['hash'],subfile=path,offset=start,size=size,
                 offset_space='decoded_parent' if isinstance(ranges,MemoryRanges) else 'archive_entry',header=head[:24].hex())
        if method in (1,3) and 0<packed<=size-9 and 0<unpacked<=8*1024*1024:
            try:
                decoded=decode(ranges.read(start,min(size,65536)),64)
            except ValueError:
                decoded=None
            if decoded is not None:
                row.update(compression=method,unpacked_size=unpacked,decoded_header=decoded[:24].hex())
                rows.append(row)
                if decoded[:2]==b'en' and unpacked<=128*1024:
                    data=decode(ranges.read(start,packed+9))
                    enemies.append(dict(row,bytes_hex=data.hex()))
                count=struct.unpack_from('<I',decoded)[0] if len(decoded)>=4 else 0
                if 1<=count<=64 and unpacked<=1024*1024:
                    prefix=decode(ranges.read(start,min(size,65536)),4+4*count)
                    offsets=list(struct.unpack_from(f'<{count}I',prefix,4))
                    present=[x for x in offsets if x]
                    if present and 4+4*count<=min(present)<=4+4*count+256 and max(present)<unpacked:
                        data=decode(ranges.read(start,packed+9));memory=MemoryRanges(data)
                        for sub,lo in enumerate(offsets):
                            if not lo:continue
                            hi=min([x for x in offsets if x>lo]+[len(data)])
                            inspect(memory,entry,lo,hi-lo,path+['decoded',sub],depth+1)
                return
        rows.append(row)
        if head[:2]==b'en' and size<=128*1024:
            enemies.append(dict(row,bytes_hex=ranges.read(start,size).hex()));return
        count=struct.unpack_from('<I',head)[0]
        if not 1<=count<=64 or 4+4*count>size:return
        offsets=list(struct.unpack(f'<{count}I',ranges.read(start+4,4*count)))
        present=[x for x in offsets if x]
        if not present or not 4+4*count<=min(present)<=4+4*count+256 or max(present)>=size:return
        for sub,lo in enumerate(offsets):
            if not lo:continue
            hi=min([x for x in offsets if x>lo]+[size])
            inspect(ranges,entry,start+lo,hi-lo,path+[sub],depth+1)
    for entry in arc.entries:
        if entry['size']<8:continue
        ranges=Ranges(arc,entry)
        inspect(ranges,entry,0,entry['size'],[])
    (OUT/'archive_subfiles.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    (OUT/'enemy_records_raw.json').write_text(json.dumps(enemies,indent=2),encoding='utf-8')
    print('Subfiles',len(rows),'enemy records',len(enemies),'enemy bytes',sum(x['size'] for x in enemies))
    print('Enemy sample', [{k:v for k,v in r.items() if k!='bytes_hex'} for r in enemies[:3]])
if __name__=='__main__':main()
