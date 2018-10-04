import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.gSystem.Load("libFWCoreFWLite.so");
ROOT.gSystem.Load("libDataFormatsFWLite.so");
ROOT.FWLiteEnabler.enable()
ROOT.gInterpreter.ProcessLine('#include "det_hash.cpp"')

from math import sqrt
import random, numpy
from sys import argv
from DataFormats.FWLite import Handle, Events

events = Events(argv[1])
prescale = int(argv[2])
maxev = int(argv[3]) if len(argv) >= 4 else 500
count, pcount, rcount, tcount, hcount, jcount = 0, 0, 0, 0, 0, 0

trks = Handle("std::vector<reco::Track>")
xs = ROOT.xorshift64star
xs2 = ROOT.xorshift128plus

c0 = prescale/2
for i,event in enumerate(events):
    event.getByLabel("generalTracks", trks)
    i0 = event.eventAuxiliary().luminosityBlock() + event.eventAuxiliary().event() 
    i0 = i0 % prescale
    h0 = numpy.array([event.eventAuxiliary().event() + event.eventAuxiliary().luminosityBlock()], dtype=numpy.uint64) 
    if (h0[0] == 0): h0 = 987654321
    j0 = numpy.array([event.eventAuxiliary().event(),  event.eventAuxiliary().luminosityBlock()], dtype=numpy.uint64) 
    for itk, tk in enumerate(trks.product()):
        if tk.pt() < 0.5: continue
        count += 1
        ## === pcount ===
        if i0 == 0:
            pcount += 1
        i0 += 1
        if i0 == prescale: i0 = 0
        ## === rcount ===
        if random.randint(0,prescale-1) == 0:
            rcount += 1
        ## === tcount ===
        c0 += 1
        if c0 == prescale:
            tcount += 1
            c0 = 0
        ## === pcount ===
        if ((xs(h0) >> 8) % prescale) == 0:
            hcount += 1
        if (xs2(j0) % prescale) == 0:
            jcount += 1
    if i >= maxev: break

print "%9d is the true count" % count
for c in pcount, rcount, tcount, hcount, jcount:
    exact = abs(c*prescale-count) < prescale
    stoc  = (c*prescale-count)/(sqrt(c)*prescale)
    print "%9.0f +- %9.0f (unw %9d): extact? %-6s  statistical? %+6.3f sigmas" % (c*prescale, sqrt(c)*prescale, c, exact, stoc)
