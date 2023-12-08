import os
import copy

from GaudiKernel.SystemOfUnits import MeV, GeV, tesla

use_pythia = False
addNoise = False
dumpGDML = False

# Input for simulations (momentum is expected in GeV!)
# Parameters for the particle gun simulations, dummy if use_pythia is set
# to True
# theta from 80 to 100 degrees corresponds to -0.17 < eta < 0.17 
# reminder: cell granularity in theta = 0.5625 degrees
# (in strips: 0.5625/4=0.14)

#Nevts = 20000
#Nevts = 50
#Nevts = 1
Nevts=1000
#momentum = 100 # in GeV
momentum = 50 # in GeV
#momentum = 10 # in GeV
_pi = 3.14159
#thetaMin = 40 # degrees
#thetaMax = 140 # degrees
thetaMin = 90 # degrees
thetaMax = 90 # degrees
phiMin = _pi/2.
phiMax = _pi/2.
#phiMin = 0
#phiMax = 2 * _pi

# particle type: 11 electron, 13 muon, 22 photon, 111 pi0, 211 pi+
pdgCode = 11
#pdgCode = 22
#pdgCode = 111

# Set to true if history from Geant4 decays is needed (e.g. to get the
# photons from pi0) 
saveG4Hist = False
if (pdgCode == 111): saveG4Hist = True

magneticField = False


from Gaudi.Configuration import *

from Configurables import FCCDataSvc
podioevent  = FCCDataSvc("EventDataSvc")

################## Particle gun setup

from Configurables import GenAlg
genAlg = GenAlg()
if use_pythia:
    from Configurables import PythiaInterface
    pythia8gentool = PythiaInterface()
    pythia8gentool.pythiacard = os.path.join(
        os.environ.get('PWD', ''),
        "MCGeneration/ee_Zgamma_inclusive.cmd"
    )
    #pythia8gentool.pythiacard = "MCGeneration/ee_Z_ee.cmd"
    pythia8gentool.printPythiaStatistics = False
    pythia8gentool.pythiaExtraSettings = [""]
    genAlg.SignalProvider = pythia8gentool
    # to smear the primary vertex position:
    #from Configurables import GaussSmearVertex
    #smeartool = GaussSmearVertex()
    #smeartool.xVertexSigma =   0.5*units.mm
    #smeartool.yVertexSigma =   0.5*units.mm
    #smeartool.zVertexSigma =  40.0*units.mm
    #smeartool.tVertexSigma = 180.0*units.picosecond
    #genAlg.VertexSmearingTool = smeartool
else:
    from Configurables import  MomentumRangeParticleGun
    pgun = MomentumRangeParticleGun("ParticleGun_Electron")
    pgun.PdgCodes = [pdgCode]
    pgun.MomentumMin = momentum * GeV
    pgun.MomentumMax = momentum * GeV
    pgun.PhiMin = phiMin
    pgun.PhiMax = phiMax
    pgun.ThetaMin = thetaMin * _pi / 180.
    pgun.ThetaMax = thetaMax * _pi / 180.
    genAlg.SignalProvider = pgun

genAlg.hepmc.Path = "hepmc"

from Configurables import HepMCToEDMConverter
hepmc_converter = HepMCToEDMConverter()
hepmc_converter.hepmc.Path="hepmc"
genParticlesOutputName = "genParticles"
hepmc_converter.GenParticles.Path = genParticlesOutputName
hepmc_converter.hepmcStatusList = []
hepmc_converter.OutputLevel = INFO

################## Simulation setup
# Detector geometry
from Configurables import GeoSvc
geoservice = GeoSvc("GeoSvc")
# if FCC_DETECTORS is empty, this should use relative path to working directory
path_to_detector = os.environ.get("FCCDETECTORS", "")
print(path_to_detector)
detectors_to_use=[
    'Detector/DetFCCeeIDEA-LAr/compact/FCCee_DectMaster_thetamodulemerged.xml',
]
# prefix all xmls with path_to_detector
geoservice.detectors = [
    os.path.join(path_to_detector, _det) for _det in detectors_to_use
]
geoservice.OutputLevel = INFO

