import os 
os.environ['ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS'] = str(1)
os.environ['MKL_NUM_THREADS'] = str(1)
os.environ['OMP_NUM_THREADS'] = str(1)
os.environ['NUMEXPR_NUM_THREADS'] = str(1)

#import itk
import SimpleITK as sitk
import quants
import numpy as np
import pandas as pd
import sys
import json
import glob
import logging
import argparse
import time
import os
import ants

def parsePath( path ):

    dirParts = os.path.split(path.rstrip('/'))
    sesTag = dirParts[1]
    subTag = os.path.split(dirParts[0])[1]

    id = subTag
    ses = sesTag

    if "sub-" in id:
        id = id.split('-')[1]
    if "ses-" in ses:
        ses = ses.split('-')[1]

    return((id,ses))


def getMyPID( uname, output ):
    stream = os.popen("ps -elf | grep "+uname)
    jobList = stream.read().split('\n')
    stream.close()
    thisJob = [ x for x in jobList if output in x ]

    if len(thisJob) > 1:
        return None

    return(thisJob[0].split(' ')[3])


def getMyThreads( uname, output ):
    pid = getMyPID( uname, output )
    stream = os.popen("ps -o thcount "+str(pid) )
    output = stream.read().split('\n')
    stream.close()
    return( output[1] )

    
def getInputs(petFile,antsDir):
    suffix = {"suvr": petFile,
        "t1": os.path.join(antsDir,"*ExtractedBrain0N4.nii.gz"),
        "mask": os.path.join(antsDir,"*BrainExtractionMask.nii.gz"),
        "seg": os.path.join(antsDir,"*BrainSegmentation.nii.gz"),
        "n4": os.path.join(antsDir,"*BrainSegmentation0N4.nii.gz"),
        "gmp": os.path.join(antsDir,"*BrainSegmentationPosteriors2.nii.gz"),
        "deepgm": os.path.join(antsDir,"*BrainSegmentationPosteriors4.nii.gz"),
        "warp" : os.path.join(antsDir,"*_TemplateToSubject0Warp.nii.gz"),
        "mat" : os.path.join(antsDir,"*_TemplateToSubject1GenericAffine.mat")
    }
    
    imgFiles = suffix
    
    for tag in suffix.keys():
        files = glob.glob(suffix[tag])
        imgFiles[tag] = files
    
    return(imgFiles)


