#!/usr/bin/perl
# from Tommaso Boccali, INFN Pisa

# ETH0 TRAFFIC RATE - use: traffic [INTERFACE eth0,1] [DELAY sec] [SCALE *]

while (1) {
    &ProcessInterface("eth0",1,1);  # set default INTERFACE(eth0,eth1), DELAY(sec), SCALE(Mbs/N)
}

sub ProcessInterface
{
    if ($ARGV[0]) {$intrf = $ARGV[0];} else {$intrf = $_[0];}
    if ($ARGV[1]) {$delay = $ARGV[1];} else {$delay = $_[1];}
    if ($ARGV[2]) {$scale = $ARGV[2];} else {$scale = $_[2];}

    # get network interface info -  time 0,1
    $in0  = `/sbin/ifconfig $intrf | grep bytes | cut -d":" -f2 | cut -d" " -f1`;
    $out0 = `/sbin/ifconfig $intrf | grep bytes | cut -d":" -f3 | cut -d" " -f1`;

    # SLEEP (sec)
    sleep $delay;

    $in1  = `/sbin/ifconfig $intrf | grep bytes | cut -d":" -f2 | cut -d" " -f1`;
    $out1 = `/sbin/ifconfig $intrf | grep bytes | cut -d":" -f3 | cut -d" " -f1`;

    # remove eol chars
    chomp($in0); chomp($out0);
    chomp($in1); chomp($out1);

    # get date
    $date = localtime time;

    # TRAFFIC rate
    $IN  = (($in1 -$in0 ) /$delay) /1E+6;  if ($IN <0) {$IN =$IN +1E9;}
    $OUT = (($out1-$out0) /$delay) /1E+6;  if ($OUT<0) {$OUT=$OUT+1E9;}
    $IN  = sprintf ("%6.3f",$IN );
    $OUT = sprintf ("%6.3f",$OUT);

    # GRAPHIC array
    # for($i=0 ; $i < $N   ; $i++) {push (@array,"x")};  print "@array\n";
    $graphIN  = ""; $graphOUT = "";
    for ($i=1; $i<=$scale*$IN ; $i++) {$graphIN  = $graphIN  . "*";}
    for ($i=1; $i<=$scale*$OUT; $i++) {$graphOUT = $graphOUT . "*";}
    # 1 line
      $graph = sprintf ("IN:%-6s %-10s - OUT %-6s %-10s"          , $IN,$graphIN,$OUT,$graphOUT);
    # 2 lines
    # $graph = sprintf ("IN:%-6s - OUT:%-6s \n IN %-10s OUT %-10s", $IN,$OUT,$graphIN,$graphOUT);

    # PRINT
    print  "$date - [$intrf] Mb/s $graph \n";
}
