#!/bin/bash
# Processes PET data to create SUVR images.
# Follows BIDS PET standard and expects BIDS-format filenames. 
# Note that subject and session labels cannot contain BIDS-incompatible 
# characters like underscores or periods.

function fwenv { source /project/ftdc_misc/software/pkg/miniconda3/bin/activate; conda activate flywheel; }
fwenv

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

# Parse command-line arguments to get working directory, subject ID, tracer, and PET/MRI session labels.
petdir=`dirname ${petName}` # PET session input directory
bn=`basename ${petName}`
id=`echo $bn | grep -oE 'sub-[^_]*' | cut -d '-' -f 2` # Subject ID
petsess=`echo $bn | grep -oE 'ses-[^_]*' | cut -d '-' -f 2` # PET session label
trc=`echo $bn | grep -oE 'trc-[^_]*' | cut -d '-' -f 2` # PET tracer name.
t1bn=`basename ${t1Name}`
mrisess=`echo $t1bn | grep -oE 'ses-[^_]*' | cut -d '-' -f 2` # MRI session label
wd=${petdir/sub-${id}\/ses-${petsess}} # Subjects directory
scriptdir=`dirname $0` # Location of this script
# JSP: note that output directory is specified here!
outdir="/project/ftdc_pipeline/data/pet/sub-${id}/ses-${petsess}"
if [[ ! -d ${outdir} ]]; then mkdir -p ${outdir}; fi

# Some processing defaults
# JSP: I don't think we'll want to alter any of these defaults, but we could allow the user to set all of these options.
runMoco=1 # Run motion correction?
makeSUVR=1 # Create SUVR images?
regLab=1 # Register label images to PET data?
doWarps=1 # Warp SUVR images to template space(s)?
lstat=0 # Save label statistic in CSV format?
psfwhm=4.9 # FWHM of PET camera point-spread function.
# JSP: refRegion could also be a user-supplied option. Only cb and wm are recognized.
refRegion="cb" # PET reference region--for now, cerebellum, can be changed to "wm".
# JSP: adding any new partial-volume correction methods (including Shidahara et al.'s SFS-RR algorithm) will require
# some substantial code additions that Sandy and I can help with.
pvcMethod=("RVC" "IY") # PVC methods.

# Get template info from ANTsCT container.
# JSP: If we want to allow users to supply their own template, tempName should be a user-supplied option.
# Here we are getting the ADNI template from the ANTsCT gear to ensure that it's the same reference used in the
# ANTsCT stream.
antsct=/project/ftdc_pipeline/ftdc-picsl/antsct-aging-0.3.3-p01/antsct-aging-0.3.3-p01.sif
singularity exec -B ${outdir}:/data ${antsct} cp -r /opt/template /data/ # copy template dir to PET output dir
tempName=${outdir}/template/T_template0_BrainCerebellum.nii.gz

# Define session-specific filename variables.
pfx="${outdir}/sub-${id}_ses-${petsess}_trc-${trc}"
t1dir=`dirname ${t1Name}`
bmaskName=${t1dir}/sub-${id}_ses-${mrisess}_BrainExtractionMask.nii.gz
segName=${t1dir}/sub-${id}_ses-${mrisess}_BrainSegmentation.nii.gz

