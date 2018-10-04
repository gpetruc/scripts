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
jets = Handle("std::vector<reco::PFJet>")
rho = Handle("double")

for i,event in enumerate(events):
    event.getByLabel("ak4PFJetsCHS", jets)
    event.getByLabel("fixedGridRhoFastjetAll", rho)
    print "EVENT %d, rho = %10.5f" % (i, rho.product()[0])
    for ic,p in enumerate(jets.product()):
        print "  %4d pt %10.5f eta %+7.5f phi %+7.5f jetArea %10.6f" % (ic, p.pt(), p.eta(), p.phi(), p.jetArea())
    if i > 5: break
    print ""