# Geant4 service
# Configures the Geant simulation: geometry, physics list and user actions
from Configurables import (
    SimG4FullSimActions, SimG4Alg,
    SimG4PrimariesFromEdmTool, SimG4SaveParticleHistory
)
actions = SimG4FullSimActions()

if saveG4Hist:
    actions.enableHistory=True
    actions.energyCut = 1.0 * GeV
    saveHistTool = SimG4SaveParticleHistory("saveHistory")

from Configurables import SimG4Svc
geantservice = SimG4Svc(
    "SimG4Svc",
    detector='SimG4DD4hepDetector',
    physicslist="SimG4FtfpBert",
    actions=actions
)

# from Configurables import GeoToGdmlDumpSvc
if dumpGDML:
    from Configurables import GeoToGdmlDumpSvc
    gdmldumpservice = GeoToGdmlDumpSvc("GeoToGdmlDumpSvc")

# Fixed seed to have reproducible results, change it for each job if you
# split one production into several jobs
# Mind that if you leave Gaudi handle random seed and some job start within
# the same second (very likely) you will have duplicates
geantservice.randomNumbersFromGaudi = False
geantservice.seedValue = 4242

# Range cut
geantservice.g4PreInitCommands += ["/run/setCut 0.1 mm"]

# Magnetic field
from Configurables import SimG4ConstantMagneticFieldTool
if magneticField == 1:
    field = SimG4ConstantMagneticFieldTool(
        "SimG4ConstantMagneticFieldTool",
        FieldComponentZ=-2*tesla,
        FieldOn=True,
        IntegratorStepper="ClassicalRK4"
    )
else:
    field = SimG4ConstantMagneticFieldTool(
        "SimG4ConstantMagneticFieldTool",
        FieldOn=False
    )

# Geant4 algorithm
# Translates EDM to G4Event, passes the event to G4, writes out outputs
# via tools and a tool that saves the calorimeter hits

# Detector readouts
# ECAL
ecalBarrelReadoutName = "ECalBarrelModuleThetaMerged"
ecalBarrelReadoutName2 = "ECalBarrelModuleThetaMerged2"
ecalEndcapReadoutName = "ECalEndcapPhiEta"
# HCAL
hcalBarrelReadoutName = "HCalBarrelReadout"
hcalEndcapReadoutName = "HCalEndcapReadout"

# Configure saving of calorimeter hits
ecalBarrelHitsName = "ECalBarrelPositionedHits"
from Configurables import SimG4SaveCalHits
saveECalBarrelTool = SimG4SaveCalHits(
    "saveECalBarrelHits",
    readoutName = ecalBarrelReadoutName,
    OutputLevel = INFO
)
saveECalBarrelTool.CaloHits.Path = ecalBarrelHitsName

saveECalEndcapTool = SimG4SaveCalHits(
    "saveECalEndcapHits",
    readoutName = ecalEndcapReadoutName
)
saveECalEndcapTool.CaloHits.Path = "ECalEndcapHits"

saveHCalTool = SimG4SaveCalHits(
    "saveHCalBarrelHits",
    readoutName = hcalBarrelReadoutName
)
saveHCalTool.CaloHits.Path = "HCalBarrelPositionedHits"

#saveHCalEndcapTool = SimG4SaveCalHits(
#    "saveHCalEndcapHits",
#    readoutName = hcalEndcapReadoutName
#)
#saveHCalEndcapTool.CaloHits.Path = "HCalEndcapHits"

# next, create the G4 algorithm, giving the list of names of tools ("XX/YY")
from Configurables import SimG4PrimariesFromEdmTool
particle_converter = SimG4PrimariesFromEdmTool("EdmConverter")
particle_converter.GenParticles.Path = genParticlesOutputName

from Configurables import SimG4Alg
outputTools = [
    saveECalBarrelTool,
    saveHCalTool,
    saveECalEndcapTool,
    #saveHCalEndcapTool
]
if saveG4Hist:
    outputTools += [saveHistTool]

