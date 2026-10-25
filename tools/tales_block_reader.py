"""Bounded reader for Tales PSX type 1/3 blocks (no compression/writing).

Format reference: https://github.com/vs-sr-dev/tales-blockcodec-doc/blob/main/tales-block-codec.md
Independently written for prefix inspection and strict declared-length checks.
"""
import struct

def decode(data, limit=None):
    method,packed,expected=struct.unpack_from('<BII',data)
    if method not in (1,3) or not 0<expected<=8*1024*1024:
        raise ValueError('Invalid block header')
    stop=expected if limit is None else min(expected,limit)
    dictionary=bytearray(4096)
    dictionary[:2048]=b''.join(bytes([x,0])*4 for x in range(256))
    dictionary[2048:3840]=b''.join(bytes([x,255])*3+bytes([x]) for x in range(256))
    cursor=4096-(17 if method==3 else 18)
    output=bytearray(); index=9; end=9+packed
    def emit(value):
        nonlocal cursor
        dictionary[cursor]=value;cursor=(cursor+1)&4095;output.append(value)
    while len(output)<stop:
        if index>=min(end,len(data)):raise ValueError('Truncated flags')
        flags=data[index];index+=1
        for bit in range(8):
            if len(output)>=stop:break
            if index>=min(end,len(data)):raise ValueError('Truncated token')
            if flags&(1<<bit):
                emit(data[index]);index+=1;continue
            if index+2>min(end,len(data)):raise ValueError('Truncated match')
            low,high=data[index:index+2];index+=2
            if method==3 and high&15==15:
                if high>>4:
                    count,value=(high>>4)+3,low
                else:
                    if index>=min(end,len(data)):raise ValueError('Truncated run')
                    count,value=low+19,data[index];index+=1
                for _ in range(count):emit(value)
            else:
                source=low|((high>>4)<<8)
                for offset in range((high&15)+3):emit(dictionary[(source+offset)&4095])
            if len(output)>expected:raise ValueError('Output exceeds declared length')
    if limit is None and (len(output)!=expected or index!=end):
        raise ValueError('Declared lengths disagree')
    return bytes(output[:stop])
