#!/usr/bin/env python
import subprocess
import sys, re, time
import os.path

class Profiler:
    def __init__(self):
        self._traces = []
        self._pstack_pattern = re.compile(r"#(\d+)\s+(0x[0-9a-f]+) in (\S.*\S) from (\S+)\s*$")
        self._libs = {}
        self._funcs = {}
        self.init_counters()
        self._aliases = {}
    def pstack(self,pid):
        if not os.path.exists("/proc/%s"%pid): return False
        try:
            trace = subprocess.check_output(["pstack",str(pid)])
        except:
            if not os.path.exists("/proc/%s"%pid): return False
            raise
        ret = []
        for line in trace.split("\n"):
            m = re.match(self._pstack_pattern, line)
            if not m:
                #print "line does not match pattern: [[%s]]" % line.strip()
                continue
            num,id,func,lib = m.group(1), m.group(2), m.group(3), m.group(4)
            if id in self._funcs:
                if self._funcs[id] != func: raise RuntimeError, "Relocated?? %s is now %s, was %s" % (id, func, self._funcs[id])
            else:
                self._funcs[id] = func
            if func in self._libs:
                if self._libs[func] != lib: raise RuntimeError, "Relocated?? %s is now %s, was %s" % (func, lib, self._libs[func])
            else:
                self._libs[func] = lib
            ret.append(id)
        return ret
    def lib(self,id):
        while id in self._aliases: id = self._aliases[id]
        return self._libs(id)
    def init_counters(self):
        # number of times a stack trace touched at a given function map (id -> list of traces)
        self._hits = {}
        # number of times a stack trace ended at a given function (map id -> list of traces)
	self._hitself = {}
        # callers of a function (map id -> { id -> list of traces) )
	self._callers = {}
        # callees of a function (map id -> { id -> list of traces) )
	self._callees = {}
        # revmap
        self._func2id = {}
    def record(self,trace):
        ntrace = len(self._traces); self._traces.append(trace)
        self.record_trace(ntrace,trace)
    def record_trace(self,ntrace,trace):
        if trace[0] not in self._hitself: self._hitself[trace[0]] = []
        self._hitself[trace[0]].append(ntrace)
        for i,id in enumerate(trace):
            if id not in self._hits: self._hits[id] = []
            self._hits[id].append(ntrace)
            if i > 0:
                prev = trace[i-1]
                if prev not in self._callers: self._callers[prev] = {id:[]}
                if id not in self._callers[prev]: self._callers[prev][id] = []
                self._callers[prev][id].append(ntrace)
                if id not in self._callees: self._callees[id] = { prev:[] }
                if prev not in self._callees[id]: self._callees[id][prev] = []
                self._callees[id][prev].append(ntrace)
    def playback(self):
        self.init_counters()
        func2id = {}
        id2id = {} 
        # step1: take all ids that map to the same function and consolidate them
        for id,func in self._funcs.iteritems():
            if func not in func2id:
                func2id[func] = id
            id2id[id] = func2id[func]
        # step2: get arund cycles:
        for itrace,trace in enumerate(self._traces):
            hits = {}
            for iptr in reversed(xrange(len(trace))):
                id = trace[iptr]
                # consolidate
                if id2id[id] != id:
                    id = id2id[id]
                    trace[iptr] = id
                # break cycles
                if id in hits:
                    trace[iptr] = "%x%s%s" % (hits[id]+1,"x",id[2:])
                    hits[id] += 1
                    self._funcs[trace[iptr]] = self._funcs[id]+(" (cycle %x)" % (hits[id]+1))
                    self._libs[self._funcs[trace[iptr]]] = self._libs[self._funcs[id]]
                else:
                    hits[id] = 1
        # step 3: 
        for itrace,trace in enumerate(self._traces):
            self.record_trace(itrace,trace)
        # step 4: purge unused functions
        for idf in self._funcs.keys():
            if idf not in self._hits: del self._funcs[idf]
    def run(self,pid,sleeptime):
        while True:
            trace = self.pstack(pid)
            if not trace: 
                print "\nProcess %s not found. exiting" % pid
                return
            else:
                self.record(trace)
                sys.stdout.write("."); sys.stdout.flush()
            time.sleep(sleeptime)
    def save(self,out):
        import cPickle as pickle
        pickle.dump(self,open(out,"w"))
    def fn(self,id):
        return self._funcs[id].replace(") const ()",")")
    def lb(self,id):
        return os.path.basename(self._libs[self._funcs[id]])
    def hits(self,id,onlyself=False):
        map = self._hitself if onlyself else self._hits
        return len(map[id]) if id in map else 0
    def report_flat(self,map,grep=".*",limit=999):
        retshort = {}
        print "List of %d functions matching '%s'" % (limit,grep)
        norm_all = 0.01*float(len(self._traces))
        cgrep = re.compile(grep)
        ret = [ (id, self.fn(id), self.lb(id), len(traces)) for (id,traces) in map.iteritems() if re.search(cgrep,self.fn(id)) ]
        ret.sort(key = lambda (id,f,l,h): h, reverse = True)
        print "      | stack-trace-id        hits   all% | function [library]"
        for i,(id,f,l,h) in enumerate(ret[:limit]):
            fastkey = "#"+str(i)
            print "%-5s | %s   %5d  %5.1f | %s [%s]" % (fastkey,id,h,h/norm_all,f,l)
            retshort[fastkey] = ["func",id]
        print ""
        return retshort;
    def report_fn(self,id,showtraces=False):
        retshort = {}
        print "Id %s: function %s [%s]: hits %d, self hits %d" % (id, self.fn(id), self.lb(id), self.hits(id), self.hits(id,True))
        norm_all = 0.01*float(len(self._traces))
        norm_me  = 0.01*float(max(1,self.hits(id)))
        if id in self._callees:
            ret = [ (ic, self.fn(ic), self.lb(ic), len(traces)) for (ic,traces) in self._callees[id].iteritems() ]
            ret.sort(key = lambda (ic,f,l,h): h, reverse = True)
            print " ---+-----------------------------------------+------------------- "
            print "    | Callee stack id       hits   all%  fun% | function [library]"
            for i,(ic,f,l,h) in enumerate(ret):
                print "%+3d | %s   %5d  %5.1f %5.1f | %s [%s]" % (1+i,ic,h,h/norm_all,h/norm_me,f,l)
                retshort["%+d"%(i+1)] = ["func",ic]
        print " ---+-----------------------------------------+------------------- "
        print "    | %s   %5d  %5.1f %5.1f | %s" % (id,self.hits(id),self.hits(id)/norm_all,self.hits(id)/norm_me, "SELF + CALLEES")
        print "    | %s   %5d  %5.1f %5.1f | %s" % (id,self.hits(id,True),self.hits(id,True)/norm_all,self.hits(id,True)/norm_me,"SELF ONLY")
        if id in self._callers:
            ret = [ (ic, self.fn(ic), self.lb(ic), len(traces)) for (ic,traces) in self._callers[id].iteritems() ]
            ret.sort(key = lambda (ic,f,l,h): h, reverse = True)
            print " ---+-----------------------------------------+------------------- "
            print "    | Caller stack id       hits   all%  fun% | function [library]"
            for i,(ic,f,l,h) in enumerate(ret):
                print "%+3d | %s   %5d  %5.1f %5.1f | %s [%s]" % (-1-i,ic,h,h/norm_all,h/norm_me,f,l)
                retshort["%+d"%(-1-i)] = ["func",ic]
            print ""
        if showtraces:
            print "Trackes including at %s: %s" % (id, ", ".join(self._hits[id]))
            print "Trackes ending at %s   : %s" % (id, ", ".join(self._hitself[id]))
        return retshort
        
    def report(self):
        print "Functions by number of hits, inclusive:"
        self.report_fn(self._hits)
    def interactive(self):
        short = {}
        while True:
            sys.stderr.write("> "); sys.stderr.flush()
            command = sys.stdin.readline()
            if not command:
                break
            tokens = command.split()
            if len(tokens) == 0:
                continue
            if tokens[0] in short:
                tokens = short[tokens[0]]
                sys.stderr.write("< "+" ".join(tokens)+"\n"); sys.stderr.flush()
            if tokens[0] in ["flat","self"]:
                limit=20; grep = []
                for t in tokens[1:]:
                    if t.startswith("limit="): limit=int(t.replace("limit=",""))
                    else: grep.append(t)
                short = self.report_flat(self._hits if tokens[0] == "flat" else self._hitself, limit=limit, grep=("|".join(grep) if grep else "."))
            if tokens[0] == "func":
                if len(tokens) == 1: 
                    print "must give a function name or pattern" 
                    continue
                traces = False
                for t in tokens[2:]:
                    if t.startswith("traces"): traces = True 
                if re.match("[0-9a-f]x[0-9a-f]{16}",tokens[1]):
                    short = self.report_fn(tokens[1],showtraces=traces)
                else:
                    cgrep = re.compile(tokens[1])
                    for id,func in self._funcs.iteritems():
                        if re.search(cgrep,func):
                            short = self.report_fn(id,showtraces=traces)
            if tokens[0] in ["exit","quit",".q"]:
                break


