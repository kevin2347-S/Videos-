import numpy as np, subprocess, json, sys
def frames(f,fps=10,w=320,h=180):
    raw=subprocess.run(['ffmpeg','-v','error','-i',f,'-vf',f'fps={fps},scale={w}:{h}','-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True).stdout
    return np.frombuffer(raw,np.uint8).reshape(-1,h,w,3).astype(np.float32)
out={}
for n in ['A','B','C']:
    F=frames(f'w/{n}.mov')
    bg=np.median(F[::max(1,len(F)//120)],axis=0)
    xs=[];ys=[]
    for fr in F:
        d=np.abs(fr-bg).sum(2)
        m=d>70
        m[:, :]=m
        cols=m.sum(0).astype(float); rows=m.sum(1).astype(float)
        # keep densest 40px window horizontally
        if cols.sum()<30: xs.append(np.nan); continue
        k=np.convolve(cols,np.ones(40),'same'); c=int(k.argmax())
        lo,hi=max(0,c-30),min(320,c+30)
        sub=m[:,lo:hi]; cc=sub.sum(0).astype(float)
        xs.append((cc*np.arange(lo,hi)).sum()/max(cc.sum(),1))
    xs=np.array(xs)
    idx=np.arange(len(xs)); ok=~np.isnan(xs)
    xs=np.interp(idx,idx[ok],xs[ok])
    # smooth: gaussian ~0.8s (sigma 8 frames @10fps)
    s=8; k=np.exp(-0.5*(np.arange(-3*s,3*s+1)/s)**2); k/=k.sum()
    p=np.pad(xs,(3*s,3*s),mode='edge'); sm=np.convolve(p,k,'valid')
    out[n]=(sm*2).tolist()   # to 640px space, 10fps
    print(n,len(F),'frames', 'x range',round(min(out[n])),round(max(out[n])),'nan%',round(100*(~ok).mean(),1))
json.dump(out,open('track.json','w'))
