import json
import re
import fnmatch
import os.path
from optparse import OptionParser
parser = OptionParser()
parser.add_option("-v", dest="exclude", default=None, help="pattern to exclude")
parser.add_option("-d", dest="depth", type="int", default=1)
parser.add_option("-r", "--re", dest="re", default=False, action="store_true", help="use regexp")
options, args = parser.parse_args()

def match(pattern,arg):
    if options.re:
        return re.match(pattern,arg)
    else:
        return fnmatch.fnmatch(pattern,arg)

def cd_dot_dot(path,n):
    for i in xrange(n):
        parent = os.path.dirname(path)
        if path == parent: return None
        path = parent
    return path

rawdata = json.load(open(args[0]))
data = []

def maxpathlen(dir,depth,start,pr):
    if depth == 0 or not rawdata[start+"/"+dir]["subs"]:
        return len(start+"/"+dir)
    else:
        return max(maxpathlen(s, depth-1, start+"/"+dir) for s in rawdata[start+"/"+dir]["subs"])

def lsdir(dir,base,deep,prefix=""):
    selfdir = base+"/"+dir; self = rawdata[selfdir]
    if deep == 0 or not self["subs"]:
        return [ (prefix+dir, self["deep"]) ]
    elif len(self["subs"]) == 1 and self["deep"] == rawdata[selfdir+"/"+self["subs"][0]]["deep"]:
        return lsdir(self["subs"][0],selfdir,deep-1,prefix+dir+"/")
    else:
        ret = [ (prefix+dir, self["deep"]) ]
        for s in sorted(self["subs"]):
            ret += lsdir(s,selfdir,deep-1,prefix+"   ")
        return ret

data = []
if len(args) > 1:
    for a in args[1:]:
        data += lsdir(os.path.basename(a), os.path.dirname(a), options.depth)
else:
    for a in sorted(rawdata.keys()):
        a = re.sub("/*$","",a)
        if a in rawdata and os.path.dirname(a) not in rawdata:
            data += lsdir(os.path.basename(a), os.path.dirname(a), options.depth)
        
total = sum(s for (d,s) in data if d[0] != " ")
maxl = max([20]+[len(d) for (d,s) in data])
for d,s in data:
    print ("%%-%ds %%10.2f %%5.1f%%%%" % maxl) % (d,s/1024,100.0*s/total)

