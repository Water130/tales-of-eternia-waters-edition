"""Local spell-label atlas assembled from the owned native victory lettering.

Only letter masks are composed. Both native front/shadow layers are generated;
the native mesh updater still owns position, lifetime, scale, flash and sound.
No external font or downloaded game asset is used.
"""
import io,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/pydeps'))
from PIL import Image,ImageChops,ImageFilter,ImageDraw
from damage_color_patch import PAIRS

LABELS={
70:('LIS.EAU','A.EDGE'),71:('GEYSER','SPREAD'),72:('L.VENT','W.BLADE'),
73:('EST.AIR','A.THRST'),74:('CYCLONE','CYCLONE'),75:('B.FEU','FIREBL'),
76:('ERUPT.','ERUPT.'),77:('M.FLAM.','F.WALL'),78:('EXPLOS.','EXPLODE'),
79:('TOMBE','GRAVE'),80:('STALAG.','STALAG.'),81:('EL.TERR','G.DASH'),
82:('EP.GLAC','I.NEEDL'),83:('L.GLACE','F.LANCE'),84:('BLIZZ.','BLIZZ.'),
85:('CRYOG.','ABSOL.'),86:('FOUDRE','LIGHTN.'),87:('L.TONN.','T.BLADE'),
88:('INDIGN.','INDIGN.'),89:('FAISC.','RAY'),90:('L.SACR.','H.LANCE'),
91:('V.SOMB.','D.FORCE'),92:('H.SANG.','B.HOWL'),93:('METEORE','METEOR'),
94:('ETOILE','S.STAR'),95:('DISTOR.','DISTOR.'),96:('F.ARD.','B.FORCE'),
97:('C.VENT','A.BLADE'),98:('SP.EAU','A.SPIR.'),99:('L.ENRG.','R.LASER'),
100:('L.SOMB.','D.LASER'),101:('ELEMENT','ELEMENT'),112:('ETINC.','SPARK'),
113:('E.LUM.','P.SWORD')}


def label_palettes():
    """Use each spell's native element, including compound and special spells."""
    rows=json.loads((ROOT/'audit/build-25190541/artes_native.json').read_text(encoding='utf-8'))
    byid={r['id']:r for r in rows}
    return {aid:dict(element=byid[aid]['launch_bytes'][2]&15,
                    primary=PAIRS[byid[aid]['launch_bytes'][2]&15][0].hex(),
                    secondary=PAIRS[byid[aid]['launch_bytes'][2]&15][1].hex())
            for aid in LABELS}


def ink_color(pair,y,shadow=False):
    # Native 128 means full intensity. Keep the requested pair and the native
    # inverse shadow layer; the original effect still supplies its animation.
    t=min(56,max(0,y-4))
    primary=bytes.fromhex(pair['primary']);secondary=bytes.fromhex(pair['secondary'])
    rgb=tuple(round((min(255,a*2)*(56-t)+min(255,b*2)*t)/56)
              for a,b in zip(primary,secondary))
    return tuple(255-v for v in rgb) if shadow else rgb

