#!/usr/bin/env perl

## Tool to dig out information about the event size in PAT
## 
## Please run this giving as argument the root file, and redirecting the output on an HTML file
## Notes:
##    - you must have a correctly initialized environment, and FWLite auto-loading with ROOT
##    - you must put in the same folder of the html also these three files:
##            http://cern.ch/gpetrucc/patsize.css
##            http://cern.ch/gpetrucc/blue-dot.gif
##            http://cern.ch/gpetrucc/red-dot.gif
##      otherwise you will get an unreadable output file
##    - for small files, compression does not work (as you will read from the output html)
##    - per-event provenance is just the GetZipBytes of EventMetaData, EventHistory.
##    -  

use strict; 
use warnings;
use Data::Dumper;
use File::Temp qw/tempfile/;
use File::stat;

my $filename = shift(@ARGV);

if ((!$filename) || ($filename eq "-h")) {
    print STDERR "Usage: diskSize.pl filename.root > filename.html\n";
    exit(1);
}

my $allsize = 0;
if ($filename =~ /^rfio:(.*)/) {
    my $rfiosiz = qx(nsls -l $1);
    my @cols = split(/\s+/,$rfiosiz);
    $allsize = $cols[4]/1024.0;
} else {
    my $st = stat($filename);
    $allsize = $st->size/1024.0;
} 

my ($MACRO, $macrofile) = tempfile( "macroXXXXX", SUFFIX=>'.c' , UNLINK => 1 );
my ($macroname) = ($macrofile =~ m/(macro.....)\.c/);

print STDERR "Getting list of branches ...\n";

print $MACRO "void $macroname(){\nEvents->Print();\n}\n";
close $MACRO;
my $IN = qx(root.exe -b -l $filename $macrofile -q 2> /dev/null);

my %survey = ();
my $obj = undef; my $item = undef;
my $events = 0;
my %arrays = ();