geantsim = SimG4Alg("SimG4Alg",
                    outputs = outputTools,
                    eventProvider=particle_converter,
                    OutputLevel=INFO)

############## Digitization (Merging hits into cells, EM scale calibration)
# EM scale calibration (sampling fraction)
from Configurables import CalibrateInLayersTool
calibEcalBarrel = CalibrateInLayersTool("CalibrateECalBarrel",
                                        samplingFraction = [0.36599110182660616] * 1 + [0.1366222373338866] * 1 + [0.1452035173747207] * 1 + [0.1504319190969367] * 1 + [0.15512713637727382] * 1 + [0.1592916726494782] * 1 + [0.16363478857307595] * 1 + [0.1674697333180323] * 1 + [0.16998205747422343] * 1 + [0.1739146363733975] * 1 + [0.17624609543603845] * 1 + [0.1768613530850488] * 1,
                                        readoutName = ecalBarrelReadoutName,
                                        layerFieldName = "layer")

from Configurables import CalibrateCaloHitsTool
calibHcells = CalibrateCaloHitsTool("CalibrateHCal", invSamplingFraction="31.4")
calibEcalEndcap = CalibrateCaloHitsTool("CalibrateECalEndcap", invSamplingFraction="4.27")
calibHcalEndcap = CalibrateCaloHitsTool("CalibrateHCalEndcap", invSamplingFraction="31.7")

# Create cells in ECal barrel
# 1. step - merge hits into cells with theta and module segmentation
# (module is a 'physical' cell i.e. lead + LAr + PCB + LAr +lead)
# 2. step - rewrite the cellId using the merged theta-module segmentation
# (merging several modules and several theta readout cells).
# Add noise at this step if you derived the noise already assuming merged cells

# Step 1: merge hits into cells according to initial segmentation
from Configurables import CreateCaloCells
EcalBarrelCellsName = "ECalBarrelCells"
createEcalBarrelCells = CreateCaloCells("CreateECalBarrelCells",
                                        doCellCalibration=True,
                                        calibTool = calibEcalBarrel,
                                        addCellNoise=False,
                                        filterCellNoise=False,
                                        addPosition=True,
                                        OutputLevel=INFO,
                                        hits=ecalBarrelHitsName,
                                        cells=EcalBarrelCellsName)

# Step 2a: compute new cellID of cells based on new readout
# (merged module-theta segmentation with variable merging vs layer)
from Configurables import RedoSegmentation
resegmentEcalBarrel = RedoSegmentation("ReSegmentationEcal",
                                       # old bitfield (readout)
                                       oldReadoutName = ecalBarrelReadoutName,
                                       # specify which fields are going to be altered (deleted/rewritten)
                                       oldSegmentationIds = ["module", "theta"],
                                       # new bitfield (readout), with new segmentation (merged modules and theta cells)
                                       newReadoutName = ecalBarrelReadoutName2,
                                       OutputLevel = INFO,
                                       debugPrint = 200,
                                       inhits = EcalBarrelCellsName,
                                       outhits = "ECalBarrelCellsMerged")

# Step 2b: merge new cells with same cellID together
# do not apply cell calibration again since cells were already
# calibrated in Step 1
EcalBarrelCellsName2 = "ECalBarrelCells2"
createEcalBarrelCells2 = CreateCaloCells("CreateECalBarrelCells2",
                                         doCellCalibration=False,
                                         addCellNoise=False,
                                         filterCellNoise=False,
                                         OutputLevel=INFO,
                                         hits="ECalBarrelCellsMerged",
                                         cells=EcalBarrelCellsName2)

# Add to Ecal barrel cells the position information
# (good for physics, all coordinates set properly)
from Configurables import CellPositionsECalBarrelModuleThetaSegTool
from Configurables import CreateCaloCellPositionsFCCee

