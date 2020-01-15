<html>
<head>
    <title>MCM Summary</title>
    <script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
    <script src="//code.jquery.com/jquery-migrate-1.2.1.min.js"></script>
<style type="text/css">
    body { font-family: 'Consolas', 'Courier New', courier, monospace; font-size: small; }
    td, th { border-bottom: 1px solid black; padding: 1px 0.3em; vertical-align: middle; font-size: small; }
    a { text-decoration: none; color: black; }
    a:hover { color: blue; }
    td { text-align: left; }
    td.stat { padding-left: 0.4em; border-left: 1px solid black; }
    div.topitem, div.botitem { font-size: small; }
    td.num { text-align: right; font-size: small; padding-right: 0.3em;}
    td.tot { font-weight: bold; }
    td.img { text-align: left; }
    td.dataset { text-align: left; }
    span.done { background-color: rgb(204,235,255); }
    span.almostdone { background-color: rgb(180,255,180); }
    span.ongoing { background-color: rgb(232,246,188); }
    span.started { background-color: rgb(255,224,180); }
    span.bad { background-color: rgb(255,200,200); }
</style>
<script type="text/javascript">
var rawdata =  []; var rawfile = "";
var sorted   = [];
var requests = [];
var campaigns = [];
var alltiers = [];
var lastupdate = "unknown";
var tiers    = [];
var tierspan = [];
function getraw() {
    fname = document.sel.report.value;
    if (fname.match(/^[a-zA-Z0-9_\-\.]+\.json$/)) {
        if (fname != rawfile) {
            rawfile = fname;
            $.getJSON( fname, function( data ) {
                rawdata = data.rows;
                requests = data.requests;
                campaigns = data.campaigns;
                alltiers = data.tiers;
                lastupdate = data.date;
                update();
            })
        }
    }
}
function tierFormVal(tier) {
    if (tier == "LHE") return document.sel.lhe.value;
    if (tier == "GEN-SIM") return document.sel.gensim.value;
    if (tier == "GEN-SIM-DIGI-RAW") return document.sel.digiraw.value;
    if (tier == "AODSIM") return document.sel.aod.value;
    if (tier == "MINIAODSIM") return document.sel.mini.value;
    if (tier == "NANOAODSIM") return document.sel.nano.value;
}
function filterdata() {
    var ret = Array();
    var pat = new RegExp(".*"+document.sel.match.value+".*");
    var nopat = new RegExp(".*"+document.sel.exclude.value+".*");
    for (var i = 0; i < rawdata.length; ++i) {
        if (rawdata[i].pd.match(pat)) {
            if (document.sel.exclude.value != "" && rawdata[i].pd.match(nopat)) {
                continue;
            }
            ret.push(rawdata[i]);
        }
    }
    tiers = Array();
    tierspan = Array();
    for (var i = 0; i < alltiers.length; ++i) {
        var choice = tierFormVal(alltiers[i]);
        if (choice == "no") continue;
        tiers.push(alltiers[i]);
        tierspan.push(choice == "full" ? 3 : 2);
    }
    return ret;
}
function daslink(dataset,text,hover) {
    var query = "https://cmsweb.cern.ch/das/request?input=dataset%3D" + encodeURI(dataset)+"&instance=prod%2Fglobal";
    return "<a href=\""+query+"\" title=\""+hover+"\">" + text + "</a>";
}
function mcmpreplink(prepid,text,hover) {
    var query = "https://cms-pdmv.cern.ch/mcm/requests?prepid="+encodeURI(prepid)+"&page=0&shown=275414779961";
    return "<a href=\""+query+"\" title=\""+hover+"\">" + text + "</a>";
}

