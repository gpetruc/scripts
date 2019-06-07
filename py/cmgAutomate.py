#!/usr/bin/env python
import cPickle, os, re, shutil, subprocess, sys, tempfile
from time import strftime, localtime
from datetime import datetime
from glob import glob
from collections import defaultdict
from gzip import GzipFile

def _isValidChunk(dirname):
    if not os.path.isdir(dirname): return False
    if os.path.isfile(dirname+"/config.pck"): return True
    if dirname.endswith(".dir") and os.path.isdir(dirname+"/source"): return True
    return False

def _freeDiskInGb(path):
    if path.startswith("/afs"):
        quota, used =  map(float, subprocess.check_output(["fs", "listq", path]).split("\n")[1].split()[1:3])
        return (quota - used)/(1024.0**2)
    elif path.startswith("/eos"):
        raise RuntimeError("ERROR: EOS not supported yet for free disk area")
    else:
        return int(subprocess.check_output(["df", "-kP", path]).split("\n")[1].split()[3])/(1024.0**2)

def _getEvents(fname):
    import ROOT
    ROOT.gROOT.SetBatch(True)
    ROOT.PyConfig.IgnoreCommandLineOptions = True
    #try:
    tfile = ROOT.TFile.Open(fname)
    if not tfile: return 1
    events = tfile.Get("Events")
    if not events: return 2
    ret = events.GetEntries()
    tfile.Close()
    return ret
    #except:
    #    return 0

class ChunkContainer:
    def __init__(self, dirname, chunks = None, isData=None):
        self.dir = os.path.abspath(dirname.rstrip("/"))
        self.chunks = chunks[:] if chunks else []
    def allChunks(self, split=True):
        ret = []
        for c in self.chunks:
            if split and c.isSplit():
                ret += c.allChunks(split=split)
            else: 
                ret.append(c)
        return ret
    def allChunksByStatus(self, status, split=True):
        return [ c for c in self.allChunks() if c.status == status ]
    def allSplitChunks(self):
        return [ c for c in self.chunks if c.isSplit() ]
    def append(self,chunk):
        if not isinstance(chunk,Chunk): raise RuntimeError("Can only append a chunk to a chunk")
        self.chunks.append(chunk)
    def loadStatus(self, options=["-t","NanoAOD","-z"], log=None):
        chunkmap = {}
        for c in self.chunks:
            if not c.isSplit(): c.status = "ok"
            chunkmap[c.dir] = c
        resublog = log if log else open(self.dir+"/to_resub", "w")
        for line in subprocess.check_output(["cmgListChunksToResub", "-d", self.dir] + options).split("\n"):
            resublog.write(line+"\n")
            if re.match(r"#\s+Chunk\s+(\S+)\s+.*running.*",line):
                #print line.split()[2], " --> RUNNIG"
                if line.split()[2] not in chunkmap: continue
                chunkmap[line.split()[2]].status = "running"
            elif line.startswith("cmgResubChunk "):
                #print line.split()[1], " --> FAIL"
                if line.split()[1] not in chunkmap: continue
                chunkmap[line.split()[1]].status = "failed"
            elif line.strip() and not line.strip().startswith("#"):
                print line.strip(), " ---> ERR!!!"
                pass
        for c in self.allSplitChunks():
            c.loadStatus(options=options, log=log)
    def countStatuses(self, subFraction=1.0):
        """return two set of numbers for each status: the first is the number of chunks, the second is the number of final jobs (can be more if a sample is split)"""
        ret = dict(ok = [0,0], running = [0,0], failed = [0,0])
        for c in self.chunks:
            if c.isSplit():
                cret = c.countStatuses(subFraction = subFraction)
                call = cret['ok'][0] + cret['running'][0] + cret['failed'][0]
                if cret['ok'][0] >= subFraction * call:
                    cstatus = 'ok'
                elif cret['running'][0] > 0 and cret['failed'][0] <= (1.0-subFraction) * call:
                    cstatus = 'running'
                else:
                    cstatus = 'failed'
                ret[cstatus][0] += 1
                for s,(n0,n1) in cret.items():
                    ret[s][1] += n1
            else:
                ret[c.status][0] += 1
                ret[c.status][1] += 1
        return ret
    def printStatus(self, subFraction=1.0, name=None, verbose=True):
        status = self.countStatuses()
        nall = len(self.chunks), len(self.allChunks())
        if verbose:
            print "%-40s : running %4d [%4d]   failed  %4d [%4d]     done  %4d [%4d]    %5.1f%% [%5.1f%%]" % (name if name else getattr(self, 'name'), 
                    status['running'][0], status['running'][1], 
                    status['failed'][0], status['failed'][1], 
                    status['ok'][0], status['ok'][1], 
                    (100.0*status['ok'][0])/nall[0], (100.0*status['ok'][1])/nall[1])
        else:
            print "%4d  %4d  %4d  %3.0f%%  %s" % ( 
                    status['running'][1], 
                    status['failed'][1], 
                    status['ok'][0], 
                    (100.0*status['ok'][0])/nall[0], 
                    name if name else getattr(self, 'name'))
    def isComplete(self, completionTarget = 100.0):
        status = self.countStatuses()
        if completionTarget == 100.0:
            return status['ok'][1] == len(self.allChunks())
        else:
            return status['ok'][0] >= completionTarget * len(self.chunks)
    def isEmpty(self):
        return not self.chunks
    def moveAllChunks(self, dstdir):
        if not os.path.isdir(dstdir):
            raise RuntimeError("Cannot move chunks to %s" % dstdir)
        for c in self.chunks:
            shutil.move(c.dir, dstdir+"/"+c.name)
    def moveFailedChunks(self, faildir, verbose = False):
        if faildir is None: 
            faildir = os.path.dirname(self.dir)+"/failed";
        if not os.path.isdir(faildir): 
            os.mkdir(faildir)
        if not os.path.isdir(faildir):
            raise RuntimeError("Cannot move failing chunks to %s" % faildir)
        for c in self.chunks:
            if c.isSplit(): continue
            if c.status != 'ok':
                if verbose: print "Move %s %s to %s" % (c.status, c.name, faildir)
                shutil.move(c.dir, faildir)
    def mergeSplitChunks(self, completionTarget = 100.0, verbose = False, faildir=None):
        ok = True
        for c in self.allSplitChunks():
            if not c.isComplete(completionTarget = completionTarget):
                if verbose: print "%s is split but not complete at %.1f%%, will not hadd" % (c.name, completionTarget)
                ok = False
            elif not c.mergeSplitChunks(completionTarget = completionTarget, verbose = verbose, faildir=faildir):
                if verbose: print "%s has split components that were not merged." % (c.name)
                ok = False
            elif not c.merge(verbose = verbose, faildir=faildir):
                if verbose: print "%s failed merging." % (c.name)
                ok = False
        return ok

