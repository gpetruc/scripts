#!/bin/bash
SAVCOL=${CMSSW_PS1_COLOR}
export SCRAM_ARCH=$(pwd | perl -ne 'chomp; $a=$ENV{"SCRAM_ARCH"}; if (s{(CMSSW_\d_\d[0-9A-Za-z_\-]+)/src.*}{$1}) { chdir("$_/.SCRAM"); @a = glob("slc*"); if (@a) { $a = shift(@a); } }; print $a ');

if test -f $PWD/env.sh; then
    export src=$PWD
    source $PWD/env.sh;
    . ~/sh/d; 
    . ~/sh/vg
    return; 
fi;

export GRID=1 # poche seghe
if [[ "$GRID" != "" ]] ; then
    if [[ "$CRABDIR" == "" ]] && echo ARC-$SCRAM_ARCH | grep -v -q ARC-slc6; then 
        #. /afs/cern.ch/cms/LCG/LCG-2/UI/cms_ui_env.sh
        eval $(scramv1 runtime -sh); 
        #alias project > /dev/null 2>&1 && project CMSSW || /bin/true;
        #. /afs/cern.ch/cms/ccs/wm/scripts/Crab/crab.sh
        #. /cvmfs/cms.cern.ch/crab3/crab.sh
    fi
    alias csb='crab -status  | tee status | awk "/^[0-9]/{if ((\$2 != \"Cleared\") || (\$4 != 0) || (\$5 != 0)) print }"'
    alias csbq='crab -status | tee status | awk "/^[0-9]/{print \$2}" | sort | uniq -c' 
    #. ~/sh/fixpy1612;
    eval $(scramv1 runtime -sh);
    #echo $PWD | grep -q "/\(CMGTools\(Git\)\?\|cmgprod\)/CMSSW_" && . ~/sh/init_cmgtools
else
    if [[ "$KEEPDIR" != "1" ]]; then
        alias project > /dev/null 2>&1 && project CMSSW || /bin/true;
    fi;
    eval $(scramv1 runtime -sh);
fi;
if [[ "${SAVCOL}" != "" ]]; then export CMSSW_PS1_COLOR=${SAVCOL}; fi;
. ~/sh/cmssw_ps1; . ~/sh/d; . ~/sh/r; .  ~/sh/vg; 
#. ~/sh/ipy
alias ipy=ipython
ulimit -s unlimited
#export PYTONPATH=$CMSSW_BASE/src/PhysicsTools/PythonAnalysis/python:$CMSSW_RELEASE_BASE/src/PhysicsTools/PythonAnalysis/python:${PYTHONPATH}
export src=$CMSSW_BASE/src
export bsrc=${CMSSW_RELEASE_BASE}/src
alias rd='pushd'
alias bq3='bqueues 8nm 1nh 8nh 1nd 2nd 1nw 2nw  cmscaf1nd cmscaf1nh cmscaf1nw'
alias showtags="(cd $CMSSW_BASE/src; ls -1d */*/BuildFile.xml */*/python | sed 's+/BuildFile.xml\|/python++' | sort | uniq)"
export PATH=~/bin/:${PATH}

# apparently these are now necessary
if [[ "$CRABDIR" != "" ]]; then
    #. /afs/cern.ch/cms/LCG/LCG-2/UI/cms_ui_env.sh
    eval $(scramv1 runtime -sh);
fi;
function crabwhich {
    if [[ "$1" != "" ]]; then
        for F in $*; do grep -H datasetpath $F/share/crab.cfg; done
    else
        grep -H datasetpath crab_0_*/share/crab.cfg
    fi;
}
alias psc="ps x | grep 'cmsRun\|combine\|tmp_heppy.py' | grep -v grep"
function dasql {
   q="$1"; shift;
   dasgoclient --query="$q" $*
}

# https://hypernews.cern.ch/HyperNews/CMS/get/git/210.html
if git --exec-path | grep -q 1.8.3.1-odfocd2; then
    alias git='git --exec-path=/cvmfs/cms.cern.ch/slc6_amd64_gcc491/external/git/1.8.3.1-odfocd/libexec/git-core/'
fi;
test -d /data/gpetrucc/tmp && export TMPDIR=/data/gpetrucc/tmp 
export X509_USER_PROXY=/afs/cern.ch/user/g/gpetrucc/priv/proxy
