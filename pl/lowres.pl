#!/usr/bin/perl -w
use Getopt::Long;


my $format = "%.3f";

GetOptions(
    'format=s' => \$format
);

while (<>) {
    s/(-?\d+\.\d+)/sprintf($format,$1)/ge;
    print;
}