class Production(ChunkContainer):
    def __init__(self, dirname, initSamples=True, options=None):
        ChunkContainer.__init__(self, dirname)
        self.options = options
        if options and options.verbose: print "Loading production dir "+self.dir, "..."
        for dirname in glob(self.dir+"/*_Chunk*"):
            if _isValidChunk(dirname):
                self.append(Chunk(dirname))
        if options and options.verbose: print " (%d chunks)" % len(self.chunks) 
        if initSamples:
            self.samples = {}
            for c in self.chunks:
                s = c.sampleName()
                if s not in self.samples: self.samples[s] = Sample(s, self.dir, options=options)
                self.samples[s].append(c)
        if options and options.verbose: print " (%d samples)" % len(self.samples) 
        for n, s in self.samples.iteritems():
            if options and options.verbose: print " - %s (%d chunks)" % (n, len(s.chunks))
    def printStatus(self, verbose = None):
        if verbose is None: verbose = self.options.verbose
        if not verbose:
            print " run  fail  done   [%]   sample"
        for s in sorted(self.samples.iterkeys()):
            self.samples[s].printStatus(verbose = verbose)
        if len(self.samples) > 1:
            if not verbose:
                print "----  ----  ----  ----   ------"
            ChunkContainer.printStatus(self, name = "TOTAL", verbose=verbose)
    def mergeSplitChunks(self, completionTarget = 100.0, verbose = None, faildir=None):
        if verbose is None: verbose = self.options.verbose
        if faildir is None: faildir = self.dir+"/failed";
        for s in self.samples.itervalues():
            s.mergeSplitChunks(completionTarget=completionTarget, verbose=verbose, faildir=faildir)
    def processCompletedSamples(self, action = None, completionTarget = 100.0, verbose = None, faildir=None):
        if action  is None: action = self.options.completedSampleAction
        if verbose is None: verbose = self.options.verbose
        if faildir is None: faildir = self.dir+"/failed";
        if action == "none": return
        for s in self.samples.itervalues():
            if not s.isComplete(completionTarget = completionTarget): continue
            if verbose: print "%s is complete at %.1f%%: %s" % (s.name, completionTarget, action)
            s.moveFailedChunks(faildir, verbose=verbose)
            if action == "move":
                donedir = self.dir+"/done"
                if not os.path.isdir(donedir): os.mkdir(donedir)
                s.moveAllChunks(donedir)
            elif action == "hadd":
                s.hadd(verbose=verbose)
    def printMergedSamples(self, verbose = None):
        if verbose is None: verbose = self.options.verbose
        merged = []
        for f in glob(self.dir+"/*"):
            if "Chunk" in f: continue
            if os.path.isfile(f) and f.endswith(".root"):
                fname = f
            elif os.path.isdir(f):
                fname = "%s/%s.root" % (f, os.path.basename(f))
                if not os.path.isfile(fname): continue
            else: continue
            merged.append(dict(name = os.path.basename(fname).replace(".root",""),
                age = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(fname))).total_seconds()/3600,
                size = os.path.getsize(fname)/(1024.)**3,
                events = _getEvents(fname)/1e6))
        if not merged: return
        merged.sort(key = lambda m : m['name'])
        print "\n --- completed samples ---"
        print "events[M]  size[G]  age[h]  sample"; 
        for m in merged:
            print "{events:8.3f}   {size:6.3f}   {age:5.1f}   {name}".format(**m)
        if len(merged) > 1:
            print "--------    -----    ----   ------"; 
            print "{events:8.3f}   {size:6.3f}   {age:5s}   {name}".format(
                    name = "TOTAL", age="",
                    events = sum(x['events'] for x in merged), 
                    size=sum(x['size'] for x in merged))


