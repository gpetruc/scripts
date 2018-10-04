import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libFWCoreFWLite.so");
ROOT.gSystem.Load("libDataFormatsFWLite.so");
ROOT.gSystem.Load("libRecoTrackerDeDx.so");
ROOT.FWLiteEnabler.enable()

from sys import argv
from math import *
from DataFormats.FWLite import Handle, Events
from PhysicsTools.HeppyCore.utils.deltar import *

events = Events(argv[1])
if "AOD" in argv[1] and ( "MINIAOD" not in argv[1].upper()):
    miniAOD = False
    print "This is AOD"
    trks = Handle("std::vector<reco::Track>")
    tklabel = "generalTracks"
    asso = Handle("edm::Association<reco::DeDxHitInfoCollection>")
    assolabel = "dedxHitInfo"
else:
    miniAOD = True
    print "This is MINIAOD"
    trks = Handle("std::vector<pat::IsolatedTrack>")
    tklabel = "isolatedTracks"
    asso = Handle("edm::Association<reco::DeDxHitInfoCollection>")
    assolabel = "isolatedTracks"

for i,event in enumerate(events):
    event.getByLabel(tklabel, trks)   
    event.getByLabel(assolabel, asso)  
    if "ootb" in argv[1]:
        fixed = asso.product().fixOffsets(-1)
        getref = fixed.get
    else:
        getref = asso.product().get
    evno = "Event %6d:%5d:%12d" % ( event.eventAuxiliary().run(), event.eventAuxiliary().luminosityBlock(), event.eventAuxiliary().event() )
    for itk, tk in enumerate(trks.product()):
        if tk.pt() < 50: continue
        print "%s   track pt %8.1f eta %+5.2f phi %+5.2f    hits %1d + %2d  highPurity %1d     " % ( 
                    evno, tk.pt(), tk.eta(), tk.phi(),  
                    tk.hitPattern().numberOfValidPixelHits(), tk.hitPattern().numberOfValidStripHits(), 
                    tk.isHighPurityTrack() if miniAOD else tk.quality(tk.highPurity)),
        #print "map size: %d " % (asso.product().size())
        #print "ref size: %d " % (asso.product().ref().get().size())
        ref = getref(itk)
        if ref.isNull(): 
            print " <no de/dx>"
            continue
        dedx = ref.get(); nhits = dedx.size()
        print " de/dx info with %d hits" % nhits
