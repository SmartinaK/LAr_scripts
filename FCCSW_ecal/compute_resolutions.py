#!/usr/bin/env python

import glob
import argparse
import csv
import ROOT
import numpy as np

Nplates = 1486

def main():
    """Read command line and trigger processing"""

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--inputDir", default = "FCCSW_ecal/baseline_LAr_testResol_1/",
            help = "Directory containing the input files to process", type=str)
    parser.add_argument("-o", "--outFile", default = "out.csv",
            help = "Output CSV file", type=str)
    parser.add_argument("--clusters", nargs='+', action="extend", default=[],
            help = "Cluster collections to use", type=str)
#    parser.add_argument("--MVAcalibCalo", help = "Path to XGBoost json file used to calibrate CaloClusters",
#    type=str)
#    parser.add_argument("--MVAcalibTopo", help = "Path to XGBoost json file used to calibrate CaloTopoClusters",
#    type=str)
    args = parser.parse_args()
    run(args.inputDir, args.clusters, args.outFile)
#    run(args.inputDir, args.clusters, args.outFile, args.MVAcalibCalo, args.MVAcalibTopo)


#def run(in_directory, clusters_colls, out_file, MVAcalibCalo, MVAcalibTopo):
def run(in_directory, clusters_colls, out_file):
    """Actual processing"""
    init_stuff()
    res = []
#    if MVAcalibCalo:
#        res += get_MVAcalib_resolution(in_directory, "CaloClusters", MVAcalibCalo)
#    if MVAcalibTopo:
#        res += get_MVAcalib_resolution(in_directory, "CaloTopoClusters", MVAcalibTopo)
    res += get_resolutions(in_directory, clusters_colls)
    res.sort(key=lambda it: it[0])
    print("All raw results")
    for r in res:
        print(r)
    write_output(res, out_file)


def init_stuff():
    readoutName = "ECalBarrelModuleThetaMerged"
    geometryFile = "../../FCCDetectors/Detector/DetFCCeeIDEA-LAr/compact/FCCee_DectMaster_thetamodulemerged.xml"
    ROOT.gROOT.SetBatch(True)
    ROOT.gSystem.Load("libFCCAnalyses")
    _fcc = ROOT.dummyLoader
    ROOT.gInterpreter.Declare("using namespace FCCAnalyses;")
    ROOT.gInterpreter.Declare("using namespace FCCAnalyses::CaloNtupleizer;")
    ROOT.CaloNtupleizer.loadGeometry(geometryFile, readoutName)
    ROOT.ROOT.EnableImplicitMT(32)

class Results:
    def __init__(self, n_init, n_pass, resp_e, resol_e, h_e, resp_theta, resol_theta, h_theta, resp_phi, resol_phi, h_phi, h_phi_e, p_phi_e):
        self.n_init = n_init
        self.n_pass = n_pass
        self.resp_e = resp_e
        self.resol_e = resol_e
        self.h_e = h_e
        self.resp_theta = resp_theta
        self.resol_theta = resol_theta
        self.h_theta = h_theta
        self.resp_phi = resp_phi
        self.resol_phi = resol_phi
        self.h_phi = h_phi
        self.h_phi_e = h_phi_e
        self.p_phi_e = p_phi_e


