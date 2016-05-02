import re
import os, sys, json
import urllib2
from optparse import OptionParser

parser = OptionParser(usage=r"""usage: %prog [options] /*/Spring14*  [ --map <aodsim>:<miniaod>  .... ]
where the  <aodsim>:<miniaod> pattern are used to map processings from AOD to MINIAOD, where
the processing is the middle part of the dataset (e.g. Spring14dr-PU20bx25_POSTLS170_V5-v*).
The default is
    (.*)-(.*)-v\d+:.*-\2-v\d+
which means map things that have the same global tag.

""")
parser.add_option("-f", "--full", dest="full", action="store_true", default=False, help="Get full information, including number of files and size (slow!)" )
parser.add_option("-F", "--force", dest="noCache", action="store_true", default=False, help="Don't use the cache")
parser.add_option("-o", "--out", dest="out", default="miniAODlist.json", type="string", help="Output file")
parser.add_option("-m", "--map", dest="maps", default=[], action="append", type="string", help="aodsim2miniaod map")
#parser.add_option("--CSA14v2", dest="maps", action="store_const", const=r"Spring14dr-PU_S14.*POSTLS170_V6-v\d+:Spring14miniaod-141029_PU40bx50.*PLS170_V6AN2-v\d+")
(options, args) = parser.parse_args()

a2m = []
if options.maps == []:
    options.maps.append(r"(.*)-(.*)-v\d+:.*-\2-v\d+")
for map in options.maps:
    a2m_find, a2m_repl = map.split(":")
    print "AOD     processing: ",a2m_find
    print "MINIAOD processing: ",a2m_repl
    a2m.append((a2m_find,a2m_repl))

if len(args) != 1 or args[0].count("/") != 2:
    parser.print_usage()
    sys.exit(1)

cache = {}
if options.full and not options.noCache:
    try:
        fcache = open("%s/.listMiniAODS_cache.json" % os.environ['HOME'],"r")
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

def getsamples(query, full=False):
    global cache
    ret = {}
    print "Doing DAS query %s" % query
    opts = ( " --key {0} --cert {0}".format(os.environ['X509_USER_PROXY']) if 'X509_USER_PROXY' in os.environ else "")
    output = os.popen("das_client.py --query='dataset %s' --limit=10000 %s" % (query,opts))
    for line in output:
        if "AOD" in line: 
            ds = line.strip()
            if ds in ret: continue # skip dups
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

aods     = getsamples("dataset=%s/AOD*" % args[0], full=options.full) 
miniaods = getsamples("dataset=%s/MINIAOD*" % args[0], full=options.full) 
atcern   = getphedex("%s/MINIAOD*" % args[0]) 
if not aods or not miniaods or not atcern: 
    raise RuntimeError, "Query failed"

records = {}
for ds in aods.iterkeys():
    (dummy,pd,proc,ec) = ds.split("/")
    (era,gt,ver) = proc.split("-")
    mproc_target = None
    for (a2m_find, a2m_repl) in a2m:
        if re.match(a2m_find, proc):
            mproc_target = re.sub(a2m_find, a2m_repl, proc);
    if mproc_target == None: continue
    #print "\n",ds
    vnum = int(ver[1:])
    key = (pd,era,gt,ec)
    if key in records and records[key]['vnum'] > vnum:
        continue
    records[key] = { 'ds':ds, 'vnum':vnum, 'miniaod':'', 'atcern':False, 'miniproc':''  }
    for mds in miniaods.iterkeys():
        (dummy,mpd,mproc,mec) = mds.split("/")
        if mpd != pd or mec != "MINI"+ec:
            continue
        #print "  try to match to %s. requested proc map: %s" % ( mds, mproc_target)
        if not re.match(mproc_target, mproc):
            continue 
        #print " ---> matched"
        (mera,mgt,mver) = mproc.split("-")
        mvnum = int(mver[1:])
        mkey = (mpd,mera,mgt,mec)
        if mkey in records and records[mkey]['vnum'] > mvnum:
            continue
        records[mkey] = { 'ds':mds, 'vnum':mvnum }
        records[key]['miniaod'] = mds
        records[key]['miniproc'] = mproc
        records[key]['atcern']  = atcern[mds] if (mds in atcern) else { 'group':'none', 'percent':0 }

report = []
for (pd,era,gt,ec) in sorted(records.keys()):
    if "MINI" in ec: continue
    data=records[(pd,era,gt,ec)]
    row = { 'pd':pd, 'gt':gt, 'era':era, 'ds':data['ds'], 'miniaod':data['miniaod'], 'miniproc':data['miniproc'], 'atcern':data['atcern'],  }
    if options.full:
        row['aodinfo'] = cache[row['ds']]
        if row['miniaod']: 
            row['miniaodinfo'] = cache[row['miniaod']]
    report.append(row)

fout = open(options.out, "w")
json.dump(report, fout)
fout.close()

if options.full:
    fcache = open("%s/.listMiniAODS_cache.json" % os.environ['HOME'],"w")
    json.dump(cache, fcache)
    print "Final cache size: %d samples" % (len(cache))
    fcache.close()

