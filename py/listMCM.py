import re
import os, sys, json
from fnmatch import fnmatch
from time import strftime, strptime, localtime
from collections import defaultdict

class ObjFromDict:
    def __init__(self,j):
        self._data = j
    def __repr__(self):
        return json.dumps(self._data, indent=4)
    def __getattr__(self,name):
        if '__' not in name and name not in self.__dict__:
            return self._data[name]

class Sample(ObjFromDict):
    def __init__(self,j):
        ObjFromDict.__init__(self,j)
        self.children = []
        self.parent = None
        if options.debug:
            print self
        # now we try to fix the parent
        if self.input() and self.outputs():
            input_tier = self.input().split("/")[-1]
            for req in self.reqmgr_name:
                if self.outputs() and not any(o in req['content']['pdmv_dataset_list'] for o in self.outputs()):
                    continue
                for dataset in req['content']["pdmv_dataset_list"]:
                    if dataset.startswith("/"+self.dataset_name+"/") and dataset.endswith("/"+input_tier):
                        if self._data['input_dataset'] != dataset:
                            if options.debug:
                                print "Replace input dataset for %s from %s to %s" % (self.prep(), self.input(), dataset)
                            self._data['input_dataset'] = dataset
        #
    def initTier(self,tiers,tiermap):
        self.tier = "UNKNOWN"
        self.itier = 99
        if self.outputs():
            for i,tier in enumerate(tiers):
                if any(o.endswith("/"+tier) for o in self.outputs()):
                    self.tier = tier
                    self.itier = i
        if self.tier == "UNKNOWN":
            for i,tier in enumerate(tiers):
                if any((c in self.member_of_campaign) for c in tiermap[tier]):
                    self.tier = tier
                    self.itier = i
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
        return self.status, self.priority, strftime('%d %b %y %H:%M', strptime(self.history[-1]["updater"]["submission_date"], '%Y-%m-%d-%H-%M'))
    def evts(self):
        return self.total_events, self.completed_events
    def short(self):
        return self.pdkey(), self.prep(), self.io(), self.stat(), self.evts()
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
parser.add_option("-C", "--cache", dest="noCache", action="store_false", default=True, help="Use cached results if available")
parser.add_option("-t", "--tiers", dest="datatiers", default="GEN-SIM,AODSIM,MINIAODSIM,NANOAODSIM", type="string", help="Data tiers to use")
parser.add_option("-o", "--out", dest="out", default="MCMSummary.json", type="string", help="Output file")
parser.add_option("-d", "--dataset", dest="dataset", default=None, type="string", help="Dataset name")
parser.add_option("-D", "--debug", dest="debug", action="store_true", default=False, help="Make new cookie")
(options, args) = parser.parse_args()

if len(args) == 0:
    print "Usage: listMCM.py [ -o MCMSummary-<name>.json ] Campaign [ Campaign2 Campaign3 ... ] " 
    print "example: listMCM.py -o MCMSummary-Autumn18.json ] \"RunIIAutumn18*\" \"RunIIFall18*GS\" " 
    sys.exit()

# == INIT DATA TIERS ==
TIERs = options.datatiers.split(",")
TIERMAP = dict([ ("LHE",["LHE"]), ("GEN-SIM",["GS"]), ("AODSIM",["DR"]), ("MINIAODSIM",["MiniAOD"]), ("NANOAODSIM",["NanoAOD"]) ])

# == INIT SSO COOKIE ==
if options.noCache:
    print "Get new SSO cookie for McM into $HOME/private/mcm-prod-cookie.txt"
    os.system("cern-get-sso-cookie -u https://cms-pdmv.cern.ch/mcm/ -o $HOME/private/mcm-prod-cookie.txt --krb --reprocess")

# == INIT CAMPAIGNS ==
if options.noCache:
    print "Query to McM for list of all campaign names"
    os.system('curl -k --cookie $HOME/private/mcm-prod-cookie.txt "https://cms-pdmv.cern.ch/mcm/search/?db_name=campaigns&page=-1" > McM-campaigns.json')
ALLCNs = [c['prepid'] for c in json.load(open('McM-campaigns.json'))['results']]

CNs = []
for a in args:
    CNs += [ c for c in ALLCNs if fnmatch(c,a) ]
CNs = sorted(set(CNs))

if len(CNs) == 0:
    print "No campaigns selected. Aborting."
    sys.exit(1)
else:
    print "Will load the following campaigns: %s " % (", ".join(CNs))

# == LOAD CAMPAIGNS ==
BYPREP = {}
BYOUTPUT = {}
BYCHAIN = defaultdict(list)

for cname in CNs:
    # query
    if options.noCache or not os.path.exists('McM-%s.json' % cname):
        query = "member_of_campaign="+cname
        if options.dataset: 
            query += "&dataset_name="+options.dataset
        print "Query to McM for campaign "+cname
        os.system('curl -k --cookie $HOME/private/mcm-prod-cookie.txt "https://cms-pdmv.cern.ch/mcm/search/?db_name=requests&page=-1&%s" > McM-%s.json' % (query,cname))
    # parse
    requests = json.load(open('McM-%s.json' % cname, 'r'))['results']
    if not requests: 
        print "No results found for %s" % cname
        continue
    if options.dataset:
        requests = [r for r in requests if r['dataset_name'] == options.dataset]
    samples = map(Sample, [r for r in requests if r and (r['dataset_name'].strip() != "")])
    print "Loaded %s from json (%d samples)" % (cname, len(samples))
    for req in samples:
        if not req.initTier(TIERs, TIERMAP): 
            print "Skipping %s %s of undetermined tier" % (req.prep(), req.pdkey())
            continue
        if req.tier not in TIERs:
            print "Skipping %s %s of unselected tier %s" % (req.prep(), req.pdkey(), req.tier)
            continue
        BYPREP[req.prep()] = req
        for ds in req.outputs():
            if ds in BYOUTPUT:
                print "ATTENTION: duplicate requests producing %s:\n%s%s" % (ds, req, BYOUTPUT[ds])
            BYOUTPUT[ds] = req
        if req.member_of_chain and len(req.member_of_chain) == 1:
            if (req.flown_with if req.flown_with else req.member_of_campaign) in req.member_of_chain[0]:
                BYCHAIN[req.member_of_chain[0]].append(req)

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
