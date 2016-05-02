from sys import argv
argv.append( '-b-' )
import ROOT
ROOT.gROOT.SetBatch(True)
argv.remove( '-b-' )

ROOT.gSystem.Load("libFWCoreFWLite.so");
ROOT.gSystem.Load("libDataFormatsFWLite.so");
ROOT.AutoLibraryLoader.enable()

from DataFormats.FWLite import Handle, Events
events = Events("patTuple_micro.root")
trig = Handle("std::vector<pat::TriggerObjectStandAlone>")

for i,event in enumerate(events):
    print "\nEvent", i
    event.getByLabel("patTrigger", trig)
    for j,to in enumerate(trig.product()):
        print "%04d pt %6.2f eta %+5.3f phi %+5.3f  %-30s " % (j,to.pt(),to.eta(),to.phi(),to.collection())
        print "         filters: ", ", ".join([str(f) for f in to.filterLabels()])
        pathslast = set(to.pathNames(True))
        print "         paths:   ", ", ".join([("%s*" if f in pathslast else "%s")%f for f in to.filterLabels()])


