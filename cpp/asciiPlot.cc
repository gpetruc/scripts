void asciiPlot(TH1 *h, int cols=80) {
  using std::cout; using std::endl;
  cout << "Histo " << h->GetName() << "; Title " << h->GetTitle() << endl;
  cout << "Bins: " << h->GetNbinsX() << endl;
  int bins = h->GetNbinsX();
  double scale = cols / (h->GetMaximum() ? h->GetMaximum() : 1.0);
  for (int i = 0; i <= bins + 1; i++) {
    cout << " ";
    int n = static_cast<int>(h->GetBinContent(i)*scale);
    for (int j = 0; j<n; j++) cout << "*";
    for (int j = n; j<=cols; j++) cout << " ";
    cout << "\t X = " << h->GetBinCenter(i) << "; Y = " << h->GetBinContent(i) << endl;
  }
}
void asciiPlot() { }
