import os
from Gaudi.Configuration import *

from GaudiKernel.SystemOfUnits import MeV, GeV

# Electron momentum in GeV
momentum = 10
# Theta min and max in degrees
thetaMin = 90.
thetaMax = 90.

# Data service
from Configurables import FCCDataSvc
podioevent  = FCCDataSvc("EventDataSvc")

################## Particle gun setup
_pi = 3.14159

from Configurables import  MomentumRangeParticleGun
pgun = MomentumRangeParticleGun("ParticleGun_Photon")
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
genParticlesOutputName = "genParticles"
hepmc_converter.GenParticles.Path = genParticlesOutputName
hepmc_converter.hepmcStatusList = []

# DD4hep geometry service
from Configurables import GeoSvc
geoservice = GeoSvc("GeoSvc",
                    OutputLevel = INFO)

path_to_detector = os.environ.get("FCCDETECTORS", "")
detectors_to_use=[ 
    'Detector/DetFCCeeIDEA-LAr/compact/FCCee_DectEmptyMaster.xml',
    #'Detector/DetFCCeeIDEA-LAr/compact/FCCee_DectMaster.xml',
    #'Detector/DetFCCeeECalInclined/compact/original_FCCee_ECalBarrel_calibration.xml',
    'Detector/DetFCCeeECalInclined/compact/FCCee_ECalBarrel_thetamodulemerged_calibration.xml',
    ]
geoservice.detectors = [os.path.join(path_to_detector, _det) for _det in detectors_to_use]

# Geant4 service
# Configures the Geant simulation: geometry, physics list and user actions
from Configurables import SimG4Svc
geantservice = SimG4Svc("SimG4Svc", detector='SimG4DD4hepDetector', physicslist="SimG4FtfpBert", actions="SimG4FullSimActions")
geantservice.g4PostInitCommands += ["/run/setCut 0.1 mm"]
geantservice.randomNumbersFromGaudi = False
geantservice.seedValue = 4242

# Geant4 algorithm
# Translates EDM to G4Event, passes the event to G4, writes out outputs via tools
# and a tool that saves the calorimeter hits
ecalBarrelHitsName = "ECalBarrelPositionedHits"
from Configurables import SimG4Alg, SimG4SaveCalHits
saveECalBarrelTool = SimG4SaveCalHits("saveECalBarrelHits",readoutNames = ["ECalBarrelModuleThetaMerged"])
saveECalBarrelTool.CaloHits.Path = ecalBarrelHitsName

from Configurables import SimG4PrimariesFromEdmTool
particle_converter = SimG4PrimariesFromEdmTool("EdmConverter")
particle_converter.GenParticles.Path = genParticlesOutputName

# next, create the G4 algorithm, giving the list of names of tools ("XX/YY")
geantsim = SimG4Alg("SimG4Alg",
                    outputs= [saveECalBarrelTool],
                    eventProvider = particle_converter,
                    OutputLevel = INFO)

from Configurables import SamplingFractionInLayers
hist = SamplingFractionInLayers("hists",
                                 energyAxis = momentum,
                                 readoutName = "ECalBarrelModuleThetaMerged",
                                 layerFieldName = "layer",
                                 activeFieldName = "type",
                                 activeFieldValue = 0,
                                 numLayers = 12,
                                 OutputLevel = INFO)
hist.deposits.Path = ecalBarrelHitsName

THistSvc().Output = ["rec DATAFILE='histSF_fccee_inclined.root' TYP='ROOT' OPT='RECREATE'"]
THistSvc().PrintAll=True
THistSvc().AutoSave=True
THistSvc().AutoFlush=False
THistSvc().OutputLevel=INFO

#CPU information
from Configurables import AuditorSvc, ChronoAuditor
chra = ChronoAuditor()
audsvc = AuditorSvc()
audsvc.Auditors = [chra]
geantsim.AuditExecute = True
hist.AuditExecute = True

from Configurables import PodioOutput
### PODIO algorithm
out = PodioOutput("out",OutputLevel=INFO)
out.outputCommands = ["drop *"]
out.filename = "fccee_samplingFraction_inclinedEcal.root"

from Configurables import EventCounter
event_counter = EventCounter('event_counter')
event_counter.Frequency = 10

# ApplicationMgr
from Configurables import ApplicationMgr
ApplicationMgr( TopAlg = [event_counter, genalg_pgun, hepmc_converter, geantsim, hist, out],
                EvtSel = 'NONE',
                EvtMax = 100,
                # order is important, as GeoSvc is needed by G4SimSvc
                ExtSvc = [geoservice, podioevent, geantservice, audsvc],
                OutputLevel = INFO,
                StopOnSignal = True
)
