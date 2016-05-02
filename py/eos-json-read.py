import json
import re
from optparse import OptionParser
parser = OptionParser()
parser.add_option("-v", dest="exclude", default=None, help="pattern to exclude")
parser.add_option("-V", dest="vetofile", default=None, help="pattern to exclude")
parser.add_option("-S", dest="selefile", default=None, help="pattern to exclude")
parser.add_option("-s", dest="stale", default=False, action="store_true", help="show stale files")
parser.add_option("-o", dest="others", default=False, action="store_true", help="show other files")
parser.add_option("-b", dest="bare", default=False, action="store_true", help="show other files")
options, args = parser.parse_args()

def readFranzoni(fname):
    stems = {}
    for line in open(fname):
        if "CMG" not in line: continue
        pd = re.sub(r".*/CMG/", "/", line.strip())
        stems[pd] = True
    return stems
def stmatch(path,franz):
    parts = path.split("/")
    for i in xrange(1,len(parts)):
        p = "/".join(parts[:i])+"/"
        if p in franz:
            return True
    return False

if options.stale:
    STALE  = readFranzoni("/afs/cern.ch/user/f/franzoni/public/4cmgtools/cms-t3-stale-2014-03-03.txt")
    VSTALE = readFranzoni("/afs/cern.ch/user/f/franzoni/public/4cmgtools/cms-t3-very-stale-2014-03-03.txt")

vetos = []
if options.exclude: 
    vetos.append(re.compile(options.exclude))
if options.vetofile:
    for l in open(options.vetofile):
        if len(l.strip()) == 0: continue
        vetos.append(re.compile("^"+l.strip()+"$"))

matches = []
if options.selefile:
    for l in open(options.selefile):
        if len(l.strip()) == 0: continue
        matches.append(re.compile("^"+l.strip()+"$"))

rawdata = json.load(open(args[0]))
data = []
for k,v in rawdata.iteritems():
    k = re.sub(r".*/CMG/", "/", k)
    if len(args) > 1 and not re.search(args[1], k):
        continue
    if len(matches) and len([True for p in matches if re.search(p,k)]) == 0:
        continue
    if len(vetos) and len([True for p in vetos if re.search(p,k)]) > 0:
        continue
    if options.exclude and re.search(options.exclude, k):
        continue
    m = re.match(r"((/[^/]+){3})/(.+)",k)
    if not m: continue
    siz = v['rootfiles']
    if options.others: siz += v['other']
    if siz == 0: continue
    ds, proc = m.group(1), m.group(3)
    proc = re.sub(r"V5(_B)?/","",proc)
    data.append(("%s/%s" % (ds,m.group(3)), ds, proc, siz/1024.))

tot, tots, totvs  = 0, 0, 0
data.sort()
if options.bare:
    for d,ds,p,s in data:
        print d
    exit()
    
print '%TABLE{ sort="on" initsort="1" }%'
if options.stale:
    print '|  *Sample*  |  *Size (Gb)*  |  *Status*  |'
    for d,ds,p,s in data:
        if stmatch(d,VSTALE): 
            used ="%RED%<b>VERY STALE</b>%ENDCOLOR%"
            totvs += s
        elif stmatch(d,STALE): 
            tots += s
            used ="Stale"
        else:
            used ="%GREEN%<b>Live</b>%ENDCOLOR%"
        print "| %s   |   %.2f |   %s  |" % (d,s,used)
        tot += s
    print "Total: %.2f TB %%BR%%" % (tot/1024)
    print "Live: %.2f TB (%.1f%%) %%BR%%" % ((tot-tots-totvs)/1024,(tot-tots-totvs)/tot*100)
    print "Stale: %.2f TB (%.1f%%) %%BR%%" % (tots/1024,tots/tot*100)
    print "Very stale: %.2f TB (%.1f%%)" % (totvs/1024,totvs/tot*100)
else:
    print '|  *Sample*  |  *Size (Gb)*  |'
    for d,ds,p,s in data:
        print "| %s   |   %.2f |" % (d,s)
        tot += s
    print "Total: %.2f TB" % (tot/1024)
