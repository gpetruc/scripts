<html>
<head>
    <title>MiniAOD List</title>
    <script src="//code.jquery.com/jquery-1.11.0.min.js"></script>
    <script src="//code.jquery.com/jquery-migrate-1.2.1.min.js"></script>
<style type="text/css">
    body { font-family: 'Consolas', 'Courier New', courier, monospace; font-size: small; }
    td, th { border-bottom: 1px solid black; padding: 1px 0.3em; vertical-align: middle; font-size: normal; }
    a { text-decoration: none; color: black; }
    a:hover { color: blue; }
    td { text-align: center; }
    td.num { text-align: right; font-size: small;}
    td.tot { font-weight: bold; }
    td.img { text-align: left; }
    td.dataset { text-align: left; }
    tr.atcern { background-color: #CCFFCC; }
    tr.partial { background-color: #FFFFCC; }
    tr.nomini { background-color: #FFCCCC; }
    tr.partial { background-color: #FFCCFF; }
</style>
<script type="text/javascript">
var rawdata =  []; var rawfile = "";
var filtered = [];
var sorted   = [];
function getraw() {
    fname = document.sel.report.value;
    if (fname.match(/^[a-zA-Z0-9_\-\.]+\.json$/)) {
        if (fname != rawfile) {
            rawfile = fname;
            $.getJSON( fname, function( data ) {
                rawdata = data;
                update();
            })
        }
    }
}

function filterdata() {
    var ret = Array();
    var pat = new RegExp(".*"+document.sel.match.value+".*");
    var nopat = new RegExp(".*"+document.sel.exclude.value+".*");
    for (var ds in rawdata) {
        if (ds.match(pat)) {
            if (rawdata[ds].atcern == true) {
                if (document.sel.atcern.value == "no") continue;
                rawdata[ds].atcern = { 'group':'unknown', 'percent': 100. }
            } else if (rawdata[ds].atcern == false) {
                if (document.sel.atcern.value == "yes") continue;
                rawdata[ds].atcern = { 'group':'none', 'percent': 0. }
            } else {
                if (document.sel.atcern.value == "yes" && ( rawdata[ds].atcern['group'] == 'unknown' || rawdata[ds].atcern['percent'] < 100) ) continue; 
                if (document.sel.atcern.value == "no"  && ( rawdata[ds].atcern['percent'] == 100) ) continue; 
            }
            if (document.sel.exclude.value != "" && ds.match(nopat)) {
                continue;
            }
            rawdata[ds].ds = ds
            ret.push(rawdata[ds]);
        }
    }
    return ret;
}
function daslink(dataset,text) {
    var query = "https://cmsweb.cern.ch/das/request?input=dataset%3D" + encodeURI(dataset)+"&instance=prod%2Fglobal";
    return "<td class=\"dataset\"><a href=\""+query+"\">" + text + "</td>";
}
function evnum(num) {
    if (num < 10000) {
        return String(num);
    } else if (num < 1000000) {
        if (num % 1000 == 0) {
            return String(num/1000)+" k";
        } else {
            return Number(num/1000.).toFixed(1)+" k";
        }
    } else {
        return Number(num/1.0e6).toFixed(2)+" M";
    }
}
function update() {
    if (document.sel.report.value != rawfile) {
        getraw(); return;
    }
    var thedata = filterdata();
    sorted = thedata;
    sorted.sort(function (a,b) {return a.ds == b.ds ? 0 : (a.ds < b.ds ? -1 : 1);})
    var aods = 0, miniaods = 0, atcern = 0;
    var aods_size = 0, miniaods_size = 0, atcern_size = 0;
    var aods_events = 0, miniaods_events = 0, atcern_events = 0;
    var ret = "<tr><th>dataset</th><th>files</th><th>events</th><th>size</th><th>at CERN</th></tr>";
    for (var i = 0; i < sorted.length; ++i) {
        if (document.sel.atcern.value == "any" && sorted[i].atcern['percent'] == 100) {
            ret += "<tr class=\"atcern\">";
        } else if (document.sel.atcern.value == "any" && sorted[i].atcern['group'] != 'none' && sorted[i].atcern['percent'] < 100) {
            ret += "<tr class=\"partial\">";
        } else if (sorted[i].status != "VALID") {
            ret += "<tr class=\"partial\">";
        } else {
            ret += "<tr>";
        }
        miniaods += 1;
        ret += daslink(sorted[i].ds, sorted[i].ds);
        ret += "<td class=\"num\">"+sorted[i].nfiles+"</td>";
        ret += "<td class=\"num\">"+evnum(sorted[i].nevents)+"</td>";
        ret += "<td class=\"num\">"+Number(sorted[i].size/1024.0/1024.0/1024.0).toFixed(2)+" Gb</td>";
        miniaods_size   += sorted[i].size;
        miniaods_events += sorted[i].nevents;
        if (sorted[i].atcern['group'] != 'none') {
            ret += '<td>'+Number(sorted[i].atcern['percent']).toFixed(0)+'% ('+sorted[i].atcern['group']+')</td>';
            if (sorted[i].atcern['percent'] == 100) {
                atcern += 1;
                atcern_size   += sorted[i].size;
                atcern_events += sorted[i].nevents;
            }
        } else {
            ret += '<td>NO</td>';
        }
        ret += "</tr>\n";
    }
    ret += "<tr>";
    ret += "<td class=\"tot\">TOTAL: "+miniaods+" DATASETS</td>";
    ret += "<td class=\"num\">&nbsp;</td>";
    ret += "<td class=\"num\">"+evnum(miniaods_events)+"</td>";
    ret += "<td class=\"num\">"+Number(miniaods_size/1024.0/1024.0/1024.0).toFixed(2)+" Gb</td>";
    ret += "<td></td></tr>";
    ret += "<tr>";
    ret += "<td class=\"tot\">AT CERN: "+atcern+" DATASETS</td>";
    ret += "<td class=\"num\">&nbsp;</td>";
    ret += "<td class=\"num\">"+evnum(atcern_events)+"</td>";
    ret += "<td class=\"num\">"+Number(atcern_size/1024.0/1024.0/1024).toFixed(2)+" Gb</td>";
    ret += "<td></td></tr>";

    document.getElementById("total").innerHTML = ret;
    return false;
}

</script>
</head>
<body onload="update()">
<h1>DataSet List</h1>
<div>
<form name="sel" onsubmit="update();">
Report:
<select name="report">
<?php 
    foreach(glob("miniAODlist3-*.json") as $filename) {
        if (isset($_GET['report']) && $_GET['report'] == $filename) {
            print "<option value=\"$filename\" selected=\"selected\">$filename</option>";
        } else {
            print "<option value=\"$filename\">$filename</option>";
        }
    }
?>
</select>
Selection: <input type="text" name="match" size="60" maxlength="160" value="<?php print isset($_GET['match']) ? htmlspecialchars($_GET['match']) : ""?>" >
Exclusion: <input type="text" name="exclude" size="20" maxlength="160" value="<?php print isset($_GET['exclude']) ? htmlspecialchars($_GET['exclude']) : ""?>" >
at CERN: <select name="atcern">
<option value="any">--</option>
<option value="yes" <?php if (isset($_GET['atcern']) && $_GET['atcern'] == "yes") print 'selected="selected"'; ?> >yes</option>
<option value="no" <?php if (isset($_GET['atcern']) && $_GET['atcern'] == "no") print 'selected="selected"'; ?> >no</option>
</select>

<input type="button" value="Go" onclick="update()" />
</form>
</div>
<div>
<table id="total">
</table>
</body></html>
