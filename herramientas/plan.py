import subprocess,re,json
WINS=[('A',2.50,20.60),('B',1.85,8.95),('B',18.05,31.45),
      ('C',12.95,14.45),('C',17.50,22.65),('C',32.25,49.55),('C',52.70,55.95),('C',244.20,251.10)]
def silences(n):
    r=subprocess.run(['ffmpeg','-i',f'w/{n}.wav','-af','silencedetect=noise=-33dB:d=0.90','-f','null','-'],capture_output=True,text=True).stderr
    st=[float(x) for x in re.findall(r'silence_start: ([\d.]+)',r)]
    en=[float(x) for x in re.findall(r'silence_end: ([\d.]+)',r)]
    return list(zip(st,en))
S={n:silences(n) for n in 'ABC'}
PAD_B,PAD_A=0.22,0.30
chunks=[]
for n,a,b in WINS:
    cur=a
    for s,e in S[n]:
        if e<=a or s>=b: continue
        s=max(s,a); e=min(e,b)
        if s-cur>0.3: chunks.append([n,cur,(b if s>b-1.2 else min(s+PAD_A,e))])
        cur=max(e-PAD_B,cur)
    if b-cur>0.3: chunks.append([n,cur,b])
# merge tiny gaps
tot=0
for c in chunks:
    c[1],c[2]=round(c[1],2),round(c[2],2); tot+=c[2]-c[1]
    print(c, round(c[2]-c[1],2))
print('total',round(tot,1),'chunks',len(chunks))
json.dump(chunks,open('chunks.json','w'))
