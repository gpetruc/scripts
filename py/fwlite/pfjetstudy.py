#!/usr/bin/env python
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libFWCoreFWLite.so");
ROOT.gSystem.Load("libDataFormatsFWLite.so");
ROOT.FWLiteEnabler.enable()

import sys

from math import sqrt, cosh

from DataFormats.FWLite import Handle, Events
from PhysicsTools.HeppyCore.utils.deltar import deltaR, matchObjectCollection, matchObjectCollection3, bestMatch

from optparse import OptionParser
parser = OptionParser("%(prog) infile [ src [ dst ] ]")
parser.add_option("-e", "--events", dest="events", action="append", default=[],  type="string", help="Select these events")
parser.add_option("-N", "--maxEv", dest="maxEv", default=1000, type=int, help="Max events to process")
options, args = parser.parse_args()


htk = Handle("std::vector<reco::Track>")
hvx = Handle("std::vector<reco::Vertex>")
hpf = Handle("std::vector<reco::PFCandidate>")
hpfb = Handle("std::vector<reco::PFBlock>")
hgsfe = Handle("std::vector<reco::GsfElectron>")
hmu   = Handle("std::vector<reco::Muon>")
hpfc = Handle("std::vector<reco::PFCluster>")
hcalt = Handle("edm::SortedCollection<CaloTower,edm::StrictWeakOrdering<CaloTower> >")
hcalj = Handle("std::vector<reco::CaloJet>")
genj  = Handle("std::vector<reco::GenJet>")
genp  = Handle("std::vector<reco::GenParticle>")

gIndex_ = 0

class Base:
    def __init__(self,p,init=True):
        global gIndex_;
        self._vals = dict(pt = p.pt(), eta = p.eta(), phi=p.phi(), charge=p.charge()) if init else {}
        gIndex_ += 1
        self._i = gIndex_
    def keys(self): 
        return self._vals.keys()
    def eta(self):
        return self._vals['eta']
    def phi(self):
        return self._vals['phi']
    def pt(self):
        return self._vals['pt']
    def charge(self):
        return self._vals['charge']
    def __getitem__(self,k):
        return self._vals[k]
    def __setitem__(self,k,v):
        self._vals[k] = v
    def pdgId(self):
        return self._vals['pdgId'] if 'pdgId' in self._vals else (self._vals['charge'] * 211)
    def uid(self): 
        return self._i

PFTypes = {}
for tn in "TRACK GSF ECAL HCAL HFEM HFHAD SC".split():
    PFTypes[tn] = getattr(ROOT.reco.PFBlockElement, tn)
    PFTypes[PFTypes[tn]] = tn
class PFBlock(Base):
    def __init__(self,p):
        Base.__init__(self,p,init=False)
        self._elems = []
        p4 = ROOT.reco.Particle.LorentzVector(0.,0.,0.,0.)
        #print "PFBlock with %d elements: " % p.elements().size()
        for el in p.elements():
            eltype = el.type()
            #print "  Element of type %d" % eltype
            if eltype == PFTypes['TRACK'] or eltype == PFTypes['GSF']:
                trk = (el.trackRef() if eltype == PFTypes['TRACK'] else el.GsftrackRef()).get() 
                p4 += ROOT.reco.Particle.PolarLorentzVector(trk.pt(),trk.eta(),trk.phi(),0.130)
                self._elems.append(Track(trk))
                if el.muonRef().isNonnull():
                    self._elems[-1]['pdgId'] = -13 * trk.charge()
                elif eltype == PFTypes['GSF']:
                    self._elems[-1]['pdgId'] = -11 * trk.charge()
                self._elems[-1]['type'] = eltype 
            elif eltype in (PFTypes['ECAL'], PFTypes['HCAL'], PFTypes['HFEM'], PFTypes['HFHAD']):
                if eltype == PFTypes['HCAL'] and not el.clusterRef().isAvailable(): continue
                clust = el.clusterRef().get()
                p4 += ROOT.reco.Particle.PolarLorentzVector(clust.pt(),clust.eta(),clust.phi(),0)
                self._elems.append(PFClust(clust, pdgId=(22 if eltype == PFTypes['ECAL'] else 130)))
                self._elems[-1]['type'] = eltype 
            elif eltype == PFTypes['SC']:
                clust = el.superClusterRef().get()
                pt = clust.energy()/cosh(clust.eta())
                p4 += ROOT.reco.Particle.PolarLorentzVector(pt,clust.eta(),clust.phi(),0)
                self._elems.append(Base(clust, init=False))
                self._elems[-1]['pt'] = pt
                self._elems[-1]['eta'] = clust.eta()
                self._elems[-1]['phi'] = clust.phi()
                self._elems[-1]['charge'] = 0
                self._elems[-1]['pdgId'] = 22
                self._elems[-1]['type'] = eltype 
        if len(self._elems) != 0:
            self._vals['charge'] = 0
            self._vals['pt'] = p4.Pt()
            self._vals['eta'] = p4.Eta()
            self._vals['phi'] = p4.Phi()
            #print "  total: pt %7.2f eta %+5.2f phi %+5.2f" % (p4.Pt(), p4.Eta(), p4.Phi())
        #else:
        #print "  total: zorro" 
    def __nonzero__(self):
        return len(self._elems) != 0
    def elems(self):
        return self._elems

