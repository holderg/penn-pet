#!/bin/bash
# Processes PET data to create SUVR images.
# Follows BIDS PET standard and expects BIDS-format filenames. 
# Note that subject and session labels cannot contain BIDS-incompatible 
# characters like underscores or periods.

#
# Initial comment to check pull requests
# 

# Load required software on PMACS LPC.
module load ANTs/2.3.5
module load afni_openmp/20.1
module load PETPVC/1.2.10
module load fsl/6.0.3

# JSP: If we can find an alternative to copying the template and associated labels and warps from the ANTsCT container,
# we can get rid of the singularity call.
module load DEV/singularity

# Command-line arguments.
petName=$1 # Absolute path of BIDS-format, attentuation-corrected dynamic PET image
t1Name=$2 # Absolute path of N4-corrected, skull-on T1 image from ANTsCT output directory

# JSP: required files include:
# petName=$1 # Absolute path of BIDS-format, attentuation-corrected dynamic PET image
# t1Name=$2 # Absolute path of N4-corrected, skull-on T1 image from ANTsCT output directory
# bmaskName=${t1dir}/sub-${id}_ses-${mrisess}_BrainExtractionMask.nii.gz
# segName=${t1dir}/sub-${id}_ses-${mrisess}_BrainSegmentation.nii.gz
# T1-template transforms:
#   ${t1dir}/*_SubjectToTemplate1Warp.nii.gz
#   ${t1dir}/*_SubjectToTemplate0GenericAffine.mat`
#   ${t1dir}/*_TemplateToSubject0Warp.nii.gz
#   ${t1dir}/*_TemplateToSubject1GenericAffine.mat`
# Tissue probability posterior images: ${t1dir}/*Posteriors[1-6]nii.gz 

# Record job ID.
# JSP: useful for job monitoring and debugging failed jobs.
echo "LSB job ID: ${LSB_JOBID}"
scriptdir=`dirname $0` # Location of this script

# Parse command-line arguments to get working directory, subject ID, tracer, and PET/MRI session labels.
petdir=`dirname ${petName}` # PET session input directory
bn=`basename ${petName}`
id=`echo $bn | grep -oE 'sub-[^_]*' | cut -d '-' -f 2` # Subject ID
petsess=`echo $bn | grep -oE 'ses-[^_]*' | cut -d '-' -f 2` # PET session label
trc=`echo $bn | grep -oE 'trc-[^_]*' | cut -d '-' -f 2` # PET tracer name.
outdir="/project/ftdc_pipeline/data/pet/sub-${id}/ses-${petsess}"

t1dir=`dirname ${t1Name}`
mrisess=`echo $t1bn | grep -oE 'ses-[^_]*' | cut -d '-' -f 2` # MRI session label
wd=${petdir/sub-${id}\/ses-${petsess}} # Subjects directory

# Define session-specific filename variables.
pfx="${outdir}/sub-${id}_ses-${petsess}_trc-${trc}"

# Get label statistics for multiple atlases using QuANTs.
for metricFile in "${pfx}_desc-suvr${mrisess}_pet.nii.gz" "${pfx}_desc-IY${mrisess}_pet.nii.gz" "${pfx}_desc-RVC${mrisess}_pet.nii.gz"; do
    python pet_quants.py ${metricFile} ${t1dir}
done

# JSP: need to at least make the template directory writeable; otherwise, if the script crashes out, it can't be deleted.
chgrp -R ftdclpc ${outdir}
chmod -R 775 ${outdir}

rm -r ${outdir}/template