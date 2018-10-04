import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libFWCoreFWLite.so");
ROOT.gSystem.Load("libDataFormatsFWLite.so");
ROOT.FWLiteEnabler.enable()

from math import sqrt
from sys import argv
from DataFormats.FWLite import Handle, Events
from PhysicsTools.HeppyCore.utils.deltar import *
from PhysicsTools.HeppyCore.statistics.tree import *

fout = ROOT.TFile.Open(argv[2], "RECREATE")
tree = Tree("t","t","F");
for var in "pt eta phi hadTowOverEm sigmaIetaIeta trkSumPtSolidConeDR03 trkSumPtHollowConeDR03 ecalRecHitSumEtConeDR03 genDR genPT".split():
    tree.var(var)

events = Events(argv[1])
phos, phoLabel  = Handle("std::vector<pat::Photon>"), "slimmedPhotons"
gps, gpLabel  = Handle("std::vector<reco::GenParticle>"), "prunedGenParticles"

maxev = int(argv[3]) if len(argv) >= 4 else 20

for iev,event in enumerate(events):
    event.getByLabel(phoLabel, phos)
    event.getByLabel(gpLabel, gps)
    gpho = [ p for p in gps.product() if p.pdgId() == 22 and p.pt() > 20 and p.isPromptFinalState() ]

    for p in phos.product():
        if p.pt() < 20: continue
        match, dr2 = bestMatch(p, gpho)
        if match == None or dr2 > 0.2**2: continue
        for var in "pt eta phi hadTowOverEm sigmaIetaIeta trkSumPtSolidConeDR03 trkSumPtHollowConeDR03 ecalRecHitSumEtConeDR03".split():
            tree.fill(var, getattr(p,var)())
        tree.fill("genDR", sqrt(dr2))
        tree.fill("genPT", match.pt())
        tree.tree.Fill()
    if iev > maxev: break 
    if maxev > 20 and iev % (maxev/20) == 0:
        print "Processing: %d events, %d photons" % (iev+1, tree.tree.GetEntries())
print ""
print "Processed events:  %d" % (iev+1)
print "Selected  photons: %d" % tree.tree.GetEntries()
fout.cd()
fout.WriteTObject(tree.tree)
fout.Close()