class Sample(ChunkContainer):
    def __init__(self, name, dirname, isData=None, options=None):
        ChunkContainer.__init__(self, dirname)
        self.name = name
        self.options = options
        self.isData = isData if isData != None else ("Run201" in self.name)
    def mergeSplitChunks(self, completionTarget = 100.0, verbose = True, faildir=None):
        if completionTarget is None:
            completionTarget = self.options.completionData if self.isData else self.options.completionMC 
        ChunkContainer.mergeSplitChunks(self, completionTarget=completionTarget, verbose=verbose, faildir=faildir)
    def diskSize(self):
        ret = 0
        for c in self.chunks:
            ret += sum(os.path.getsize(f) for f in glob(c.dir+"/*.root"))
        return ret / (1024.0**3) # Gb
    def hadd(self, verbose=False, outdir=None):
        if outdir is None: outdir = self.dir
        logfilename = "%s/hadd_%s.log" % (self.dir, self.name)
        if os.path.isfile(logfilename):
            print "ERROR: Exising log of hadd in %s: will not retry again." % (logfilename)
            return False
        tmpdir = tempfile.mkdtemp()
        freespace = _freeDiskInGb(tmpdir)
        size = self.diskSize()
        if freespace < 1.5 * self.diskSize() + 2: # some safety margin
            print "WARN: Will not try to merge sample of size %.1f G with only %.1f G free on %s" % (size, freespace, tmpdir)
            os.rmdir(tmpdir)
            return False
        if verbose: print "Will merge sample of size %.1f G on %s (%.1f G free)" % (size, tmpdir, freespace)
        for c in self.chunks:
            os.symlink(c.dir, tmpdir+"/"+c.name)
        try:
            haddlog = subprocess.check_output(["haddChunks.py","-c","-n",".","--max-size","3.8"], cwd=tmpdir, stderr=subprocess.STDOUT)

            haddlog += "\n\nOutput files:\n"
            outputs = [ f for f in glob("%s/%s*.root" % (tmpdir, self.name)) if not re.match(r".*_sub\d+\.root$",f) ]

            total = 0
            for f in outputs:
                fsize = os.path.getsize(f)
                if  fsize < 2048:
                    print "WARNING: very small output file %s (%.1f k)" % (f, os.path.getsize(f)/1024.)
                total += fsize / (1024.**3)
                haddlog += "   %s : %10.6f G\n" % (f, fsize / (1024.**3))
                if verbose: print  "   %s : %10.6f G\n" % (os.path.basename(f), fsize / (1024.**3))
            haddlog += "Total : %7.3f G\n" % (total)

            freedst = _freeDiskInGb(outdir)
            haddlog += "Free  : %7.3f G in destination %s \n" % (total, outdir)

            if freedst < 1.2 * total + 0.5: # some safety margin
                log = open(logfilename, "w");
                log.write(haddlog+"\n")
                log.write("ERROR: not enough free space for safe copy")
                log.close()
                print "ERROR: output of hadded %s is %.1f G, too close to the %1.f G free space in %s" % (self.name, total, freedst, outdir)
                shutil.rmtree(tmpdir)
                return False

            ok = True
            for f in outputs:
                target = outdir+"/"+os.path.basename(f)
                if os.path.isfile(target):
                    print      "ERROR: already existing file %s"   % target
                    haddlog += "ERROR: already existing file %s\n" % target
                    ok = False; break
                shutil.move(f, target)
                if not os.path.isfile(target) or os.path.getsize(target) == 0:
                    print      "ERROR in copying %s to %s"   % (f, target)
                    haddlog += "ERROR in copying %s to %s\n" % (f, target)
                    ok = False; break
            if not ok:
                log = open(logfilename, "w");
                log.write(haddlog+"\n")
                log.close()

            # remove chunks
            for c in self.chunks:
                shutil.rmtree(c.dir)

            # remove tmpdir
            shutil.rmtree(tmpdir)
            return ok
        except subprocess.CalledProcessError as err:
            log = open(logfilename, "w");
            log.write("Error %s in %s\n" % (err.returncode, err.cmd))
            log.write(err.output)
            log.close()
            print "ERROR in hadd of %s: log saved in %s" % (self.name, logfilename)
            shutil.rmtree(tmpdir)
            return False