def get_resolutions(in_directory, clusters_colls):
    in_files = glob.glob(in_directory+"/*.root")
    print("Der kuchenmann",in_files)
    results = []
    for f in in_files:
        results_f = {}
        truth_e = float(f[f.rfind('_')+1:f.rfind('.')])/1000
        print(f"Now running on {f} for truth energy {truth_e} GeV")
        df = ROOT.ROOT.RDataFrame("events", f)
        num_init = df.Count()
        print ("Stonjek ", num_init)
        df = (
            df
            .Define("e_theta", "atan2(sqrt(genParticles.momentum.y*genParticles.momentum.y+genParticles.momentum.x*genParticles.momentum.x), genParticles.momentum.z)")
            .Define("e_phi", "atan2(genParticles.momentum.y,genParticles.momentum.x)")
            )
        for clusters in clusters_colls:
            df2 = (
                df
                .Alias(f"clusters_energy", f"{clusters}.energy")
                .Define(f"good_clusters", f"{clusters}[clusters_energy>0.1]")
                .Filter(f"good_clusters.size()>0", ">=1 cluster with E>100MeV")
                .Define(f"good_clusters_e", f"getCaloCluster_energy(good_clusters)")
                .Define(f"good_clusters_x", f"getCaloCluster_x(good_clusters)")
                .Define(f"good_clusters_y", f"getCaloCluster_y(good_clusters)")
                .Define(f"good_clusters_z", f"getCaloCluster_z(good_clusters)")
                .Define(f"good_clusters_theta", f"atan2(sqrt(good_clusters_y*good_clusters_y + good_clusters_x*good_clusters_x), good_clusters_z)")
                .Define(f"good_clusters_phi", f"atan2(good_clusters_y,good_clusters_x)")
                .Define(f"good_clusters_phi_mod", f"fmod(good_clusters_phi,{2*np.pi/Nplates})")
                .Define(f"leading_cluster_idx", f"ArgMax(good_clusters_e)")
                .Define(f"response_e", f"(good_clusters_e[leading_cluster_idx] - {truth_e}) / {truth_e}")
                .Define(f"response_theta", f"ROOT::VecOps::DeltaPhi(e_theta[0], good_clusters_theta[leading_cluster_idx])")
                .Define(f"response_phi", f"ROOT::VecOps::DeltaPhi(e_phi[0], good_clusters_phi[leading_cluster_idx])")
                )
            h_phi = df2.Histo1D("response_phi")
            h_theta = df2.Histo1D("response_theta")
            h_e = df2.Histo1D(("", "", 500, -0.5, 0.5), "response_e")
            h_phi_e = df2.Histo2D(("", "", 40, -0.005, 0.005, 100, -0.5, 0.5), "good_clusters_phi_mod", "response_e")
            p_phi_e = df2.Profile1D(("", "", 40, -0.005, 0.005), "good_clusters_phi_mod", "response_e")
            num_pass = df2.Count()
            resol_e = df2.StdDev("response_e")
            resol_theta = df2.StdDev("response_theta")
            resol_phi = df2.StdDev("response_phi")

            results_f[clusters] = Results(num_init, num_pass, df2.Mean("response_e"), resol_e, h_e,
                                          df2.Mean("response_theta"), resol_theta, h_theta, df2.Mean("response_phi"),
                                          resol_phi, h_phi, h_phi_e, p_phi_e)

        for k, v in results_f.items():
            v.h_phi.SetName(f"Phi_{k}_{truth_e}")
            v.h_theta.SetName(f"Theta_{k}_{truth_e}")
            v.h_e.SetName(f"E_{k}_{truth_e}")
            c = ROOT.TCanvas()
            v.h_phi.Draw()
            resp_phi_v, resol_phi_v = get_response_and_resol(v.h_phi, v.resp_phi.GetValue(), v.resol_phi.GetValue())
            c.Print(in_directory+'/'+v.h_phi.GetName()+'.png')
            v.h_theta.Draw()
            resp_theta_v, resol_theta_v = get_response_and_resol(v.h_theta, v.resp_theta.GetValue(), v.resol_theta.GetValue())
            c.Print(in_directory+'/'+v.h_theta.GetName()+'.png')
            v.h_e.Draw()
            resp_e_v, resol_e_v = get_response_and_resol(v.h_e, v.resp_e.GetValue(), v.resol_e.GetValue())
            c.Print(in_directory+'/'+v.h_e.GetName()+'.png')
            #v.h_phi_e.Draw("colz")
            #c.Print(in_directory+f"/Phi_E_{k}_{truth_e}.png")
            #v.p_phi_e.Draw()
            #c.Print(in_directory+f"/Prof_phi_E_{k}_{truth_e}.png")

            row = [truth_e, k, v.n_init.GetValue(), v.n_pass.GetValue(), resp_e_v, resol_e_v, resp_theta_v, resol_theta_v, resp_phi_v, resol_phi_v]
            results.append(row)


    results.sort(key=lambda it: it[0])
    return results


