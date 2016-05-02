TH1* iih1(TH1 *hist, double norm=100.0, bool fromRight=true) {
    double scale = hist->Integral() + hist->GetBinContent(0) + hist->GetBinContent(hist->GetNbinsX()+1);
    if (fromRight) {
        for (int b = hist->GetNbinsX(); b >= 0; --b) {
            hist->SetBinContent(b, hist->GetBinContent(b+1) + hist->GetBinContent(b));
        }
    } else {
        for (int b = 1; b <= hist->GetNbinsX(); ++b) {
            hist->SetBinContent(b, hist->GetBinContent(b-1) + hist->GetBinContent(b));
        }
    }
    if (norm) {
        hist->Sumw2();
        hist->Scale(norm/scale);
    }
    hist->Draw();
    return hist;
}

void ii(double norm=100.0, TString name="htemp") {
  if (gROOT->FindObject(name)) {
	  iih1((TH1*) gROOT->FindObject(name), norm);
  }
}

TGraph *rocCurve2(TString expr, TTree *signalTree, TString signal, TTree *backgroundTree, TString background, bool highIsGood=false, Long64_t maxEntries=1000000000) {
    double nS = signalTree->Draw(expr, signal, "", maxEntries);
    TH1F *hS = (TH1F*) gROOT->FindObject("htemp")->Clone("hS");
    iih1(hS,1,highIsGood);
    if (expr.Contains(">>htemp")) backgroundTree->Draw(expr, background, "", maxEntries);
    else backgroundTree->Draw(expr+TString::Format(">>htemp(%d,%g,%g)", hS->GetNbinsX(), hS->GetXaxis()->GetXmin(), hS->GetXaxis()->GetXmax()), background, "", maxEntries);
    TH1F *hB = (TH1F*) gROOT->FindObject("htemp")->Clone("hB");
    iih1(hB,1,highIsGood);
    int i=0;
    while(hS->GetArray()[i] == 0) i++;
    int points = 0, ipoint = 0;
    for (int j = (i > 0 ? i : 1); j < hS->GetSize(); ++j) {
        if ( ! ( hS->GetArray()[j] ==  hS->GetArray()[j-1] && hB->GetArray()[j] ==  hB->GetArray()[j-1] ) ) {
            if ( hS->GetArray()[j] != 1.0 && hB->GetArray()[j] != 1.0 && hS->GetArray()[j] != 0.0 && hB->GetArray()[j] != 0.0) {
                points++;
                if (points == 1) ipoint = j;
                //if (points < 5) cout << "point " << j << " B=" <<  hB->GetArray()[j]  << " S=" <<  hS->GetArray()[j] << std::endl;
            }
        }
    }
    if (points <= 1) {
        printf("ROC curve degenerates to a single point, eff(s) = %.3f%%, eff(b) = %.3f%%\n", hS->GetArray()[ipoint]*100, hB->GetArray()[ipoint]*100);
        return new TGraph(1,&hB->GetArray()[ipoint],&hS->GetArray()[ipoint]);
    } else {
        return new TGraph(hS->GetSize()-i-1,&hB->GetArray()[i],&hS->GetArray()[i]);
    }
}

TGraph *rocCurve(TTree *tree, TString expr, TString signal, TString background, bool highIsGood=false) {
    return rocCurve2(expr,tree,signal,tree,background,highIsGood);
}