class Track(Base):
    def __init__(self,p,vtx=None):
        Base.__init__(self,p)
        self._vals.update(ptError=p.ptError(), hp=p.quality(p.highPurity), vz=p.vertex().Z(),
                algo=p.algo(), origAlgo=p.originalAlgo(), 
                algoJ=p.isAlgoInMask(p.jetCoreRegionalStep), 
                algoM=p.isAlgoInMask(p.muonSeededStepOutIn), 
                algoC=p.isAlgoInMask(p.conversionStep), 
                algoE=(p.isAlgoInMask(p.outInEcalSeededConv) or p.isAlgoInMask(p.inOutEcalSeededConv)),
                chi2n = p.normalizedChi2(), 
                dxy = (abs(p.dxy(vtx.position())), p.dxyError()) if vtx else (-1,-1),
                dz = (abs(p.dz(vtx.position())), p.dzError()) if vtx else (-1,-1),
        )
        hp = p.hitPattern()
        self._vals['layers'] = ( hp.trackerLayersWithMeasurement(),
                                 hp.trackerLayersWithoutMeasurement(hp.TRACK_HITS),
                                 hp.trackerLayersWithoutMeasurement(hp.MISSING_INNER_HITS),
                                 hp.trackerLayersWithoutMeasurement(hp.MISSING_OUTER_HITS) )
    def algoStr(self):
        return "%2d%-4s" % (self._vals['algo'], 
                   "".join(L for L in "JMCE" if self._vals['algo'+L]))
    def chi2nStr(self): 
        return ("%.1f" % min(self._vals['chi2n'], 99.9))[:3]

    def layersStr(self): 
        return ("v/l %2d/%1d+%1d+%2d" % self._vals['layers'])

    def dxyStr(self):
        return self.ipStr('dxy')
    def dzStr(self):
        return self.ipStr('dz')
    def ipStr(self,ip):
        ipv = self._vals[ip][0]
        if ipv < 0.9:
            return ("%.2f +- %.2f" % self._vals[ip]).replace("0.",".")
        elif ipv < 9.9:
            return "%.1f +- %.1f" % self._vals[ip]
        else:
            return "%.0f. +- %.0f." % self._vals[ip]

class Cand(Base):
    def __init__(self,p):
        Base.__init__(self,p)
        self._vals.update(pdgId=p.pdgId(), vz=p.vertex().Z())
    def pdgId(self):
        return self._vals['pdgId']

class CaloTower(Base):
    def __init__(self,p):
        Base.__init__(self,p)
        self._vals.update(emEt = p.emEt(), hadEt = p.hadEt(), ieta = p.ieta(), iphi = p.iphi())
class CaloJet(Base):
    def __init__(self,p):
        Base.__init__(self,p)
        self._vals.update(emEt = p.pt()*p.emEnergyFraction(), hadEt = p.pt()*p.energyFractionHadronic())


