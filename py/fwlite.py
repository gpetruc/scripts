import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libFWCoreFWLite.so");
ROOT.gSystem.Load("libDataFormatsFWLite.so");
ROOT.FWLiteEnabler.enable()

from sys import argv
from math import *
from DataFormats.FWLite import Handle, Events
from PhysicsTools.HeppyCore.utils.deltar import *

events = Events(argv[1])
trig = Handle("std::vector<pat::TriggerObjectStandAlone>")

for iev,event in enumerate(events):
    print "\nEvent %d:%d:%d" % ( event.eventAuxiliary().run(), event.eventAuxiliary().luminosityBlock(), event.eventAuxiliary().event())
    event.getByLabel("patTrigger", trig)
    for j,to in enumerate(trig.product()):
        print "%04d pt %6.2f eta %+5.3f phi %+5.3f  %-30s " % (j,to.pt(),to.eta(),to.phi(),to.collection())
        print "         filters: ", ", ".join([str(f) for f in to.filterLabels()])
        pathslast = set(to.pathNames(True))
        print "         paths:   ", ", ".join([("%s*" if f in pathslast else "%s")%f for f in to.filterLabels()])


