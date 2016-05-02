import os.path, subprocess, sys, json

EOS="/afs/cern.ch/project/eos/installation/0.3.15/bin/eos.select"
def eosls(dir):
    global EOS
    output = subprocess.check_output((EOS+" ls -l /eos/cms/"+dir).split())
    ret = { 'subs':[], 'rootfiles':0.0, 'other':0.0 }
    for line in output.split("\n"):
        if len(line.strip()) == 0: continue
        fields = line.split()
        if fields[0][0] == "d":
            ret['subs'].append(fields[8])
        else:
            if fields[8].endswith(".root"):
                ret['rootfiles'] += float(fields[4])/1024/1024
            else:
                ret['other'] += float(fields[4])/1024/1024
    sys.stderr.write("%s has %.1f Mb of root files, %.1f Mb of rest, and %d subs: %s\n" % (dir, ret['rootfiles'], ret['other'], len(ret['subs']), ", ".join(ret['subs'][:6])))
    return ret

def eoslsall(base,sub="",ret={}):
    self = os.path.join(base,sub) 
    ls1 = eosls(self)
    ls1['deep'] = ls1['rootfiles']+ls1['other']
    for s in ls1['subs']:
        lss = eoslsall(base, os.path.join(sub,s))
        ls1['deep'] += lss['deep']
    ret[self] = ls1
    return ls1 if sub else ret

if __name__ == "__main__":
    ret = eoslsall(sys.argv[1])
    print json.dumps(ret)
    
