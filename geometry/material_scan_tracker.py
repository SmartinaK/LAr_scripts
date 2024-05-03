from Configurables import MaterialScan
from Configurables import GeoSvc
import os
from Gaudi.Configuration import INFO


from Configurables import ApplicationMgr
ApplicationMgr().EvtSel = 'None'
ApplicationMgr().EvtMax = 1
ApplicationMgr().OutputLevel = INFO

# DD4hep geometry service
# parse the given xml file
path_to_detectors = os.environ.get("K4GEO", "")
geoservice = GeoSvc("GeoSvc")
detcard = 'FCCee/ALLEGRO/compact/ALLEGRO_o1_v02/ALLEGRO_o1_v02_trackeronly.xml'
# detcard = 'FCCee/ALLEGRO/compact/ALLEGRO_o1_v02/ALLEGRO_o1_v02.xml'
# detcard = 'FCCee/ALLEGRO/compact/ALLEGRO_o1_v02/ALLEGRO_o1_v02_trackeronly.xml'
# detcard = 'FCCee/ALLEGRO/compact/ALLEGRO_o1_v02/ALLEGRO_o1_v02_ecalonly.xml'
geoservice.detectors = [
    os.path.join(path_to_detectors, detcard)
]
geoservice.OutputLevel = INFO
ApplicationMgr().ExtSvc += [geoservice]

# Material scan is done from the interaction point to the end of world volume.
# In order to use other end boundary, please provide the name of a thin, e.g. cylindrical volume.
# For instance adding envelopeName="BoundaryPostCalorimetry" will perform the scan only till the end of calorimetry.
# BoundaryPostCalorimetry is defined in Detector/DetFCChhECalInclined/compact/envelopePreCalo.xml
materialservice = MaterialScan("GeoDump")
materialservice.filename = "out_material_scan_tracker.root"
# materialservice.etaBinning = 0.05
# materialservice.etaMax = 0.9
# full detector down to cos(theta)=0.9952 (theta = 7 degrees)
# materialservice.etaBinning = 0.1
# materialservice.etaMax = 2.8
# barrel down to cos(theta) = 0.766 (theta =  40 degrees)
# materialservice.etaBinning = 0.1
# materialservice.etaMax = 1.0
materialservice.etaBinning = float("0.1")
materialservice.etaMax = float("2.7")
materialservice.nPhiTrials = 10
ApplicationMgr().ExtSvc += [materialservice]
