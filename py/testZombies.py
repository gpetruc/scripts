import sys,ROOT,os
from glob import iglob
ROOT.gROOT.SetBatch(True)

# http://stackoverflow.com/questions/16582194/python-version-of-freopen
def freopen(f,option,stream):
    oldf = open(f,option)
    oldfd = oldf.fileno()
    newfd = stream.fileno()
    os.close(newfd)
    os.dup2(oldfd, newfd)
freopen("/dev/null","w",sys.stderr)

for f in sys.argv:
    if f[0] == "-": continue
    for file in iglob(f):
        if not file.endswith(".root"): continue
        tfile = ROOT.TFile.Open(file)
        if not tfile or tfile.IsZombie():
            print "%s is zombie" % file
        else:
            print "%s is ok" % file
        try:
            tfile.Close()
        except:
            pass

