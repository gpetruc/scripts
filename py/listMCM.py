import re
import os, sys
try:
  import simplejson as json # faster, at least in 2.7
except ImportError:
  import json
import random
from fnmatch import fnmatch
from time import strftime, strptime, localtime, sleep
from datetime import datetime
from collections import defaultdict
from gzip import GzipFile

class ObjFromDict:
    def __init__(self,j,keys=None,ikeys=None,skeys=None):
        if keys:
            self._data = dict((k,j[k]) for k in keys if k in j)
            if skeys: # convert from unicode to string (saves memory)
                for k in skeys:
                    if k in j:
                        if isinstance(j[k], str):
                            self._data[k] = j[k]
                        elif isinstance(j[k], unicode):
                            self._data[k] = str(j[k])
                        else:
                            raise RuntimeError("Shouldn't coerce to str the key %s, value %r" % (k, j[k]))
            if ikeys:
                for k in ikeys:
                    if k in j:
                        self._data[k] = intern(str(j[k]))
        else:
            self._data = j
    def __repr__(self):
        return json.dumps(self._data, indent=4)
    def __getattr__(self,name):
        if '__' not in name and name not in self.__dict__:
            return self._data[name]

class Sample(ObjFromDict):
    def __init__(self,j):
        ObjFromDict.__init__(self,j,keys=["extension","priority","total_events","completed_events","member_of_chain","output_dataset"],
                                    skeys=["_id","input_dataset","flown_with","dataset_name","member_of_campaign","status"])
        self.children = []
        self.parent = None
        # now we try to fix the parent
        if self.input() and self.outputs():
            input_tier = self.input().split("/")[-1]
            for req in j['reqmgr_name']:
                if 'pdmv_dataset_list' not in req['content']: continue
                if self.outputs() and not any(o in req['content']['pdmv_dataset_list'] for o in self.outputs()):
                    continue
                for dataset in req['content']["pdmv_dataset_list"]:
                    if dataset.startswith("/"+self.dataset_name+"/") and dataset.endswith("/"+input_tier):
                        if self._data['input_dataset'] != dataset:
                            if options.debug:
                                print "Replace input dataset for %s from %s to %s" % (self.prep(), self.input(), dataset)
                            self._data['input_dataset'] = dataset
        #
        self._lastDate = strftime('%d %b %y %H:%M', strptime(j['history'][-1]["updater"]["submission_date"], '%Y-%m-%d-%H-%M'))
        if options.debug:
            print self
    def initTier(self,tiers,tiermap):
        self.tier = "UNKNOWN"
        self.itier = 99
        if self.outputs():
            for i,tier in enumerate(tiers):
                if any(o.endswith("/"+tier) for o in self.outputs()):
                    self.tier = tier
                    self.itier = i
                    if options.debug:
                        print "Request %s (input %s) selected for tier %s" % (self.prep(), self.input(), tier)
        if self.tier == "UNKNOWN":
            for i,tier in enumerate(tiers):
                if any((c in self.member_of_campaign.replace("TDR","")) for c in tiermap[tier]): # avoid "TDR" to match "DR"
                    self.tier = tier
                    self.itier = i
                    if options.debug:
                        print "Request %s (campaing %s) selected for tier %s (%s)" % (self.prep(), self.member_of_campaign, tier, tiermap[tier])
        return self.tier != "UNKNOWN"
    def pdkey(self):
        return (self.dataset_name, self.extension)
    def prep(self):
        return self._id
    def input(self):
        return self.input_dataset
    def outputs(self):
        return self.output_dataset
    def io(self):
        return self.input(), self.outputs()
    def stat(self):
        return self.status, self.priority, self._lastDate
    def evts(self):
        return self.total_events, self.completed_events
    def short(self):
        return self.prep(), self.pdkey(), self.io(), self.stat(), self.evts()
    def __str__(self):
        return "=== %s ===\n%s\n%s\n" % (self.prep(), self.short(), repr(self))
    def dprint(self, indent=0):
        print "%s%s (%s: input %s, events %s, status %s) producing %s" % (" "*indent, self.prep(), self.tier, self.input(), self.evts(), self.stat(), ", ".join(self.outputs()))
        for c in self.children:
            c.dprint(indent+4)
    def rowset(self, prefix=[]):
        uptome = prefix + [ self.prep() ] 
        if self.children:
            return sum((c.rowset(uptome) for c in self.children), [])
        else:
            return [ uptome ]
    def json(self):
        return dict(pd=self.dataset_name, ext=self.extension, tier=self.tier, input=self.input(), outputs=self.outputs(), stat=self.stat(), evts=self.evts())


