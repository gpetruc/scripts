#!/usr/bin/env perl
use warnings;
use Date::Parse;
use POSIX;

use Getopt::Long;
my $lumis = undef;
GetOptions('lumis'=>\$lumis);

foreach my $file (@ARGV) {
    open FILE, $file or die "Can't read $file\n";
    my @lines = <FILE>;
    print "$file : \n";
    my ($evtot,$timev);
    my $start = 0; my $end = 0; 
    my $vsize = 0; my $lastev = 0;
    my ($run, $firstlumi, $lastlumi) = (0,0,0);
    my $files = 0;
    my $timeev;
    foreach (@lines) {
        if ($lumis) {
            if (/^Begin processing the \d+\w+ record. Run (\d+), Event \d+, LumiSection (\d+)/) {
                if ($run != $1) { 
                    $lastev += ($lastlumi - $firstlumi + 1);
                    $firstlumi = $2; $lastlumi = $2;
                    $run = $1;
                } else {
                    $lastlumi = $2;
                }
            }
        } else { 
            /^Begin processing the (\d+)/ and $lastev = $1;
        }
        if (/at\s+(\d\d-[A-Z][a-z][a-z]-20\d\d\s+[012]\d:\d\d:\d\d(?:\.\d+))\s+([A-Z][A-Z][A-Z]+)/) {
            my $t = str2time($1);
            if (($start == 0) || ($t < $start)) { $start = $t; }
            if (($end   == 0) || ($t > $end  )) { $end   = $t; }
        }
        /^\d+.*\sSuccessfully opened file / and $files++;
        m/TrigReport Events (total = \d+ passed = \d+ failed = 0)/ and $evtot = $1;
        m/TrigReport Events total = (\d+) passed = \d+ failed = 0/ and $lastev = $1;
        m{(CPU/event = \S+ Real/event = \S+)} and $timev = $1;
        if (m/VSIZE (\S+) \S+ RSS (\S+)/) { $vsize = $1 unless $vsize > $1; }
    }
    my $time = $end - $start;
    $evtot = $lastev unless $evtot;
    my ($EVENTS,$EV) = ("events","ev");
    if ($lumis) { 
        $evtot = $lastev + ($lastlumi - $firstlumi + 1); $lastev = $evtot; 
        $EVENTS = "lumis"; $EV = "ls"; 
    }
    print "\t$EVENTS: $evtot (files: $files)\n";
    my ($mev,$mevscale) = (0, 1);
    if ($time > 0 && $lastev > 0) { # minutes/<X>events, where X is a power of 10
        my $pow10 = -floor(log($time/60./$lastev)/log(10.)); 
        $mevscale = floor(exp(log(10.)*$pow10)+0.01);
        $mev = (($time/60.)/($lastev/$mevscale));
        if ($mevscale >= 1e6) { $mevscale = sprintf('%dM',$mevscale/1e6); }
        if ($mevscale >= 1e3) { $mevscale = sprintf('%dk',$mevscale/1e3); }
    }
    print sprintf("\ttime: \%d s = \%.1f m = \%.2f h (%.1f $EVENTS/min; %.2f mins/\%s$EV)\n", 
        $time, $time/60.0, $time/3600.0, 
        $lastev/($time > 0 ? $time/60. : 1), 
        $mev,$mevscale );
    print "\tperf: $timev\n" if $timev; 
    print "\tvsize: $vsize Mb\n" if $vsize; 
    print "\n";
    close FILE;
}
