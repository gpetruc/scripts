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
from PhysicsTools.HeppyCore.statistics.tree import *

fout = ROOT.TFile.Open(argv[2], "RECREATE")
tree = Tree("t","t","F");

events = Events(argv[1])
trig = Handle("std::vector<pat::IsolatedTrack>")
nevents = 0; ntracks = 0;

for var in "pt eta dxy dxyError dz dzError ptRelError miniRelIso pfNeutralSum relIso03".split():
    tree.var(var)
for ivar in "highPurity nHits nLayers nPixelHits nPixelLayers pfLepOverlap".split():
    tree.var(ivar,int)

for i,event in enumerate(events):
    nevents += 1
    event.getByLabel("isolatedTracks", trig)
    if i % 100 == 0: 
        print "events %8d tracks %8d" % (nevents, ntracks)

    for itk, tk in enumerate(trig.product()):
        if tk.pt() < 10: continue
        for var in "pt eta dxy dxyError dz dzError".split():
            tree.fill(var, getattr(tk,var)())
        ptRelError = -1
        if tk.packedCandRef().isNonnull() and tk.packedCandRef().get().bestTrack(): 
            ptRelError = tk.packedCandRef().get().bestTrack().ptError() / tk.pt()
        tree.fill("ptRelError",   ptRelError)
        tree.fill("miniRelIso", tk.miniPFIsolation().chargedHadronIso()/tk.pt() )
        tree.fill("relIso03", tk.pfIsolationDR03().chargedHadronIso()/tk.pt() )
        tree.fill("pfNeutralSum", tk.pfNeutralSum()/tk.pt() )
        tree.fill("highPurity",   tk.isHighPurityTrack())
        tree.fill("nHits",   tk.hitPattern().numberOfValidHits())
        tree.fill("nLayers",  tk.hitPattern().trackerLayersWithMeasurement())
        tree.fill("nPixelHits",   tk.hitPattern().numberOfValidPixelHits())
        tree.fill("nPixelLayers",  tk.hitPattern().pixelLayersWithMeasurement())
        tree.fill("pfLepOverlap",  tk.pfLepOverlap())
        tree.tree.Fill()
        ntracks += 1
    if nevents >= 1000: break

print "Processed events: %d" % nevents
print "Selected  tracks: %d" % ntracks
fout.cd()
fout.WriteTObject(tree.tree)
fout.Close()