from optparse import OptionParser
parser = OptionParser(usage=r"""usage: %prog [options]  """)
parser.add_option("-a", "--ancestry", dest="ancestry", action="store_true", default=False, help="Include also ancestor campaigns as defined by McM flows")
parser.add_option("-F", "--no-cache", dest="noCache", action="store_true", default=False, help="Use cached results if available")
parser.add_option("-C", "--cache", dest="forceCache", action="store_true", default=False, help="Use cached results if available")
parser.add_option("-t", "--tiers", dest="datatiers", default="LHE,GEN-SIM,AODSIM,MINIAODSIM,NANOAODSIM", type="string", help="Data tiers to use")
parser.add_option("-o", "--out", dest="out", default="MCMSummary.json", type="string", help="Output file")
parser.add_option("-x", "--exclude", dest="exclude", default=[], action="append", type="string", help="Campaigns to exclude")
parser.add_option("-d", "--dataset", dest="dataset", default=None, type="string", help="Dataset name")
parser.add_option("-D", "--debug", dest="debug", action="store_true", default=False, help="Make new cookie")
parser.add_option("-T", "--cache-time", dest="cacheTime", default=60, type="int", help="Cache time in minutes for McM queries (cookies always have 1h life)")
parser.add_option("-r", "--retries", dest="retries", default=2, type="int", help="Retry this number of times")
parser.add_option("--sleep-before-retry", dest="retrySleep", default=30, type="int", help="Seconds to sleep before retrying")
parser.add_option("-p", "--paginated", dest="paginatedQuery", default=0, type="int", help="Make a paginated query with this number of rows per step")
parser.add_option("-n", "--pretend", dest="pretend", default=False, action="store_true", help="Only list the campaigns that would be considered")
(options, args) = parser.parse_args()

if len(args) == 0:
    print "Usage: listMCM.py [ -o MCMSummary-<name>.json ] Campaign [ Campaign2 Campaign3 ... ] " 
    print "example: listMCM.py -o MCMSummary-Autumn18.json ] \"RunIIAutumn18*\" \"RunIIFall18*GS\" " 
    sys.exit()

def fileAge(fname):
    diff = datetime.now() - datetime.fromtimestamp(os.path.getmtime(fname))
    return diff.days*24*3600 + diff.seconds
def goodFile(fname):
    if fname.endswith(".json") or fname.endswith(".json.gz"):
        try:
            x = json.load(GzipFile(fname) if fname.endswith(".gz") else open(fname))
            if 'results' in x:
                if len(x['results']) == 0:
                    print "Empty JSON file "+fname+" (probably an error from McM)"
                    return False
            elif 'rows' in x:
                if len(x['rows']) == 0:
                    print "Empty JSON file "+fname+" (probably an error from McM)"
                    return False
        except:
            print "Corrupt JSON file "+fname
            return False
    return True

def cacheTimeCheck(age, cachetime, rand=True):
    if not cachetime: cachetime = 60*options.cacheTime
    if rand: cachetime = cachetime * (0.3 + random.random())
    return age < cachetime
def cachedCmd(text, command, fname, cachetime = 0):
    goodcache = os.path.exists(fname) and cacheTimeCheck(fileAge(fname), 60*cachetime) and goodFile(fname)
    if (options.noCache or not goodcache) and not options.forceCache:
        print text
        for retry in xrange(options.retries+1):
            print '$ '+command
            try:
                os.system(command)
                if (os.path.exists(fname) and goodFile(fname)):
                    return True
            except:
                pass
            if retry != options.retries:
                print "   request failed. waiting %ds and retrying (%d/%d)" % (options.retrySleep, retry+1, options.retries)
                sleep(options.retrySleep)
            else:
                print "   request failed."

