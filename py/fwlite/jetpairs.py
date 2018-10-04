import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libFWCoreFWLite.so");
ROOT.gSystem.Load("libDataFormatsFWLite.so");
ROOT.FWLiteEnabler.enable()


from optparse import OptionParser
parser = OptionParser(usage="usage: %prog inputfile_ref inputfile_new out.root")
parser.add_option("-N", "--maxEv", dest="maxEv", default=100000, type=int, help="Max events to process")
parser.add_option("-l", "--lumifile", dest="lumifile", default=None, help="Max events to process")
parser.add_option("-a", "--allevents", dest="allevents", default=False, action="store_true", help="Max events to process")
parser.add_option("-A", "--allprint", dest="allprint", default=False, action="store_true", help="Max events to process")
parser.add_option("-R", "--regression", dest="regression", default=False, action="store_true", help="Max events to process")
parser.add_option("--tol", dest="tolerance", default=3e-6, type="float", help="Tolerance in regression check")
(options, args) = parser.parse_args()


lumiSel = set() 
if options.lumifile:
    for line in open(options.lumifile, "r"):
        if "(Lumi)" not in line: continue
        fields = line.split()
        lumiSel.add(tuple(map(int,fields[:2])))
    print "Will only consider %d lumi blocks: %s" % (len(lumiSel), list("%d:%d" % l for l in sorted(lumiSel)))

if len(args) != 3:
    parser.print_usage()
    exit(1)

from DataFormats.FWLite import Handle, Events

class Jet:
    def __init__(self,p):
        rawpt = p.pt()*p.jecFactor('Uncorrected')
        self._vals = dict(pt = p.pt(), eta = p.eta(), phi=p.phi(), rawpt = rawpt, ch = rawpt*p.chargedHadronEnergyFraction(), nh = rawpt*p.neutralHadronEnergyFraction(), ce = rawpt*p.chargedEmEnergyFraction(), ne = rawpt*p.neutralEmEnergyFraction(), mu = rawpt*p.muonEnergyFraction(), gen = p.genJet().pt() if p.genJet() else -99, gen_eta = p.genJet().eta() if p.genJet() else -99)
    def keys(self): 
        return self._vals.keys()
    def eta(self):
        return self._vals['eta']
    def phi(self):
        return self._vals['phi']
    def val(self,k): 
        return self._vals[k]

def readEvents(filename, role):
    ret = dict()
    events = Events(filename)

    jets = Handle("std::vector<pat::Jet>")

    for i,event in enumerate(events):
        event.getByLabel("slimmedJets", jets)
        run,lumi,evt = event.eventAuxiliary().run(), event.eventAuxiliary().luminosityBlock(), event.eventAuxiliary().event()
        if lumiSel and ((run,lumi) not in lumiSel): continue
        seljets = []
        for p in jets.product():
            if (not p.genJet()) or p.genJet().pt() < 20: continue
            if p.eta() < -2.9 or p.eta() > -1.6 or p.phi() < -2.2 or p.phi() > -0.7: continue
            seljets.append( Jet(p) )
        if seljets:
            ret[(run,lumi,evt)] = seljets
        if i > options.maxEv: break

    print "Read %d events from %s %s, found %s events with interesting jets" % (i, role, filename, len(ret))
    return ret

events_ref = readEvents(args[0], "reference")
events_new = readEvents(args[1], "new")
common = sorted(set(events_ref.keys()).intersection(events_new.keys()))
print "%d common events. now doing jet-by-jet comparison" % len(common)


from PhysicsTools.HeppyCore.utils.deltar import matchObjectCollection3, deltaR
from PhysicsTools.HeppyCore.statistics.tree import Tree
fout = ROOT.TFile.Open(args[2], "RECREATE")
tree = Tree("t","t","F");
for X in "run", "lumi", "event":
    tree.var(X,int)
jetvars = events_ref[common[0]][0].keys() 
for Y in jetvars:
    tree.var("r_"+Y)
    tree.var(""  +Y)
tree.var("deltaR")


goodevents = set()
print "%-14s     |  %8s   %8s   %8s   %7s  |  %7s  %7s    %7s  %7s    %7s  %7s    %7s  %7s    %7s  %7s" % ( 
        "event", "new pt", "ref pt", "gen pt", "gen eta",  "c had","ref", "n had","ref", "c em","ref", "n em","ref", "mu","ref")
for key in common:
    (run,lumi,event) = key
    jets_ref = events_ref[key]
    jets_new = events_new[key]
    matching = matchObjectCollection3(jets_ref, jets_new, 0.3, filter = lambda r,n : abs(r.val("gen")-n.val("gen"))<0.01)
    tree.fill("run", run)
    tree.fill("lumi", lumi)
    tree.fill("event", event)
    for jr in jets_ref:
        jm = matching[jr]
        if not jm: continue
        for v in jetvars:
            tree.fill("r_"+v,jr.val(v))
            tree.fill(v,jm.val(v))
        tree.fill("deltaR", deltaR(jr,jm))
        tree.tree.Fill()
        goodevents.add(key)
        newpt, refpt, genpt, gen_eta = jm.val("pt"), jr.val("pt"), jr.val("gen"), jr.val("gen_eta")
        toPrint = options.allprint
        if abs(newpt/refpt-1) > 0.2 and abs(refpt/genpt-1)<0.2 and abs(newpt/genpt-1)>2*abs(refpt/genpt-1): toPrint = True
        if options.regression:
            toPrint = False
            for var in jetvars:
                if abs(jm.val(var)-jr.val(var)) > options.tolerance*(abs(jm.val(var))+abs(jr.val(var))+1): 
                    print "Regression on %d:%d:%d  jet pt %8.2f eta %+6.2f  variable %s: %10.6f  %10.6f  %+10.6f   %g" % (
                            run,lumi,event, genpt, gen_eta, var, 
                            jm.val(var), jr.val(var), jm.val(var)-jr.val(var), abs(jm.val(var)-jr.val(var))/(abs(jm.val(var))+abs(jr.val(var))+1))
                    toPrint = True
                    break
        quality = "  "
        if abs(newpt-refpt) < options.tolerance*(newpt+refpt):
            quality = "==" 
        elif abs(newpt-genpt) < 0.7*abs(refpt-genpt):
            quality = "++"
        elif abs(refpt-genpt) < 0.7*abs(newpt-genpt):
            quality = "--"
        elif abs(newpt-genpt) < 0.9*abs(refpt-genpt):
            quality = "+ "
        elif abs(refpt-genpt) < 0.9*abs(newpt-genpt):
            quality = "- "
        if toPrint:
            print "%-14s  %s |  %8.2f   %8.2f   %8.2f   %+7.2f  |  %7.1f  %7.1f    %7.1f  %7.1f    %7.1f  %7.1f    %7.1f  %7.1f    %7.1f  %7.1f" % (
                    "%d:%d:%d" % key, quality, newpt, refpt, genpt, gen_eta,  jm.val("ch"), jr.val("ch"), jm.val("nh"), jr.val("nh"),  jm.val("ce"), jr.val("ce"), jm.val("ne"), jr.val("ne"), jm.val("mu"), jr.val("mu") )

print "Processed events:  %d" % len(common)
print "Matched jet pairs: %d" % tree.tree.GetEntries()
fout.cd()
fout.WriteTObject(tree.tree)
fout.Close()

print "Ntuple saved on %s" % args[2]

if options.allevents:
    print "all events: %s" % ", ".join('"%d:%d:%d"' % k for k in sorted(goodevents))