function evnum(num) {
    if (num < 10000) {
        return String(num);
    } else if (num < 1000000) {
        if (num % 1000 == 0) {
            return String(num/1000)+"k";
        } else {
            return Number(num/1000.).toFixed(1)+"k";
        }
    } else {
        if (num >= 10*1000*10000) return Number(num/1.0e6).toFixed(0)+"M";
        return Number(num/1.0e6).toFixed(1)+"M";
    }
}
function mcstatus(prepid, mcmitem, maxev, showpd) {
   var stat = mcmitem.stat[0];
   if (stat == "submitted") stat = "<nobr>sub. ("+evnum(mcmitem.stat[1])+")</nobr>";
   var statstyle = "bad";
   if (mcmitem.stat[0] == "done") statstyle = "done";
   else if (mcmitem.evts[1] > 0.80 * mcmitem.evts[0]) statstyle = "almostdone";
   else if (mcmitem.evts[1] > 0.20 * mcmitem.evts[0]) statstyle = "ongoing";
   else if (mcmitem.evts[1] > 0) statstyle = "started";
   var ret = "<td class=\"stat\"><span class=\""+statstyle+"\">" + mcmpreplink(prepid, stat, prepid+" (last change: "+mcmitem.stat[2]+")") + "</span></td>";
   if (showpd) {
       if (mcmitem.outputs.length > 0) {
           var outds = mcmitem.outputs[0];
           ret += "<td class=\"out\"><nobr>"+ daslink(outds, middlename(outds), "Link to DAS") + "</nobr></td>";
       } else {
           ret += "<td class=\"out\">&nbsp;</td>";
       }
   }
   ret += "<td class=\"num\">";
   if (mcmitem.evts[1] > 0) { 
       ret += daslink(mcmitem.outputs[0], evnum(mcmitem.evts[1]), Number(mcmitem.evts[1]/mcmitem.evts[0]*100).toFixed(1)+"% (Link to DAS)"); // + " / "+evnum(mcmitem.evts[0]));
   } else {
       ret += "&ndash;";//evnum(Math.max(0,mcmitem.evts[1])); // + " / "+evnum(mcmitem.evts[0]);
   }
   ret += "</td>";

   return ret;
}
function middlename(dataset) {
    return dataset.split("/")[2];
}
function forceUpdate() {
    rawfile = "";
    $.ajaxSetup({ cache: false}); // disable cache
    update();
    $.ajaxSetup({ cache: true}); // re-enable cache
}

function update() {
    document.getElementById("total").innerHTML = "<tr><td>Loading....</td></tr>";
    if (document.sel.report.value != rawfile) {
        getraw(); return;
    }
    document.getElementById("total").innerHTML = "<tr><td>Rendering....</td></tr>";
    document.title = "McM Summary (" + lastupdate + ")";
    document.getElementById("toptitle").innerHTML = "McM Summary (last update: " + lastupdate + ")";
    document.getElementById("extra").innerHTML = "Monitored campaigns: "+campaigns.join(", ")+"; data tiers: "+alltiers.join(", ");
    sorted = filterdata();
    var ret = "<tr><th>Dataset</th><th>Events</th>";
    for (var i = 0; i < tiers.length; ++i) {
        ret += "<th colspan=\""+tierspan[i]+"\">" + tiers[i]+ "</th>";
    }
    ret += "</tr>";
    for (var i = 0; i < sorted.length; ++i) {
        ret += "<tr><td class=\"dataset\"><nobr>"+sorted[i].pd+(sorted[i].ext ? " ext"+sorted[i].ext : "")+"</nobr></td>";
        var row = sorted[i].row;
        var maxev = requests[row[0]].evts[0];
        ret += "<td class=\"num\">"+evnum(maxev)+"</td>";
        for (var i2 = 0; i2 < tiers.length; ++i2) {
            var found = false;
            for (var j = 0; j < row.length; ++j) {
                var mcmitem = requests[row[j]];
                if (mcmitem.tier != tiers[i2]) continue;
                ret += mcstatus(row[j], mcmitem, maxev, tierspan[i2] == 3);
                found = true;
                break;
            } 
            if (!found) {
                ret += "<td class=\"stat\" colspan=\""+(tierspan[i2]-1)+"\">&nbsp;</td>";
                ret += "<td class=\"num\" >&nbsp;</td>";
            }
        }
        ret += "</tr>\n";

    }
    document.getElementById("total").innerHTML = ret;
    return false;
}