class Chunk(ChunkContainer):
    def __init__(self, dirname, name=None, sample=None, isData=None):
        ChunkContainer.__init__(self, dirname)
        self.name = os.path.basename(self.dir)
        self.isData = isData if isData != None else ("Run201" in self.name)
        if dirname.endswith(".dir"):
            self.chunks = [ Chunk(d) for d in glob(self.dir+"/*_Chunk*") if _isValidChunk(d) ]
    def chunkIndex(self): 
        m = re.match(r"\S+_Chunk(\d+)(\.dir)?$", self.name)
        return int(m.group(1)) if m else -1
    def sampleName(self):
        m = re.match(r"(\S+)_Chunk\d+(\.dir)?$", self.name)
        return m.group(1) if m else self.name
    def condor(self,what,throw=True):
        files = glob(self.dir+"/condor_job*."+what)
        if len(files) != 1:
            if throw: raise RuntimeError("Condor %s file missing or duplicate for %s" % (what, self.dir))
            else:     return None
        return files[0]
    def preprocessorLog(self):
        files = glob(self.dir+"/preprocessor.log*")
        if len(files) == 0: return None
        if len(files) >  1:
            raise RuntimeError("Preprocessor log is duplicate for %s (%s)" % (self.dir, files))
        return GzipFile(files[0]) if files[0].endswith(".gz") else open(files[0])

    def fileAge(self,fname="condor.log"):
        if fname.startswith("condor."): 
            fname = self.condor(fname.split(".")[1], throw=False)
            if not fname: return 999
        if fname[0] != "/" and os.path.isfile(self.dir+"/"+fname): 
            fname = self.dir+"/"+fname
        elif not os.path.isfile(fname):
            return 999
        diff = datetime.now() - datetime.fromtimestamp(os.path.getmtime(fname))
        return diff.days*24 + diff.seconds/3600.
    def countResubmit(self,reason=None):
        rlog = self.dir+"/resubmit.log"
        if not os.path.isfile(rlog): 
            return 0
        count = 0
        for line in rlog:
            if not line.strip(): continue
            if line[0] in (" ", "\t", "#" ): continue
            if reason and reason not in line: 
                continue
            count += 1
        return count
    def getFiles(self):
        if not hasattr(self, '_files'):
            try:
                comp = cPickle.load(open(self.dir+"/config.pck"))
                self._files = comp.files
            except:
                raise RuntimeError, "Pickle file %s/config.pck does not exist or can't be read" % self.dir
        return self._files
    def doResubmit(self,failure):
        rlog = open(self.dir+"/resubmit.log", "a")
        rlog.write(str(failure)+"\n")
        rlog.write("\tResubmit at %s\n" % strftime('%d %b %y %H:%M %Z', localtime()))
        rlog.close()
        here = os.getcwd()
        subprocess.call("rename condor_job OLD_condor_job * 2> /dev/null", shell=True, cwd=self.dir)
        subprocess.call("rename preprocessor.log OLD_preprocessor.log * 2> /dev/null", shell=True, cwd=self.dir)
        os.chdir(here)
    def isSplit(self):
        return self.dir.endswith(".dir")
    def split(self, splitFactor=0):
        if self.isSplit(): raise RuntimeError("Splitting a split chunk: %s" % self.dir)
        from CMGTools.Production.reSplitChunk import reSplitChunk
        os.chdir(os.path.dirname(os.path.abspath(self.dir)))
        if splitFactor == 0: splitFactor = (6 if len(self.getFiles()) >= 12 else -1)
        self.chunks = [Chunk(c) for c in reSplitChunk(self.dir, splitFactor)]
        self.dir += ".dir"
        self.status = 'failed'
    def merge(self, verbose=False, faildir=None):
        if not self.isSplit(): raise RuntimeError("Merging a non-split chunk: %s" % self.dir)
        logfilename = self.dir+"/hadd.log"
        if os.path.isfile(logfilename):
            print "ERROR: Exising log of failed hadd in %s: will not retry again." % logfilename
            return False
        if verbose: print "Merging split chunk %s" % self.dir
        self.moveFailedChunks(faildir, verbose=verbose)
        try:
            subprocess.check_output(["haddChunks.py","-c","-n","."], cwd=self.dir, stderr=subprocess.STDOUT)
            for f in [ "options.json", "batchScript.sh", "pycfg.py" ]:
                if os.path.isfile(self.dir+"/source/"+f):
                    shutil.move(self.dir+"/source/"+f, self.dir+"/"+f)
            self.dir = self.dir[:-len(".dir")]
            os.rename(self.dir+".dir", self.dir)
        except subprocess.CalledProcessError as err:
            log = open(logfilename, "w");
            log.write("Error %s in %s\n" % (err.returncode, err.cmd))
            log.write(err.output)
            log.close()
            print "ERROR in hadd of %s: log saved in %s" % (self.name, logfilename)
            return False
        self.status = 'ok'
        return True

