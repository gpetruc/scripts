import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libFWCoreFWLite.so");
ROOT.gSystem.Load("libDataFormatsFWLite.so");
ROOT.FWLiteEnabler.enable()

from sys import argv
#from math import pow, sqrt
from DataFormats.FWLite import Handle, Events

events = Events(argv[1])
cands = Handle("std::vector<reco::PFCandidate>")

for i,event in enumerate(events):
    event.getByLabel("particleFlow", cands)
    print "\nNEW EVENT"
    for ic,p in enumerate(cands.product()):
        if p.pt() < 0.7: continue
        if abs(p.eta()) < 1.5 or abs(p.eta()) > 3.0: continue
        print "  %4d pdgId %+4d  pt %7.2f eta %+5.2f phi %+5.2f :   hcalEnergy %7.1f (raw %7.1f). " % (ic, p.pdgId(), p.pt(), p.eta(), p.phi(), p.hcalEnergy(), p.rawHcalEnergy()),
        for d in xrange(1,8):
            fr = p.hcalDepthEnergyFraction(d)
            if fr > 0: print " depth %d: %5.3f  " % (d, fr),
            #if fr > 0: print " depth %d: %r  " % (d, fr),
        print ""
    if i > 5: break
