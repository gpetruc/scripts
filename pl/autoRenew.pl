#!/usr/bin/perl
use strict;
use warnings;
$SIG{CHLD} = "IGNORE";
fork and exit;
while (1) {
    sleep 5*60*60;
    system("kinit","-R");
}

