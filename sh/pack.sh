#!/bin/bash
INDIR=$1
OUTFILE=$2
if [[ "$2" == "" ]]; then echo "Usage: $0 dir outfile"; exit 1; fi
if test \! -d $INDIR; then echo "Missing directory $1"; exit 1; fi
if ls $INDIR/*stdout > /dev/null 2>&1 ; then echo -n "..."; else echo "No output files in $INDIR/*stdout"; exit 2; fi;
if ls $INDIR/*root   > /dev/null 2>&1 ; then echo -n "..."; else echo "No output files in $INDIR/*root";   exit 2; fi;
~/sh/hadd2 -f $OUTFILE.root $INDIR/*root
~/sh/report $INDIR/*stdout | tee $OUTFILE.report.txt
test -f $INDIR/lumiSummary.json && cp -v $INDIR/lumiSummary.json $OUTFILE.report.json
ls -ltraah $OUTFILE.root