cellPositionEcalBarrelTool = CellPositionsECalBarrelModuleThetaSegTool(
    "CellPositionsECalBarrel",
    readoutName = ecalBarrelReadoutName,
    OutputLevel = INFO
)
createEcalBarrelPositionedCells = CreateCaloCellPositionsFCCee(
    "ECalBarrelPositionedCells",
    OutputLevel = INFO
)
createEcalBarrelPositionedCells.positionsTool = cellPositionEcalBarrelTool
createEcalBarrelPositionedCells.hits.Path = EcalBarrelCellsName
createEcalBarrelPositionedCells.positionedHits.Path = "ECalBarrelPositionedCells"

cellPositionEcalBarrelTool2= CellPositionsECalBarrelModuleThetaSegTool(
    "CellPositionsECalBarrel2",
    readoutName = ecalBarrelReadoutName2,
    OutputLevel = INFO
)
createEcalBarrelPositionedCells2 = CreateCaloCellPositionsFCCee(
    "ECalBarrelPositionedCells2",
    OutputLevel = INFO
)
createEcalBarrelPositionedCells2.positionsTool = cellPositionEcalBarrelTool2
createEcalBarrelPositionedCells2.hits.Path = EcalBarrelCellsName2
createEcalBarrelPositionedCells2.positionedHits.Path = "ECalBarrelPositionedCells2"

# Create cells in HCal
# 1. step - merge hits into cells with the default readout
createHcalBarrelCells = CreateCaloCells("CreateHCaloCells",
                                        doCellCalibration=True,
                                        calibTool=calibHcells,
                                        addCellNoise = False,
                                        filterCellNoise = False,
                                        OutputLevel = INFO,
                                        hits="HCalBarrelHits",
                                        cells="HCalBarrelCells")

# Create cells in ECal endcap
createEcalEndcapCells = CreateCaloCells("CreateEcalEndcapCaloCells",
                                        doCellCalibration=True,
                                        calibTool=calibEcalEndcap,
                                        addCellNoise=False,
                                        filterCellNoise=False,
                                        OutputLevel=INFO)
createEcalEndcapCells.hits.Path="ECalEndcapHits"
createEcalEndcapCells.cells.Path="ECalEndcapCells"

#createHcalEndcapCells = CreateCaloCells("CreateHcalEndcapCaloCells",
#                                    doCellCalibration=True,
#                                    calibTool=calibHcalEndcap,
#                                    addCellNoise=False,
#                                    filterCellNoise=False,
#                                    OutputLevel=INFO)
#createHcalEndcapCells.hits.Path="HCalEndcapHits"
#createHcalEndcapCells.cells.Path="HCalEndcapCells"


#Empty cells for parts of calorimeter not implemented yet
from Configurables import CreateEmptyCaloCellsCollection
createemptycells = CreateEmptyCaloCellsCollection("CreateEmptyCaloCells")
createemptycells.cells.Path = "emptyCaloCells"

# Produce sliding window clusters
from Configurables import CaloTowerTool
towers = CaloTowerTool("towers",
                       deltaEtaTower = 0.01, deltaPhiTower = 2*_pi/768.,
                       radiusForPosition = 2160 + 40 / 2.0,
                       ## ecalBarrelReadoutName = ecalBarrelReadoutNamePhiEta,
                       ecalBarrelReadoutName = ecalBarrelReadoutName,
                       ecalEndcapReadoutName = ecalEndcapReadoutName,
                       ecalFwdReadoutName = "",
                       hcalBarrelReadoutName = hcalBarrelReadoutName,
                       hcalExtBarrelReadoutName = "",
                       hcalEndcapReadoutName = "",
                       hcalFwdReadoutName = "",
                       OutputLevel = INFO)
towers.ecalBarrelCells.Path = EcalBarrelCellsName
towers.ecalEndcapCells.Path = "ECalEndcapCells"
towers.ecalFwdCells.Path = "emptyCaloCells"
towers.hcalBarrelCells.Path = "emptyCaloCells"
towers.hcalExtBarrelCells.Path = "emptyCaloCells"
towers.hcalEndcapCells.Path = "emptyCaloCells"
towers.hcalFwdCells.Path = "emptyCaloCells"