class Failure:
    def __init__(self, chunk, reason, extra=None, resub=False):
        self.chunk = chunk
        self.reason = reason
        self.extra = extra
        self.resub = resub # job can be resubmitted cheaply
    def __str__(self):
        ret = "%s in chunk %s (%s)" % (self.reason, self.chunk.name, self.chunk.dir)
        if self.extra: ret += "\n\t"+self.extra.replace("\n","\n\t")
        return ret
    def canHaveExpensiveResub(self):
        """Return true if the job can be resubmitted but at an increased cost (e.g. splitting it)"""
        return False
    def prepareResub(self):
        self.chunk.doResubmit(self)
        return [ self.chunk.dir ]

class TimeExceeded(Failure):
    def __init__(self, chunk, **kwargs):
        Failure.__init__(self, chunk, "TimeExceeded", **kwargs)
    @staticmethod 
    def test(chunk):
        for i, line in enumerate(open(chunk.condor("log"),'r')):
            if "Job removed by SYSTEM_PERIODIC_REMOVE due to wall time exceeded allowed max" in line:
                return TimeExceeded(chunk, extra=("%s at line %d of %s" % (line.strip(), i, chunk.condor("log"))))
        return None
    def canHaveExpensiveResub(self):
        """Return true if the job can be resubmitted but at an increased cost (e.g. splitting it)"""
        return len(chunk.getFiles()) > 1
    def prepareResub(self):
        self.chunk.doResubmit(self)
        self.chunk.split(-1)
        return [ c.dir for c in self.chunk.chunks ]