# Check that ANTsCT output directory has subject-template transforms (affine & warp) and posteriors.
# If not, quit and tell us about it.
flist=(`ls ${t1dir}/*Posteriors*nii.gz ${t1dir}/*Warp*nii.gz ${t1dir}/*.mat`)
if [[ ${#flist[@]} -lt 10 ]]; then
    echo "Missing transform and/or posteriors files from T1 directory."
    exit 1
fi

# Also symlink processed T1 to PET directory.
if [[ ! -f ${outdir}/`basename ${t1Name}` ]]; then
    ln -s ${t1Name} ${outdir}/
fi

# Motion-correct PET data.
# Create plot in mm and radians
if [[ ${runMoco} -eq 1 ]]; then
    mcflirt -in ${petName} -out ${pfx}_desc-mc_pet.nii.gz -dof 6 -plots
    nvol=`fslinfo ${pfx}_desc-mc_pet.nii.gz | grep dim4 | grep -v pixdim4`
    nvol=${nvol/dim4}
    fslmaths "${pfx}_desc-mc_pet.nii.gz" -Tmean "${pfx}_desc-mean_pet.nii.gz"
fi

# JSP: Let's try some variations on these antsRegistration parameters.
# We can assess the fit between PET and T1 at least by visual inspection--can we develop any quantitative metrics?
# Run affine registration between PET and T1 images.
echo "Running antsRegistration between PET and T1 images..."
petxfm="${pfx}_desc-rigid${mrisess}_0GenericAffine.mat"
mpar="MI[ ${t1Name}, ${pfx}_desc-mean_pet.nii.gz, 1, 64, regular, 0.3 ]"
cpar="[1000x1000x1000,1.e-7,20]"
spar="2x1x0"
fpar="4x2x1"

regcmd="antsRegistration -d 3 -m ${mpar} -t Rigid[0.3] -c ${cpar} -s ${spar} -r [ ${t1Name}, ${pfx}_desc-mean_pet.nii.gz, 1 ] -f ${fpar} -l 1 -a 0 -o [ ${pfx}_desc-rigid${mrisess}_, ${pfx}_desc-rigid${mrisess}_pet.nii.gz, ${pfx}_desc-inv${mrisess}_T1w.nii.gz]"

${regcmd}

3dcalc -a "${bmaskName}" -b "${pfx}_desc-rigid${mrisess}_pet.nii.gz" -expr 'a*b' -overwrite -prefix "${pfx}_desc-rigid${mrisess}_pet.nii.gz"

# Compute SUVR maps by dividing each voxel by average value in reference region.
if [[ ${makeSUVR} -eq 1 ]]; then
    
    echo "Creating SUVR maps..."

    if [[ "${refRegion}" == "cb" ]]; then
    # Create an inferior cerebellar reference by lopping off the dorsal cerebellum in the template BrainCOLOR labels,
    # transforming to the T1 space, then multiplying it by the same labels in the T1-space BrainCOLOR label image.
    
        3dcalc -a ${outdir}/template/labels/BrainCOLOR/BrainCOLORSubcortical.nii.gz -expr 'step(equals(a,38)+equals(a,39))*step(i-148)' -overwrite -prefix ${outdir}/template_reference.nii.gz
        
        antsApplyTransforms -d 3 -e 0 -i ${outdir}/template_reference.nii.gz -r ${t1Name} -o ${outdir}/sub-${id}_ses-${mrisess}_reference.nii.gz -n NearestNeighbor -t "${t1dir}/sub-${id}_ses-${mrisess}_TemplateToSubject1GenericAffine.mat" -t "${t1dir}/sub-${id}_ses-${mrisess}_TemplateToSubject0Warp.nii.gz"

        3dcalc -a ${outdir}/sub-${id}_ses-${mrisess}_reference.nii.gz -b ${segName} -c ${t1dir}/sub-${id}_ses-${mrisess}_BrainColorSubcortical.nii.gz -expr 'step(step(a)*equals(b,6)*(equals(c,38)+equals(c,39)))' -overwrite -prefix ${outdir}/sub-${id}_ses-${mrisess}_reference.nii.gz
        
    elif [[ "${refRegion}" == "wm" ]]; then

        3dcalc -a ${segName} -expr 'equals(a,3)' -prefix ${outdir}/sub-${id}_ses-${mrisess}_reference.nii.gz

        3dmask_tool -input ${outdir}/sub-${id}_ses-${mrisess}_reference.nii.gz -overwrite -prefix ${outdir}/sub-${id}_ses-${mrisess}_reference.nii.gz -dilate_result -1

    fi

    refval=`3dmaskave -quiet -mask ${outdir}/sub-${id}_ses-${mrisess}_reference.nii.gz ${pfx}_desc-rigid${mrisess}_pet.nii.gz`        
    3dcalc -a "${pfx}_desc-rigid${mrisess}_pet.nii.gz" -expr 'a/'${refval} -overwrite -prefix "${pfx}_desc-suvr${mrisess}_pet.nii.gz"

fi

# Partial-volume correction using iterative Yang.
tmpflist=(`ls ${t1dir}/*BrainSegmentationPosteriors*nii.gz`)
fslmerge -t "${outdir}/sub-${id}_ses-${mrisess}_IY_mask.nii.gz" ${tmpflist[@]:1:6}
pvc_iy "${pfx}_desc-suvr${mrisess}_pet.nii.gz" "${outdir}/sub-${id}_ses-${mrisess}_IY_mask.nii.gz" "${pfx}_desc-IY${mrisess}_pet.nii.gz" -x ${psfwhm} -y ${psfwhm} -z ${psfwhm}
3dcalc -a "${bmaskName}" -b "${pfx}_desc-IY${mrisess}_pet.nii.gz" -expr 'a*b' -overwrite -prefix "${pfx}_desc-IY${mrisess}_pet.nii.gz"

# Partial-volume correction using reblurred Van Cittert.
pvc_vc "${pfx}_desc-suvr${mrisess}_pet.nii.gz" "${pfx}_desc-RVC${mrisess}_pet.nii.gz" -x ${psfwhm} -y ${psfwhm} -z ${psfwhm}
3dcalc -a "${bmaskName}" -b "${pfx}_desc-RVC${mrisess}_pet.nii.gz" -expr 'a*b' -overwrite -prefix "${pfx}_desc-RVC${mrisess}_pet.nii.gz"

# JSP: insert code for SFS-RR partial-volume correction about here.

# Warp SUVR maps to template space.
antsApplyTransforms -d 3 -e 0 -i "${pfx}_desc-suvr${mrisess}_pet.nii.gz" -r ${tempName} -o "${pfx}_desc-suvrTemplate_pet.nii.gz" -t "${t1dir}/sub-${id}_ses-${mrisess}_SubjectToTemplate0GenericAffine.mat" -t "${t1dir}/sub-${id}_ses-${mrisess}_SubjectToTemplate1Warp.nii.gz"

antsApplyTransforms -d 3 -e 0 -i "${pfx}_desc-IY${mrisess}_pet.nii.gz" -r ${tempName} -o "${pfx}_desc-IYTemplate_pet.nii.gz" -t "${t1dir}/sub-${id}_ses-${mrisess}_SubjectToTemplate0GenericAffine.mat" -t "${t1dir}/sub-${id}_ses-${mrisess}_SubjectToTemplate1Warp.nii.gz"

antsApplyTransforms -d 3 -e 0 -i "${pfx}_desc-RVC${mrisess}_pet.nii.gz" -r ${tempName} -o "${pfx}_desc-RVCTemplate_pet.nii.gz" -t "${t1dir}/sub-${id}_ses-${mrisess}_SubjectToTemplate0GenericAffine.mat" -t "${t1dir}/sub-${id}_ses-${mrisess}_SubjectToTemplate1Warp.nii.gz"

# JSP: add warping of SFS-RR-corrected image to template space.

# Run QuANTs
for metricFile in "${pfx}_desc-suvr${mrisess}_pet.nii.gz" "${pfx}_desc-IY${mrisess}_pet.nii.gz" "${pfx}_desc-RVC${mrisess}_pet.nii.gz"; do
    python ${scriptdir}/pet_quants.py -N ${scriptdir}/atlases -o ${outdir} -s ${id} -S ${petsess} -t /project/ftdc_misc/pcook/quants/tpl-TustisonAging2019ANTs/template_description.json ${metricFile} ${t1dir}
    
#ap.add_argument('-d', '--debug', default=False,  action='store_true', help='debug')
#ap.add_argument('-N', '--network-dir', default=None,  action='store', required=True, help='network directory')
#ap.add_argument('-o', '--output-dir', default=None,  action='store', required=True, help='output directory')
#ap.add_argument('-s', '--subject', default=None, action='store', required=True, help='SubjectID')
#ap.add_argument('-S', '--session', default=None, action='store', required=True, help='SessionID')
#ap.add_argument('-t', '--template', default=None, action='store', required=True, help='template')
#ap.add_argument('-v', '--verbose', default=False,  action='store_true', help='verbose')

#ap.add_argument('PetFile', nargs=1, help='PETFilePath')
#ap.add_argument('AntsDir', nargs=1, help='ANTsCTDirPath')
#pet_quants.py: error: the following arguments are required: -N/--network-dir, -o/--output-dir, -s/--subject, -S/--session, -t/--template
#usage: pet_quants.py [-h] [-d] -N NETWORK_DIR -o OUTPUT_DIR -s SUBJECT -S
#                     SESSION -t TEMPLATE [-v]
#                     PetFile AntsDir

done

# JSP: need to at least make the template directory writeable; otherwise, if the script crashes out, it can't be deleted.
chgrp -R ftdclpc ${outdir}
chmod -R 775 ${outdir}

rm -rf ${outdir}/template