def paginatedQuery(campaign, query, cachetime = 0, limit=500, compress=True, _queries=[0]):
    fname = 'McM-%s.json' % campaign
    if compress:
        fname += ".gz"
    goodcache = os.path.exists(fname) and cacheTimeCheck(fileAge(fname), 60*cachetime)
    if options.forceCache or (goodcache and not options.noCache):
        try:
            data = json.load(GzipFile(fname,'r') if compress else open(fname,'r'))
            if 'results' in data and len(data['results']) >= 0:
                return data['results']
        except:
            print "Bad cache for %s" % cname
            pass
    cacheinfo = "cache %.0f min old, expiration %d min" % (fileAge(fname)/60, cachetime if cachetime else options.cacheTime) if os.path.exists(fname) else "cache does not exist"
    print "Paginated query to McM for campaign %s (%d rows at a time), %s" % (cname, limit, cacheinfo)
    results = []; page = 0; pagname = 'McM-%s-paged.json' % campaign
    while page != -1:
        if os.path.exists(pagname): os.unlink(pagname)
        url = "https://cms-pdmv.cern.ch/mcm/search/?db_name=requests&page=%d&limit=%d&%s&get_raw" % (page, limit, query)
        for retry in xrange(options.retries+2):
            print '$   curl -m 60 -k --cookie $HOME/private/mcm-prod-cookie.txt "%s" -o %s' % (url,pagname)
            os.system('curl -m 60 -k --cookie $HOME/private/mcm-prod-cookie.txt "%s" -o %s' % (url,pagname))
            if os.path.exists(pagname):
                try:
                    data = json.load(open(pagname,'r'))
                    if 'total_rows' in data:
                        results += [ _['doc'] for _ in data['rows'] ]
                        print "   .... now at %d/%d " % (len(results), data['total_rows'])
                        os.unlink(pagname)
                        if len(results) >= data['total_rows']:
                            page = -1
                        else:
                            page = page + 1
                            #print "sleep 10s."; 
                            sleep(10)
                        break
                except:
                    pass
            if retry != options.retries + 1:
                print "   request failed. waiting %ds and retrying (%d/%d)" % (options.retrySleep, retry+1, options.retries+1)
                sleep(options.retrySleep)
                if retry == 2: getCookie()
            else:
                print "Failed after too many retries"
                if os.path.exists(fname):
                    try:
                        data = json.load(GzipFile(fname,'r') if compress else open(fname,'r'))
                        if 'results' in data and len(data['results']) >= 0:
                            print "Returning old results, from %.1f hours ago." % (fileAge(fname)/3600.0)
                            return data['results']
                    except:
                        pass
                return None
    json.dump({'results':results}, GzipFile(fname,'w') if compress else open(fname, 'w'))
    # avoid stressing the code too much
    _queries[0] += len(results)
    if _queries[0] > 20000:
        print "More than 20k records retrieved. Will pause for 15 minutes to give McM some time.",
        for i in range(3*60): 
            sleep(5); print ".",; sys.stdout.flush()
        print " done."
        _queries[0] = 0
    return results
                
# == INIT DATA TIERS ==
TIERs = options.datatiers.split(",")
TIERMAP = dict([ ("LHE",["LHE"]), ("GEN-SIM",["GS"]), ("AODSIM",["DR","FS"]),  ("GEN-SIM-DIGI-RAW",["DR"]), ("MINIAODSIM",["MiniAOD"]), ("NANOAODSIM",["NanoAOD"]) ])

# == INIT SSO COOKIE ==
def getCookie():
    cachedCmd( "Get new SSO cookie for McM into $HOME/private/mcm-prod-cookie.txt",
               "cern-get-sso-cookie -u https://cms-pdmv.cern.ch/mcm/ -o $HOME/private/mcm-prod-cookie.txt --krb --reprocess",
               os.path.expandvars("$HOME/private/mcm-prod-cookie.txt"), cachetime = 30)
getCookie()

# == INIT CAMPAIGNS ==
cachedCmd( "Query to McM for list of all campaign names",
           'curl -k --cookie $HOME/private/mcm-prod-cookie.txt "https://cms-pdmv.cern.ch/mcm/search/?db_name=campaigns&page=-1" > McM-campaigns.json',
           'McM-campaigns.json')

CAMPAIGNs = [c for c in json.load(open('McM-campaigns.json'))['results']]
ALLCNs = [c['prepid'] for c in CAMPAIGNs]

CNs = []
for a in args:
    CNs += [ c for c in ALLCNs if fnmatch(c,a) ]
CNs = sorted(set(CNs))
if options.ancestry:
    def parents(cn):
        return [c['prepid'] for c in CAMPAIGNs if cn in c['next']]
    def ancestry(cns):
        ret = set()
        for cn in cns:
            ret.add(cn)
            for cn2 in ancestry(parents(cn)):
                ret.add(cn2)
        return ret
    CNs = sorted(ancestry(CNs))
if options.exclude:
    CNs = [ c for c in CNs if not any(fnmatch(c,e) for e in options.exclude) ]

if len(CNs) == 0:
    print "No campaigns selected. Aborting."
    sys.exit(1)
