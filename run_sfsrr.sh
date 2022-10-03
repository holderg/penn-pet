#!/bin/bash
#$ -S /bin/bash
 set -x -e

tracer=""

function pvc()
{
  id=$1

  PETfn=/home/srdas/wd/TAUPET/long/${id}/T00/${tracer}petpvc/T00_${id}_${tracer}pet.img;
  MRIfn=/home/srdas/wd/TAUPET/long/${id}/T00/${tracer}petpvc/T00_${id}_mprage.img;
  SEGfn=/home/srdas/wd/TAUPET/long/${id}/T00/${tracer}pvc/T00_${id}_hammers.img;
  c3d /home/srdas/wd/TAUPET/long/${id}/T00_${id}_${tracer}pet.nii.gz -type int -o $PETfn
  c3d /home/srdas/wd/TAUPET/long/${id}/T00_${id}_mprage.nii.gz -type int -o $MRIfn
  c3d /home/srdas/wd/TAUPET/long/${id}/T00/thickness/allhammerslabels.nii.gz -type int -o $SEGfn
  MATLAB_ROOT=/share/apps/matlab/R2009b_64


$MATLAB_ROOT/bin/matlab $MATOPT -nodisplay <<MAT5
  cd /home/srdas/bin/mrpet/pvc_sfsRR_2015_noninteractive
  pvc_sfsRR( '${PETfn}', '${MRIfn}', '${SEGfn}' );
MAT5
  c3d /home/srdas/wd/TAUPET/long/${id}/T00_${id}_${tracer}pet.nii.gz \
    /home/srdas/wd/TAUPET/long/${id}/T00/${tracer}petpvc/pvc_folder/T00_${id}_${tracer}pet_tmp_mask_pvc.img \
    -copy-transform -o /home/srdas/wd/TAUPET/long/${id}/T00_${id}_${tracer}pet_pvc.nii.gz
  c3d /home/srdas/wd/TAUPET/long/${id}/T00_${id}_mprage.nii.gz \
    /home/srdas/wd/TAUPET/long/${id}/T00_${id}_${tracer}pet_pvc.nii.gz \
    -reslice-matrix /home/srdas/wd/TAUPET/long/${id}/T00_${tracer}pet_to_T00_mprageANTs0GenericAffine_RAS.mat \
    -o /home/srdas/wd/TAUPET/long/${id}/T00_${tracer}pet_pvc_to_T00_mprageANTs.nii.gz
  c3d /home/srdas/wd/TAUPET/long/${id}/T00_${id}_tse.nii.gz \
    /home/srdas/wd/TAUPET/long/${id}/T00_${id}_${tracer}pet_pvc.nii.gz \
    -reslice-matrix /home/srdas/wd/TAUPET/long/${id}/T00_${tracer}pet_to_T00_tseANTs_RAS.mat \
    -o /home/srdas/wd/TAUPET/long/${id}/T00_${tracer}pet_pvc_to_T00_tseANTs.nii.gz

}

function main()
{
# for id in $(cat /home/srdas/wd/TAUPET/adnipet_Oct172016.csv); do
for id in $(cat /home/srdas/wd/TAUPET/long/sublist.txt); do

  mkdir -p /home/srdas/wd/TAUPET/long/${id}/T00/${tracer}petpvc/dump
  cd /home/srdas/wd/TAUPET/long/${id}/T00/${tracer}petpvc
  qsub -l h_vmem=7.1G,s_vmem=7G -V -cwd -o dump -j y -N "pvcamy_${id}" \
    $0 pvc $id
done

}

if [[ ! $1 ]]; then
  main
elif [[ $1 = "pvc" ]]; then
  pvc $2 $3
fi