def alphabet(im,lang):
    rgb=im.convert('RGB');alpha=im.getchannel('A');mask=Image.new('L',im.size)
    mask.putdata([255 if max(c)>65 and a>64 else 0 for c,a in zip(rgb.get_flattened_data(),alpha.get_flattened_data())])
    words_fr=[('NIV.',(0,0,116,64)),('TRAN.',(0,64,172,128)),('ESTOC',(0,128,174,192)),
        ('POING',(384,0,559,64)),('PIED',(384,64,514,128)),('NOUV.',(704,64,874,128)),
        ('TECHN.',(704,128,898,192)),('BONUS',(384,576,600,640)),('GALD',(0,704,172,768)),
        ('MAX',(0,960,148,1024)),('MOY.',(384,832,550,896))]
    words_en=[('LEVEL',(0,0,130,64)),('SLASH',(0,64,130,128)),('STAB',(0,128,104,192)),
        ('PUNCH',(384,0,525,64)),('KICK',(384,64,484,128)),('NEW',(704,64,800,128)),
        ('SKILL!',(704,128,826,192)),('BONUS',(384,576,566,640)),('GALD',(0,704,150,768)),
        ('TIME',(384,704,526,768)),('MAXVITALITY',(0,384,412,460))]
    glyphs={}
    for text,box in (words_fr if lang==0 else words_en):
        crop=mask.crop(box);occupied=[crop.crop((x,0,x+1,crop.height)).getbbox() is not None for x in range(crop.width)]
        runs=[];start=None
        for x,v in enumerate(occupied+[False]):
            if v and start is None:start=x
            elif not v and start is not None:runs.append((start,x));start=None
        if lang==1 and text=='STAB':runs=[(4,28),(34,56),(56,76),(80,100)]
        if lang==1 and text=='SKILL!':runs=[(4,24),(28,48),(52,60),(64,80),(84,100),(100,116)]
        if lang==1 and text=='BONUS':runs=[(4,40),(44,76),(76,114),(116,145),(146,176)]
        if lang==1 and text=='GALD':runs=[(4,36),(40,76),(76,104),(108,140)]
        if lang==1 and text=='TIME':runs=[(4,44),(44,64),(64,102),(104,140)]
        if lang==1 and text=='MAXVITALITY':runs=[(4,50),(50,88),(88,128),(132,176),(176,192),(192,234),(234,266),(266,300),(300,322),(322,364),(364,408)]
        if len(runs)!=len(text):raise ValueError((lang,text,runs))
        for ch,(x0,x1) in zip(text,runs):
            if ch in glyphs:continue
            g=crop.crop((x0,0,x1,crop.height));g=g.crop(g.getbbox())
            h=10 if ch=='.' else 56
            g=g.resize((max(4,round(g.width*h/g.height)),h),Image.Resampling.LANCZOS)
            glyphs[ch]=g
    # Missing letters are constructed from strokes of this same native alphabet.
    g=glyphs['E'].copy();ImageDraw.Draw(g).rectangle((max(5,g.width//3),44,g.width,56),fill=0);glyphs['F']=g
    if 'R' not in glyphs:
        g=glyphs['P'].copy();d=ImageDraw.Draw(g);d.line((g.width//2,28,g.width-2,55),fill=255,width=max(5,g.width//3));glyphs['R']=g
    glyphs['Z']=glyphs['N'].rotate(90,expand=True).resize((glyphs['N'].width,56),Image.Resampling.LANCZOS)
    if '.' not in glyphs:
        g=glyphs['!'];glyphs['.']=g.crop((0,g.height-9,g.width,g.height))
    return glyphs

def build():
    # Read the installed, unmodified font resources; fall back to earlier local
    # extraction only for tests. These are independent of the HP/TP atlas.
    from zarc_audit import ROOT as GAME
    import UnityPy
    from build_profile import OUT as out
    out.mkdir(parents=True,exist_ok=True)
    atlas=Image.new('RGBA',(1024,4096));entries={};preview=Image.new('RGBA',(640,64*len(LABELS)),(22,44,72,255))
    palettes=label_palettes()
    for lang,key in enumerate(('0x08010011','0x0801000f')):
        matches=list((GAME/'Tales of Eternia Remastered_Data/StreamingAssets/aa/StandaloneWindows64').glob('*_assets_'+key+'_*.bundle'))
        assert len(matches)==1, (key, 'Required owned resource missing or ambiguous; set TOE_GAME_DIR')
        path=matches[0]
        env=UnityPy.load(path.read_bytes())
        tex=next(o.parse_as_object() for o in env.objects if o.type.name=='Texture2D')
        glyphs=alphabet(tex.image,lang)
        for n,(aid,names) in enumerate(LABELS.items()):
            text=names[lang];width=sum(glyphs[c].width+3 for c in text)-3+12
            assert width<=320,(text,width)
            mask=Image.new('L',(320,64));x=6
            for ch in text:
                g=glyphs[ch];mask.paste(g,(x,60-g.height));x+=g.width+3
            outline=mask.filter(ImageFilter.MaxFilter(9))
            for shadow in (0,1):
                label=Image.new('RGBA',(320,64));label.putalpha(outline)
                bg=221 if shadow else 34
                ink=Image.new('RGBA',(320,64))
                for y in range(64):
                    ImageDraw.Draw(ink).line((0,y,319,y),fill=(*ink_color(palettes[aid],y,shadow),255))
                label.paste((bg,bg,bg,255),(0,0,320,64));label.putalpha(outline)
                label=Image.composite(ink,label,mask)
                slot=(lang*2+shadow)*len(LABELS)+n;x=(slot%3)*320;y=(slot//3)*64
                atlas.paste(label,(x,y))
                entries[aid,lang,shadow]=(x,y,width,64)
                if not shadow:preview.alpha_composite(label,(lang*320,n*64))
    # Dedicated unused rectangles for the original Hyades projectiles. The
    # native texture manager owns their lifetime, independent of enemy actors.
    assert ((len(LABELS)*4+2)//3)*64<=3840
    from hyades_orb_asset import frames
    spheres,source_sha=frames()
    # Two horizontal frames per facing, advanced by the native mesh animator.
    rects=[[i*192,3840,192,128] for i in range(4)]
    for sphere,(x,y,w,h) in zip(spheres,rects):atlas.paste(sphere,(x,y))
    (out/'hyades-spheres-source.json').write_text(json.dumps(dict(
        archive_entry=237,group=273,source_sha256=source_sha,
        source_rect=[256,136,96,32],palette=1,scale=4,frame_count=2,frame_interval=2,
        rectangles=rects),indent=2))
    from spirit_projectile_assets import frames as spirit_frames, RECTS
    sprites,sources=spirit_frames()
    for sprite,(x,y,w,h) in zip(sprites,RECTS):
        assert sprite.size==(w,h) and x+w<=1024 and y+h<=4096
        atlas.paste(sprite,(x,y))
    (out/'spirit-projectiles-source.json').write_text(json.dumps(sources,indent=2))
    stream=io.BytesIO();atlas.save(stream,format='PNG',optimize=True)
    png=stream.getvalue();(out/'spell-native-labels.png').write_bytes(png)
    preview.save(out/'spell-native-labels-preview.png')
    return png,entries

if __name__=='__main__':
    png,entries=build();print(json.dumps(dict(bytes=len(png),labels=len(entries))))
