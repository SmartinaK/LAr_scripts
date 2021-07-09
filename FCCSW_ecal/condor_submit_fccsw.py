import subprocess
import subprocess
import sys, os, stat, time, math
import glob
import argparse
from datetime import date
from shutil import copyfile

#__________________________________________________________
def getCommandOutput(command):
    p = subprocess.Popen(command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE,universal_newlines=True)
    (stdout,stderr) = p.communicate()
    return {"stdout":stdout, "stderr":stderr, "returncode":p.returncode}

#__________________________________________________________
def SubmitToCondor(cmd,nbtrials):
    submissionStatus=0
    cmd=cmd.replace('//','/') # -> dav : is it needed?
    for i in range(nbtrials):
        outputCMD = getCommandOutput(cmd)
        stderr=outputCMD["stderr"].split('\n')
        stdout=outputCMD["stdout"].split('\n') # -> dav : is it needed?

        if len(stderr)==1 and stderr[0]=='' :
            print ("------------GOOD SUB ")
            submissionStatus=1
        else:
            print ("++++++++++++ERROR submitting, will retry")
            print("Trial : "+str(i)+" / "+str(nbtrials))
            print("stderr : ",len(stderr))
            print (stderr)

            time.sleep(10)


        if submissionStatus==1:
            return 1

        if i==nbtrials-1:
            print(("failed sumbmitting after: "+str(nbtrials)+" trials, will exit"))
            return 0

def get_condor_submit_header(executable_regex, jobFlavour = 'microcentury'):
    return """executable     = $(filename)
Log            = $(filename).log
Output         = $(filename).out
Error          = $(filename).err
requirements    = ( (OpSysAndVer =?= "CentOS7") && (Machine =!= LastRemoteHost) && (TARGET.has_avx2 =?= True) )
max_retries    = 3
+JobFlavour    = "{0}"
RequestCpus = 1
queue filename matching files {1}
""".format(jobFlavour, executable_regex)

def get_exec_file_header():# assumes you installed FCCSW locally with the 'install' folder at the root of your FCCSW repository
    return """#!/bin/bash
source /cvmfs/sw.hsf.org/key4hep/setup.sh
export K4RECCALORIMETER=%s
export K4SIMGEANT4=%s
export K4FWCORE=%s
export FCCDETECTORS=%s
export PYTHONPATH=%s
LD_LIBRARY_PATH=%s
CMAKE_PREFIX_PATH=%s
PATH=%s
"""%(os.environ.get("K4RECCALORIMETER", ""), os.environ.get("K4SIMGEANT4", ""), os.environ.get("K4FWCORE", ""), os.environ.get("FCCDETECTORS", ""), os.environ.get("PYTHONPATH", ""), os.environ.get("LD_LIBRARY_PATH", ""), os.environ.get("CMAKE_PREFIX_PATH", ""), os.environ.get("PATH", ""))