def main():
    
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Summarize ROI values using ANTsCT output")
    parser.add_argument("-t","--template", type=str, required=True, help="JSON file listing template info")
    parser.add_argument("--atlas_dir", type=str, required=True, help="Directory with label system definition files (json)") 
    parser.add_argument("--atlas_images", type=str, required=True, help="Directory with label sytem images")
    parser.add_argument('-o', '--output', default=None,  action='store', required=True, help='output filename')
    parser.add_argument('-s', '--subject', default=None, action='store', required=True, help='SubjectID')
    parser.add_argument('-S', '--session', default=None, action='store', required=True, help='SessionID')
    parser.add_argument("--seg_dirs", type=str, required=False, nargs='+', help="Directories to search for segmentations")
    parser.add_argument('PetFile', nargs=1, help='PETFilePath')
    parser.add_argument('AntsDir', nargs=1, help='ANTsCTDirPath')
    args = parser.parse_args()
    print(args)
    
    logging.basicConfig(
        format='%(asctime)s %(name)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S')
    
    psOut = getMyPID( 'jtduda', args.output )
    threads = getMyThreads( 'jtduda', args.output )
    logging.info("Started with nThreads="+str(threads))
    
    #threader = itk.MultiThreaderBase.New()
    #threader.SetGlobalDefaultNumberOfThreads(1)
    #logging.info("ITK Max Threads = " + str(threader.GetGlobalDefaultNumberOfThreads()))
    
    sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(1)
    logging.info("SimpleITK Max Threads = " + str(sitk.ProcessObject.GetGlobalDefaultNumberOfThreads()))
    
    petFile = args.PetFile[0]
    petDir = os.path.dirname(petFile)    
    antsDir = args.AntsDir[0]
    print("antsDir: ", antsDir)
    template = args.template
    networkDir = args.atlas_dir
    networkImageDir = args.atlas_images
    OutputDir = os.path.dirname(args.output)
    
    q = quants.Quantsifier()
    
    #user = os.getlogin()
    user = os.getenv('USER')
    threads = getMyThreads( user, args.output )
    logging.info("Initialized quantsifier with nThreads="+str(threads))
    
    templateDir = os.path.dirname(os.path.abspath(template))
    templateF = open(template)
    templateDef = json.load(templateF)
    templateF.close()
    q.SetTemplate(templateDef, templateDir)
    
    bidsInfo = parsePath(petDir)
    inputFiles =  getInputs(petFile, antsDir)
    print("input files: ", inputFiles)
    
    inputImgs = {}
    for tag in inputFiles.keys():
        if tag != 'mat':
            if tag != 'warp':
                if len(inputFiles[tag])>0:
                    #print("Reading "+inputFiles[tag][0])
                    inputImgs[tag] = sitk.ReadImage(inputFiles[tag][0])
                else:
                    inputImgs[tag] = None

    threads = getMyThreads( user, args.output )
    logging.info("Set quantsifier inputs with nThreads="+str(threads))

    if len(inputFiles['mat']) > 0:
        txMat = sitk.ReadTransform(inputFiles['mat'][0])
        txWarp = sitk.DisplacementFieldTransform( sitk.ReadImage(inputFiles['warp'][0]) )
        q.subjectMat = txMat
        q.subjectWarp = txWarp
        q.subjectWarpName = inputFiles['warp'][0]
        
        ants_t1 = ants.image_read(inputFiles['t1'][0])
        logJacobian = ants.create_jacobian_determinant_image(ants_t1, inputFiles['warp'][0], True, True)
        logJacobian = quants.ants_2_sitk(logJacobian)

        # Apply the mat to get jacobian into subject space 
#        resample = sitk.ResampleImageFilter()
#        resample.SetReferenceImage( inputImgs['t1'] )
#        resample.SetTransform( sitk.ReadTransform(inputFiles['mat'][0]) )
#        resample.SetInterpolator( sitk.sitkLinear )
#        resample.SetNumberOfThreads(1)
#        resizedJacobian = resample.Execute(logJacobian)

        #opath = os.path.join( os.path.dirname(args.output), 'sub-'+bidsInfo[0], 'ses-'+bidsInfo[1] )
        #if not os.path.exists(opath):
        #    os.makedirs(opath)
        #jacName = os.path.join( opath, 'sub-'+bidsInfo[0]+"_ses-"+bidsInfo[1]+"_subject_log_jacobian.nii.gz" )
        #sitk.WriteImage(resizedJacobian, jacName)

 
        if 'thickness' in inputImgs:
            logging.info("Apply thickness masking using" + inputFiles['thickness'][0])
            thickMask = sitk.BinaryThreshold(inputImgs['thickness'], lowerThreshold=0.0001 )
            thickMask = sitk.Cast(thickMask, sitk.sitkUInt32)
            cortex = sitk.Threshold(inputImgs['seg'], lower=2, upper=2)
            cortex = sitk.Multiply(thickMask, cortex)

            c1 = sitk.Threshold(inputImgs['seg'], lower=1, upper=1)
            c3 = sitk.Threshold(inputImgs['seg'], lower=3, upper=3)
            c4 = sitk.Threshold(inputImgs['seg'], lower=4, upper=4)
            c5 = sitk.Threshold(inputImgs['seg'], lower=5, upper=5)
            c6 = sitk.Threshold(inputImgs['seg'], lower=6, upper=6)

            seg = sitk.Add(cortex, c1)
            seg = sitk.Add(seg, c3)
            seg = sitk.Add(seg, c4)
            seg = sitk.Add(seg, c5)
            seg = sitk.Add(seg, c6)
            inputImgs['seg'] = seg
            #sitk.WriteImage(seg, "seg.nii.gz")

            threads = getMyThreads( user, args.output )
            logging.info("Applied thickness masking with nThreads="+str(threads))

        q.SetSegmentation(inputImgs['seg'])
        q.SetMask(inputImgs['mask'])

        # 1=CSF, 2=CGM, 3=WM, 4=SCGM, 5=BS, 6=CBM
        # Add measure named 'thickness' for voxels with segmentation==2