</script>
</head>
<body onload="">
<h1 id="toptitle">MCM Summary</h1>
<div id="extra"></div>
<div>
<form name="sel" onsubmit="update();">
Report:
<select name="report">
<?php 
    foreach(glob("MCMSummary*.json") as $filename) {
        if (isset($_GET['report']) && $_GET['report'] == $filename) {
            print "<option value=\"$filename\" selected=\"selected\">$filename</option>";
        } else {
            print "<option value=\"$filename\">$filename</option>";
        }
    }
?>
</select>
Selection: <input type="text" name="match" size="40" maxlength="160" value="<?php print isset($_GET['match']) ? htmlspecialchars($_GET['match']) : ""?>" >
Exclusion: <input type="text" name="exclude" size="20" maxlength="160" value="<?php print isset($_GET['exclude']) ? htmlspecialchars($_GET['exclude']) : ""?>" >
Show LHE <select name="lhe">
<option value="yes" <?php if (isset($_GET['lhe']) && $_GET['lhe'] == "yes") print 'selected="selected"'; ?> >yes</option>
<option value="no" <?php if (isset($_GET['lhe']) && $_GET['lhe'] == "no") print 'selected="selected"'; ?> >no</option>
<option value="full" <?php if (isset($_GET['lhe']) && $_GET['lhe'] == "full") print 'selected="selected"'; ?> >full</option>
</select>, GEN-SIM <select name="gensim">
<option value="yes" <?php if (isset($_GET['gensim']) && $_GET['gensim'] == "yes") print 'selected="selected"'; ?> >yes</option>
<option value="no" <?php if (isset($_GET['gensim']) && $_GET['gensim'] == "no") print 'selected="selected"'; ?> >no</option>
<option value="full" <?php if (isset($_GET['gensim']) && $_GET['gensim'] == "full") print 'selected="selected"'; ?> >full</option>
</select>, DIGI-RAW <select name="digiraw">
<option value="yes" <?php if (isset($_GET['digiraw']) && $_GET['digiraw'] == "yes") print 'selected="selected"'; ?> >yes</option>
<option value="no" <?php if (isset($_GET['digiraw']) && $_GET['digiraw'] == "no") print 'selected="selected"'; ?> >no</option>
<option value="full" <?php if (isset($_GET['digiraw']) && $_GET['digiraw'] == "full") print 'selected="selected"'; ?> >full</option>
</select>, AOD<select name="aod">
<option value="yes" <?php if (isset($_GET['aod']) && $_GET['aod'] == "yes") print 'selected="selected"'; ?> >yes</option>
<option value="no" <?php if (isset($_GET['aod']) && $_GET['aod'] == "no") print 'selected="selected"'; ?> >no</option>
<option value="full" <?php if (isset($_GET['aod']) && $_GET['aod'] == "full") print 'selected="selected"'; ?> >full</option>
</select>, MiniAOD <select name="mini">
<option value="full" <?php if (isset($_GET['mini']) && $_GET['mini'] == "full") print 'selected="selected"'; ?> >full</option>
<option value="yes" <?php if (isset($_GET['mini']) && $_GET['mini'] == "yes") print 'selected="selected"'; ?> >yes</option>
<option value="no" <?php if (isset($_GET['mini']) && $_GET['mini'] == "no") print 'selected="selected"'; ?> >no</option>
</select>, NanoAOD <select name="nano">
<option value="full" <?php if (isset($_GET['nano']) && $_GET['nano'] == "full") print 'selected="selected"'; ?> >full</option>
<option value="yes" <?php if (isset($_GET['nano']) && $_GET['nano'] == "yes") print 'selected="selected"'; ?> >yes</option>
<option value="no" <?php if (isset($_GET['nano']) && $_GET['nano'] == "no") print 'selected="selected"'; ?> >no</option>
</select> 
<input type="button" value="Go" onclick="update()" />
<input type="button" value="Reload" onclick="forceUpdate()" />
</form>
</div>
<div>
<table id="total">
</table>
</body></html>
