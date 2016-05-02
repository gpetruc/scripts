#!/bin/bash
EOS="/afs/cern.ch/project/eos/installation/0.3.15/bin/eos.select"
if [[ "$1" == "-r" ]]; then
    shift;
    for P in $*; do
        for D in $( $EOS ls $P ); do
            $0 $P/$D
        done
    done
    exit
fi;
for D in $*; do
    echo -n -e "$D\t";
    for F in $($EOS ls $D | grep '\.root$'); do
        echo -n "." 1>&2;
        edmFileUtil --ls ${D#/eos/cms}/$F 2> /dev/null;
    done | awk 'BEGIN{te=0; ts=0; tf=0;} /events/{tf+=1; te += $6; ts += $8/(1024*1024*1024); }  END{ printf("%3d files, %9d events, %8.2f Gb\n", tf, te, ts); }'
done
