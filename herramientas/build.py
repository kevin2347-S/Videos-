import json,subprocess,numpy as np,re,sys
from PIL import Image,ImageDraw,ImageFont,ImageFilter
W,H,FPS=1080,1920,30
chunks=json.load(open('chunks.json')); T=json.load(open('track.json'))
words={n:json.load(open(f'w/{n}.wav.json')) for n in 'ABC'}
FB='/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
EMO='/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'
END_SEC=4.0; TITLE_SEC=6.5

# ---------- timeline ----------
o=0.0; starts=[]
for c in chunks: starts.append(o); o+=c[2]-c[1]
SPEECH=o; TOTAL=o+END_SEC
print('speech',round(SPEECH,1),'total',round(TOTAL,1))

# ---------- overlays ----------
def emoji_img(ch,size):
    f=ImageFont.truetype(EMO,109); im=Image.new('RGBA',(136,128),(0,0,0,0))
    ImageDraw.Draw(im).text((0,0),ch,font=f,embedded_color=True)
    im=im.crop(im.getbbox()); r=size/im.height
    return im.resize((int(im.width*r),size),Image.LANCZOS)
def text_block(lines,size,y,fill='white',stroke=7,emoji=None,gap=1.12,img=None):
    img=img or Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(img); f=ImageFont.truetype(FB,size)
    for i,l in enumerate(lines):
        w=d.textlength(l,font=f); x=(W-w)/2; yy=y+i*size*gap
        d.text((x,yy),l,font=f,fill=fill,stroke_width=stroke,stroke_fill=(0,0,0,255))
    return img,y+len(lines)*size*gap
title,yb=text_block(['¿POR QUÉ SUFRIMOS','DE ANSIEDAD LOS','CRISTIANOS?'],88,170)
_f=ImageFont.truetype(FB,88); _w=ImageDraw.Draw(title).textlength('CRISTIANOS?',font=_f)
e=emoji_img('🤔',90); title.alpha_composite(e,(int((W+_w)/2+16),int(170+2*88*1.12+4)))
# end card
card=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(card)
d.rounded_rectangle((70,560,W-70,1360),radius=48,fill=(14,14,28,200))
_,y=text_block(['NO SIGAS CARGANDO','UN PESO QUE DIOS','YA TE INVITÓ A SOLTAR'],74,610,img=card,stroke=0)
d=ImageDraw.Draw(card); d.rectangle((W//2-90,y+20,W//2+90,y+28),fill=(124,58,237,255))
_,y=text_block(['MIRA LA PRÉDICA','COMPLETA EN YOUTUBE'],66,y+70,fill=(255,255,255,255),img=card,stroke=0)
# purple pill with link in bio
f=ImageFont.truetype(FB,62); pill='LINK EN LA BIO'; pw=d.textlength(pill,font=f)
x0=(W-pw)/2-110; d.rounded_rectangle((x0,y+60,W-x0,y+190),radius=65,fill=(124,58,237,255))
d.text(((W-pw)/2+50,y+85),pill,font=f,fill='white')
em=emoji_img('👉',80); card.alpha_composite(em,(int(x0)+55,int(y+84)))
_,y2=text_block(['“MERIMNAO” · CASA ROCA LLANOGRANDE'],40,y+245,fill=(210,210,230,255),img=card,stroke=0)

# ---------- video ----------
def xs(n,t):
    a=T[n]; i=min(int(t*10),len(a)-2); fr=t*10-i
    return a[i]*(1-fr)+a[i+1]*fr
enc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
   '-c:v','libx264','-crf','17','-preset','medium','-pix_fmt','yuv420p','stage1.mp4'],stdin=subprocess.PIPE)
