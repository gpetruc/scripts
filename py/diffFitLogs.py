#!/usr/bin/env python
import re
import glob
from optparse import OptionParser
from math import *

parser = OptionParser(usage="usage: %prog [options] logfiles")
parser.add_option("-t", "--tail", dest="tail", default=None,  type="int", help="Take only the tail lines of this file")
parser.add_option("-T", "--tolerance", dest="tolerance", default=0.001,  type="float", help="Take only the tolerance lines of this file")
parser.add_option("-g", "--grep", dest="grep", default=None,  type="string", help="Grep lines matching this")
parser.add_option("-v", "--values", dest="values",  action="store_true", default=False, help="compare values")
parser.add_option("-b", "--bare", dest="bare",  action="store_true", default=False, help="compare bare")
parser.add_option("-q", "--quick", dest="quick",  action="store_true", default=False, help="compare quick")
(options, args) = parser.parse_args()

if len(args) == 0:
    parser.print_usage()
    exit(1)

logmap = {}
columns = []
for logfile in args:
    if "=" in logfile:
        alias,name = logfile.split("=")
        if "*" in name:
            names = glob.glob(name)
            if len(names) == 0:
                raise RuntimeError, "No file matches '%s'\n" % (name,)
            logmap[alias] = names
        else:
            logmap[alias] = [ name ]
        columns.append(alias)
    else:
        alias = logfile.replace(".root","").replace(".txt","")
        logmap[alias] = [ logfile ]
        columns.append(alias)
        
results = {}
plainpatt = re.compile(r"(\S+)\s+=\s+([\-0-9]\S*)\s+\+/-\s+(\S+)(\s+\(limited\))?$")
nonepatt  = re.compile(r"\s*(\S+)\s+:\s+([\-+]\d+\.\d\d\d)$")
minospatt = re.compile(r"\s*(\S+)\s+:\s+([\-+]\d+\.\d\d\d)\s+[\-+](\d+\.\d\d\d)/\+(\d+.\d\d\d)\s+\(68%\)$")
timepatt  = re.compile(r"Done in (\S+) min \(cpu\), (\S+) min \(real\)")
for logfile in columns:
    lines = []
    for f in logmap[logfile]:
        flines = [ l.strip() for l in open(f,'r') ]
        if options.tail: flines = flines[len(flines)-options.tail-1:]
        lines += flines
    results[logfile] = {}
    for line in lines:
        m = re.match(plainpatt,line)
        if m:
            poi,val,err = m.group(1), float(m.group(2)), float(m.group(3))
            if options.grep and not re.match(options.grep, poi): 
                continue
            if poi in results[logfile] and len(results[logfile][poi]) > 2:
                continue
            results[logfile][poi] = [ val, err ]
        m = re.match(nonepatt,line)
        if m:
            poi,val = m.group(1), float(m.group(2))
            if options.grep and not re.match(options.grep, poi): 
                continue
            if poi in results[logfile] and len(results[logfile][poi]) > 1:
                if abs(results[logfile][poi][0]-val)<0.002:
                    continue # keep result from starting thing
            results[logfile][poi] = [ val ]
        m = re.match(minospatt,line)
        if m:
            poi,val,errL,errH = m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4))
            if options.grep and not re.match(options.grep, poi): 
                continue
            results[logfile][poi] = [ val, errL, errH ]
        m = re.match(timepatt,line)
        if m:
            cpu,real = float(m.group(1)), float(m.group(2))
            if None not in results[logfile]:
                results[logfile][None] = [ 0, 0]
            results[logfile][None][0] += cpu
            results[logfile][None][1] += real

allpoi = []
for logfile, poimap in results.iteritems():
    for poi in poimap.keys():
        if poi and (poi not in allpoi): allpoi.append(poi)
minlength = 25
if options.values or options.bare: minlength = 20
colpatt = "%%-%ds   " % max([minlength]+[len(a) for a in columns])
poipatt = "%%-%ds" % max([15]+[len(p) for p in allpoi])
print (poipatt % "parameter"), " ".join([colpatt % a for a in columns])
print (poipatt % ("-"*15)), " ".join([colpatt % ("-" * 20) for a in columns])
if options.quick:
    filtered_pois = []
    for p in sorted(allpoi):
        ref = None
        take = False
        for i,lf in enumerate(columns):
            if p in results[lf]:
                pv = results[lf][p]
                if len(pv) == 2:
                    if not ref:
                        ref = (pv[0],pv[1])
                    else:
                        ndlnl = (abs((pv[0]-ref[0])/ref[1])**2)/options.tolerance
                        if ndlnl > 1:
                            take = True
            else:
                take = True    
        if take: filtered_pois.append(p)
    allpoi = filtered_pois

for p in sorted(allpoi):
    print poipatt % p,
    ref = None
    for i,lf in enumerate(columns):
        if p in results[lf]:
            pv = results[lf][p]
            if options.values:
                if not ref:
                    ref = pv[:]
                    print colpatt % ("% .3f" % pv[0]),
                else:
                    print colpatt % ("% .3f  [%+.3f]" % (pv[0],pv[0]-ref[0])),
            elif options.bare:
                if len(pv) == 1:
                    print colpatt % ("% .3f" % pv[0]),
                elif len(pv) == 2:
                    print colpatt % ("% .3f +/- %.3f" % (pv[0],pv[1])),
                elif len(pv) == 3:
                    print colpatt % ("% .3f -%.3f/+%.3f" % (pv[0],pv[1],pv[2])),
                else:
                    print colpatt % ("??? len=%d" % len(pv))

            else:
                if len(pv) == 1:
                    if not ref:
                        print colpatt % ("% .3f" % pv[0]),
                    else:
                        ndlnl = (abs((pv[0]-ref[0])/ref[1])**2)/options.tolerance
                        print colpatt % ("% .3f  [%3.1f]" % (pv[0],ndlnl)),
                elif len(pv) == 2:
                    if not ref:
                        ref = (pv[0],pv[1])
                        print colpatt % ("% .3f +/- %.3f" % (pv[0],pv[1])),
                    else:
                        ndlnl = (abs((pv[0]-ref[0])/ref[1])**2)/options.tolerance
                        print colpatt % ("% .3f +/- %.3f  [%3.1f]" % (pv[0],pv[1],ndlnl)),
                elif len(pv) == 3:
                    if not ref:
                        ref = (pv[0],max(pv[1],pv[2]))
                        print colpatt % ("% .3f -%.3f/+%.3f" % (pv[0],pv[1],pv[2])),
                    else:
                        ndlnl = (abs((pv[0]-ref[0])/ref[1])**2)/options.tolerance
                        print colpatt % ("% .3f -%.3f/+%.3f  [%3.1f]" % (pv[0],pv[1],pv[2],ndlnl)),
                else:
                    print colpatt % ("??? len=%d" % len(pv))
        else:
            print colpatt % "<missing in action>",
    print ""
for p in [None]:
    print poipatt % "Fit time",
    ref = None
    for i,lf in enumerate(columns):
        if p in results[lf]:
            pv = results[lf][p]
            if not ref:
                ref = pv
                print colpatt % ("%.3f min" % pv[0]),
            else:
                ratio = pv[0]/ref[0] 
                print colpatt % ("%.3f min [x%.1f]" % (pv[0],ratio)),
        else:
            print colpatt % "<missing in action>",
    print ""



