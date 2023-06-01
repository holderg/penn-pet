#!/bin/bash
# infile: a two-column csv file, no header row, with the full paths to the
# unprocessed PET file and the T1 BrainSegmentation0N4 image from the ANTsCT
# output directory.

infile=${1}
scriptdir=`dirname $0`

cat ${infile} | while IFS="," read f t1; do
	fbase=`basename ${f}`
	fp=(${fbase//_/\ })
	subj=${fp[0]}
	petsess=${fp[1]}
	wd=/project/ftdc_pipeline/data/pet/${subj}/${petsess}
	if [[ ! -d ${wd} ]]; then mkdir -p ${wd}; fi
	logstem=/project/ftdc_pipeline/data/pet/logs/${subj}_${petsess}
	cmd="bsub -J pet_proc_${subj}_${petsess} -o ${logstem}_%J.stdout -e ${logstem}_%J.stderr ${scriptdir}/pet_proc_bids.sh ${f} ${t1}"
	echo $cmd
	$cmd
done