# Cluster variables
windE = 9
windP = 17
posE = 5
posP = 11
dupE = 7
dupP = 13
finE = 9
finP = 17
# Minimal energy to create a cluster in GeV (FCC-ee detectors have to reconstruct low energy particles)
threshold = 0.040

from Configurables import CreateCaloClustersSlidingWindow
createClusters = CreateCaloClustersSlidingWindow("CreateClusters",
                                                 towerTool = towers,
                                                 nEtaWindow = windE, nPhiWindow = windP,
                                                 nEtaPosition = posE, nPhiPosition = posP,
                                                 nEtaDuplicates = dupE, nPhiDuplicates = dupP,
                                                 nEtaFinal = finE, nPhiFinal = finP,
                                                 energyThreshold = threshold,
                                                 energySharingCorrection = False,
                                                 attachCells = True,
                                                 OutputLevel = INFO
                                                 )
createClusters.clusters.Path = "CaloClusters"
createClusters.clusterCells.Path = "CaloClusterCells"

createEcalBarrelPositionedCaloClusterCells = CreateCaloCellPositionsFCCee(
    "ECalBarrelPositionedCaloClusterCells",
    OutputLevel = INFO
)
createEcalBarrelPositionedCaloClusterCells.positionsTool = cellPositionEcalBarrelTool
createEcalBarrelPositionedCaloClusterCells.hits.Path = "CaloClusterCells"
createEcalBarrelPositionedCaloClusterCells.positionedHits.Path = "PositionedCaloClusterCells"

from Configurables import CorrectCaloClusters
correctCaloClusters = CorrectCaloClusters("correctCaloClusters",
                                          inClusters = createClusters.clusters.Path,
                                          outClusters = "Corrected"+createClusters.clusters.Path,
                                          numLayers = [12],
                                          firstLayerIDs = [0],
                                          lastLayerIDs = [11],
                                          ## readoutNames = [ecalBarrelReadoutNamePhiEta],
                                          readoutNames = [ecalBarrelReadoutName],
                                          #upstreamParameters = [[0.02729094887360858, -1.378665489864182, -68.40424543618059, 3.6930827214130053, -5528.714729126099, -1630.7911298009794]],
                                          upstreamParameters = [[0.02729094887360858, -1.378665489864182, -68.40424543618059, 3.6930827214130053, -5528.714729126099, -1630.7911298009794]],
                                          upstreamFormulas = [['[0]+[1]/(x-[2])', '[0]+[1]/(x-[2])']],
                                          #downstreamParameters = [[-0.0032351643028483354, 0.006597484738888312, 0.8972024981692965, -1.0207168610322181, 0.017878133854084398, 9.108099243443101]],
                                          downstreamParameters = [[-0.0032351643028483354, 0.006597484738888312, 0.8972024981692965, -1.0207168610322181, 0.017878133854084398, 9.108099243443101]],
                                          downstreamFormulas = [['[0]+[1]*x', '[0]+[1]/sqrt(x)', '[0]+[1]/x']],
                                          OutputLevel = INFO
                                          )

# TOPO CLUSTERS PRODUCTION
from Configurables import (
    CaloTopoClusterInputTool, CaloTopoClusterFCCee,
    TopoCaloNeighbours, TopoCaloNoisyCells
)
createTopoInput = CaloTopoClusterInputTool("CreateTopoInput",
                                           ecalBarrelReadoutName = ecalBarrelReadoutName,
                                           #ecalBarrelReadoutName = ecalBarrelReadoutName2,
                                           ecalEndcapReadoutName = "",
                                           ecalFwdReadoutName = "",
                                           hcalBarrelReadoutName = "",
                                           hcalExtBarrelReadoutName = "",
                                           hcalEndcapReadoutName = "",
                                           hcalFwdReadoutName = "",
                                           OutputLevel = INFO)

