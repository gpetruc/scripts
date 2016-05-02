#!/usr/bin/env perl
use strict;
use warnings;
use Getopt::Long;

my $out = "/tmp/gpetrucc/merged.root";
my $help;
my $sort;
my $xrd;
my $mix;
my $bare;
my $uniq;

GetOptions(
    'o|out|output=s'=>\$out,
    's|sort=s'=>\$sort,
    'r|xrootd'=>\$xrd,
    'm|mixed'=>\$mix,
    'b|bare'=>\$bare,
    'u|uniq'=>\$uniq,
    'help|h|?'=>\$help,
);

sub usage() {
print <<EOF

   usage: $0 [options] dir [pattern] > cfg.py

   options:
      -h, --help, -?: 
            show this help

      -o, --out:
            select output file name

EOF
}

my $cdir = shift(@ARGV);
my $expr = shift(@ARGV);

my $in = "";

if (defined($cdir)) {
    my $ls     = ($cdir =~ /castor/ ? "nsls"  : "ls");
    my $prefix = ($cdir =~ /castor/ ? "rfio:" : "file:");
    foreach (qx($ls $cdir)) {
        chomp;
        m/$expr/ or next if defined ($expr);
        $in .= "\t'$prefix$cdir/$_',\n";
    }
} else {
    foreach (<>) {
        chomp;
        my ($file) = (m/(\S+\.(?:root|lhe))/) or next;
        #my ($file) = (m/(\S+\.root)/) or next;
        my $prefix = "file:";
        if ($file =~ m{^/store/}) { $prefix = ""; }
        if ($file =~ m{^/castor/}) { $prefix = "rfio:"; }
        if (defined($xrd) and $file =~ m{^/data/}) { $prefix = "root://pcmssd12.cern.ch/"; }
        $in .= "\t'$prefix$file',\n";
    }
}

if (defined($bare)) {
    print "process.source.fileNames = [\n$in]\n";
    exit();
}

print <<EOF;
import FWCore.ParameterSet.Config as cms
process = cms.Process('cmsMerge')

process.load("FWCore.MessageLogger.MessageLogger_cfi")
process.options   = cms.untracked.PSet( wantSummary = cms.untracked.bool(True) )
process.MessageLogger.cerr.FwkReport.reportEvery = 1000

process.source = cms.Source("PoolSource", fileNames = cms.untracked.vstring(), skipBadFiles = cms.untracked.bool(False))
process.source.fileNames = [\n$in]

process.out = cms.OutputModule("PoolOutputModule",fileName = cms.untracked.string('$out'))
process.end = cms.EndPath(process.out)  
EOF

if (defined($uniq)) {
print <<EOF;
process.uniq = cms.EDFilter("DuplicateEventIdFilter")
process.p_uniq = cms.Path(process.uniq)
process.out.SelectEvents = cms.untracked.PSet(SelectEvents = cms.vstring('p_uniq'))
EOF
}

if (defined($mix)) {
print <<EOF;
process.source.inputCommands = cms.untracked.vstring("keep *",
    "drop LumiSummary_lumiProducer__RECO",
)
process.out.overrideInputFileSplitLevels = cms.untracked.bool(True)
EOF
}
if (defined($sort)) {
    my $out_unsorted = $out; $out_unsorted =~ s/\.root$/.unsorted.root/;
    print "process.out.fileName = '$out_unsorted'";
    $sort =~ s/(\.py)?$/.py/;
    open SORT, "> $sort";
    print SORT <<EOF;
import FWCore.ParameterSet.Config as cms
process = cms.Process('cmsSort')

process.load("FWCore.MessageLogger.MessageLogger_cfi")
process.options   = cms.untracked.PSet( wantSummary = cms.untracked.bool(True) )
process.MessageLogger.cerr.FwkReport.reportEvery = 1000

process.source = cms.Source("PoolSource", fileNames = cms.untracked.vstring('file:$out_unsorted'))
process.out = cms.OutputModule("PoolOutputModule",fileName = cms.untracked.string('$out'))
process.end = cms.EndPath(process.out)  
EOF
    close SORT;
}