class PFCand(Cand):
    def __init__(self,p):
        Cand.__init__(self,p)
        self._vals.update(e=p.energy(), ecal=p.ecalEnergy(), rawecal=p.rawEcalEnergy(), hcal=p.hcalEnergy(), rawhcal=p.rawHcalEnergy(),
                          mvaIso=max(-9.99,p.mva_Isolated()), mvaEP=max(-9.99,p.mva_e_pi()))

class GsfEle(Cand):
    def __init__(self,p):
        Cand.__init__(self,p)
        self._vals.update(e=p.energy(), ecal=p.ecalEnergy(),
                          mvaIso=p.mva_Isolated(), mvaEP=p.mva_e_pi(), sieie=p.full5x5_sigmaIetaIeta(), r9=p.full5x5_r9(), ecalD=p.ecalDriven(), pfPresel=p.passingPflowPreselection())
        self._vals['1ep'] = abs(1.0-p.eSuperClusterOverP())/p.ecalEnergy()
        self._vals['deta'] = abs(p.deltaEtaSuperClusterTrackAtVtx() - p.superCluster().eta() + p.superCluster().seed().eta())
        self._vals['dphi'] = abs(p.deltaPhiSuperClusterTrackAtVtx())

class Muon(Cand):
    def __init__(self,p):
        Cand.__init__(self,p)
        self._vals.update(pf=p.isPFMuon(), seg=p.numberOfMatchedStations(), glb=p.isGlobalMuon(), cc=p.caloCompatibility(), iso03=p.isolationR03().sumPt,
                          tkPt = p.innerTrack().pt() if p.innerTrack().isNonnull() else -99, tkPtErr = p.innerTrack().ptError() if p.innerTrack().isNonnull() else -99,
                          staPt = p.outerTrack().pt() if p.outerTrack().isNonnull() else -99, staPtErr = p.outerTrack().ptError() if p.outerTrack().isNonnull() else -99,
                          glbPt = p.globalTrack().pt() if p.globalTrack().isNonnull() else -99, glbPtErr = p.globalTrack().ptError() if p.globalTrack().isNonnull() else -99)
    def idWord(self):
        return "".join(["G" if self['glb'] else " ", 
                        "T%1d" % self['seg'] if self['seg'] else "  ", 
                        "P" if self['pf'] else " ",
                        "/C%.3f" % self['cc']])
    def allpts(self):
        return "%-18s %-18s %-18s" % (("tk %5.1f +- %4.1f " % (self['tkPt'],self['tkPtErr']) if self['tkPt'] > 0 else ""),
                                      ("sta %5.1f +- %4.1f " % (self['staPt'],self['staPtErr']) if self['staPt'] > 0 else ""),
                                      ("glb %5.1f +- %4.1f " % (self['glbPt'],self['glbPtErr']) if self['glbPt'] > 0 else ""))

class PFClust(Base):
    def __init__(self,p,pdgId=0):
        Base.__init__(self,p)
        self._vals.update(pdgId=pdgId)
    def pdgId(self):
        return self._vals['pdgId']


class GenJet(Base):
    def __init__(self,p):
        Base.__init__(self,p)
        self._daus = [ Cand(p.daughter(i)) for i in xrange(p.numberOfDaughters()) ]
        for d in self._daus: 
            d.dr = deltaR(d,p)
        self._daus.sort(key = lambda d : d.dr)
    def daus(self):
        return self._daus

