import re
import os, sys, json
import urllib2
from optparse import OptionParser
from time import strftime, strptime, gmtime, mktime

parser = OptionParser(usage=r"""usage: %prog [options] /*/Spring14*/MINIAOD* """)
parser.add_option("-F", "--force", dest="noCache", action="store_true", default=False, help="Don't use the cache")
parser.add_option("-o", "--out", dest="out", default="miniAODlist.json", type="string", help="Output file")
parser.add_option("-x", "--exclude", dest="exclude", action="append", default=[], help="Exclude datasets matching this pattern")
(options, args) = parser.parse_args()

if len(args) < 1 or any(a for a in args if a.count("/") != 3):
    parser.print_usage()
    sys.exit(1)

cache = {}; icache = {}
if not options.noCache:
    try:
        fcache = open("%s/.listMiniAODS3_cache.json" % os.environ['HOME'],"r")
        if fcache:
            cache = json.load(fcache)
            print "Loaded %d samples from cache file. " % (len(cache))
            for ds in cache.keys():
                if cache[ds]['nfiles'] <= 0:
                    del cache[ds]
        fcache.close()
    except:
        print "Failed to read cache form ~/.listMiniAODS_cache.json"
    try:
        fcache = open("%s/.listMiniAODS3_icache.json" % os.environ['HOME'],"r")
        if fcache:
            icache = json.load(fcache)
            print "Loaded %d incomplete samples from icache file. " % (len(icache))
            for ds in icache.keys():
                if icache[ds]['nfiles'] <= 0:
                    del icache[ds]
        fcache.close()
    except:
        print "Failed to read cache form ~/.listMiniAODS3_icache.json"


def getinfo(dataset,status,time):
    info = { 'nfiles':-1, 'nevents':-1, 'size':-1 }
    print "getting detailed info on ",dataset," status:",status,"last fetch:",time
    opts = ""
    output = os.popen("dasgoclient --query='summary dataset=%s' --format=json %s" % (dataset,opts))
    text = [l for l in output]
    try:
        data = json.loads("".join(text))['data'][0]['summary'][0]
        for key in "nfiles", "nevents":
            info[key] = int(data[key])
        info['size'] = int(data['file_size'])
    except:
        print "Error in getting the summary for dataset %s %s " % (dataset,opts)
        for line in text:
            print "  >>  ",line
    return info

def getsamples(query, status, full=False):
    global cache, icache
    ret = {}
    if True:
        print "Doing DAS query %s status %s " % (query,status)
        opts = ""
        pipa = os.popen("dasgoclient --query='dataset %s status=%s'  --format=json %s" % (query,status,opts))
        txt =  ''.join(l for l in pipa)
        dump = open('debug-%s.json' % status,'w'); dump.write(txt); dump.close()
        data = json.loads(txt)
        print "Loaded"
    else:
        print "Pretending to do DAS query %s, but reading from debug.json" % query
        data = json.load(open('debug-%s.json' % status, 'r'))
    tnow = mktime(gmtime())
    snow = strftime('%Y-%m-%d %H:%M:%S', gmtime())
    day  = 3600 * 24.
    for rec in data['data']:
        try:
            ds = rec['dataset'][0]['name'] 
            if ds is None: 
                print "Skipping bogus record: %s" % rec
                continue
        except KeyError:
            print "Error in getting the record: "
            print "rec: ", rec
            print "dataset: ", rec['dataset']
            raise
        if any(re.match(excl, ds) for excl in options.exclude):
            print "skipping ",ds
            continue 
        #if len(ret) < 4: print ds, status, time
        if status == 'VALID':
            #if ds not in cache: continue # FIXME
            if ds not in cache: cache[ds] = getinfo(ds, status, "not cached")
            ret[ds] = cache[ds]
            ret[ds]['status'] = status 
            if ds in icache: del icache[ds]
        elif status == 'PRODUCTION':
            #if ds not in icache: continue # FIXME
            if ds in icache:
                cached = icache[ds]
                age = tnow - mktime(strptime(cached['time'], '%Y-%m-%d %H:%M:%S'))
                if age > (0.2+0.005*(len(ds) % 37))*day:
                    icache[ds] = getinfo(ds, status, cached['time'])
                    icache[ds]['time'] = snow  
            else:
                icache[ds] = getinfo(ds, status, "not cached")
                icache[ds]['time'] = snow  
            ret[ds] = icache[ds]
            ret[ds]['status'] = status 
    return ret

def getphedex(dataset):
    print "Doing PhEDEx query for %s" % dataset
    urlquery = 'https://cmsweb.cern.ch/phedex/datasvc/json/prod/subscriptions?node=T2_CH_CERN&create_since=0&dataset=%s' % dataset.replace("/","%2F")
    text = urllib2.urlopen(urlquery).read()
    if not text: return None
    jsondata = json.loads(text)
    datasets = jsondata['phedex']['dataset']
    ret = {}
    for d in datasets:
        for s in d['subscription']:
            #if len(ret) < 5: print d['name'], s['percent_files']
            if d['name'] in ret:
                if ret[d['name']]['group'] == 'local' and s['group'] != 'local': continue
            ret[d['name']] = { 'group':s['group'], 'percent':s['percent_files'] }
    return ret

miniaods = {}
atcern = {}
for a in args:
    miniaods.update( getsamples("dataset=%s" % a, status="PRODUCTION", full=True) )
    miniaods.update( getsamples("dataset=%s" % a, status="VALID",      full=True) )
    atcern.update( getphedex("%s" % a) ) 
if not miniaods: 
    raise RuntimeError, "DAS Query failed"
if not atcern: 
    print "Phedex Query failed, or no subscribed datasets!"

all = {}
for k,v in icache.iteritems(): all[k] = v
for k,v in  cache.iteritems(): all[k] = v

for ds in miniaods.iterkeys():
        miniaods[ds]['atcern']  = atcern[ds] if (ds in atcern) else { 'group':'none', 'percent':0 }

fout = open(options.out, "w")
json.dump(miniaods, fout)
fout.close()

fcache = open("%s/.listMiniAODS3_cache.json" % os.environ['HOME'],"w")
json.dump(cache, fcache)
print "Final cache size: %d samples" % (len(cache))
fcache.close()
fcache = open("%s/.listMiniAODS3_icache.json" % os.environ['HOME'],"w")
json.dump(icache, fcache)
print "Final incomplete cache size: %d samples" % (len(icache))
fcache.close()