createTopoInput.ecalBarrelCells.Path = "ECalBarrelPositionedCells"
#createTopoInput.ecalBarrelCells.Path = "ECalBarrelPositionedCells2"
createTopoInput.ecalEndcapCells.Path = "emptyCaloCells" 
createTopoInput.ecalFwdCells.Path = "emptyCaloCells" 
createTopoInput.hcalBarrelCells.Path = "emptyCaloCells" 
createTopoInput.hcalExtBarrelCells.Path = "emptyCaloCells" 
createTopoInput.hcalEndcapCells.Path = "emptyCaloCells"
createTopoInput.hcalFwdCells.Path = "emptyCaloCells"

readNeighboursMap = TopoCaloNeighbours("ReadNeighboursMap",
                                       fileName = os.environ['FCCBASEDIR']+"/LAr_scripts/data/neighbours_map_barrel_thetamodulemerged.root",
                                       OutputLevel = INFO)

#Noise levels per cell
readNoisyCellsMap = TopoCaloNoisyCells("ReadNoisyCellsMap",
                                       fileName = os.environ['FCCBASEDIR']+"/LAr_scripts/data/cellNoise_map_electronicsNoiseLevel_thetamodulemerged.root",
                                       OutputLevel = INFO)

createTopoClusters = CaloTopoClusterFCCee("CreateTopoClusters",
                                          TopoClusterInput = createTopoInput,
                                          #expects neighbours map from cellid->vec < neighbourIds >
                                          neigboursTool = readNeighboursMap,
                                          #tool to get noise level per cellid
                                          noiseTool = readNoisyCellsMap,
                                          #cell positions tools for all sub - systems
                                          positionsECalBarrelTool = cellPositionEcalBarrelTool,
                                          #positionsECalBarrelTool = cellPositionEcalBarrelTool2,
                                          #positionsHCalBarrelTool = HCalBcells,
                                          #positionsHCalExtBarrelTool = HCalExtBcells,
                                          #positionsEMECTool = EMECcells,
                                          #positionsHECTool = HECcells,
                                          #positionsEMFwdTool = ECalFwdcells,
                                          #positionsHFwdTool = HCalFwdcells,
                                          seedSigma = 4,
                                          neighbourSigma = 2,
                                          lastNeighbourSigma = 0,
                                          OutputLevel = INFO)
createTopoClusters.clusters.Path ="CaloTopoClusters" 
createTopoClusters.clusterCells.Path = "CaloTopoClusterCells"

createEcalBarrelPositionedCaloTopoClusterCells = CreateCaloCellPositionsFCCee(
    "ECalBarrelPositionedCaloTopoClusterCells",
    OutputLevel = INFO
)
#createEcalBarrelPositionedCaloTopoClusterCells.positionsTool = cellPositionEcalBarrelTool2
createEcalBarrelPositionedCaloTopoClusterCells.positionsTool = cellPositionEcalBarrelTool
createEcalBarrelPositionedCaloTopoClusterCells.hits.Path = "CaloTopoClusterCells"
createEcalBarrelPositionedCaloTopoClusterCells.positionedHits.Path = "PositionedCaloTopoClusterCells"

correctCaloTopoClusters = CorrectCaloClusters(
    "correctCaloTopoClusters",
    inClusters = createTopoClusters.clusters.Path,
    outClusters = "Corrected"+createTopoClusters.clusters.Path,
    numLayers = [12],
    firstLayerIDs = [0],
    lastLayerIDs = [11],
    ## readoutNames = [ecalBarrelReadoutNamePhiEta],
    readoutNames = [ecalBarrelReadoutName],
    #upstreamParameters = [[0.02729094887360858, -1.378665489864182, -68.40424543618059, 3.6930827214130053, -5528.714729126099, -1630.7911298009794]],
    upstreamParameters = [[0.02729094887360858, -1.378665489864182, -68.40424543618059, 3.6930827214130053, -5528.714729126099, -1630.7911298009794]],
    upstreamFormulas = [['[0]+[1]/(x-[2])', '[0]+[1]/(x-[2])']],
    #downstreamParameters = [[-0.0032351643028483354, 0.006597484738888312, 0.8972024981692965, -1.0207168610322181, 0.017878133854084398, 9.108099243443101]],
    downstreamParameters = [[-0.0032351643028483354, 0.006597484738888312, 0.8972024981692965, -1.0207168610322181, 0.017878133854084398, 9.108099243443101]],
    downstreamFormulas = [['[0]+[1]*x', '[0]+[1]/sqrt(x)', '[0]+[1]/x']],
    OutputLevel = INFO
)

