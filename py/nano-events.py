#!/usr/bin/env python
import subprocess, multiprocessing, re, os.path, sys
from optparse import OptionParser
import ROOT
ROOT.gROOT.SetBatch(True)
parser = OptionParser(usage="usage: %prog paths ")
(options, args) = parser.parse_args()
if len(args) == 0:
    parser.print_usage()
    exit(1)

for a in args:
    if not a.endswith(".root"): continue
    tfile = ROOT.TFile.Open(a)
    if not tfile: 
        print "%10d %s [bad file]" % (0, a)
        continue
    events = tfile.Get("Events")
    if not events: 
        friends = tfile.Get("Friends")
        if friends:
            print "%10d %s [friend tree]" % (friends.GetEntries(), a)
        else:
            print "%10d %s [bad file]" % (0, a)
        continue
    runs = tfile.Get("Runs")
    if not runs:
        print "%10d %s [no run tree]" % (events.GetEntries(), a)
        continue
    elif not runs.GetBranch("genEventCount"):
        print "%10d %s [data]" % (events.GetEntries(), a)
        continue
    runs.Draw("0.5>>htemp(1,0,1)","genEventCount","goff")
    ngen = ROOT.gROOT.FindObject("htemp").GetBinContent(1)
    print "%10d %s ( %10d before selection, skim eff %6.2f%%)" % (events.GetEntries(), a, ngen, 100.0*events.GetEntries()/ngen if ngen else 0)
