"""Lossless sprite extraction from the owned Hyades battle resource.

Archive 237 uses packed offset/size pairs, aligned to FOUR bytes, not sectors.
Hyades group 273, record 3: CP932 name ヒアデス; opcode 19 at record +0x129
selects two horizontal 48x32 frames at TIM (256,136), changing every two
ticks (opcode bytes 12/13 are interval/frame count, not a 2x2 grid). The low two bits
of 0x89 select palette 1; the actor's palette 0 is not the projectile palette.
No actor texture is used at runtime.
"""
import hashlib,struct

def frames():
    from zarc_audit import Archive
    from archive_subfiles import Ranges
    from tales_block_reader import decode
    from PIL import Image
    arc=Archive()
    try:
        r=Ranges(arc,arc.entries[237]);pos=7625904
        count=struct.unpack('<I',r.read(pos,4))[0];assert count==4
        pairs=list(struct.iter_unpack('<II',r.read(pos+4,count*8)))
        def leaf(i):
            off,size=pairs[i];return decode(r.read(pos+off,size))
        record=leaf(3);assert record[2:22].split(b'\0')[0].decode('cp932')=='ヒアデス'
        assert record[0x129:0x139]==bytes.fromhex('03 13 f4 f9 01 89 32 20 f8 00 f0 00 02 02 18 20')
        tim=leaf(1)
        assert struct.unpack_from('<II',tim)==(16,8)
        assert struct.unpack_from('<I4H',tim,8)==(524,0,492,256,1)
        assert struct.unpack_from('<I4H',tim,532)==(65548,320,0,128,256)
        palette=struct.unpack_from('<16H',tim,20+32)
        colors=[((v&31)*255//31,((v>>5)&31)*255//31,((v>>10)&31)*255//31,0 if v==0 else 255) for v in palette]
        raw=tim[544:];result=[]
        for facing in (1,-1):
            for frame in range(2):
                im=Image.new('RGBA',(48,32))
                im.putdata([colors[(raw[(y*512+x)//2]>>(4*(x%2)))&15]
                            for y in range(136,168)
                            for x in range(256+frame*48,304+frame*48)])
                if facing<0:im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                result.append(im.resize((192,128),Image.Resampling.NEAREST))
        return result,hashlib.sha256(tim).hexdigest()
    finally:arc.f.close()
