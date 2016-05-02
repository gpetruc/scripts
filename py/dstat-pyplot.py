import ROOT
from math import *

from sys import argv
argv[1] = argv[1].replace(".dstat","")
dumpfile = open(argv[1]+".dstat")

## Skip headers
header = []
for line in dumpfile:
    if '"usr","sys"' in line: 
        header = [ x.replace('"','') for x in line.strip().split(",") ]
        break

cpuscale = 0.16
iocol = "read" if "eos" not in argv[1] else "recv"

## Start reading data
cpu_us, cpu_w, io = [],[], []
for line in dumpfile:
    if not line.strip(): break
    f = dict(zip(header, [ float(x) for x in line.strip().split(",") ]))
    cpu_us.append(f['usr']+f['sys'])
    cpu_w.append(f['wai'])
    io.append(f[iocol]/(1024.0**2))

iocut  = 0.02 * max(io)
cpucut = 0.05 * max(cpu_us) * cpuscale
cpu_us2, cpu_w2, io2 = [],[], []
checkio = False; addmore = 2
for k,(us,w,i) in enumerate(zip(cpu_us,cpu_w,io)):
   if checkio:
      if i < iocut: continue
   checkio = False
   if len(io2) == 0 and k >= 1:
       cpu_us2.append(cpu_us[k-1])
       cpu_w2.append(cpu_w[k-1])
       io2.append(io[k-1])
   cpu_us2.append(us)
   cpu_w2.append(w)
   io2.append(i)
   if len(io2) > 4 and us < cpucut:
        addmore -= 1
        if addmore == 0: break

cpu_us = cpu_us2
cpu_w = cpu_w2
io = io2
if addmore:
    for x in cpu_us,cpu_w,io: 
        x.append(0.)

ROOT.gROOT.ProcessLine(".x ~/cpp/tdrstyle.cc")
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetCanvasDefW(850);
ROOT.gStyle.SetPaperSize(850./500.*20.,20.);
ROOT.gROOT.SetBatch(True)
c1 = ROOT.TCanvas("c1","c1");
c1.SetTicky(0)
c1.SetWindowSize(950 + (950 - c1.GetWw()), 500 + (500 - c1.GetWh()));
c1.SetRightMargin(0.12)

nbins = len(cpu_us)
hcpu_us = ROOT.TH1F("cpu_us","cpu_us",nbins,0,nbins-0.01);
hcpu_w  = ROOT.TH1F("cpu_w" ,"cpu_w ",nbins,0,nbins-0.01);
hio     = ROOT.TH1F("io","io",nbins,0,nbins-0.01);
cpumax = 0
for b in xrange(nbins):
    hcpu_us.SetBinContent(b+1, cpu_us[b]*cpuscale)
    hcpu_w.SetBinContent(b+1,  cpu_w[b]*cpuscale)
    cpumax = max([cpumax, cpu_us[b]*cpuscale, cpu_w[b]*cpuscale])
    hio.SetBinContent(b+1, io[b])

def spam(x1,y1,x2,y2,text,color=1,align=12,_labels=[]):
   label = ROOT.TPaveText(x1,y1,x2,y2,"NDC");
   label.SetTextSize(0.05);
   label.SetFillColor(0);
   label.SetFillStyle(0);
   label.SetLineStyle(2);
   label.SetLineColor(0);
   label.SetTextAlign(align);
   label.SetTextFont(42);
   label.SetTextColor(color);
   label.AddText(text);
   label.Draw("same");
   _labels.append(label)
 
int_io = sum(io)/1024.
int_cpu_us   = sum([x*cpuscale for x in cpu_us])
cpu_sorted = cpu_us[:]; cpu_sorted.sort(reverse=True)
idx_max10percent = int(floor(0.1*len(cpu_us)))
cpu_max10percent = cpu_sorted[idx_max10percent]
ncpus_eff = int(round(cpuscale*cpu_max10percent))
cpu_eff_perc = 100.0 * sum(cpu_us) / ((ncpus_eff/cpuscale) * len(cpu_us)) 
 
hio.SetLineColor(62)
hio.SetLineWidth(4)
hio.GetYaxis().SetLabelColor(62)
hio.GetYaxis().SetAxisColor(62)
#hio.SetFillColor(62)
#hio.SetLineColor(213)
hio.GetXaxis().SetTitle("time [s]")
hio.GetYaxis().SetTitle("read rate (MB/s)")
hio.Draw("L ")
hio.SetMaximum(1.3*hio.GetMaximum())
c1.Update()
spam(.18,.85,.40,.93, "Total data: %.1f GB" % int_io, 214, align=11)
spam(.48,.85,.85,.93, "Total CPU: %.0f s" % int_cpu_us, 209, align=11)
spam(.48,.78,.85,.85, "%d CPU Eff: %.0f%%" % (ncpus_eff, cpu_eff_perc), 209, align=11)
multiplier = 1
if "x2" in argv[1]: multiplier = 2
if "x3" in argv[1]: multiplier = 3
if "x4" in argv[1]: multiplier = 4
if multiplier > 1:
    spam(.18,.78,.40,.85,  "Data/run: %.1f GB" % (int_io/multiplier), 214, align=11)
    spam(.48,.78,.85,.85, "CPU/run: %.0fs" % (int_cpu_us/multiplier), 209, align=31)

hcpu_us.SetLineColor(209)
hcpu_us.SetLineWidth(3)
hcpu_w.SetLineColor(206)
hcpu_w.SetLineWidth(3)

rightmax = 1.3*cpumax;
scale = ROOT.gPad.GetUymax()/rightmax;
hcpu_w.Scale(scale);
hcpu_us.Scale(scale);
hcpu_us.Draw("L same");
hcpu_w.Draw("L same");

# draw an axis on the right side
axis = ROOT.TGaxis(ROOT.gPad.GetUxmax(),ROOT.gPad.GetUymin(), ROOT.gPad.GetUxmax(), ROOT.gPad.GetUymax(),0,rightmax,510,"+L");
axis.SetLabelFont(42)
axis.SetTitleFont(42)
axis.SetTitleOffset(0.82)
axis.SetLabelSize(0.05)
axis.SetTitleSize(0.06)
axis.SetTitle("CPU: #color[209]{sys+user}, #color[206]{wait}")
axis.SetLineColor(209);
axis.SetLabelColor(209);
axis.Draw();

c1.Print(argv[1]+".png")