def readEvents(fname):
    ret = {}
    events = Events(fname)
    print "Reading %s " % fname,
    for iev,event in enumerate(events):
        if iev > options.maxEv: break
        if iev % 10 == 9: 
            sys.stdout.write("."); sys.stdout.flush()
        idev = "%d:%d:%d" % ( event.eventAuxiliary().run(), event.eventAuxiliary().luminosityBlock(), event.eventAuxiliary().event())
        if options.events:
           if idev not in options.events: continue
           sys.stdout.write("+"); sys.stdout.flush()

        event.getByLabel("ak4GenJetsNoNu", genj)
        event.getByLabel("genParticles", genp)
        selGen = []
        for j in genj.product():
            if j.pt() < 20 or j.eta() < -3.1 or j.eta() > -1.4 or j.phi() < -2.5 or j.phi() > -0.5: continue
            selGen.append(GenJet(j))

        if not selGen: continue

        event.getByLabel("offlinePrimaryVertices", hvx)
        PV0 = hvx.product()[0]

        selTracks = []
        event.getByLabel("generalTracks", htk)
        for tk in htk.product():
            if min(deltaR(j,tk) for j in selGen) < 0.7:
                selTracks.append(Track(tk, vtx=PV0))

        selPF = []
        event.getByLabel("particleFlow", hpf)
        for pf in hpf.product():
            if min(deltaR(j,pf) for j in selGen) < 0.7:
                selPF.append(PFCand(pf))

        selPFB = []
        event.getByLabel("particleFlowBlock", hpfb)
        iblock = 0
        for pf in hpfb.product():
            pfblock = PFBlock(pf)
            if pfblock and pfblock.pt() > 1.0:
                iblock += 1
                for pf in pfblock.elems():
                    pf['ib'] = iblock
                    if min(deltaR(j,pf) for j in selGen) < 0.7:
                        selPFB.append(pf)

        selGSF = []
        event.getByLabel("gedGsfElectrons", hgsfe)
        for pf in hgsfe.product():
            if min(deltaR(j,pf) for j in selGen) < 0.7:
                selGSF.append(GsfEle(pf))

        selMu = []
        event.getByLabel("muons", hmu)
        for pf in hmu.product():
            if min(deltaR(j,pf) for j in selGen) < 0.7:
                selMu.append(Muon(pf))


        selEcal = []
        event.getByLabel("particleFlowClusterECAL", hpfc)
        for pf in hpfc.product():
            if min(deltaR(j,pf) for j in selGen) < 0.7:
                selEcal.append(PFClust(pf, pdgId=22))

        selCaloTowers = []
        if not event.getByLabel("caloTowerForTrk", hcalt):
            event.getByLabel("towerMaker", hcalt)
        for pf in hcalt.product():
            if min(deltaR(j,pf) for j in selGen) < 0.7:
                selCaloTowers.append(CaloTower(pf))
        selCaloJets = []
        if not event.getByLabel("ak4CaloJetsForTrk", hcalj):
            event.getByLabel("ak4CaloJets", hcalj)
        for pf in hcalj.product():
            if min(deltaR(j,pf) for j in selGen) < 0.7:
                  selCaloJets.append(CaloJet(pf))

        ret[idev] = dict(gen=selGen, tracks=selTracks, ecal=selEcal, pf=selPF, pfblock=selPFB, gsfE=selGSF, mu=selMu, caloT=selCaloTowers, caloJ=selCaloJets)
        if options.events and len(ret) == len(options.events): 
            break
    print "\nRead %d events from %s, found %s events with interesting jets" % (iev, fname, len(ret))
    return ret

events_ref = readEvents(args[0])
events_new = readEvents(args[1])
common = sorted(set(events_ref.keys()).intersection(events_new.keys()))
print "%d common events" % len(common)

