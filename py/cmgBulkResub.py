#!/usr/bin/env python
import re, os, sys, subprocess

from optparse import OptionParser
parser = OptionParser(usage="%prog [options] chunk-list")
parser.add_option("-t", "--time", dest="time", type="int", default=800, help="Job time in minutes")
parser.add_option("-a", "--accounting-group", dest="acc", type="str", default=None, help="Specify an AccountingGroup for ClassAds")
parser.add_option("--cmg", dest="acc", action="store_const", const="group_u_CMST3.all", help="Use CMG accounting group")
parser.add_option("-g", "--go", action="store_true", default=False, help="Submit also the jobs instead of just creating the condor file")
parser.add_option("-o", "--out", dest="output", type="str", default="resub.cfg", help="Name of condor resubmit file")
(options,args) = parser.parse_args()

chunklist = []
for line in (sys.stdin if (len(args) == 0 or args[0] == "-") else open(args[0], 'r')):
    if line.strip().startswith("#"): continue
    m = re.match(r"(.*\s)?(\S+_Chunk\d+)/?(\s.*)?", line)
    if not m: continue
    if not os.path.isdir(m.group(2)):
        print "Non-existent dir: "+m.group(2)
    chunklist.append(os.path.abspath(m.group(2)))

if len(chunklist) == 0:
    print "No jobs to resubmit"
    if os.path.isfile(options.output): os.unlink(options.output)
    sys.exit(0)

acc = ('+AccountingGroup = "%s"' % options.acc) if options.acc else ""
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
for c in chunklist: jif.write("    "+c+"\n")
jif.write(")\n")
jif.close()

print "Config created to resubmit %d jobs: %s" % (len(chunklist), options.output)

if options.go:
    here = os.getcwd()
    for c in chunklist:
        subprocess.call("rename condor_job OLD_condor_job * 2> /dev/null", shell=True, cwd=c)
    os.chdir(here)
    subprocess.call(["condor_submit", options.output], cwd=here)