else:
    print "Will load the following campaigns: %s " % (" ".join(CNs))
    if options.pretend: sys.exit(0)

# == LOAD CAMPAIGNS ==
BYPREP = {}
BYOUTPUT = {}
BYCHAIN = defaultdict(list)

for cname in CNs:
    #print "--> ",cname
    # query
    query = "member_of_campaign="+cname
    if options.dataset: 
        query += "&dataset_name="+options.dataset
    if options.paginatedQuery > 0:
        requests = paginatedQuery(cname, query, limit=options.paginatedQuery)
    else:
        cachedCmd("Query to McM for campaign " + cname,
                  'curl -m 60 -k --cookie $HOME/private/mcm-prod-cookie.txt "https://cms-pdmv.cern.ch/mcm/search/?db_name=requests&page=-1&%s" | gzip > McM-%s.json.gz' % (query,cname),
                  'McM-%s.json.gz' % cname)
        data = json.load(GzipFile('McM-%s.json.gz' % cname, 'r'))
        if 'results' in data:
            requests = data['results']
        else:
            requests = [ _['doc'] for _ in data['rows'] ]
    if not requests: 
        print "No results found for %s" % cname
        continue
    if options.dataset:
        requests = [r for r in requests if r['dataset_name'] == options.dataset]
    samples = map(Sample, [r for r in requests if r and (r['dataset_name'].strip() != "")])
    del requests
    print "Loaded %s from json (%d samples)" % (cname, len(samples))
    for req in samples:
        #print "Request %s (input %s, output %s)" % (req.prep(), req.input(), req.outputs())
        if not req.initTier(TIERs, TIERMAP): 
            print "Skipping %s %s of undetermined or unrequested tier" % (req.prep(), req.pdkey())
            continue
        if req.tier not in TIERs:
            print "Skipping %s %s of unselected tier %s" % (req.prep(), req.pdkey(), req.tier)
            continue
        BYPREP[req.prep()] = req
        for ds in req.outputs():
            if ds in BYOUTPUT:
                print "ATTENTION: duplicate requests producing %s:" % (ds)
                print req.short()
                print BYOUTPUT[ds].short()
                if req.status not in ("done", "submitted") and BYOUTPUT[ds].status in ("done", "submitted"):
                    print "Preferring %s (better status)" % BYOUTPUT[ds].prep()
                elif int(req.prep().split("-")[2]) < int(BYOUTPUT[ds].prep().split("-")[2]):
                    print "Preferring %s (higher id)" % BYOUTPUT[ds].prep()
                else:
                    BYOUTPUT[ds] = req
        for chain in req.member_of_chain:
            if (req.flown_with if req.flown_with else req.member_of_campaign) in chain:
                BYCHAIN[chain].append(req)
print "I have %d total requests in %d campaigns, producing %d datasets" % (len(BYPREP), len(CNs), len(BYOUTPUT))

primitives = [ ]
for req in BYPREP.itervalues():
    if req.input() in BYOUTPUT:
        src = BYOUTPUT[req.input()]
        src.children.append(req)
        req.parent = src

# now try link by chain
for chain, reqs in BYCHAIN.iteritems():
    pieces = chain.split("-")[1].split("_")[1:]
    steps = [None for p in pieces]
    for req in reqs:
        arg = (req.flown_with if req.flown_with else req.member_of_campaign)
        if arg not in pieces: continue
        steps[pieces.index(arg)] = req
    for i in xrange(1,len(steps)):
        if steps[i-1] is None: continue
        if steps[i] is None: continue
        if steps[i].parent is None or steps[i].parent.prep() != steps[i-1].prep():
            if options.debug:
                print "Adding new connection %s -> %s" % (steps[i-1].prep(), steps[i].prep())
            steps[i].parent = steps[i-1]
            steps[i-1].children.append(steps[i])

primitives = [ req for req in BYPREP.itervalues() if req.parent is None ]
primitives.sort(key = lambda r : (r.pdkey(), r.itier))
rows = []
for prim in primitives:
    #print prim.pdkey()
    #prim.dprint(3)
    for row in prim.rowset():
        #print "\t", row
        rows.append(dict(pd = prim.dataset_name, ext=prim.extension, row=row))

bigdump = open(options.out, 'w')
json.dump(dict(requests = dict( (r.prep(), r.json()) for r in BYPREP.itervalues() ), 
               rows = rows, tiers=TIERs, date=strftime('%d %b %y %H:%M %Z', localtime()), campaigns=CNs), 
          bigdump)
bigdump.close()

print "Wrote to %s" % options.out