#def get_MVAcalib_resolution(in_directory, clusters, MVAcalib_file):
#    import xgboost as xgb
#    reg = xgb.XGBRegressor(tree_method="hist")
#    reg.load_model(MVAcalib_file)
#
#    in_files = glob.glob(in_directory+"/*.root")
#    results = []
#    for f in in_files:
#        truth_e = float(f[f.rfind('_')+1:f.rfind('.')])/1000
#        print(f"Now running on {f} for truth energy {truth_e} GeV")
#        df = ROOT.ROOT.RDataFrame("events", f)
#        num_init = df.Count()
#        if clusters == "CaloClusters":
#            cells = "CaloClusterCells"
#        if clusters == "CaloTopoClusters":
#            cells = "CaloTopoClusterCells"
#        df = (
#            df
#            .Alias(f"clusters_energy", f"{clusters}.energy")
#            .Define(f"good_clusters", f"{clusters}[clusters_energy>0.1]")
#            .Filter(f"good_clusters.size()>0", ">=1 cluster with E>100MeV")
#            .Define(f"good_clusters_e", f"getCaloCluster_energy(good_clusters)")
#            .Define(f"good_clusters_EnergyInLayers", f"getCaloCluster_energyInLayers(good_clusters, {cells}, 12)")
#            .Define(f"lc_idx", f"ArgMax(good_clusters_e)")
#            .Define(f"Cluster_E", f"good_clusters_e[lc_idx]")
#            )
#        for i in range(12):
#            df = df.Define(f"good_clusters_E{i}", f"getFloatAt({i})(good_clusters_EnergyInLayers)")
#            df = df.Define(f"Cluster_E{i}", f"good_clusters_E{i}[lc_idx]")
#
#        cols_to_use = [f"Cluster_E{i}" for i in range(12)]
#        cols_to_use += ["Cluster_E"]
#        v_cols_to_use = ROOT.std.vector('string')(cols_to_use)
#        # Filter to remove weird events and get a proper tree
#        #filter_str = "&&".join([f" Cluster_E{i}!=0 " for i in range(12)])
#        #df2 = df.Filter(filter_str + " && Cluster_E!=0", "Remove bad clusters with missing cell links")
#        df2 = df.Filter("Cluster_E5!=0 && Cluster_E!=0", "Remove bad clusters with missing cell links")
#        cols = df2.AsNumpy(v_cols_to_use)
#        num_pass = df2.Count()
#        #df2.Report().Print()
#
#        layers = np.array(
#        [
#            cols["Cluster_E0"],
#            cols["Cluster_E1"],
#            cols["Cluster_E2"],
#            cols["Cluster_E3"],
#            cols["Cluster_E4"],
#            cols["Cluster_E5"],
#            cols["Cluster_E6"],
#            cols["Cluster_E7"],
#            cols["Cluster_E8"],
#            cols["Cluster_E9"],
#            cols["Cluster_E10"],
#            cols["Cluster_E11"],
#        ]
#        )
#
#        cluster_E = layers.sum(axis=0)
#        normalized_layers = np.divide(layers, cluster_E)
#        data = np.vstack([normalized_layers, cluster_E])
#
#        calib_e = reg.predict(data.T) * cluster_E
#        #print(np.array([calib_e, data.sum(axis=0)]))
#        h_e = ROOT.TH1D("hMVA", "hMVA", 500, -0.5, 0.5)
#        for e in calib_e:
#            h_e.Fill((e - truth_e)/truth_e)
#
#        c = ROOT.TCanvas()
#        h_e.SetName(f"E_Calibrated{clusters}_{truth_e}")
#        h_e.Draw()
#        c.SetLogy()
#        resp_e_v, resol_e_v = get_response_and_resol(h_e, h_e.GetMean(), h_e.GetStdDev())
#        c.Print(in_directory+'/'+h_e.GetName()+'.png')
#
#        row = [truth_e, f"Calibrated{clusters}", num_init.GetValue(), num_pass.GetValue(), resp_e_v, resol_e_v, 0, 0, 0, 0]
#        results.append(row)
#
#
#    results.sort(key=lambda it: it[0])
#    return results



def get_response_and_resol(h, mean_guess=0, resol_guess=1):
    res = h.Fit("gaus", "LS", "", mean_guess-2*resol_guess, mean_guess+2*resol_guess)
    # Resolution should be corrected for the response (i.e as if response was brutally adjusted per energy)
    return (res.Parameter(1), res.Parameter(2)/(1+res.Parameter(1)))

def write_output(results, out_file):
    with open(out_file, 'w') as csvfile:
        fieldnames = ['E_truth', 'ClusterType', 'NeventsInit', 'NeventsPass', 'E_response', 'E_resol', 'Theta_response', 'Theta_resol', 'Phi_response', 'Phi_resol']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        print(f"results for csv -- len = {len(results)}") # Alex hat gesagt ich soll das machen
        for res in results:
            writer.writerow(dict(zip(fieldnames, res)))


if __name__ == "__main__":
    main()

    #ROOT.gInterpreter.Declare("""
    #float generatedE(const ROOT::RDF::RSampleInfo &id) {
        #TString s(id.AsString());
        #TPRegexp tpr("_(\\\\d+)\\\\.root");
        #TString ss = s(tpr);
        #TString e_string = ss(1, ss.Index('.')-1);
        #return e_string.Atof() / 1000.;
    #}
    #""")


