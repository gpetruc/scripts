#!/usr/bin/env python
import subprocess, multiprocessing, re, os.path, sys
from math import ceil
from optparse import OptionParser
parser = OptionParser(usage="usage: %prog paths ")
parser.add_option("-j", dest="jobs", default=4,  type="int", help="parallel threads")
parser.add_option("-c", dest="chunks", default=8,  type="int", help="number of files in a single edmFileUtil --ls request")
parser.add_option("-w", dest="warn", default=False,  action="store_true", help="Warn about bad or corrupted files")
(options, args) = parser.parse_args()
if len(args) == 0:
    parser.print_usage()
    exit(1)


def _run(files):
    sys.argv = [ "-b", "-n", "-l" ]
    import ROOT
    ROOT.gROOT.SetBatch(True)
    ret = []
    for lfn in files:
        #tfile = ROOT.TNetXNGFile("root://eoscms//eos/cms"+lfn)
        #tfile = ROOT.TFile.Open("root://eoscms//eos/cms"+lfn)
        try:
            tfile = ROOT.TFile.Open("/eos/cms"+lfn)
            record = {}
            for T in "LuminosityBlocks", "Events":
                tree = tfile.Get(T)
                record[T] = tree.GetEntries() if tree else 0
            ret.append( record )
            tfile.Close()
        except:
            if options.warn: sys.stderr.write("Error reading file /eos/cms"+lfn+"\n")
    return ret

for arg in args:
    path, pattern = arg, ".*root$"
    if "*" in arg:
        path = os.path.dirname(arg)
        pattern = os.path.basename(arg).replace(".","\\.").replace("*",".*")+"$" 
    if path.startswith("/eos/cms"): path = path.replace("/eos/cms","")
    cpattern = re.compile(pattern)
    out = subprocess.check_output(["ls", "-l", "/eos/cms"+path ])
    files = []
    totsize = 0
    for line in out.split("\n"):
        try:
            (ugo, repl, user, group, size, month, day, time, filename) = line.strip().split()
        except ValueError: 
            continue
        if int(repl) == 0 or int(size) < 10240:
             if re.match(cpattern,filename):
                 if options.warn: sys.stderr.write("Empty file /eos/cms/%s/%s (size %d)\n" % (path, filename, int(size)))
             continue
        if re.match(cpattern,filename):
            files.append(path+"/"+filename)
            totsize += long(size)/2 # fuse returns twice the size
    if len(files) > 0:
        chunksize = options.chunks
        if len(files) < options.jobs * chunksize:
            chunksize = int(ceil(len(files)/float(options.jobs)))
        nchunks = int(ceil(len(files)/float(chunksize)))
        chunks = [ files[i:i+chunksize] for i in xrange(0,len(files),chunksize) ]
        pool = multiprocessing.Pool(options.jobs)
        ret = sum(pool.map(_run, chunks), [])
        keys = [ "LuminosityBlocks","Events" ]
        tot = dict([ (k,sum(r[k] for r in ret)) for k in keys ])
    else:
        tot = { 'LuminosityBlocks':0, 'Events':0 }
    print "%s\t%s\t%5d files, %6d lumis, %10d events, %8.3f Gb " % (path, pattern, len(files), tot['LuminosityBlocks'], tot['Events'], totsize/(1024.0**3))
    


