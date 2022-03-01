#!/appl/R-4.0/bin/Rscript

library(ANTsR)

args<-commandArgs(trailingOnly=T)

# Check that all required command-line arguments are present.
for (i in 1:length(args)) {
    cat("Arg", i, args[i],'\n')
}

if (length(args)<4) { stop('Must specify label index and image files, metric file, and output directory.') }
labIndex<-args[1]
labImage<-args[2]
metricFile<-args[3]
if (length(args) == 4) {
	outStem<-args[4]
	outFile <- paste(outStem,"LabelStats.csv", sep = "_")
} else {
    outFile <- gsub(".nii.gz", "_LabelStats.csv", metricFile)
}

# Define the function that will do all the work.
lpc_lstat <- function(labIndexFile,labImageFile,metricFile,exMaskFile=NA,outFile=NA) {
    # Read in text file with label indices & names.
    # These are csv for DKT31/BrainColor & tsv for Schaefer.
    if (tools::file_ext(labIndexFile) == "csv") {
        labs<-read.csv(labIndexFile)
    } else if (tools::file_ext(labIndexFile) == "tsv") {
        labs<-read.table(labIndexFile, sep = "\t", header = TRUE, stringsAsFactors = FALSE)
        labs <- labs[ ,c("index","name")]
        names(labs) <- c("Label.ID","Label.Name")
    }
	labs$Volume<-labs$SD<-labs$Max<-labs$Q3<-labs$Mean<-labs$Median<-labs$Q1<-labs$Min<-NA
	summvar<-c('Min','Q1','Median','Mean','Q3','Max')
	nround<-6

	labMask<-antsImageRead(labImageFile,3)
	metric<-antsImageRead(metricFile,3)
	
    # Mask the labels to exclude CSF and WM.
    segName <- Sys.glob(paste(dirname(labImageFile),'*BrainSegmentation.nii.gz',sep='/'))
    brainSeg <- antsImageRead(segName, 3)
	labMask <- maskImage(img.in = labMask, img.mask = brainSeg, level = c(2,4,5,6))

    # Calculate label volumes and summary statistics.
	hdr<-antsImageHeaderInfo(labImageFile)
	voxvol<-prod(hdr$spacing)
	for (i in 1:nrow(labs)) {
		labind<-labs$Label.ID[i]
		w<-which(as.numeric(labMask)==labind)
		if (length(w)>0) {
			x<-as.numeric(metric)[w]
			labs[i,summvar]<-summary(x,na.rm=T)
			labs$SD[i]<-sd(x,na.rm=T)
			labs$Volume[i]<-voxvol*length(w)
		}
		cat(labs$Label.ID[i], labs$Volume[i],'\n')
	}
	for (v in c(summvar,'SD')) { labs[,v]<-round(labs[,v],nround) }

    # Reshape to long format.
	labs<-reshape(labs,direction='long',idvar=c('Label.ID','Label.Name'),varying=
		list(c(summvar,'SD','Volume')),v.names='Value',timevar='Type',times=c(summvar,
		'SD','Volume'),new.row.names=1:(8*nrow(labs)))

	# Get intracranial volume from the volume of the brain extraction mask.
	if (is.na(exMaskFile)) {
		exMaskFile<-Sys.glob(paste(dirname(labImageFile),'*BrainExtractionMask.nii.gz',sep='/'))
	}
	icv<-labs[1,]
	icv$Label.ID<-NA
	icv$Label.Name<-'ICV'
	icv$Type<-'IntracranialVolume'
	exMask<-antsImageRead(exMaskFile,3)
	icv$Value<-voxvol*length(which(as.numeric(exMask)==1))
	
	# Use ICV to normalize regional volumes by head size.
	volsub<-subset(labs,labs$Type=='Volume')
	volsub$Value<-volsub$Value/icv$Value
	volsub$Type<-'NormalizedVolume'

    # Put together all the pieces.
	labs<-rbind(labs,volsub)
	labs<-rbind(labs,icv)
	labs<-labs[order(labs$Label.ID,labs$Type),]

    # Write results to csv.
	if (!is.na(outFile)) {
		write.csv(file=outFile,labs,row.names=F)
	}

    # Also return the results as a data frame (in interactive R sessions).
	return(labs)

}

# Call the function and write the results to a csv file.
lstat<-lpc_lstat(labIndexFile = labIndex,labImageFile = labImage,metricFile = metricFile, outFile = outFile)
