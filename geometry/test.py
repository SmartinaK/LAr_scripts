from __future__ import print_function
import argparse
import ROOT

ROOT.gROOT.SetBatch(ROOT.kTRUE)

def main():
    parser = argparse.ArgumentParser(description='Material Plotter')
    parser.add_argument('--fnames', "-f", dest='fnames', nargs='+', default=["beampipe.root", "beaminstrum.root", "LumiCal.root", "homabs.root", "vertex.root", "drift.root"], type=str, help="list of file names to read")
    parser.add_argument('--etaMax', "-m", dest='etaMax', default=1.19, type=float, help="maximum pseudorapidity")
    parser.add_argument('--etaBin', "-b", dest='etaBin', default=0.05, type=float, help="pseudorapidity bin width")
    args = parser.parse_args()

    detectorDict = {}
    histDict = {}
    for fname in args.fnames:
        f = ROOT.TFile.Open(fname, "read")
        tree = f.Get("materials")
        
        accumulatedX0 = 0
        for etaBin, entry in enumerate(tree):
            nMat = entry.nMaterials
            for i in range(nMat):
                material = entry.material.at(i)
                if material == "Air":
                    continue
                
                x0 = entry.nX0.at(i)
                eta = entry.eta  # Access eta directly
                
                if material not in histDict:
                    histDict[material] = ROOT.TH1F(material + "_x0", "X0 distribution for " + material, (int)(2 * args.etaMax / args.etaBin), -args.etaMax, args.etaMax)
                
                etaBin = int((eta + args.etaMax) / args.etaBin) + 1
                histDict[material].SetBinContent(etaBin, histDict[material].GetBinContent(etaBin) + x0)
#                print(histDict[material])
#                accumulatedX0 = accumulatedX0 + x0
                print(detectorDict[fname])
                detectorDict[fname].SetBinContent(etaBin, detectorDict[fname].GetBinContent(etaBin) + x0)                
#        detectorDict[fname] = accumulatedX0

    axis_titles = ["Number of X_{0}", "Number of #lambda", "Material depth [cm]"]

    for plot, title in zip(["x0", "lambda", "depth"], axis_titles):
        legend = ROOT.TLegend(.75, .75, .94, .94)
        legend.SetLineColor(0)
        ths = ROOT.THStack()
        
        	
        for i, detector in enumerate(detectorDict.keys()):
            detectorDict[detector].SetFillColor(i + 10)  # Set fill color dynamically
            detectorDict[detector].SetLineWidth(1)
            detectorDict[detector].SetFillStyle(1001)
	

            ths.Add(detectorDict[detector])
            legend.AddEntry(detectorDict[detector], detector, "f")

        ths.SetMaximum(1.5 * ths.GetMaximum())
        cv = ROOT.TCanvas()
        ths.Draw()
        ths.GetXaxis().SetTitle("#eta")
        ths.GetYaxis().SetTitle(title)

        legend.Draw()
        cv.Print(plot + "_X0_vs_eta.pdf")
        cv.Print(plot + "_X0_vs_eta.png")

if __name__ == "__main__":
    main()

