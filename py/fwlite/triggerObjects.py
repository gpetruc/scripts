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
triggerBits, triggerBitLabel = Handle("edm::TriggerResults"), ("TriggerResults","","HLT")
triggerObjects, triggerObjectLabel  = Handle("std::vector<pat::TriggerObjectStandAlone>"), "slimmedPatTrigger"

for iev,event in enumerate(events):
    print "\nEvent %d:%d:%d" % ( event.eventAuxiliary().run(), event.eventAuxiliary().luminosityBlock(), event.eventAuxiliary().event())
    event.getByLabel(triggerObjectLabel, triggerObjects)
    event.getByLabel(triggerBitLabel, triggerBits)

    for j,to in enumerate(triggerObjects.product()):
        if to.pt() < 20: continue
        to.unpackNamesAndLabels(event.object(), triggerBits.product())
        pathslast = set(to.pathNames(True))
        if not any(("HLT_Ele" in str(p) or "HLT_IsoMu" in str(p))for p in to.pathNames()): continue
        #if not to.type(82): continue
        if len(pathslast) == 0: continue
        print "%04d pt %6.2f eta %+5.3f phi %+5.3f pdgId %+2d  %-30s " % (j,to.pt(),to.eta(),to.phi(),to.pdgId(),to.collection())
        print "         ids: ", ", ".join([str(f) for f in to.triggerObjectTypes()])
        print "         filters: ", ", ".join([str(f) for f in to.filterLabels()])
        print "         paths:   ", ", ".join([("%s*" if f in pathslast else "%s")%f for f in to.pathNames()])
        print ""
    
    if iev > 20: break 