################ Output
from Configurables import PodioOutput
out = PodioOutput("out",
                  OutputLevel=INFO)

#out.outputCommands = ["keep *"]
#out.outputCommands = ["keep *", "drop ECalBarrelHits", "drop HCal*", "drop ECalBarrelCellsStep*", "drop ECalBarrelPositionedHits", "drop emptyCaloCells", "drop CaloClusterCells"]
#out.outputCommands = ["keep *", "drop ECalBarrelHits", "drop HCal*", "drop ECalBarrelCellsStep*", "drop ECalBarrelPositionedHits", "drop emptyCaloCells", "drop CaloClusterCells", "drop %s"%EcalBarrelCellsName, "drop %s"%createEcalBarrelPositionedCells.positionedHits.Path]
#out.outputCommands = ["keep *", "drop ECalBarrelHits", "drop HCal*", "drop *ells*", "drop ECalBarrelPositionedHits", "drop emptyCaloCells"]
#out.outputCommands = ["keep *", "drop HCal*", "drop ECalBarrel*", "drop emptyCaloCells"]
out.outputCommands = ["keep *", "drop HCal*", "drop emptyCaloCells"]

import uuid
# out.filename = "root/output_fullCalo_SimAndDigi_withTopoCluster_MagneticField_"+str(magneticField)+"_pMin_"+str(momentum*1000)+"_MeV"+"_ThetaMinMax_"+str(thetaMin)+"_"+str(thetaMax)+"_pdgId_"+str(pdgCode)+"_pythia"+str(use_pythia)+"_Noise"+str(addNoise)+".root"
out.filename = "./root_merge/output_evts_"+str(Nevts)+"_pdg_"+str(pdgCode)+"_"+str(momentum)+"_GeV"+"_ThetaMinMax_"+str(thetaMin)+"_"+str(thetaMax)+"_PhiMinMax_"+str(phiMin)+"_"+str(phiMax)+"_MagneticField_"+str(magneticField)+"_Noise"+str(addNoise)+".root"

#CPU information
from Configurables import AuditorSvc, ChronoAuditor
chra = ChronoAuditor()
audsvc = AuditorSvc()
audsvc.Auditors = [chra]
genAlg.AuditExecute = True
hepmc_converter.AuditExecute = True
geantsim.AuditExecute = True
createEcalBarrelCells.AuditExecute = True
#createHcalBarrelCells.AuditExecute = True
createEcalBarrelPositionedCells.AuditExecute = True
createTopoClusters.AuditExecute = True 
out.AuditExecute = True

from Configurables import EventCounter
event_counter = EventCounter('event_counter')
event_counter.Frequency = 10

ExtSvc = [geoservice, podioevent, geantservice, audsvc]
if dumpGDML:
    ExtSvc += [gdmldumpservice]

from Configurables import ApplicationMgr
ApplicationMgr(
    TopAlg = [
              event_counter,
              genAlg,
              hepmc_converter,
              geantsim,
              createEcalBarrelCells,
              createEcalBarrelPositionedCells,
              resegmentEcalBarrel,
              createEcalBarrelCells2,
              createEcalBarrelPositionedCells2,
              createEcalEndcapCells,
              ## createHcalBarrelCells,
              ## createHcalEndcapCells,
              createemptycells,
              ## createClusters,
              ## createEcalBarrelPositionedCaloClusterCells,
              ## correctCaloClusters,
              createTopoClusters,
              createEcalBarrelPositionedCaloTopoClusterCells,
              correctCaloTopoClusters,
              out
              ],
    EvtSel = 'NONE',
    EvtMax = Nevts,
    ExtSvc = ExtSvc,
    StopOnSignal = True,
 )
