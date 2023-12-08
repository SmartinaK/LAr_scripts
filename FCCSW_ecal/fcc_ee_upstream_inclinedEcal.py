from Gaudi.Configuration import *

from GaudiKernel.SystemOfUnits import MeV, GeV

# Electron momentum in GeV
momentum = 50
# Theta min and max in degrees                                                                                                      
thetaMin = 90.
thetaMax = 90.

# Data service
from Configurables import FCCDataSvc
podioevent = FCCDataSvc("EventDataSvc")

################## Particle gun setup
_pi = 3.14159

from Configurables import  MomentumRangeParticleGun
pgun = MomentumRangeParticleGun("ParticleGun_Electron")
pgun.PdgCodes = [22]
pgun.MomentumMin = momentum * GeV
pgun.MomentumMax = momentum * GeV
pgun.PhiMin = 0
pgun.PhiMax = 2 * _pi
# theta = 90 degrees (eta = 0)
pgun.ThetaMin = thetaMin * _pi / 180.       
pgun.ThetaMax = thetaMax * _pi / 180.       

from Configurables import GenAlg
genalg_pgun = GenAlg()
genalg_pgun.SignalProvider = pgun 
genalg_pgun.hepmc.Path = "hepmc"

from Configurables import HepMCToEDMConverter
hepmc_converter = HepMCToEDMConverter()
hepmc_converter.hepmc.Path="hepmc"
hepmc_converter.GenParticles.Path="GenParticles"

# DD4hep geometry service
from Configurables import GeoSvc
from os import environ, path
detector_path = environ.get("FCCDETECTORS", "")
detectors = ['Detector/DetFCCeeIDEA-LAr/compact/FCCee_DectEmptyMaster.xml',
             'Detector/DetFCCeeECalInclined/compact/FCCee_ECalBarrel_thetamodulemerged_upstream.xml']
geoservice = GeoSvc("GeoSvc", detectors=[path.join(detector_path, detector) for detector in detectors],
                    OutputLevel = WARNING)

# Geant4 service
# Configures the Geant simulation: geometry, physics list and user actions
from Configurables import SimG4Svc
geantservice = SimG4Svc("SimG4Svc", detector='SimG4DD4hepDetector', physicslist="SimG4FtfpBert", actions="SimG4FullSimActions")
geantservice.g4PostInitCommands += ["/run/setCut 0.1 mm"]

# Fixed seed to have reproducible results, change it for each job if you split one production into several jobs
# Mind that if you leave Gaudi handle random seed and some job start within the same second (very likely) you will have duplicates
geantservice.randomNumbersFromGaudi = False
geantservice.seedValue = 4242

# Geant4 algorithm
# Translates EDM to G4Event, passes the event to G4, writes out outputs via tools
# and a tool that saves the calorimeter hits
from Configurables import SimG4Alg, SimG4SaveCalHits
saveecaltool = SimG4SaveCalHits("saveECalBarrelHits",readoutNames = ["ECalBarrelModuleThetaMerged"])
saveecaltool.CaloHits.Path = "ECalBarrelHits"

from Configurables import SimG4PrimariesFromEdmTool
particle_converter = SimG4PrimariesFromEdmTool("EdmConverter")
particle_converter.GenParticles.Path = "GenParticles"

# next, create the G4 algorithm, giving the list of names of tools ("XX/YY")
geantsim = SimG4Alg("SimG4Alg",
                    outputs= ["SimG4SaveCalHits/saveECalBarrelHits"],
                    eventProvider = particle_converter,
                    OutputLevel = INFO)

from Configurables import CreateCaloCells
createcellsBarrel = CreateCaloCells("CreateCaloCellsBarrel",
                                    doCellCalibration=False,
                                    addPosition=True,
                                    addCellNoise=False, filterCellNoise=False)
createcellsBarrel.hits.Path="ECalBarrelHits"
createcellsBarrel.cells.Path="ECalBarrelCells"

from Configurables import EnergyInCaloLayers
energy_in_layers = EnergyInCaloLayers("energyInLayers",
                                      readoutName="ECalBarrelModuleThetaMerged",
                                      numLayers = 12,
                                      # sampling fraction is given as the energy correction will be applied on
                                      # calibrated cells
                                      samplingFractions = [0.3632447480841956] * 1 + [0.13187261040190248] * 1 + [0.14349714292943705] * 1 + [0.150266118277841] * 1 + [0.15502683375826457] * 1 + [0.15954408786354762] * 1 + [0.16375302347299436] * 1 + [0.16840384714588075] * 1 + [0.17219540619311383] * 1 + [0.1755068643940401] * 1 + [0.17816980262822366] * 1 + [0.18131266048670405] * 1,
                                      OutputLevel=INFO)
energy_in_layers.deposits.Path = "ECalBarrelCells"
energy_in_layers.particle.Path = "GenParticles"

#CPU information
from Configurables import AuditorSvc, ChronoAuditor
chra = ChronoAuditor()
audsvc = AuditorSvc()
audsvc.Auditors = [chra]
geantsim.AuditExecute = True
#energy_in_layers.AuditExecute = True

from Configurables import PodioOutput
### PODIO algorithm
out = PodioOutput("out",OutputLevel=INFO)
out.outputCommands = ["keep *", "drop ECalBarrelCells", "drop ECalBarrelHits"]
out.filename = "fccee_deadMaterial_inclinedEcal.root"

# ApplicationMgr
from Configurables import ApplicationMgr
ApplicationMgr( TopAlg = [genalg_pgun, hepmc_converter, geantsim, createcellsBarrel, energy_in_layers, out],
                EvtSel = 'NONE',
                EvtMax = 10,
                # order is important, as GeoSvc is needed by G4SimSvc
                ExtSvc = [geoservice, podioevent, geantservice, audsvc],
                OutputLevel = INFO
)
