import sys,json,numpy as np,subprocess
from faster_whisper import WhisperModel
m=WhisperModel('small',device='cpu',compute_type='int8')
for f in sys.argv[1:]:
    a=np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i',f,'-f','s16le','-ac','1','-ar','16000','-'],capture_output=True).stdout,np.int16).astype(np.float32)/32768
    segs,_=m.transcribe(a,language='es',word_timestamps=True,vad_filter=True)
    out=[]
    for s in segs:
        out.append({'s':s.start,'e':s.end,'t':s.text,'w':[(w.word,w.start,w.end) for w in s.words]})
    json.dump(out,open(f+'.json','w'),ensure_ascii=False)
    print('=====',f)
    for s in out: print(f"[{s['s']:.1f}-{s['e']:.1f}] {s['t']}")