if __name__ == '__main__':
    from optparse import OptionParser
    parser = OptionParser(usage="usage: %prog pid")
    parser.add_option("-o", "--out", dest="out", default="traces.{pid}",  type="string", help="output file")
    parser.add_option("-t", "--time", dest="time", default=1.0,  type="float", help="time between each stack trace (s)")
    parser.add_option("-q", dest="quit", action="store_true", default=False)
    parser.add_option("-r", dest="run", action="store_true", default=False)
    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.print_usage()
        exit(1)
    if re.match(r"\d+",args[0]):
        print "Will profile process %s" % args[0]
        prof = Profiler()
        prof.run(args[0],options.time)
        fout = options.out.format(pid=args[0])
        print "Done, saving output to %s" % fout
        prof.save(fout)
        if not options.quit:
            print "Opening in interactive mode"
            prof.playback()
            prof.interactive()
    elif options.run:
        print "Will run: ", " ".join(args)
        pid = subprocess.Popen(args, bufsize=-1).pid
        print "Process running as pid %s" % pid 
        time.sleep(options.time)
        prof = Profiler()
        prof.run(pid,options.time)
        fout = options.out.format(pid=pid)
        print "Done, saving output to %s" % fout
        prof.save(fout)
        if not options.quit:
            print "Opening in interactive mode"
            prof.playback()
            prof.interactive()
    else:
        print "Will read %s" % args[0]
        import cPickle as pickle
        prof = pickle.load(open(args[0]))
        prof.playback()
        prof.interactive()
    