class SetupEnvProblem(Failure):
    def __init__(self, chunk, **kwargs):
        Failure.__init__(self, chunk, "SetupEnvProblem", **kwargs)

    @staticmethod 
    def test(chunk):
        for i, line in enumerate(open(chunk.condor("error"),'r')):
            if i > 50: break
            #if "Could not find platform independent libraries <prefix>" in line:
            if ("scram: command not found" in line or
                "tee: preprocessor.log: No space left on device" in line or
                re.match(".*ERROR.*Server responded with an error:.*No space left on device.*",line) or
                re.match(".*ERROR.*Server responded with an error:.*XrdXrootdAio: Unable to read /store\\S+.root; Unknown error.*",line)):
                return SetupEnvProblem(chunk, 
                        resub=(chunk.countResubmit("SetupEnvProblem") < 2 and chunk.fileAge() > 2), 
                        extra=("%s at line %d of %s" % (line.strip(), i, chunk.condor("error"))))
        return None

class PreprocessorFailure(Failure):
    def __init__(self, chunk, name, **kwargs):
        Failure.__init__(self, chunk, name, **kwargs)

    @staticmethod
    def test(chunk):
        busError = False
        badPreprocOutput = False
        noPreprocLog = False
        for i, line in enumerate(open(chunk.condor("error"),'r')):
            line = line.strip()
            if re.match(r"condor_exec.exe:.*\s+Bus error\s+.*", line):
                busError = "Crash in condor error log, line %d: %s" % (i, line)
            if "file Loop/cmsswPreProcessing.root probably not closed, trying to recover" in line:
                badPreprocOutput = "Bad output from preprocessor (condor error log, line %d): %s" % (i, line)
            if re.match("cp: cannot create regular file '.*/preprocessor.log.gz': Permission denied.*", line):
                noPreprocLog = "Failed to get preprocessor log (condor error log, line %d): %s" % (i, line)

        if badPreprocOutput and noPreprocLog:
            return PreprocessorFailure(chunk, "PreprocessorJobFailed",
                    resub=(chunk.countResubmit("PreprocessorJobFailed") == 0 and chunk.fileAge() > 2),
                    extra=(badPreprocOutput+"\n"+noPreprocLog))

        log = chunk.preprocessorLog()
        if not log: return None
        wasreading = False
        for i, line in enumerate(log):
            wasreading = line.startswith("Begin processing the")
        if wasreading and busError:
            return PreprocessorFailure(chunk, "PreprocessorJobCrashed",
                    resub=(chunk.countResubmit("PreprocessorJobCrashed") < 2 and chunk.fileAge() > 2),
                    extra=("%s\n and preprocessor log ends abruptly with line %r" % (busError, line)))
        return None


from optparse import OptionParser
parser = OptionParser(usage="%prog [options] chunk-list-or-directories ")
parser.add_option("--completion-mc", dest="completionMC", type="float", default=97., help="Percent of jobs to declare a MC sample complete (default: 97)")
parser.add_option("--completion-data", dest="completionData", type="float", default=100., help="Percent of jobs to declare a data sample complete (default: 100)")
parser.add_option("--cheap-resub-timeout", dest="cheapResubTimeout", type="int", default=20, help="Time to wait before cheap resubmission (e.g. env failure)")
parser.add_option("--expensive-resub-timeout", dest="expensiveResubTimeout", type="int", default=120, help="Time to wait before cheap resubmission (e.g. env failure)")
parser.add_option("-t", "--time", dest="time", type="int", default=800, help="Job time in minutes")
parser.add_option("-M", "--max-extra-jobs", dest="maxExtra", type="int", default=0, help="Max extra jobs")
parser.add_option("-a", "--accounting-group", dest="acc", type="str", default=None, help="Specify an AccountingGroup for ClassAds")
parser.add_option("--cmg", dest="acc", action="store_const", const="group_u_CMST3.all", help="Use CMG accounting group")
parser.add_option("-o", "--out", dest="output", type="str", default="resub.cfg", help="Name of condor resubmit file")
parser.add_option("-g", "--go", action="store_true", default=False, help="Submit also the jobs instead of just creating the condor file")
parser.add_option("--csa", "--completed-sample-action", dest="completedSampleAction", type="str", default="none", help="Algorithm to wait for completion")
parser.add_option("--completion", dest="completionAlgo", type="str", default="none", help="Algorithm to wait for completion")
parser.add_option("--FC", dest="completionAlgo", action="store_const", const="FORCE", help="Force completion whatever the state")
parser.add_option("--fc", dest="completionAlgo", action="store_const", const="force", help="Force completion if the target fraction is achieved")
parser.add_option("-v", "--verbose", action="store_true", default=False, help="More output")
(options,args) = parser.parse_args()

