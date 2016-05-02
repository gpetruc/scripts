import re
import os, sys, json
import urllib2
from optparse import OptionParser

parser = OptionParser(usage=r"""usage: %prog [options] /*/*Something*  --tiers GEN-SIM,GEN-SIM-RAW,GEN-SIM-RECO,AODSIM,MINIAODSIM,RAW,RECO,AOD,MINIAOD
""")
parser.add_option("-t", "--tiers", dest="tiers", type="string", default="GEN-SIM,GEN-SIM-RAW,GEN-SIM-RECO,AODSIM,MINIAODSIM,RAW,RECO,AOD,MINIAOD")
parser.add_option("-F", "--force", dest="noCache", action="store_true", default=False, help="Don't use the cache")
parser.add_option("-o", "--out", dest="out", default="samplesList.json", type="string", help="Output file")
(options, args) = parser.parse_args()

tiers = options.tiers.split(",")

if len(args) != 1 or args[0].count("/") != 2:
    parser.print_usage()
    sys.exit(1)

cache = {}
if not options.noCache:
    try:
        fcache = open("%s/.listSamples_cache.json" % os.environ['HOME'],"r")
        if fcache:
            cache = json.load(fcache)
            print "Loaded %d samples from cache file. " % (len(cache))
            for ds in cache.keys():
                if cache[ds]['nfiles'] <= 0:
                    del cache[ds]
        fcache.close()
    except:
        print "Failed to read cache form ~/.listMiniAODS_cache.json"

def getinfo(dataset):
    global cache
    info = { 'nfiles':-1, 'nevents':-1, 'size':-1 }
    print "getting detailed info on ",dataset
    opts = ( " --key {0} --cert {0}".format(os.environ['X509_USER_PROXY']) if 'X509_USER_PROXY' in os.environ else "")
    output = os.popen("das_client.py --query='summary dataset=%s' %s" % (dataset,opts))
    for line in output:
        if "nfiles" in line:
            info['nfiles'] = int(line.split(":")[1]);
        elif "nevents" in line:
            info['nevents'] = int(line.split(":")[1]);
        elif "file_size" in line:
            info['size'] = int(line.split(":")[1]);
    cache[dataset] = info

def getsamples(query, full=True):
    global cache, tiers
    ret = {}
    print "Doing DAS query %s" % query
    opts = ( " --key {0} --cert {0}".format(os.environ['X509_USER_PROXY']) if 'X509_USER_PROXY' in os.environ else "")
    output = os.popen("das_client.py --query='dataset %s' --limit=10000 %s" % (query,opts))
    for line in output:
        if line.startswith("Showing"): continue
        if line[0] == "/": 
            ds = line.strip()
            if ds in ret: continue # skip dups
            pd,proc,tier = ds.split("/")[1:]
            if tier not in tiers: continue
            if full:
                if ds not in cache:
                    getinfo(ds)
                ret[ds] = cache[ds]
            else:
                ret[ds] = True
    return ret

def getphedex(dataset):
    print "Doing PhEDEx query for %s" % dataset
    urlquery = 'https://cmsweb.cern.ch/phedex/datasvc/json/prod/subscriptions?node=T2_CH_CERN&create_since=0&dataset=%s' % dataset.replace("/","%2F")
    text = urllib2.urlopen(urlquery).read()
    if not next: return None
    jsondata = json.loads(text)
    datasets = jsondata['phedex']['dataset']
    ret = {}
    for d in datasets:
        for s in d['subscription']:
            if d['name'] in ret:
                if ret[d['name']]['group'] == 'local' and s['group'] != 'local': continue
            ret[d['name']] = { 'group':s['group'], 'percent':s['percent_files'] }
    return ret

samples = getsamples("dataset=%s/*" % args[0], full=True) 
atcern  = getphedex("%s/*" % args[0]) 
if not samples or not atcern: 
    raise RuntimeError, "Query failed"

records = {}
for ds in samples.iterkeys():
    (dummy,pd,proc,ec) = ds.split("/")
    (era,gt,ver) = proc.split("-")
    vnum = int(ver[1:])
    key = (pd,era,gt,ec)
    if key in records and records[key]['vnum'] > vnum:
        continue
    records[key] = { 'ds':ds, 'vnum':vnum, 'pd':pd, 'gt':gt, 'era':era, 'tier':ec }
    records[key]['atcern']  = atcern[ds] if (ds in atcern) else { 'group':'none', 'percent':0 }
    records[key]['info'] = cache[ds]

report = records.values()

fout = open(options.out, "w")
json.dump(report, fout)
fout.close()

fcache = open("%s/.listSamples_cache.json" % os.environ['HOME'],"w")
json.dump(cache, fcache)
print "Final cache size: %d samples" % (len(cache))
fcache.close()

