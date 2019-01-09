#!/usr/bin/env python
import subprocess, multiprocessing, re, os.path, sys
from math import ceil
from optparse import OptionParser
parser = OptionParser(usage="usage: %prog commands-file ")
parser.add_option("-j", dest="jobs", default=4,  type="int", help="parallel threads")
parser.add_option("-w", dest="warn", default=False,  action="store_true", help="Warn about failing commands")
(options, args) = parser.parse_args()
if len(args) != 1:
    parser.print_usage()
    exit(1)


def _run(command):
    retval = os.system(command)
    return retval

commands = [l.strip() for l in (open(args[0]) if args[0] != "-" else sys.stdin)]
print "Executing %d lines in %d queues" % (len(commands), options.jobs)
pool = multiprocessing.Pool(options.jobs)
ret = pool.map(_run, commands)
