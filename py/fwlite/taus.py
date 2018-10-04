import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libFWCoreFWLite.so");
ROOT.gSystem.Load("libDataFormatsFWLite.so");
ROOT.FWLiteEnabler.enable()

from sys import argv
from DataFormats.FWLite import Handle, Events

events = Events(argv[1])
taus, tauLabel  = Handle("std::vector<pat::Tau>"), "slimmedTaus"

for iev,event in enumerate(events):
    print "\nEvent %d:%d:%d" % ( event.eventAuxiliary().run(), event.eventAuxiliary().luminosityBlock(), event.eventAuxiliary().event())
    event.getByLabel(tauLabel, taus)

    for j,t in enumerate(taus.product()):
        print "Tau pt %6.2f eta %+5.3f phi %+5.3f " % (t.pt(),t.eta(),t.phi())
        for pair in t.tauIDs():
            print "\t%-50s: %8.4f" % (pair.first, pair.second)
        print ""
    
    if iev > 20: break 

