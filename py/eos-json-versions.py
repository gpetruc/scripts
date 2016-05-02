import json, re, sys
from optparse import OptionParser
parser = OptionParser()
parser.add_option("-v", dest="exclude", default=None, help="pattern to exclude")
parser.add_option("-s", dest="stale", default=False, action="store_true", help="show stale files")
parser.add_option("-V", dest="version", default=5165, type=int, help="version code: new files are those >= this version")
options, args = parser.parse_args()
jsons    = [ a for a in args if     a.endswith(".json") ]
patterns = [ a for a in args if not a.endswith(".json") ]

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

VMAP = { 0 : 'Unkn'}
def version(proc):
    m = re.search(r'CMG(PF)?_V?(\d)_(\d+)_', proc)
    if m == None:
        return 0
    ret = 1000 * int(m.group(2)) + 10 * int(m.group(3)) + (5 if ('CMGPF' in proc or '44X' in proc) else 0)
    VMAP[ret] = (m.group(0)[:-1]).replace("CMG_","").replace("CMGPF_V","PF_V")
    return ret

if options.stale:
    STALE  = readFranzoni("/afs/cern.ch/user/f/franzoni/public/4cmgtools/cms-t3-stale-2014-03-03.txt")
    VSTALE = readFranzoni("/afs/cern.ch/user/f/franzoni/public/4cmgtools/cms-t3-very-stale-2014-03-03.txt")

data = {}
for J in jsons:
  rawdata = json.load(open(J))
  for k,v in rawdata.iteritems():
    k = re.sub(r".*/CMG/", "/", k)
    if len(patterns) > 0 and not len([ p for p in patterns if re.search(p,k) ]):
        continue
    if options.exclude and re.search(options.exclude, k):
        continue
    if "CMG" not in k:
        continue
    m = re.match(r"((/[^/]+){3})/(.+)",k)
    if not m: continue
    if v['rootfiles'] == 0: continue
    ds, proc = m.group(1), re.sub("V5(_B?)/","",m.group(3))
    #sys.stderr.write("%s --> %s %s\n" % (k,ds,proc))
    used = "live"
    if   options.stale and stmatch(k,VSTALE): used = "vstale"
    elif options.stale and stmatch(k, STALE): used =  "stale"
    if ds not in data: data[ds] = []
    found = False; ver = version(proc)
    for i,(v2,s2,u2) in enumerate(data[ds]):
        if VMAP[v2] == VMAP[ver]:
            data[ds][i][1] += v['rootfiles']/1024.0
            data[ds][i][2] = min(data[ds][i][2], used)
            found = True
            break
    if not found:
        data[ds].append( [version(proc), v['rootfiles']/1024.0, used] )

tot, tots, totvs  = 0, 0, 0
tot1, tots1, totvs1  = 0, 0, 0
print """
<html><head>
<title>CMGTuple Version</title>
<style type="text/css">
body { font-family: 'Candara', 'Verdana', sans-serif; font-size: small; }
td, th { border-bottom: 1px solid black; padding: 1px 1em; vertical-align: top; }
</style>
</head>
<body>
<h1>CMGTuple Version</h1>
<table>
<tr><th>Dataset</th><th>New versions, and sizes in Gb</th><th>Old versions and sizes in Gb</th></tr>
"""
usemap = { "stale" : 'black', 'live':'#006400', 'vstale':'#8B0000' }
for ds in sorted(data.keys()):
    data[ds].sort(); data[ds].reverse()
    new = ", ".join(["<span style='color: %s;'>%s (%.0f Gb)</span>" % (usemap[u],VMAP[v],s) for (v,s,u) in data[ds] if v >= options.version])
    old = ", ".join(["<span style='color: %s;'>%s (%.0f Gb)</span>" % (usemap[u],VMAP[v],s) for (v,s,u) in data[ds] if v <  options.version])
    if new == "": new = "&ndash;";
    if old == "": old = "&ndash;";
    print "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (ds,new,old)
    tot    += sum([s/1024 for (v,s,u) in data[ds] if v >= options.version])
    tots   += sum([s/1024 for (v,s,u) in data[ds] if v >= options.version and u ==  "stale"])
    totvs  += sum([s/1024 for (v,s,u) in data[ds] if v >= options.version and u == "vstale"])
    tot1   += sum([s/1024 for (v,s,u) in data[ds] if v <  options.version])
    tots1  += sum([s/1024 for (v,s,u) in data[ds] if v <  options.version and u ==  "stale"])
    totvs1 += sum([s/1024 for (v,s,u) in data[ds] if v <  options.version and u == "vstale"])

if options.stale:
    print '<tr><td><b>Total</b></td><td><b>%.1f TB (%.1f live, %.1f stale, %.1f very stale)</b> </td><td><b>%.1f TB (%.1f live, %.1f stale, %.1f very stale)</b></td></tr>' % (
            tot, tot-tots-totvs, tots, totvs, tot1, tot1-tots1-totvs1, tots1, totvs1)
else:
    print '<tr><td><b>Total</b></td><td><b>%.1f TB</b> </td><td><b>%.1f TB</b></td></tr>' % ( tot, tot1 )
print """
</table>
</body>
</html>
"""

