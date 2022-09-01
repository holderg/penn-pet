'''
    Script to get label statistics on PET data using QuANTs. This script will be called at the end of the PET
    processing script.
    
    Command-line arguments:
    
    1. petDir: directory with output from PET processing T1-space SUVR image. Filename must match
       the pattern "*desc-suvr2*pet.nii.gz", e.g., 
       "sub-123456_ses-20220101x1200_trc-AV1451_desc-suvr20220102x1330_pet.nii.gz", where "20220102x1330" is the
       label for the MRI session in which the T1w image was acquired.
    2. antsDir: ANTs Cortical Thickness output for T1w image to which the PET was registered.
    
    N.B. The script also expects a) a directory named "/template" with information for the reference image for
    any ROI atlases that are not already in native T1 space; and b) a directory called "/atlases" with jsons and
    niftis for all ROI atlases.
    
    Output: a csv file containing volumes and SUVR label statistics for several atlases:
        BrainColor
        DKT31
        Schaefer 100-500 resolutions (7 and 17 networks)
        Tian subcortical atlases
        
'''
import itk
import SimpleITK as sitk
import quantsifier
import numpy as np
import pandas as pd
import os 
import sys
import json
import glob

# This is the single session PET output directory.
petDir = sys.argv[1]
# ANTsCT output directory. Does this take the place of networkDir?
antsDir = sys.argv[2]
# Why needed? Supply correct path.
# On scisub: /project/ftdc_misc/pcook/quants/tpl-TustisonAging2019ANTs/template_description.json
template = "/template/template_description.json"
# Wherever jsons for different label atlases are stored.
networkDir = "/atlases"

# Get subject and session based on session output directory path.
def parsePath( path ):
    dirParts = os.path.split(path.rstrip('/'))
    sesTag = dirParts[1]
    subTag = os.path.split(dirParts[0])[1]
    id = subTag.split('-')[1]
    ses = sesTag.split('-')[1]
    return((id,ses))

# Create a custom method for getting both PET and ANTsCT files as input.
def getInputs(petDir,antsDir):
    suffix = {"suvr": os.path.join(petDir,"*desc-suvr2*pet.nii.gz"),
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

# Create an instance of the Quantsifier class.
q = quantsifier.Quantsifier()

# Feed the template to the quantsifier.
templateDir = os.path.dirname(os.path.abspath(template))
templateF = open(template)
templateDef = json.load(templateF)
templateF.close()
q.SetTemplate(templateDef, templateDir)

# Read in input files. Have to create a custom function that will replace getFTDCInputs
# and read in both PET and ANTsCT files needed.
inputFiles =  getInputs(petDir, antsDir)
print("input files: ", inputFiles)
inputImgs = {}
for tag in inputFiles.keys():
    if tag != 'mat':
        if tag != 'warp':
            if len(inputFiles[tag])>0:
                print("Reading "+inputFiles[tag][0])
                inputImgs[tag] = sitk.ReadImage(inputFiles[tag][0])
            else:
                inputImgs[tag] = None

# Supply transform files to quantsifier.
if len(inputFiles['mat']) > 0:
    txMat = sitk.ReadTransform(inputFiles['mat'][0])
    txWarp = sitk.DisplacementFieldTransform( sitk.ReadImage(inputFiles['warp'][0]) )
    q.subjectMat = txMat
    q.subjectWarp = txWarp

# Probs don't need this cortical thickness bit, but may need similar masking step.
if 'thickness' in inputImgs:
    print("Apply thickness masking")
    thickMask = sitk.BinaryThreshold(inputImgs['thickness'], lowerThreshold=0.0001 )
    thickMask = sitk.Cast(thickMask, sitk.sitkUInt32)
    cortex = sitk.Threshold(inputImgs['seg'], lower=2, upper=2)
    cortex = sitk.Multiply(thickMask, cortex)
    
    # Create masks of each tissue class.
    c1 = sitk.Threshold(inputImgs['seg'], lower=1, upper=1)
    c3 = sitk.Threshold(inputImgs['seg'], lower=3, upper=3)
    c4 = sitk.Threshold(inputImgs['seg'], lower=4, upper=4)
    c5 = sitk.Threshold(inputImgs['seg'], lower=5, upper=5)
    c6 = sitk.Threshold(inputImgs['seg'], lower=6, upper=6)
    
    # Create a revised segmentation mask that leaves voxels with low grey matter
    # probability out of the class 2 mask.
    seg = sitk.Add(cortex, c1)
    seg = sitk.Add(seg, c3)
    seg = sitk.Add(seg, c4)
    seg = sitk.Add(seg, c5)
    seg = sitk.Add(seg, c6)
    inputImgs['seg'] = seg
    #sitk.WriteImage(seg, "seg.nii.gz")

# Give segmentation and mask to quantsifier.
q.SetSegmentation(inputImgs['seg'])
q.SetMask(inputImgs['mask'])

# Add measure named 'suvr' for voxels with segmentation==2 or 4
# 1=CSF, 2=CGM, 3=WM, 4=SCGM, 5=BS, 6=CBM
q.AddMeasure(inputImgs['suvr'], 'suvr', [2,4])

# I think "networks" here just means different label atlases. Customize this to be
# just the ones we want. Include Tian subcortical labels; may not need all Schaefer
# resolutions.
# Add networks with labels in NATIVE space (ie no template labels exist)
networks = quantsifier.getNetworks(networkDir)
for n in networks:
    print("Adding network ", n['Identifier'], " in ", n['TemplateSpace'], " space...")
    templateSpace = n['TemplateSpace']
    
    # Looks through the list of atlases in the network directory, then tries to
    # find a matching native-space label image in the session ANTsCT directory.
    # Should be able to ask for the Tian label sets and just get a warning back if
    # they haven't been generated for a session.
    if templateSpace=='NATIVE':
        print("Looking for NATIVE labels matching: "+n['Filename'])
        nativeLabelName = glob.glob( os.path.join(antsDir, n['Filename']))
        print(nativeLabelName)
        if len(nativeLabelName)==1:
            img = sitk.ReadImage(nativeLabelName[0])
            q.AddNetwork(n,img)
        else:
            if len(nativeLabelName)==0:
                print("WARNING: No NATIVE label image found")
            else:
                print("WARNING: Could not find a unique file for NATIVE labels")
    else:
        if 'Filename' in n:
            fname = os.path.join(networkDir, n['Filename'])
            if os.path.exists(fname):
                print("Adding Network: "+ n["Identifier"])
                img = sitk.ReadImage(fname)
                q.AddNetwork(n,img)

# Add subject and session labels.
bidsInfo = parsePath(petDir)
q.SetConstants({"id": bidsInfo[0], "date": bidsInfo[1]})
q.SetOutputDirectory(petDir)
# Get tracer from SUVR image name.
trc = os.path.basename(inputFiles['suvr']).split("_")[2]
# Output file name.
oFile = os.path.join(petDir, "sub-" + bidsInfo[0] + "_ses-" + bidsInfo[1] + "_" + trc + "_pet_quants.csv")

# This update function is what does all the work (by calling Summarize).
q.Update()

# Extract label stats from the quantsifier. May need to customize this function
# for PET output. Make sure volume is included. (Should be, it's the default measure.)
stats = q.GetOutput()

# Use Pandas to write the label stats to a csv file.
pd.set_option("display.max_rows", None, "display.max_columns", None)
stats.to_csv(oFile, index=False, float_format='%.4f')