prev=None; zi=0; last=None; gk=0
for ci,(n,a,b) in enumerate(chunks):
    zi = (zi+1)%2 if (prev==n) else 0
    z=1.0 if zi==0 else 1.12; prev=n
    dur=b-a; nf=int(round(dur*FPS))
    p=subprocess.Popen(['ffmpeg','-v','error','-ss',str(a),'-t',str(dur+0.1),'-i',f'w/{n}.mov','-vf',f'fps={FPS}','-frames:v',str(nf+2),'-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    for k in range(nf):
        raw=p.stdout.read(640*360*3)
        if len(raw)<640*360*3: raw=last_raw
        last_raw=raw
        im=Image.fromarray(np.frombuffer(raw,np.uint8).reshape(360,640,3))
        t=a+k/FPS; cw=360*9/16/z; ch=360/z
        if n=='B' and 5.65<=t<=9.55:
            bgs=im.resize((W,H),Image.BILINEAR,box=(120,0,120+202,360)).filter(ImageFilter.GaussianBlur(30))
            bgs=Image.eval(bgs,lambda v:int(v*0.5))
            sl=im.resize((W,608),Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=2,percent=40,threshold=2))
            bgs.paste(sl,(0,520)); fr=bgs
        else:
            cx=min(max(xs(n,t),cw/2),640-cw/2); y0=(360-ch)*0.2
            fr=im.resize((W,H),Image.LANCZOS,box=(cx-cw/2,y0,cx+cw/2,y0+ch))
            fr=fr.filter(ImageFilter.UnsharpMask(radius=3,percent=70,threshold=2))
        gt=starts[ci]+k/FPS
        if gt<TITLE_SEC:
            al=1.0 if gt<TITLE_SEC-0.5 else (TITLE_SEC-gt)/0.5
            al=min(al,min(1.0,gt/0.25))
            ov=title.copy()
            if al<1: ov.putalpha(ov.getchannel('A').point(lambda v:int(v*al)))
            fr=fr.convert('RGBA'); fr.alpha_composite(ov); fr=fr.convert('RGB')
        enc.stdin.write(fr.tobytes()); last=fr; gk+=1
    p.stdout.close(); p.wait()
# end card: blurred darkened last frame
bg=last.filter(ImageFilter.GaussianBlur(14)); bg=Image.eval(bg,lambda v:int(v*0.45))
for k in range(int(END_SEC*FPS)):
    al=min(1.0,k/8)
    ov=card.copy()
    if al<1: ov.putalpha(ov.getchannel('A').point(lambda v:int(v*al)))
    fr=bg.convert('RGBA'); fr.alpha_composite(ov); enc.stdin.write(fr.convert('RGB').tobytes())
enc.stdin.close(); enc.wait()

# ---------- audio ----------
parts=[];labels=[]
for i,(n,a,b) in enumerate(chunks):
    idx={'A':0,'B':1,'C':2}[n]
    parts.append(f'[{idx}:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={b-a-0.05:.3f}:d=0.05[a{i}]'); labels.append(f'[a{i}]')
fc=';'.join(parts)+';'+''.join(labels)+f'concat=n={len(chunks)}:v=0:a=1,highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,loudnorm=I=-15:TP=-1.5:LRA=9,apad=whole_dur={TOTAL:.2f}[out]'
subprocess.run(['ffmpeg','-v','error','-y','-i','w/A.mov','-i','w/B.mov','-i','w/C.mov','-filter_complex',fc,'-map','[out]','-t',f'{TOTAL:.2f}','-c:a','pcm_s16le','-ar','48000','audio.wav'],check=True)

# ---------- subtitles (ASS) ----------
FIX={'Elias':'Elías'}
def clean(w): return w.strip()
events=[] # (out_start,out_end,word)
SEEN=set()
for ci,(n,a,b) in enumerate(chunks):
    ws=[(clean(w),s,e) for seg in words[n] for w,s,e in seg['w'] if a<=(s+min(e,s+0.7))/2<b+0.12 and (n,round(s,2)) not in SEEN]
    for _w in ws: SEEN.add((n,round(_w[1],2)))
    # custom fixes
    out=[];skip=0
    for j,(w,s,e) in enumerate(ws):
        if skip: skip-=1; continue
        nxt=[x[0] for x in ws[j:j+4]]
        if n=='C' and nxt[:4]==['le','dieron','que','a']:
            out.append(('les',s,e)); out.append(('decía:',ws[j+1][1],ws[j+1][2])); out.append(('venga',ws[j+3][1],ws[j+3][1]+0.2)); skip=3; continue
        if n=='C' and w=='Sigue': out.append(('Se ve',s,e)); continue
        if n=='A' and w=='qué' and 8<s<9: w='que'
        if n=='B' and w=='cuánto' and s<4: w='cuántos'
        w=FIX.get(w,w); out.append((w,s,e))
    for j,(w,s,e) in enumerate(out):
        s2=s-a+starts[ci]; e2=min(min(e,s+0.7)-a+starts[ci],starts[ci]+(b-a))
        events.append([max(s2,starts[ci]),e2,w,ci])
# group into captions
groups=[];cur=[]
for ev in events:
    if cur and (len(cur)>=4 or ev[3]!=cur[-1][3] or re.search(r'[.,?!:]$',cur[-1][2]) or (ev[0]-cur[-1][1])>0.8):
        groups.append(cur);cur=[]
    cur.append(ev)
if cur: groups.append(cur)
def ass_t(t): h=int(t//3600);m=int(t%3600//60);s=t%60; return f'{h}:{m:02d}:{s:05.2f}'
PUR='&H00ED3A7C&'
lines=[]
for g in groups:
    txt=[re.sub(r'[,.;:]','',x[2]).upper() for x in g]
    brk=len(txt)//2 if sum(len(t) for t in txt)+len(txt)>15 and len(txt)>1 else None
    for j,x in enumerate(g):
        st=x[0]; en=g[j+1][0] if (j+1<len(g) and g[j+1][3]==x[3]) else min(x[1]+0.12,x[0]+1.0,starts[x[3]]+(chunks[x[3]][2]-chunks[x[3]][1]))
        if j+1<len(g): en=max(en,st+0.08)
        parts=[]
        for k,t in enumerate(txt):
            sep=('\\N' if k==brk else ' ') if k>0 else ''
            run=('{\\bord16\\3c%s}%s{\\bord5\\3c&H000000&}'%(PUR,t)) if k==j else t
            parts.append(sep+run)
        lines.append(f'Dialogue: 0,{ass_t(st)},{ass_t(en)},Sub,,0,0,0,,{"".join(parts)}')
hdr=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Sub,Inter ExtraBold,74,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,5,0,2,60,60,560,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
'''
open('subs.ass','w').write(hdr+'\n'.join(lines)+'\n')
open('subs_review.txt','w').write('\n'.join(' '.join(x[2] for x in g) for g in groups))
print('subs',len(groups),'captions')
