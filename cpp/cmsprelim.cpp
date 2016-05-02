TPaveText *cmsprel;

void cmsprelim(double x1=0.75, double y1=0.40, double x2=0.95, double y2=0.48, const char *text="CMS Preliminary") { 
   cmsprel = new TPaveText(x1,y1,x2,y2,"NDC");
   cmsprel->SetTextSize(0.05);
   cmsprel->SetFillColor(0);
   cmsprel->SetFillStyle(0);
   cmsprel->SetLineStyle(2);
   cmsprel->SetLineColor(0);
   cmsprel->SetTextAlign(12);
   cmsprel->SetTextFont(42);
   cmsprel->AddText(text);
   cmsprel->Draw("same");
}