completionTarget = 100.0 
if   options.completionAlgo == "force": completionTarget = None
elif options.completionAlgo == "FORCE": completionTarget = 0.0

checks = [ SetupEnvProblem, TimeExceeded, PreprocessorFailure ]
problems = []
dirs = []
unknown = []

for a in args:
   if os.path.isdir(a): 
       prod = Production(a, options=options)
       print "\nProduction at %s: %d / %d chunks" % (prod.dir, len(prod.chunks), len(prod.allChunks()))
       if prod.isEmpty(): 
           prod.printMergedSamples()
           continue
       prod.loadStatus()
       prod.printStatus()
       prod.mergeSplitChunks(completionTarget=completionTarget)
       prod.processCompletedSamples(completionTarget=completionTarget)
       prod.printMergedSamples()
       dirs.append(prod)
       for chunk in prod.allChunksByStatus("failed"):
           for check in checks:
                problem = check.test(chunk)
                if problem: break
           if problem:
                problems.append(problem)
                if options.verbose: print problem
           else:
               unknown.append(chunk)
               if options.verbose: print "ths is ok or unknown: "+chunk.name

if len(problems):
    print "\nKnown failures: %d" % len(problems)
    problemCounter = defaultdict(list)
    for p in problems:
        problemCounter[p.reason].append(p.chunk)
    for p,cs in sorted(problemCounter.iteritems()):
        print "%6d %s: %s" %(len(cs),p, ", ".join(c.name for c in cs[:3]))
if len(unknown):
    print "\nUnknown failures: %d\n    %s" %(len(unknown), ", ".join(c.name for c in unknown[:5]))

if not options.go: 
    sys.exit(0)

resubs = []
# first all cheap resubs
for problem in problems:
    if problem.resub and problem.chunk.fileAge() > options.cheapResubTimeout/60.:
        resubs += problem.prepareResub()
# then possibly expensive resubs
for problem in problems:
    if len(resubs) >= options.maxExtra: break
    if (not problem.resub) and problem.chunk.fileAge() > options.expensiveResubTimeout/60.:
        if problem.canHaveExpensiveResub():
            resubs += problem.prepareResub()
    

if len(resubs) == 0:
    print "\nNo jobs to resubmit"
    if os.path.isfile(options.output): os.unlink(options.output)
    sys.exit(0)

acc = ('+AccountingGroup = "%s"' % options.acc) if options.acc else ""
here = os.getcwd()
jif = open(options.output, 'w')
jif.write("""
Universe = vanilla
Executable = $(Chunk)/batchScript.sh
use_x509userproxy = $ENV(X509_USER_PROXY)
Log        = $(Chunk)/condor_job_$(ProcId).log
Output     = $(Chunk)/condor_job_$(ProcId).out
Error      = $(Chunk)/condor_job_$(ProcId).error
getenv      = True
environment = "LS_SUBCWD=$(Chunk)"
request_memory = 2000
+MaxRuntime = {time}
{acc}\n\n""".format(time = options.time * 60, acc = acc))
jif.write("Queue Chunk from (\n")
for c in resubs: jif.write("    "+c+"\n")
jif.write(")\n")
jif.close()
print "\nConfig created to resubmit %d jobs: %s" % (len(resubs), options.output)
subprocess.call(["condor_submit", options.output], cwd=here)