#        q.AddMeasure(inputImgs['thickness'], 'thickness', [2])
#        q.AddMeasure(inputImgs['t1'], 'intensity0N4', [1,2,3,4,5,6])
#        q.AddMeasure(resizedJacobian, 'subject_log_jacobian', [1,2,3,4,5,6])
        q.AddMeasure(inputImgs['suvr'], 'suvr', [2,4])

        networks = quants.getNetworks(networkDir)
        def networkIdentifierFunc(x):
            return( x['Identifier'])
        networks.sort(key=networkIdentifierFunc)

        # Add networks with labels in NATIVE space (ie no template labels exist)
        for n in networks:
            templateSpace = n['TemplateSpace']

            if templateSpace=='NATIVE':
                #logging.info("Looking for NATIVE labels matching: "+n['Filename'])
                nativeLabelName = glob.glob( os.path.join(antsDir, n['Filename']))
                if len(nativeLabelName)==0:
                    if args.seg_dirs is not None:
                        for seg_dir in args.seg_dirs:
                            seg_name = glob.glob(os.path.join(seg_dir, n['Filename']))
                            if len(seg_name)>0:
                                if os.path.exists(seg_name[0]):
                                    nativeLabelName = seg_name
                                    logging.info("Using NATIVE segmentation: "+str(nativeLabelName[0]))
                                    break

                if len(nativeLabelName)==1:
                    img = sitk.ReadImage(nativeLabelName[0])
                    q.AddNetwork(n,img)
                else:
                    if len(nativeLabelName)==0:
                        logging.warning("No NATIVE label image found for "+n['Identifier'])
                    else:
                        logging.warning(n['Identifier']+" does not have unique label image")
                        for nm in nativeLabelName:
                            logging.warning("  lbl="+nm)

            else:
                if 'Filename' in n:
                    fname = os.path.join(networkImageDir, n['Filename'])
                    if os.path.exists(fname):
                        logging.info("Adding Network: "+n["Identifier"])
                        img = sitk.ReadImage(fname)
                        q.AddNetwork(n,img)
                else:
                    logging.error("No template image found for "+n['Identifier'])

        #x = quants.getFTDCQuantsifier(filenames)
        q.SetConstants({"id": args.subject, "date": args.session})
        q.SetOutputDirectory(OutputDir)
        # Get tracer from SUVR image name.
        print(inputFiles['suvr'][0])
        trc = os.path.basename(inputFiles['suvr'][0]).split("_")[2]
        # Output file name.
        oFile = os.path.join(petDir, os.path.basename(inputFiles['suvr'][0]).replace(".nii.gz","") + "_quants.csv")
        q.threadString=oFile
        logging.info("q.threadString= "+q.threadString)
        
        if 'LabelPropagation' in n:
            if n['LabelPropagation']=='True':
                print("Add Label Propagation for: "+n['Identifier'])
                prop_mask = sitk.Threshold(inputImgs['seg'], lower=2, upper=2)
                q.AddLabelPropagation(n['Identifier'], prop_mask)

        threads = getMyThreads( user, oFile )
        logging.info("Pre Update() with nThreads="+str(threads))
        time.sleep(5)
        threads = getMyThreads( user, oFile )
        logging.info("Pre Update() with nThreads="+str(threads))
        q.Update()
        stats = q.GetOutput()

        pd.set_option("display.max_rows", None, "display.max_columns", None)
        stats.to_csv(oFile, index=False, float_format='%.4f')
        logging.info("Output written to: "+oFile)

        #print("Done")

if __name__ == "__main__":
    main()