my $ALL = "all (branch is not split)";
foreach (split(/\n/, $IN)) {
  chomp; #print STDERR "    [$_]\n";
  if (m/\*Branch\s+:((\w+)_(\w+)_(\w*)_(\w+))\./) {
        $item = undef;
  }
  if (m/\*Br\s+\d+\s+:((\w+)_(\w+)_(\w*)_(\w+))\.obj\s/) {
        $survey{$1} = { 'type'=>$2, 'label'=>$3, 'instance'=>$4, 'process'=>$5, 'tot'=>0, 'num'=> 0, 'items'=>{},  };
        $obj = $ALL; $item = $1;
        print STDERR "Got item $item (type $2)\n";
  }
  next unless defined $item;
  if (m/\*Br\s+\d+\s+:((\w+)_(\w+)_(\w*)_(\w+))\.obj\.(\S+) :/) {
  #if (m/\*Br\s+\d+\s+:((\w+)_(\w+)_(\w*)_(\w+))\.(\S+) :/) {
        $obj = $6; $item = $1;
        #print STDERR "Got item $item, obj $obj\n";
        die "Product $1 not found" unless defined($survey{$1});
  }
  next unless defined $obj;
  if ((m/\w+\[\S+/) && ($survey{$item}->{'type'} ne 'edmTriggerResults')) { $arrays{$item} = 1;  }
  if (m/Entries\s+:\s*(\d+)\s+:\s+Total\s+Size=\s+(\d+)\s+bytes\s+File\s+Size\s+=\s+(\d+)/) {
        die "Mismatching number of events ($events, $1) " unless (($events == 0) || ($events == $1));
        $events = $1;
        $survey{$item}->{'items'}->{$obj} = { 'siz'=>$3/1024.0, 'ok'=>1 };
        $survey{$item}->{'tot'} += $survey{$item}->{'items'}->{$obj}->{'siz'};
  } elsif (m/Entries\s+:\s*(\d+)\s+:\s+Total\s+Size=\s+(\d+)\s+bytes\s+One basket in memory/) {
        die "Mismatching number of events ($events, $1) " unless (($events == 0) || ($events == $1));
        $events = $1;
        $survey{$item}->{'items'}->{$obj} = { 'siz'=>$2/1024.0, 'ok'=>0 };
        $survey{$item}->{'tot'} += $survey{$item}->{'items'}->{$obj}->{'siz'};
  }
}

foreach $item (keys(%survey)) {
    if (scalar(keys(%{$survey{$item}->{'items'}})) > 1) {
        if (defined($survey{$item}->{'items'}->{$ALL})) {
            print STDERR "Branch $item is split, so removing ALL\n";
            $survey{$item}->{'tot'} -= $survey{$item}->{'items'}->{$ALL}->{'siz'};
            delete $survey{$item}->{'items'}->{$ALL};
        }
    }
}

my ($grandtotal,$provenance) = (0,0);
foreach (keys(%survey)) { $grandtotal += $survey{$_}->{'tot'}; }

print STDERR "Events: $events\n";
open $MACRO, "> $macrofile";
print $MACRO "void $macroname() {\n";
print $MACRO "   TTree *Events = (TTree *) gFile->Get(\"Events\"); \n";
print $MACRO "   TH1 *htmp = 0;\n";
foreach my $coll (sort(keys(%arrays))) {
    print $MACRO "   Events->Draw(\"$coll.\@obj.size()>>htmp\");\n";
    print $MACRO "   htmp = (TH1*) gROOT->FindObject(\"htmp\"); \n";
    print $MACRO "   if ( Events->GetSelectedRows()>0) {\n";
    print $MACRO "      std::cout << \"SIZE\t$coll\\t\" << (htmp->GetMean()*htmp->GetEntries()) << std::endl;\n";
    print $MACRO "      htmp->Delete();\n";
    print $MACRO "   } else {\n";
    print $MACRO "     Events->Draw(\"$coll.obj.\@obj.size()>>htmp\");\n";
    print $MACRO "     htmp = (TH1*) gROOT->FindObject(\"htmp\"); \n";
    print $MACRO "     if ( Events->GetSelectedRows()>0) std::cout << \"SIZE\t$coll\\t\" << (htmp->GetMean()*htmp->GetEntries()) << std::endl;\n";
    print $MACRO "     else std::cout << \"SIZE\t$coll\\t\" << 0 << std::endl;\n";
    print $MACRO "   }\n";
}
#print $MACRO "   std::cout << \"PROVENANCE\t\" << (EventMetaData->GetZipBytes()+EventHistory->GetZipBytes()) << std::endl;\n";
print $MACRO "}\n";
close $MACRO;


print STDERR "Getting items in the collections (it can take a while) ...\n";

my $root = qx(root.exe -b -l "$filename" -q $macrofile  2> /dev/null);
my @lines = split('\n', $root);
foreach (grep( /^SIZE\s+\S+\s+\S+/, @lines)) {
    my ($item, $total) = (m/SIZE\s+(\w+)\s+(\S+)/);
    $survey{$item}->{'num'} = $total;
}
foreach my $item (keys(%survey)) { $survey{$item}->{'num'} = $events if $survey{$item}->{'num'} == 0; }

#foreach (grep( /^PROVENANCE\s+(\S+)/, @lines)) { /^PROVENANCE\s+(\S+)/ and $provenance = $1/1024.0; }

my $s_allsize = sprintf("%.3f Mb, \%d events, %.2f kb/event", $allsize/1024.0, $events, $allsize/$events);

print <<_END_;
<html>
<head>
    <title>$filename : PAT Size ($s_allsize)</title>
    <link rel="stylesheet" type="text/css" href="patsize.css" />
    <script type="text/javascript" src="http://gpetrucc.web.cern.ch/gpetrucc/rgraph/RGraph.common.core.js"></script>
    <script type="text/javascript" src="http://gpetrucc.web.cern.ch/gpetrucc/rgraph/RGraph.pie.js"></script>
    <script type="text/javascript" src="http://gpetrucc.web.cern.ch/gpetrucc/rgraph/RGraph.common.dynamic.js"></script>
    <script type="text/javascript" src="http://gpetrucc.web.cern.ch/gpetrucc/rgraph/RGraph.common.tooltips.js"></script>
    <script type="text/javascript" src="http://gpetrucc.web.cern.ch/gpetrucc/rgraph/RGraph.common.key.js"></script>
</head>
<h1>Summary ($s_allsize)</h1>
<canvas id="mainCanvas" width="800" height="300">[No canvas support]</canvas>
<script type="text/javascript">
var data = [
_END_
my $runningtotal = 0;
foreach (sort({$survey{$b}->{'tot'} <=> $survey{$a}->{'tot'} }
              keys(%survey))) {
    #my $tag;
    if ($survey{$_}->{'tot'} < 0.01 * $grandtotal) {
        my $tag = "<b>Others</b><br/>";
        $tag .= sprintf("Size: %.1f kb/event (%.1f%%)", ($grandtotal-$runningtotal)/$events, ($grandtotal-$runningtotal)/$grandtotal*100);
        print "\t{ 'label':'others', 'tag':'top', 'size':",($grandtotal-$runningtotal)/$events,", 'tip':'",$tag,"' }\n";
        last;
    } else {
        my $tag = "<b><a href=\"#_\">$_</a></b><br/>";
        $tag .= sprintf("Size: %.1f kb/event (%.1f%%)", $survey{$_}->{'tot'}/$events, $survey{$_}->{'tot'}/$grandtotal*100);
        if ($survey{$_}->{'num'}/$events != 1) {
            $tag .= sprintf("<br/>Items/event:  %.1f, %.2f kb/item", $survey{$_}->{'num'}/$events, $survey{$_}->{'tot'}/$survey{$_}->{'num'});
        }
        my $label = $_; m/[^_]+_([^_]+)_[^_]*_\w+/ and $label = $1;
        print "\t{ 'label':'$label', 'tag':'$_', 'size':",$survey{$_}->{'tot'}/$events,", 'tip':'",$tag,"' },\n";
    }
    $runningtotal += $survey{$_}->{'tot'};
}
print <<_END_;
];

window.onload = function() {
    values = [];
    labels = [];
    keys   = [];
    tips   = [];
    for (var i = 0; i < data.length; i++) {
        values.push( data[i].size );
        labels.push( data[i].label );
        keys.push( data[i].label );
        tips.push( data[i].tip );
    }
    var chart = new RGraph.Pie("mainCanvas", values)
                .Set('exploded', 7)
                .Set('tooltips', tips)
                .Set('tooltips.event', 'onmousemove')
                .Set('key', labels)
                .Set('key.position.graph.boxed', false)
                .Draw();
}
</script>
<table>
_END_
print "<tr class='header'><th>".join("</th><th>", "Collection", "items/event", "kb/event", "kb/item", "plot", "%" ) . "</th><th colspan=\"2\">cumulative %</th></tr>\n";
$runningtotal = 0;
foreach (sort({$survey{$b}->{'tot'} <=> $survey{$a}->{'tot'} }
              keys(%survey))) {
    print "<th><a href='#$_'>$_</a></th>";
    foreach my $val ($survey{$_}->{'num'}/$events, $survey{$_}->{'tot'}/$events, $survey{$_}->{'tot'}/$survey{$_}->{'num'}) {
        print sprintf("<td>%.2f</td>", $val);
    }
    print sprintf("<td class=\"img\"><img src='blue-dot.gif' width='\%d' height='\%d' /></td>",
                            $survey{$_}->{'tot'}/$grandtotal * 200, 10 );
    print sprintf("<td>%.1f%%</td>", $survey{$_}->{'tot'}/$grandtotal * 100.0);
    print sprintf("<td>%.1f%%</td>", ($runningtotal+$survey{$_}->{'tot'})/$grandtotal * 100.0);
    print sprintf("<td>%.1f%%</td>", ($grandtotal-$runningtotal)/$grandtotal * 100.0);
    print "</tr>\n";
    $runningtotal += $survey{$_}->{'tot'};
}

# all known data
print "<th>All Event data</th>";
print sprintf("<td>&nbsp;</td><td><b>%.2f</b></td><td>&nbsp;</td>" , $grandtotal/$events);
print sprintf("<td class=\"img\"><img src=\"green-dot.gif\" width='\%d' height='10' />", $grandtotal/$allsize*200.0);
print sprintf("</td><td>%.1f%%<sup>a</sup></td>", $grandtotal/$allsize*100.0);
print "</tr>\n";

# per-event provenance
print "<th>EventMetaData + EventHistory</th>";
print sprintf("<td>&nbsp;</td><td>%.2f</td><td>&nbsp;</td>", $provenance/$events);
print sprintf("<td class=\"img\"><img src='red-dot.gif' width='\%d' height='\%d' /></td>",$provenance/$allsize * 200, 10 );
print sprintf("<td>%.1f%%<sup>a</sup></td>", $provenance/$allsize * 100.0);
print "</tr>\n";

# other, unknown overhead
print "<th>Non per-event data or overhead</th>";
print sprintf("<td>&nbsp;</td><td>%.2f</td><td>&nbsp;</td>", ($allsize-$provenance-$grandtotal)/$events);
print sprintf("<td class=\"img\"><img src='red-dot.gif' width='\%d' height='\%d' /></td>",($allsize-$provenance-$grandtotal)/$allsize * 200, 10 );
print sprintf("<td>%.1f%%<sup>a</sup></td>", ($allsize-$provenance-$grandtotal)/$allsize * 100.0);
print "</tr>\n";


# all file
print "<th>File size</th>";
print sprintf("<td>&nbsp;</td><td><b>%.2f</b></td><td>&nbsp;</td>" , $allsize/$events);
print "<td>&nbsp;</td><td>&nbsp;</td></tr>\n";

print <<_END_;
</table>
Note: size percentages of individual event products are relative to the total size of Event data only.<br />
Percentages with <sup>a</sup> are instead relative to the full file size.
<h1>Detail</h1>
_END_
foreach (sort(keys(%survey))) {
    my $avg = sprintf("%.1f",$survey{$_}->{'num'}/$events);
    print <<_END_;
<h2><a name="$_" id="$_">$_</a> ($avg items/event)</h2>
<table>
_END_
    print "<tr class='header'><th>".join("</th><th>", "Datamember", "kb/event", "kb/item", "plot", "%", "compressed") . "</th></tr>\n";
    foreach my $it (sort({$survey{$_}->{'items'}->{$b}->{'siz'} <=> $survey{$_}->{'items'}->{$a}->{'siz'}} 
                         keys(%{$survey{$_}->{'items'}}))) {
        print "<th>$it</th>";
        my $IT = $survey{$_}->{'items'}->{$it};
        foreach my $val ($IT->{'siz'}/$events, $IT->{'siz'}/$survey{$_}->{'num'}) {
            print sprintf("<td>%.3f</td>", $val);
        }
        print sprintf("<td class=\"img\"><img src='\%s-dot.gif' width='\%d' height='\%d' /></td>",
                                ($IT->{'ok'} ? 'blue' : 'red'), $IT->{'siz'}/$survey{$_}->{'tot'} * 200, 10 );
        print sprintf("<td>%.1f%%</td>", $IT->{'siz'}/$survey{$_}->{'tot'} * 100.0);
        print "<td>". ($IT->{'ok'} ? 'ok' : 'no') . "</td>";
        print "</tr>\n";
    }
    print <<_END_;
</table>
_END_
}
print <<_END_;
</body></html>
_END_
close;