for key in common:
    print "Event: %s" % key
    genJ   = events_ref[key]["gen"]

    for j in genJ:
        print "------------------------"     
        print "gen jet pt %7.2f eta %+5.2f phi %+5.2f" % (j.pt(), j.eta(), j.phi()) 
        ptsum = 0
        for d in j.daus():
            if d.pt() < 1: continue
            ptsum += d.pt()
            print "        dau pt %7.2f  eta %+5.2f  phi %+5.2f  dr %.2f   id % +5d  ch %+1d  ptsum %7.2f" % (d.pt(), d.eta(), d.phi(), d.dr, d.pdgId(), d.charge(), ptsum) 
        print "   total pt from charged particles, pt > 1: %7.2f" % sum(d.pt() for d in j.daus() if d.charge() != 0 and d.pt() > 1)
        print "   total pt from photons          , pt > 1: %7.2f" % sum(d.pt() for d in j.daus() if d.charge() == 0 and d.pdgId() == 22 and d.pt() > 1)
        print "   total pt from neutrals (n, K0L), pt > 1: %7.2f" % sum(d.pt() for d in j.daus() if d.charge() == 0 and d.pdgId() in (130,2112,-2112) and d.pt() > 1)
        print "   total pt from short neut.(K0S) , pt > 1: %7.2f" % sum(d.pt() for d in j.daus() if d.charge() == 0 and d.pdgId() in (310,) and d.pt() > 1)
        print "   total pt from other neutrals   , pt > 1: %7.2f" % sum(d.pt() for d in j.daus() if d.charge() == 0 and d.pdgId() not in (22,130,2112,-2112,310) and d.pt() > 1)
        print ""
        
        c_tomatch = [g for g in j.daus() if g.charge() != 0 and g.pt() > 1]
        n_tomatch = [g for g in j.daus() if g.charge() == 0 and g.pt() > 1]
        a_tomatch = c_tomatch + n_tomatch

        tk2tk = matchObjectCollection3(events_new[key]["tracks"], events_ref[key]["tracks"], 0.07, lambda d,g: d.charge() == g.charge() and abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.2)
        pf2pf = matchObjectCollection3(events_new[key]["pf"], events_ref[key]["pf"], 0.07, lambda d,g: abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.6)
        pfb2pfb = matchObjectCollection3(events_new[key]["pfblock"], events_ref[key]["pfblock"], 0.07, lambda d,g: abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.6)
        gsf2gsf = matchObjectCollection3(events_new[key]["gsfE"], events_ref[key]["gsfE"], 0.07, lambda d,g: abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.6)
        #calt2calt = matchObjectCollection3(events_new[key]["caloT"], events_ref[key]["caloT"], 0.1)
        pf2tk_ref = matchObjectCollection3(events_ref[key]["pf"], events_ref[key]["tracks"], 0.07, lambda d,g: d.charge() == g.charge() and abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.6)
        pf2tk_new = matchObjectCollection3(events_new[key]["pf"], events_new[key]["tracks"], 0.07, lambda d,g: d.charge() == g.charge() and abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.6)
        pfb2tk_ref = matchObjectCollection(events_ref[key]["pfblock"], events_ref[key]["tracks"], 0.07, lambda d,g: d.charge() == g.charge() and abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.6)
        pf2pfb_ref = matchObjectCollection(events_ref[key]["pf"], events_ref[key]["pfblock"], 0.07, lambda d,g: d.charge() == g.charge() and abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.6)
        pfb2tk_new = matchObjectCollection(events_new[key]["pfblock"], events_new[key]["tracks"], 0.07, lambda d,g: d.charge() == g.charge() and abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.6)
        pf2pfb_new = matchObjectCollection(events_new[key]["pf"], events_new[key]["pfblock"], 0.07, lambda d,g: d.charge() == g.charge() and abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.6)
        mu2mu = matchObjectCollection3(events_new[key]["mu"], events_ref[key]["mu"], 0.07, lambda d,g: d.charge() == g.charge() and abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.2)
        mu2tk_ref = matchObjectCollection3(events_ref[key]["mu"], events_ref[key]["tracks"], 0.07, lambda d,g: d.charge() == g.charge() and abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.2)
        mu2tk_new = matchObjectCollection3(events_new[key]["mu"], events_new[key]["tracks"], 0.07, lambda d,g: d.charge() == g.charge() and abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.2)
        layers = [
                ('tk_ref', events_ref[key]["tracks"], []),
                ('tk_new', events_new[key]["tracks"], [tk2tk]), 
                ('ecal_ref', events_ref[key]["ecal"], []), 
                ('ecal_new', events_new[key]["ecal"], []),
                ('pfb_ref', events_ref[key]["pfblock"], [pfb2tk_ref]), 
                ('pfb_new', events_new[key]["pfblock"], [pfb2tk_new,pfb2pfb]), 
                ('pf_ref', events_ref[key]["pf"], [pf2tk_ref,pf2pfb_ref]), 
                ('pf_new', events_new[key]["pf"], [pf2tk_new,pf2pfb_new,pf2pf]),
                ('ele_ref', events_ref[key]["gsfE"], []), 
                ('ele_new', events_new[key]["gsfE"], [gsf2gsf]),
                ('mu_ref', events_ref[key]["mu"], [mu2tk_ref]), 
                ('mu_new', events_new[key]["mu"], [mu2tk_new,mu2mu]),
                ('calojets_ref', events_ref[key]["caloJ"], []), 
                ('calojets_new', events_new[key]["caloJ"], []),
                #('calotowers_ref', events_ref[key]["caloT"], []), 
                #('calotowers_new', events_new[key]["caloT"], [calt2calt]),
        ]
        keyer = {}; revkey = {}
        for ia,(a,objs,matchmaps) in enumerate(layers):
            layerlabel = chr(ia+ord("A"))
            print "    %s (%s)" %(a, layerlabel)
            matches = [ p for p in objs if deltaR(p,j) < 0.5 ]
            for d in matches: d.dr = deltaR(d,j)
            matches.sort(key = lambda p : p.dr)
            ptsum = 0
            esums = dict((k,[]) for k in ("e", "ecal", "rawecal", "hcal", "rawhcal"))
            # OK, try some MC matching for them
            if "pf" in a: 
                mcmatch =  dict((d,[]) for d in matches )
                # first, match and remove the charged
                charged = [d for d in matches if d.charge() != 0]
                neutral = [d for d in matches if d.charge() == 0]
                ch_match = matchObjectCollection3( charged, c_tomatch, 0.07, filter = lambda d,g: abs(d.pt()-g.pt())/(d.pt()+g.pt()) < 0.2 )
                gen_notused = a_tomatch[:]
                reco_notused = matches[:]
                for c in charged:
                    g = ch_match[c]
                    if g == None: continue
                    mcmatch[c] = [g]
                    gen_notused.remove(g)
                    reco_notused.remove(c)
                # then assign each gen to the nearest unmatched reco that has reco pt > 0.5 * gen pt
                for g in gen_notused[:]:
                    d, dr2 = bestMatch(g, reco_notused)
                    if dr2 < 0.01 and d.pt() > 0.5*g.pt(): 
                        gen_notused.remove(g)
                        mcmatch[d].append(g)
                # then take any remaining gen and just attach it to the nearest reco, except well-matched tracks
                rematch = neutral + [ c for c in charged if c in reco_notused ]
                for g in gen_notused:
                    d, dr2 = bestMatch(g, rematch)
                    if dr2 < 0.01: mcmatch[d].append(g) 
            matchletters = [ "X" for mm in matchmaps ]
            allmatches   = [ []  for mm in matchmaps ]
            for im,d in enumerate(matches):
                keyer[d.uid()] = "%s%02d" % (layerlabel,im)
                revkey["%s%02d" % (layerlabel,im)] = d
                if d.pt() < 0.8: continue
                print "  %s%02d  pt %6.2f  eta %+5.2f  phi %+5.2f  ch %+1d  dr %.2f  id % +5d" % (layerlabel,im, d.pt(), d.eta(), d.phi(), d.charge(), d.dr, d.pdgId()),
                for imm,mm in enumerate(matchmaps):
                    md = mm[d]
                    if md and (md.uid() in keyer): 
                        matchto = keyer[md.uid()]
                        matchletters[imm] = matchto[0]
                        allmatches[imm].append(matchto)
                        print "-> %3s" % matchto,
                    else:  
                        print "->  - ",
                for i in xrange(len(matchmaps),max(len(l[2]) for l in layers)):
                    print "      ",
                if "tk" in a or "mu" in a:
                    if "tk" in a:
                        print " vz %+7.3f ptErr %6.2f hp %1d  algo %s  dxy %s dz %s  c2/n %s  layers %s" % (d['vz'], d['ptError'], d['hp'], d.algoStr(), d.dxyStr(), d.dzStr(), d.chi2nStr(), d.layersStr()),
                    elif "mu" in a:
                        print " vz %+7.3f %s %s iso03 %6.2f" % (d['vz'], d.idWord(), d.allpts(), d['iso03']),
                    g, dr2 = bestMatch(d, c_tomatch)
                    if (dr2 < .01): 
                        # check match back
                        db, dr2b = bestMatch(g, matches)
                        if db == d: 
                            print " <-> match with  pt %5.2f  eta %+5.2f  phi %+5.2f  dr %.3f  id % +5d " % (g.pt(), g.eta(), g.phi(), sqrt(dr2), g.pdgId()),
                        else:
                            print " --> dup. of gen pt %5.2f  eta %+5.2f  phi %+5.2f  dr %.3f  id % +5d " % (g.pt(), g.eta(), g.phi(), sqrt(dr2), g.pdgId()),
                            print " <-- gen prefers reco pt %6.2f eta %+5.2f phi %+5.2f dr %.3f  id % +5d"  % (db.pt(), db.eta(), db.phi(), sqrt(dr2b), db.pdgId()),
                    else:           
                        print " --> unmatched",
                elif "calo" in a:
                    print " emEt %5.2f  hadEt %5.2f" % (d['emEt'],d['hadEt']),
                    if "tower" in a:
                        print " ieta %+3d  iphi %+3d" % (d['ieta'],d['iphi']),
                    if "jet" in a:
                        incone = [ g for g in j.daus() if g.pdgId() in (-11,11,22) and g.pt() > 0.5 and deltaR(g,d) < 0.4 ]
                    elif "tower" in a:
                        incone = [ g for g in j.daus() if g.pdgId() in (-11,11,22) and g.pt() > 0.5 and deltaR(g,d) < 0.1 ]
                    if incone:
                        incone.sort(key = lambda g : -g.pt())
                        print " --> match with  pt %7.2f from %2d particles: " % (sum(g.pt() for g in incone),len(incone)),
                        for g in sorted(incone, key = lambda g : -g.pt())[:5]:
                            print "%+d[pt %.1f]" % (g.pdgId(), g.pt()),
                    else:           
                        print " --> unmatched",
                elif "pf" in a:
                        if "pfb" in a:
                            print "  type %-5s block %2d" % (PFTypes[d['type']],d['ib']),
                        else:
                            #print " e %5.1f  ecal %6.1f (raw %5.1f)  hcal %5.1f (raw %5.1f) mva %+.2f/%+.2f" % (d["e"], d["ecal"], d["rawecal"], d["hcal"], d["rawhcal"], d["mvaIso"], d["mvaEP"]),
                            print " e %5.1f  ecal %6.1f (raw %5.1f)  hcal %5.1f (raw %5.1f)" % (d["e"], d["ecal"], d["rawecal"], d["hcal"], d["rawhcal"]),
                            if d.dr < 0.4: 
                                for k,l in esums.iteritems():
                                    myval = d[k]
                                    if "raw" in k and myval in l: continue
                                    l.append(myval)
                        incone = mcmatch[d]
                        if len(incone) == 0:
                            print " --> unmatched",
                        elif len(incone) == 1:
                            g = incone[0]
                            print " --> match with  pt %7.2f eta %+5.2f phi %+5.2f dr %.3f   id % +5d " % (g.pt(), g.eta(), g.phi(), deltaR(g,d), g.pdgId()),
                        else:
                            print " --> match with  pt %7.2f from %2d particles: " % (sum(g.pt() for g in incone),len(incone)),
                            for g in incone:
                                print "%+d[pt %.1f, dr %.2f]" % (g.pdgId(), g.pt(), deltaR(g,d)),
                elif "ele" in a :
                        print " e %5.1f  ecal %6.1f mva %+.2f/%+.2f  sieie %.4f 1ep %.4f deta %.4f dphi %.4f r9 %.3f  ecalD %1d pfPre %1d" % (d["e"], d["ecal"], d["mvaIso"], d["mvaEP"], d["sieie"], d["1ep"], d["deta"], d["dphi"], d["r9"], d["ecalD"], d["pfPresel"]),
                        incone = []
                        g, dr2 = bestMatch(d, [g for g in c_tomatch if abs(g.pt()-d.pt())/(g.pt()+d.pt()) < 0.5])
                        if dr2 < .01: incone.append(g)
                        incone += [ g for g in j.daus() if g.pdgId() in (-11,11,22) and g.pt() > 0.5 and deltaR(g,d) < (0.3 if abs(g.eta()-d.eta())<0.05 else 0.07) ]
                        if len(incone) == 0:
                            print " --> unmatched",
                        elif len(incone) == 1:
                            g = incone[0]
                            print " --> match with  pt %7.2f eta %+5.2f phi %+5.2f dr %.3f   id % +5d " % (g.pt(), g.eta(), g.phi(), deltaR(g,d), g.pdgId()),
                        else:
                            print " --> match with  pt %7.2f from %2d particles: " % (sum(g.pt() for g in incone),len(incone)),
                            for g in incone:
                                print "%+d[pt %.1f, dr %.2f]" % (g.pdgId(), g.pt(), deltaR(g,d)),
                elif "ecal" in a :
                        incone = [ g for g in j.daus() if g.pdgId() in (-11,11,22) and g.pt() > 0.5 and deltaR(g,d) < 0.07 ]
                        if len(incone) == 0:
                            print " --> unmatched",
                        elif len(incone) == 1:
                            g = incone[0]
                            print " --> match with  pt %7.2f eta %+5.2f phi %+5.2f dr %.3f   id % +5d " % (g.pt(), g.eta(), g.phi(), deltaR(g,d), g.pdgId()),
                        else:
                            print " --> match with  pt %7.2f from %2d particles: " % (sum(g.pt() for g in incone),len(incone)),
                            for g in incone:
                                print "%+d[pt %.1f, dr %.2f]" % (g.pdgId(), g.pt(), deltaR(g,d)),
                print ""
            for ml,am in zip(matchletters,allmatches):
                if ml == "X": continue
                allkeys = sorted([ k for k in keyer.values() if k[0] == ml ])
                lmatched   = [ k for k in allkeys if k   in   am ]
                lunmatched = [ k for k in allkeys if k not in am ]
                print "   %s matched to us (total pt %7.2f): %s" % ( ml, sum(revkey[k].pt() for k in lmatched),   "  ".join("%s[%.1f]" % (k,revkey[k].pt()) for k in   lmatched if revkey[k].pt() > 1) )
                print "   %s not matched   (total pt %7.2f): %s" % ( ml, sum(revkey[k].pt() for k in lunmatched), "  ".join("%s[%.1f]" % (k,revkey[k].pt()) for k in lunmatched if revkey[k].pt() > 1) )
            if len(matches) > 1: 
                if "tk" in a or "ecal" in a:
                    print "   total pT > 0.8 (R 0.4) %7.2f" % sum(d.pt() for d in matches if d.dr < 0.4 and d.pt > 0.8)
                if "pf" in a:
                    print "   total charged had:     %7.2f" % sum(d.pt() for d in matches if abs(d.pdgId()) == 211 and d.dr < 0.4 and d.pt > 0.8)
                    print "   total neutral had:     %7.2f" % sum(d.pt() for d in matches if abs(d.pdgId()) == 130 and d.dr < 0.4 and d.pt > 0.8)
                    print "   total photons:         %7.2f" % sum(d.pt() for d in matches if abs(d.pdgId()) == 22  and d.dr < 0.4 and d.pt > 0.8)
                    print "   total electrons:       %7.2f" % sum(d.pt() for d in matches if abs(d.pdgId()) == 11  and d.dr < 0.4 and d.pt > 0.8)
                    print "   total muons:           %7.2f" % sum(d.pt() for d in matches if abs(d.pdgId()) == 13  and d.dr < 0.4 and d.pt > 0.8)
                if "pf" in a and "pfb" not in a:
                    print "   total energy:          %7.2f" % sum(esums["e"])
                    print "   total ecal energy:     %7.2f" % sum(esums["ecal"])
                    print "   total ecal raw energy: %7.2f" % sum(esums["rawecal"])
                    print "   total hcal energy:     %7.2f" % sum(esums["hcal"])
                    print "   total hcal raw energy: %7.2f" % sum(esums["rawhcal"])

            print ""
    print "\n========================\n"     
