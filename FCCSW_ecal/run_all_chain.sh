#!/usr/bin/bash

#runname="trapezoid_LKr_1mm_13factor_XGBoost/"
runname="doublestrips_LAr_phitheta_segmentation_photons"

# Remake calibration xml files from the main xml file
# python write_calibration_xml.py ../../FCCDetectors/Detector/DetFCCeeECalInclined/compact/FCCee_ECalBarrel_thetamodulemerged.xml

# Compute the X0 plot
#cd ../geometry
#fccrun material_scan.py
#python material_plot.py
#cd ../FCCSW_ecal/

# Archive the files
#mkdir -vp $runname/geometry
#cp ../../FCCDetectors/Detector/DetFCCeeECalInclined/compact/*.xml $runname/geometry
#cp ../geometry/*png $runname/geometry
#cp ../geometry/*pdf $runname/geometry

# Compute sampling fractions
#python runParallel.py --outDir $runname/sampling --nEvt 1000 --energies 20000 --sampling

# Compute upstream corrections
#python runParallel.py --outDir $runname/upstream --nEvt 1000 --energies 1000 5000 10000 15000 20000 30000 50000 75000 100000 --upstream --SF $runname/sampling/SF.json

# Generate clusters for upstream studies
#python runParallel.py --outDir $runname/upstreamProd --nEvt 1000000 --upstreamProd --SF $runname/sampling/SF.json

# Generate clusters for MVA training
# Only 300k events here. Move up to 3M if needed
#python runParallel.py --outDir $runname/production --nEvt 300000 --production --SF $runname/sampling/SF.json --corrections $runname/upstream/corr_params_1d.json

# Then train the MVA on CaloClusters and CaloTopoClusters
#python training.py CaloClusters -i $runname/production/ --json $runname/upstream/corr_params_1d.json -o $runname/training_calo.json
#python training.py CaloTopoClusters -i $runname/production/ --json $runname/upstream/corr_params_1d.json -o $runname/training_topo.json

# Run clustering algs to compute resolutions
#python runParallel.py --outDir /eos/user/m/mkoppitz/Public/output_simulations/$runname/clusters --nEvt 1000 --energies 500 1000 5000 10000 15000 20000 30000 50000 75000 100000 --clusters --SF $runname/sampling/SF.json --corrections $runname/upstream/corr_params_1d.json

# Compute resolutions and responses
python compute_resolutions.py --inputDir /eos/user/m/mkoppitz/Public/output_simulations/$runname/clusters --outFile /eos/user/m/mkoppitz/Public/output_simulations/$runname/results.csv --clusters CaloClusters CorrectedCaloClusters CaloTopoClusters CorrectedCaloTopoClusters # --# # # # MVAcalibCalo $runname/training_calo.json --MVAcalibTopo $runname/training_topo.json

# And make plots
python plot_resolutions.py --outDir /eos/user/m/mkoppitz/Public/output_simulations/$runname/performancePlots --doFits plot /eos/user/m/mkoppitz/Public/output_simulations/$runname/results.csv --all
python plot_resolutions.py --outDir /eos/user/m/mkoppitz/Public/output_simulations$runname/comparisonPlots --doFits compare clusters CaloClusters CorrectedCaloClusters CaloTopoClusters CorrectedCaloTopoClusters /eos/user/m/mkoppitz/Public/output_simulations$runname/results.csv --all
#python plot_resolutions.py --outDir $runname --doFits compare clusters CaloClusters CorrectedCaloClusters CaloTopoClusters CorrectedCaloTopoClusters CalibratedCaloClusters CalibratedCaloTopoClusters $runname/results.csv --all
