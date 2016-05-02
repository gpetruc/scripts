#!/usr/bin/env perl 
use strict;
use warnings;

my @values = <>; chomp @values;
my $n = scalar(@values);
my $sum = 0; foreach (@values) { $sum += $_; }
my $avg = $sum/$n;

my $sum2 = 0; foreach (@values) { $sum2 += ($_-$avg)*($_-$avg); }
my $stdev = sqrt($sum2/($n-1));
my $merr  = $stdev/sqrt($n);

my @sorted = sort({$a <=> $b} @values);
my $min = $sorted[0];
my $max = $sorted[$n-1];
my $median = ($n % 2 == 0 ? 0.5*($sorted[$n/2-1] + $sorted[$n/2]) : $sorted[$n/2]);

use POSIX;
my $i68lo = floor($n*0.5*(1-0.68)); my $i68hi = ceil($n*0.5*(1+0.68));
my $lo68 = $sorted[ $i68lo ];       my $hi68 = $sorted[ $i68hi < $n ? $i68hi : $n - 1 ];
my $i95lo = floor($n*0.5*(1-0.95)); my $i95hi = ceil($n*0.5*(1+0.95));
my $lo95 = $sorted[ $i95lo ];       my $hi95 = $sorted[ $i95hi < $n ? $i95hi : $n - 1 ];

print "n = $n, min = $min, max = $max, sum = $sum, mean = $avg +/- $merr, sigma = $stdev, median = $median, 68\%I = [$lo68, $hi68], 95\%I = [$lo95, $hi95]\n";


