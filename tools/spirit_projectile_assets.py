"""Owned Ondine water-spear animation and Sylph stream from their native TIMs.

Ondine motion 9 loops frames 32..35 every two ticks. These are the moving
water lance, unlike the opcode-19 wedge used by Subterranean Divide.
"""
import hashlib, struct

RECTS = [(i*112,3968+facing*64,112,64) for facing in range(2) for i in range(4)]
RECTS += [(448+facing*256,3968,256,96) for facing in range(2)]

def frames():
    from zarc_audit import Archive
    from archive_subfiles import Ranges
    from tales_block_reader import decode
    from PIL import Image
    arc=Archive(); result=[]; sources=[]
    try:
        r=Ranges(arc,arc.entries[237])
        for name,pos,group,rects,scale,palette in (
            ('aqualaser',7355864,263,[(280+56*i,88,56,32) for i in range(4)],2,1),
            ('wind-arrow',7405848,265,[(176,208,64,24)],4,0)):
            pairs=list(struct.iter_unpack('<II',r.read(pos+4,struct.unpack('<I',r.read(pos,4))[0]*8)))
            def leaf(i):
                off,size=pairs[i];b=r.read(pos+off,size)
                return decode(b) if b[0] in (1,3) else b
            tim=leaf(1);assert struct.unpack_from('<II',tim)==(16,8)
            assert struct.unpack_from('<I4H',tim,8)==(524,0,492,256,1)
            _,_,_,words,h=struct.unpack_from('<I4H',tim,532);w=words*4
            if group==263:
                anim=leaf(2); table=struct.unpack_from('<H',anim,6)[0]
                loop,n,seq=struct.unpack_from('<BBH',anim,table+9*4)
                assert (loop,n,anim[seq:seq+8])==(0,4,bytes((32,2,33,2,34,2,35,2)))
                for index,(x,y,cw,ch) in enumerate(rects):
                    f=struct.unpack_from('<H',anim,12+(32+index)*2)[0]
                    d=struct.unpack_from('<H',anim,f+4)[0];b=anim[d:d+4]
                    assert ((b[0]&252)+(b[0]&3)*256,b[1]&248,b[2]&252,b[3]&248)==(x,y,cw,ch)
            colors=[((v&31)*255//31,((v>>5)&31)*255//31,((v>>10)&31)*255//31,0 if v==0 else 255)
                    for v in struct.unpack_from('<16H',tim,20+palette*32)]
            raw=tim[544:]
            for mirror in (False,True):
                for x,y,cw,ch in rects:
                    assert x+cw<=w and y+ch<=h
                    im=Image.new('RGBA',(cw,ch));im.putdata([colors[(raw[(yy*w+xx)//2]>>(4*(xx%2)))&15]
                        for yy in range(y,y+ch) for xx in range(x,x+cw)])
                    if mirror:im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                    result.append(im.resize((cw*scale,ch*scale),Image.Resampling.NEAREST))
            sources.append(dict(name=name,archive=237,group=group,source_rects=rects,palette=palette,scale=scale,
                                source_sha256=hashlib.sha256(tim).hexdigest(),
                                frame_interval=2 if group==263 else 0))
        return result,sources
    finally:arc.f.close()
