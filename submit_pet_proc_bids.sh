#!/bin/bash
# infile: a two-column csv file, no header row, with the full paths to the
# unprocessed PET file and the T1 BrainExtraction0N4 image from the ANTsCT
# output directory.

infile=${1}

cat ${infile} | while IFS="," read f t1; do
	fbase=`basename ${f}`
	fp=(${fbase//_/\ })
	subj=${fp[0]}
	petsess=${fp[1]}
	wd=/project/ftdc_pipeline/data/pet/${subj}/${petsess}
	if [[ ! -d ${wd} ]]; then mkdir -p ${wd}; fi
	cmd="bsub -J pet_proc_${subj}_${petsess} -o ${wd}/%J.stdout -e ${wd}/%J.stderr /project/ftdc_pet/PET/scripts/pet_proc_bids.sh ${f} ${t1}"
	echo $cmd
	$cmd
done

