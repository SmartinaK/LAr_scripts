print("start script")
import os
from Gaudi.Configuration import *


# Detector geometry
from Configurables import GeoSvc
geoservice = GeoSvc("GeoSvc")
# if FCC_DETECTORS is empty, this should use relative path to working directory
path_to_detector = os.environ.get("FCCDETECTORS", "")
print(path_to_detector)
detectors_to_use=[
    'Detector/DetFCCeeIDEA-LAr/compact/FCCee_DectMaster_thetamodulemerged.xml',
    #'Detector/DetFCCeeIDEA-LAr/compact/FCCee_DectMaster.xml',
]

# prefix all xmls with path_to_detector
geoservice.detectors = [os.path.join(path_to_detector, _det) for _det in detectors_to_use]
geoservice.OutputLevel = VERBOSE

# Geant4 service
# Configures the Geant simulation: geometry, physics list and user actions
from Configurables import CreateFCCeeCaloNeighbours
print("execute CreateFCCeeCaloNeighbours()")
neighbours = CreateFCCeeCaloNeighbours("neighbours", 
                                       outputFileName = "neighbours_map_barrel_thetamodulemerged.root",
                                       readoutNamesModuleTheta = ["ECalBarrelModuleThetaMerged"],
#                                       readoutNamesModuleTheta = ["ECalBarrelModuleThetaMerged2"],
                                       systemNamesModuleTheta = ["system"],
                                       systemValuesModuleTheta = [4],
                                       activeFieldNamesModuleTheta = ["layer"],
                                       activeVolumesNumbers = [12],
                                       #activeVolumesTheta = [1.2524, 1.2234, 1.1956, 1.1561, 1.1189, 1.0839, 1.0509, 0.9999, 0.9534, 0.91072],
                                       includeDiagonalCells = False,
                                       readoutNamesVolumes = [],
                                       connectBarrels = False, 
                                       OutputLevel = VERBOSE)
print(neighbours)

# ApplicationMgr
from Configurables import ApplicationMgr
ApplicationMgr( TopAlg = [],
                EvtSel = 'NONE',
                EvtMax   = 1,
                # order is important, as GeoSvc is needed by G4SimSvc
                ExtSvc = [geoservice, neighbours],
                OutputLevel=VERBOSE
)