if __name__ == "__main__":
    print("Starting, if it hangs forever, check that eos is responding (could get stuck when creating the output eos directory)...")
    parser = argparse.ArgumentParser()
    parser.add_argument("-outputFolder", default = "/eos/user/b/brfranco/rootfile_storage/", help = "Output folder absolute path for the rootfile", type = str)
    parser.add_argument("-campaignName", default = date.today().strftime("%y%m%d"), help = "Folder name used to store the submission script, logs, etc, as well as the output rootfile in the outputFolder", type = str)
    parser.add_argument("-gaudiConfig", default = "%s/runSlidingWindowAndCaloSim.py"%os.environ.get("PWD", ""), help = "Absolute path to the gaudi config to use", type = str)
    parser.add_argument("-jobType", default = "caloReco", help = "Tell the type of job we launch. Can be samplingFraction, caloReco, upstreamCorrection (not implemented yet)", type = str)
    parser.add_argument("-pythia", default = False, help = "Tell to use Pythia instead of particle gun (the energies, polar angles etc do not matter anymore). Warning: you must also manually set to true 'usePythia' in the FCCSW cfg!", type = str)
    parser.add_argument("-pythiaCfg", default = "%s/MCGeneration/ee_Z_ee.cmd"%os.environ.get("PWD", ""), help = "Absolute path to the Pythia config file", type = str)
    parser.add_argument("-inputFiles", help = "Regex used to get all the input files, if any is needed - not implemented yet.", type = str)
    parser.add_argument("-energies", default = [10], help = "Energies in MeV for the process to generate, behavior depends on fixedEnergy. Make sure you put the energies in ascending order to have an optimal job splitting.", type = int, nargs = '+')
    parser.add_argument("-fixedEnergies", default = True, help = "Do we launch several fixed energies gun or an energy range? If range, energies should have two entries: min and max - not implemented yet", type = bool)
    parser.add_argument("-polarAngles", default = [90], help="Polar angles in degrees for the process to generate, behavior depends on fixedPolarAngles", type = int, nargs = '+')
    parser.add_argument("-fixedPolarAngles", default = True, help = "Do we launch several fixed polar angles gun or a polar angle range? If range, polarAngles should have two entries: min and max", type = bool)
    parser.add_argument("-energiesForDifferentPolarAngles", help = "Use this if you want to generate the additional polar angles only for some energies", type = int, nargs = '+')
    parser.add_argument("-pdgId", default = 22, help = "PDG ID of the particle to shoot", type = int)
    parser.add_argument("-originalNjobs", default = 1, help = "If more than one energy point, the script will submit with increasing number of jobs for increasing energies, tells how many jobs should be used for the first point.", type = int)
    parser.add_argument("-nEvt", default = 1000, help = "How many events to generate.", type = int)
    parser.add_argument("-energyAtWhichStartingDilution", default = 1, help = "When launching energies far away from each other, you can end up with way too many jobs at high energy, this allows to keep it under control.", type = int)
    parser.add_argument("--submit", help="Won't actually submit the jobs unless this is provided.", action = 'store_true')

    args = parser.parse_args()

    if os.environ.get("FCCDETECTORS", "") == "":
        print("Error: fcc environment not set, please run source init.sh and source install/setup.sh in the FCCSW root directory\nExitting...")
        sys.exit(1)

    # make sure you put the energies in ascending order to have an optimal job splitting
    energies = args.energies  # in MeV
    thetas = args.polarAngles # degrees, will transform to radians later
    if args.energiesForDifferentPolarAngles:
        energies_using_other_thetas = args.energiesForDifferentPolarAngles # may not be interested in having all the theta points for all the energies
    else:
        energies_using_other_thetas = energies
    pdgid = args.pdgId
    original_n_jobs = args.originalNjobs
    total_evt_to_generate = args.nEvt
    gaudi_config_path = args.gaudiConfig
    
    storage_path = args.outputFolder
    campaign_name = args.campaignName
    if not os.path.isdir(campaign_name):
        os.mkdir(campaign_name)
    outfile_storage = os.path.join(storage_path, campaign_name)
    if not os.path.isdir(outfile_storage):
        os.mkdir(outfile_storage)

    if args.jobType == 'samplingFraction':
        command_template = """fccrun %s -n EVT --MomentumMin PMIN --MomentumMax PMAX --ThetaMin THETAMINRADIAN --ThetaMax THETAMAXRADIAN --PdgCodes PDGID --Output.THistSvc "rec DATAFILE='OUTPUTDIR/calibration_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX_jobid_JOBID.root' TYP='ROOT' OPT='RECREATE'" --filename OUTPUTDIR/fccsw_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX_jobid_JOBID.root --seedValue SEED"""%(gaudi_config_path)
        sf_commands = 'python FCC_calo_analysis_cpp/plot_samplingFraction.py OUTPUTDIR/calibration_output_pdgID_22_pMin_?_pMax_?_thetaMin_90_thetaMax_90.root 10 -r 10000 --preview -outputfolder FCC_calo_analysis_cpp/plots_sampling_fraction_$(date +"%y%m%d") --sed'.replace('OUTPUTDIR', outfile_storage)
        # write the sampling fraction derivation script
        sf_script_path = os.path.join(campaign_name, "sf.sh")
        with open(sf_script_path, "w") as f:
            f.write(sf_commands)
        st = os.stat(sf_script_path)
        os.chmod(sf_script_path, st.st_mode | stat.S_IEXEC)

    elif args.jobType == 'caloReco':
        if args.pythia:
            energies = [0]
            thetas = [0]
            pdgId = 0
            command_template = """fccrun %s -n EVT --Filename PYTHIACFG --filename OUTPUTDIR/fccsw_output_pythia_%s_jobid_JOBID.root"""%(gaudi_config_path, os.path.basename(args.pythiaCfg).split('.')[0])
        else:
            command_template = """fccrun %s -n EVT --MomentumMin PMIN --MomentumMax PMAX --ThetaMin THETAMINRADIAN --ThetaMax THETAMAXRADIAN --PdgCodes PDGID --seedValue SEED --filename OUTPUTDIR/fccsw_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX_jobid_JOBID.root"""%(gaudi_config_path)

    else:
        print("Wrong jobType provided, read the help to see what is available.")
        sys.exit()
    exec_filename_template = os.path.join(campaign_name, "exec_evt_EVT_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX_jobid_JOBID.sh")


    total_n_job = 0
    hadd_commands = ""
    rm_commands = ""
    fcc_analysis_path = "/afs/cern.ch/user/b/brfranco/work/public/Fellow/FCCSW/FCCAnalysesRepos/210607/FCCAnalyses/"
    fcc_analysis_commands = "#!/bin/sh\n#to be launched with source ... in a new shell\ncd %s\nsource setup.sh\n"%fcc_analysis_path
    for index in range(len(energies)):
        energy = energies[index]
        energy_min = energy
        energy_max = energy
        if index != 0 and energy > args.energyAtWhichStartingDilution:
            n_jobs = int(math.floor(n_jobs * energy/energies[index-1]))
        else:
            n_jobs = original_n_jobs
        evt_per_job = int(round(total_evt_to_generate/n_jobs))
        if evt_per_job == 0:
            evt_per_job = 1

        if energy in energies_using_other_thetas:
            thetas_for_loop = thetas
        else:
            thetas_for_loop = [thetas[0]]
        for theta in thetas_for_loop:
            print("Treating energy {0}, theta {1}".format(energy, theta))
            theta_min = theta
            theta_max = theta
            job_idx = 0
            evt_already_launched = 0
            if total_evt_to_generate - evt_per_job < 0:
                print("Careful, total_evt_to_generate is smaler than evt_per_job")
                evt_per_job = total_evt_to_generate
            while evt_already_launched <= total_evt_to_generate - evt_per_job:
                if args.pythia:
                    # make sure every job has different seed (seed 0 use stdlib time which is with a second granularity --> same seed if two jobs start at the same second) 
                    pythia_cfg_path = os.path.join(os.environ.get("PWD"), campaign_name, os.path.basename(args.pythiaCfg).split('.')[0] + "_%d.cmd"%job_idx)
                    copyfile(args.pythiaCfg, pythia_cfg_path)
                    os.system("sed -i 's/SEED/%d/' %s"%(job_idx, pythia_cfg_path))
                    print(pythia_cfg_path)
                    command = command_template.replace('EVT', str(evt_per_job)).replace('OUTPUTDIR', outfile_storage).replace('JOBID', str(job_idx)).replace("PYTHIACFG", pythia_cfg_path)
                    print(command)
                else:
                    command = command_template.replace('EVT', str(evt_per_job)).replace('PMIN', str(energy_min)).replace('PMAX', str(energy_max)).replace('THETAMINRADIAN', str(math.radians(theta_min))).replace('THETAMAXRADIAN', str(math.radians(theta_max))).replace('OUTPUTDIR', outfile_storage).replace('PDGID', str(pdgid)).replace('THETAMIN', str(theta_min)).replace('THETAMAX', str(theta_max)).replace('JOBID', str(job_idx)).replace('SEED', str(job_idx))
                exec_filename = exec_filename_template.replace('EVT', str(evt_per_job)).replace('PMIN', str(energy)).replace('PMAX', str(energy)).replace('THETAMIN', str(theta)).replace('THETAMAX', str(theta)).replace('JOBID', str(job_idx)).replace('PDGID', str(pdgid))
                with open(exec_filename, "w") as f:
                    f.write(get_exec_file_header())
                    f.write(command)
                st = os.stat(exec_filename)
                os.chmod(exec_filename, st.st_mode | stat.S_IEXEC)
                evt_already_launched += evt_per_job
                job_idx += 1
                total_n_job += 1

            evt_last_job = total_evt_to_generate - evt_already_launched
            if evt_last_job > 0:
                if args.pythia:
                    command = command_template.replace('EVT', str(evt_per_job)).replace('OUTPUTDIR', outfile_storage).replace('JOBID', str(job_idx))
                else:
                    command = command_template.replace('EVT', str(evt_per_job)).replace('PMIN', str(energy_min)).replace('PMAX', str(energy_max)).replace('THETAMINRADIAN', str(math.radians(theta_min))).replace('THETAMAXRADIAN', str(math.radians(theta_max))).replace('OUTPUTDIR', outfile_storage).replace('PDGID', str(pdgid)).replace('THETAMIN', str(theta_min)).replace('THETAMAX', str(theta_max)).replace('JOBID', str(job_idx)).replace('SEED', str(job_idx))
                exec_filename = exec_filename_template.replace('EVT', str(evt_last_job)).replace('PMIN', str(energy)).replace('PMAX', str(energy)).replace('THETAMIN', str(theta)).replace('THETAMAX', str(theta)).replace('JOBID', str(job_idx)).replace('PDGID', str(pdgid))
                with open(exec_filename, "w") as f:
                    f.write(get_exec_file_header())
                    f.write(command)
                st = os.stat(exec_filename)
                os.chmod(exec_filename, st.st_mode | stat.S_IEXEC)
                job_idx += 1
                total_n_job += 1

            if args.jobType == 'samplingFraction':
                hadd_commands += "#rm OUTPUTDIR/fccsw_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX_jobid_*.root\n".replace('PMIN', str(energy_min)).replace('PMAX', str(energy_max)).replace('OUTPUTDIR', outfile_storage).replace('PDGID', str(pdgid)).replace('THETAMIN', str(theta_min)).replace('THETAMAX', str(theta_max))
                hadd_commands += "hadd OUTPUTDIR/calibration_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX.root OUTPUTDIR/calibration_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX_jobid_*.root\n".replace('PMIN', str(energy_min)).replace('PMAX', str(energy_max)).replace('OUTPUTDIR', outfile_storage).replace('PDGID', str(pdgid)).replace('THETAMIN', str(theta_min)).replace('THETAMAX', str(theta_max))
                rm_commands += "cp OUTPUTDIR/calibration_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX_jobid_1.root OUTPUTDIR/calibration_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX_forTests.root\n".replace('PMIN', str(energy_min)).replace('PMAX', str(energy_max)).replace('OUTPUTDIR', outfile_storage).replace('PDGID', str(pdgid)).replace('THETAMIN', str(theta_min)).replace('THETAMAX', str(theta_max))
                rm_commands += "rm OUTPUTDIR/calibration_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX_jobid_*.root\n".replace('PMIN', str(energy_min)).replace('PMAX', str(energy_max)).replace('OUTPUTDIR', outfile_storage).replace('PDGID', str(pdgid)).replace('THETAMIN', str(theta_min)).replace('THETAMAX', str(theta_max))
            else:
                if args.pythia:
                    hadd_commands += "hadd  OUTPUTDIR/fccsw_output_pythia_{0}.root OUTPUTDIR/fccsw_output_pythia_{0}_jobid_*.root\n".format(os.path.basename(args.pythiaCfg).split('.')[0]).replace('OUTPUTDIR', outfile_storage)
                    rm_commands += "cp  OUTPUTDIR/fccsw_output_pythia_{0}_jobid_1.root OUTPUTDIR/fccsw_output_pythia_{0}_forTests.root\n".format(os.path.basename(args.pythiaCfg).split('.')[0]).replace('OUTPUTDIR', outfile_storage)
                    rm_commands += "rm  OUTPUTDIR/fccsw_output_pythia_{0}_jobid_*.root\n".format(os.path.basename(args.pythiaCfg).split('.')[0]).replace('OUTPUTDIR', outfile_storage)
                    fcc_analysis_commands += "python examples/FCCee/fullSim/caloNtupleizer/analysis.py -inputFiles OUTPUTDIR/fccsw_output_pythia_{0}.root -outputFolder FCCANAOUTPUT_pythia".format(os.path.basename(args.pythiaCfg).split('.')[0]).replace('OUTPUTDIR', outfile_storage).replace("FCCANAOUTPUT", campaign_name)
                else:
                    hadd_commands += "hadd  OUTPUTDIR/fccsw_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX.root OUTPUTDIR/fccsw_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX_jobid_*.root\n".replace('PMIN', str(energy_min)).replace('PMAX', str(energy_max)).replace('OUTPUTDIR', outfile_storage).replace('PDGID', str(pdgid)).replace('THETAMIN', str(theta_min)).replace('THETAMAX', str(theta_max))
                    rm_commands += "cp OUTPUTDIR/fccsw_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX_jobid_1.root OUTPUTDIR/fccsw_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX_forTests.root\n".replace('PMIN', str(energy_min)).replace('PMAX', str(energy_max)).replace('OUTPUTDIR', outfile_storage).replace('PDGID', str(pdgid)).replace('THETAMIN', str(theta_min)).replace('THETAMAX', str(theta_max))
                    rm_commands += "rm OUTPUTDIR/fccsw_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX_jobid_*.root\n".replace('PMIN', str(energy_min)).replace('PMAX', str(energy_max)).replace('OUTPUTDIR', outfile_storage).replace('PDGID', str(pdgid)).replace('THETAMIN', str(theta_min)).replace('THETAMAX', str(theta_max))
                    fcc_analysis_commands += "python examples/FCCee/fullSim/caloNtupleizer/analysis.py -inputFiles OUTPUTDIR/fccsw_output_pdgID_PDGID_pMin_PMIN_pMax_PMAX_thetaMin_THETAMIN_thetaMax_THETAMAX.root -outputFolder FCCANAOUTPUT_caloReco\n".replace('PMIN', str(energy_min)).replace('PMAX', str(energy_max)).replace('OUTPUTDIR', outfile_storage).replace('PDGID', str(pdgid)).replace('THETAMIN', str(theta_min)).replace('THETAMAX', str(theta_max)).replace("FCCANAOUTPUT", campaign_name)

    # write the hadd script
    hadd_script_path = os.path.join(campaign_name, "hadd.sh")
    with open(hadd_script_path, "w") as f:
        f.write(hadd_commands)
    st = os.stat(hadd_script_path)
    os.chmod(hadd_script_path, st.st_mode | stat.S_IEXEC)

    # write the rm script
    rm_script_path = os.path.join(campaign_name, "rm.sh")
    with open(rm_script_path, "w") as f:
        f.write(rm_commands)
    st = os.stat(rm_script_path)
    os.chmod(rm_script_path, st.st_mode | stat.S_IEXEC)

    # write the fcc_analysis script
    fcc_analysis_script_path = os.path.join(campaign_name, "fcc_analysis.sh")
    fcc_analysis_commands += "cd -\n"
    with open(fcc_analysis_script_path, "w") as f:
        f.write(fcc_analysis_commands)
    st = os.stat(fcc_analysis_script_path)
    os.chmod(fcc_analysis_script_path, st.st_mode | stat.S_IEXEC)

    # write the perfPlots script
    perfPlots_script_path = os.path.join(campaign_name, "perfPlots.sh")
    with open(perfPlots_script_path, "w") as f:
        string_for_perfPlots_script = "cd %s/../caloNtupleAnalyzer/\npython perfPlots.py -inputFiles '%s/FCCANAOUTPUT_caloReco/*.root' -outputPostfix FCCANAOUTPUT_condor"%(os.environ.get("PWD", ""), fcc_analysis_path)
        f.write(string_for_perfPlots_script.replace("FCCANAOUTPUT", campaign_name))
    st = os.stat(perfPlots_script_path)
    os.chmod(perfPlots_script_path, st.st_mode | stat.S_IEXEC)

    # write the condor submit file
    condor_submit_path = campaign_name + ".sub"
    with open(condor_submit_path, "w") as f:
        f.write(get_condor_submit_header(exec_filename_template.replace('EVT', '*').replace('PMIN', '*').replace('PMAX', '*').replace('THETAMIN', '*').replace('THETAMAX', '*').replace('JOBID', '*').replace('PDGID', '*')))
    submit_cmd = "condor_submit %s"%condor_submit_path
    print("%d jobs prepared in %s"%(total_n_job, campaign_name))
    print (submit_cmd)
    if args.submit:
        job=SubmitToCondor(submit_cmd, 10)
    print("Will write the output in %s"%outfile_storage)


