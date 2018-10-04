import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libFWCoreFWLite.so");
ROOT.gSystem.Load("libDataFormatsFWLite.so");
ROOT.FWLiteEnabler.enable()

from sys import argv
from DataFormats.FWLite import Handle, Events

events = Events(argv[1])
taus, tauLabel  = Handle("std::vector<pat::Photon>"), "slimmedPhotons"

for iev,event in enumerate(events):
    print "\nEvent %d:%d:%d" % ( event.eventAuxiliary().run(), event.eventAuxiliary().luminosityBlock(), event.eventAuxiliary().event())
    event.getByLabel(tauLabel, taus)

    for j,t in enumerate(taus.product()):
        print "Photon pt %6.2f eta %+5.3f phi %+5.3f  energy %6.2f" % (t.pt(),t.eta(),t.phi(),t.energy())
        for pair in t.photonIDs():
            print "\tID        %-50s: %8.4f" % (pair.first, pair.second)
        for label in t.userFloatNames():
            print "\tUserFloat %-50s: %8.4f" % (label, t.userFloat(label))
        for label in t.userIntNames():
            print "\tUserInt %-50s: %8.4f" % (label, t.userInt(label))
        print ""
    
    if iev > 20: break 

