#!/usr/bin/env perl
use strict;
use warnings;
use Getopt::Long;

my $out = "/tmp/gpetrucc/merged.root";
my $maxev = -1;
my $help;
my $sort;
my $mix;
my $compress;
my $miniAOD;
my $nanoAOD;
my $bare;
my $uniq;

GetOptions(
    'o|out|output=s'=>\$out,
    's|sort=s'=>\$sort,
    'n|max-ev=s'=>\$maxev,
    'm|mixed'=>\$mix,
    'c|compress'=>\$compress,
    'M|miniAOD'=>\$miniAOD,
    'N|nanoAOD'=>\$nanoAOD,
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
        $in .= "\t'$prefix$file',\n";
    }
}

if (defined($bare)) {
    print "process.source.fileNames = [\n$in]\n";
    exit();
}

my $outputModule = "PoolOutputModule";
if (defined($nanoAOD))  $outputModule = "NanoAODOutputModule";

print <<EOF;
import FWCore.ParameterSet.Config as cms
process = cms.Process('cmsMerge')

process.load("FWCore.MessageLogger.MessageLogger_cfi")
process.options   = cms.untracked.PSet( wantSummary = cms.untracked.bool(True) )
process.MessageLogger.cerr.FwkReport.reportEvery = 1000
process.maxEvents = cms.untracked.PSet(input = cms.untracked.int32($maxev))

process.source = cms.Source("PoolSource", fileNames = cms.untracked.vstring(), skipBadFiles = cms.untracked.bool(False))
process.source.fileNames = [\n$in]

process.out = cms.OutputModule("$outputModule",fileName = cms.untracked.string('$out'))
process.end = cms.EndPath(process.out)  
EOF

if (defined($compress)) {
print <<EOF;
process.out.compressionAlgorithm = cms.untracked.string('LZMA')
process.out.compressionLevel = cms.untracked.int32(4)
process.out.dropMetaData = cms.untracked.string('ALL')
process.out.fastCloning = cms.untracked.bool(False)
process.out.overrideInputFileSplitLevels = cms.untracked.bool(True)
process.out.eventAutoFlushCompressedSize = cms.untracked.int32(15728640)
EOF

}

if (defined($miniAOD)) {
print <<EOF;
process.out.compressionAlgorithm = cms.untracked.string('LZMA')
process.out.compressionLevel = cms.untracked.int32(4)
process.out.dataset = cms.untracked.PSet(
        dataTier = cms.untracked.string(''),
        filterName = cms.untracked.string('')
    )
process.out.dropMetaData = cms.untracked.string('ALL')
process.out.eventAutoFlushCompressedSize = cms.untracked.int32(-900)
process.out.fastCloning = cms.untracked.bool(False)
process.out.overrideBranchesSplitLevel = cms.untracked.VPSet(cms.untracked.PSet(
        branch = cms.untracked.string('patPackedCandidates_packedPFCandidates__*'),
        splitLevel = cms.untracked.int32(99)
        ), 
        cms.untracked.PSet(
            branch = cms.untracked.string('recoGenParticles_prunedGenParticles__*'),
            splitLevel = cms.untracked.int32(99)
        ), 
        cms.untracked.PSet(
            branch = cms.untracked.string('patTriggerObjectStandAlones_slimmedPatTrigger__*'),
            splitLevel = cms.untracked.int32(99)
        ), 
        cms.untracked.PSet(
            branch = cms.untracked.string('patPackedGenParticles_packedGenParticles__*'),
            splitLevel = cms.untracked.int32(99)
        ), 
        cms.untracked.PSet(
            branch = cms.untracked.string('patJets_slimmedJets__*'),
            splitLevel = cms.untracked.int32(99)
        ), 
        cms.untracked.PSet(
            branch = cms.untracked.string('recoVertexs_offlineSlimmedPrimaryVertices__*'),
            splitLevel = cms.untracked.int32(99)
        ), 
        cms.untracked.PSet(
            branch = cms.untracked.string('recoCaloClusters_reducedEgamma_reducedESClusters_*'),
            splitLevel = cms.untracked.int32(99)
        ), 
        cms.untracked.PSet(
            branch = cms.untracked.string('EcalRecHitsSorted_reducedEgamma_reducedEBRecHits_*'),
            splitLevel = cms.untracked.int32(99)
        ), 
        cms.untracked.PSet(
            branch = cms.untracked.string('EcalRecHitsSorted_reducedEgamma_reducedEERecHits_*'),
            splitLevel = cms.untracked.int32(99)
        ), 
        cms.untracked.PSet(
            branch = cms.untracked.string('recoGenJets_slimmedGenJets__*'),
            splitLevel = cms.untracked.int32(99)
        ), 
        cms.untracked.PSet(
            branch = cms.untracked.string('patJets_slimmedJetsPuppi__*'),
            splitLevel = cms.untracked.int32(99)
        ), 
        cms.untracked.PSet(
            branch = cms.untracked.string('EcalRecHitsSorted_reducedEgamma_reducedESRecHits_*'),
            splitLevel = cms.untracked.int32(99)
        ))
process.out.overrideInputFileSplitLevels = cms.untracked.bool(True)
process.out.splitLevel = cms.untracked.int32(0)
EOF

}
if (defined($nanoAOD)) {
    print <<EOF;
process.out.compressionLevel = cms.untracked.int(9)
process.out.compressionAlgorithm = cms.untracked.string("LZMA")
EOF
}



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
