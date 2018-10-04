import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libFWCoreFWLite.so");
ROOT.gSystem.Load("libDataFormatsFWLite.so");
ROOT.gSystem.Load("libRecoTrackerDeDx.so");
ROOT.gInterpreter.ProcessLine("#include <RecoTracker/DeDx/interface/DeDxTools.h>")
ROOT.FWLiteEnabler.enable()

from sys import argv
from math import pow, sqrt
from DataFormats.FWLite import Handle, Events

events = Events(argv[1])
dedxcut = float(argv[2])
ptbins = map(float,argv[3:])+[float("inf")]
#dedx = Handle("std::vector<reco::DeDxHitInfo>")
trks = Handle("std::vector<reco::Track>")
vmap = Handle("edm::ValueMap<reco::DeDxData>")
vpix = Handle("edm::ValueMap<reco::DeDxData>")
vstr = Handle("edm::ValueMap<reco::DeDxData>")
asso = Handle("edm::Association<reco::DeDxHitInfoCollection>")
prsc = Handle("edm::ValueMap<int>")
#new = (argv[2] == "new")
#passByBit = [0,0,0,0]

def harmonic2(vals, trunk):
    if len(vals) == 0: return 0
    vals.sort()
    first = int(len(vals)*(1-trunk))
    avg = sum(pow(v,-2) for v in vals[first:])/(len(vals)-first)
    return pow(avg,-0.5)

counts = [[0,0] for p in ptbins]
u_counts = [[0,0] for p in ptbins]
p_counts = [[0,0] for p in ptbins]
p2_counts = [[0,0] for p in ptbins]
for i,event in enumerate(events):
    event.getByLabel("generalTracks", trks)
    event.getByLabel("dedxPixelAndStripHarmonic2T085", vmap)
    event.getByLabel("dedxPixelHarmonic2", vpix)
    event.getByLabel("dedxHarmonic2", vstr)
    event.getByLabel("dedxHitInfo", asso)
    event.getByLabel("dedxHitInfo:prescale", prsc)
    dedx = vmap.product().get
    dxir = asso.product().get
    pscr = prsc.product()
    for itk, tk in enumerate(trks.product()):
        if tk.pt() < 0.5: continue
        val = dedx(itk).dEdx()
        for b,pt in enumerate(ptbins):
            if tk.pt() > pt: continue
            counts[b][val > dedxcut] += 1
            break
        ref = dxir(itk)
        if ref.isNull(): continue
        psv = pscr.get(ref.id(),ref.key())
        #if psv not in (1,100,2000): raise RuntimeError, "Funny prescale %s" % psv
        phits = []; shits = []
        dedxhits = ref.get(); nhits = dedxhits.size()
        for ih in xrange(nhits):
            if dedxhits.detId(ih).subdetId() <= 2: phits.append( dedxhits.charge(ih)/dedxhits.pathlength(ih) * 3.61e-06 )
            else:                             
                if ROOT.DeDxTools.shapeSelection(dedxhits.stripCluster(ih)):
                    shits.append( dedxhits.charge(ih)/dedxhits.pathlength(ih) * 3.61e-06 * 265 )
        oldval = val
        val = harmonic2(phits+shits, 0.85)
        if abs(oldval-val)>0.0001: 
            print "Mismatch in dEdx: %.4f vs %.4f" % (oldval, val)
            print "  strip only    : %.4f vs %.4f" % (vstr.product().get(itk).dEdx(), harmonic2(shits,1))
            print "  pixel only    : %.4f vs %.4f" % (vpix.product().get(itk).dEdx(), harmonic2(phits,1))
            exit()
        for b,pt in enumerate(ptbins):
            if tk.pt() > pt: continue
            u_counts[b][val > dedxcut] += 1
            p_counts[b][val > dedxcut] += psv
            p2_counts[b][val > dedxcut] += psv**2
            break
    #if i >= 500: break

i = float(i+1)
print "On a sample of %d events:" % i
for b,(f,p) in enumerate(counts):
    fu,pu = u_counts[b]
    f2,p2 = p_counts[b]
    fw2,pw2 = p2_counts[b]
    print "pt bin %4.1f - %4.1f : dEdx >  %4.1f:  %8.2f +- %7.2f tracks/event :  %8.2f +- %7.2f  weighted,   %8.2f +- %7.2f   unweighted" % (
        0.5 if b == 0 else ptbins[b-1], ptbins[b], dedxcut, p/i,sqrt(p)/i, p2/i, sqrt(pw2)/i, pu/i, sqrt(pu)/i)
    print "                   : dEdx <= %4.1f:  %8.2f +- %7.2f tracks/event :  %8.2f +- %7.2f  weighted,   %8.2f +- %7.2f   unweighted" % (
        dedxcut, f/i,sqrt(f)/i, f2/i, sqrt(fw2)/i, fu/i, sqrt(fu)/i)
