'''
    Heuristic file for BIDS classification of positron emission tomography (PET) data
    collected at the University of Pennsylvania. The main function, infotodict, is defined
    below and takes sequence information from dicom headers; you can see which information
    is extracted by running fw-heudiconv-tabulate on the session directory, which writes
    the sequence info to a tsv file that can subsequently be read in as a Pandas
    dataframe. Each row of seqinfo corresponds to one series/acquisition in an imaging
    session.
    
    This heuristic is guided by the PET BIDS standard; however, it principally aims to
    comply with file naming conventions and does not attempt to satisfy minimum require-
    ments for BIDS-compliant pharmacokinetic analysis of dynamic scan data. Additionally,
    it only provides BIDS naming for dynamic, attenuation-corrected images as well as
    the rigid-body motion correction of the same; most series are left as non-BIDS.
        
'''

import datetime
import numpy as np

def create_key(template, outtype=('nii.gz',), annotation_classes=None):
    if template is None or not template:
        raise ValueError('Template must be a valid format string')
    return template, outtype, annotation_classes

# PET acquisition types
# Tau
av1451 = create_key('sub-{subject}/{session}/pet/sub-{subject}_{session}_trc-AV1451_rec-acydyn_pet')
pi2620_suvr30_60 = create_key('sub-{subject}/{session}/pet/sub-{subject}_{session}_trc-PI2620_rec-acdyn3060_pet')
pi2620_suvr45_75 = create_key('sub-{subject}/{session}/pet/sub-{subject}_{session}_trc-PI2620_rec-acdyn4575_pet')
pi2620_suvr_other = create_key('sub-{subject}/{session}/pet/sub-{subject}_{session}_trc-PI2620_rec-othersum_pet')
pi2620_dyn0_61 = create_key('sub-{subject}/{session}/pet/sub-{subject}_{session}_trc-PI2620_rec-acdyn31frm_pet')
pi2620_dyn_other = create_key('sub-{subject}/{session}/pet/sub-{subject}_{session}_trc-PI2620_rec-otherdyn_pet')
# Amyloid
fbb = create_key('sub-{subject}/{session}/pet/sub-{subject}_{session}_trc-FLORBETABEN_rec-acdyn_pet')
fbp = create_key('sub-{subject}/{session}/pet/sub-{subject}_{session}_trc-FLORBETAPIR_rec-acdyn_pet')

from collections import defaultdict
def infotodict(seqinfo):
    """Heuristic evaluator for determining which runs belong where
        allowed template fields - follow python string module:
        index: index within category
        subject: participant id
        seqindex: run number during scanning
        subindex: sub index within group
    """

    info = {
        av1451: [],
        pi2620_suvr30_60: [],
        pi2620_suvr45_75: [],
        pi2620_suvr_other: [],
        pi2620_dyn0_61: [],
        pi2620_dyn_other: [],
        fbb: [],
        fbp: []
    }
    
    for s in seqinfo:
        protocol = s.protocol_name.lower().replace("[","").replace("]","").replace("/","").replace("-","_").replace(" ","_").replace("__","_")
        desc = s.series_description.lower().replace(" ","_").replace("__","_")
        id = s.series_id
        if all([st in desc for st in ["dy","ctac"]]):
            if ("av_1451" in desc) or ("av1451" in desc):
                info[av1451].append(id)
            elif ("av45" in desc) or ("florbetapir" in desc):
                info[fbp].append(id)
            elif ("fbb" in desc) or ("florbetaben" in desc) or ("amyloid" in desc):
                info[fbb].append(id)
            elif ("pi_2620" in desc) or ("pi2620" in desc):
                if ("30_60sum" in desc):
                    info[pi2620_suvr30_60].append(id)
                elif ("sum" in desc):
                    info[pi2620_suvr_other].append(id)
                elif ("31frm" in desc):
                    info[pi2620_dyn0_61].append(id)
                elif "frm" in desc:
                    info[pi2620_dyn_other].append(id)
                else:
                    info[pi2620_suvr45_75].append(id)
        else:
            print("Series not recognized!: ", protocol, s.dcm_dir_name)
    
    return info

#def ReplaceSession(sesname):
#    return sesname[:13].replace("-", "x").replace(".","x").replace("_","x")

#def ReplaceSubject(subjname):
#    return subjname[:10].replace("-", "x").replace(".","x").replace("_","x")

MetadataExtras = {
    av1451: {
       "TracerName": "AV1451",
       "TracerRadionuclide": "F18",
       "InjectedRadioactivity": 0,
       "InjectedRadioactivityUnits": "MBq",
       "InjectedMass": "n/a",
       "InjectedMassUnits": "ug",
       "SpecificRadioactivity": "n/a",
       "SpecificRadioactivityUnits": "Bq/g",
       "ModeOfAdministration": "bolus",
       "TimeZero": "00:00:00",
       "ScanStart": 2700,
       "InjectionStart": 0,
       "FrameTimesStart": [2700, 3000, 3300, 3600, 3900, 4200],
       "FrameDuration": [300, 300, 300, 300, 300, 300],
       "AcquisitionMode": "list mode",
       "ImageDecayCorrected": True,
       "ImageDecayCorrectionTime": 2700,
       "ReconMethodName": "blob-os-tf",
       "ReconMethodParameterLabels": ["unknown"],
       "ReconFilterType": ["unknown"],
       "AttenuationCorrection": "CTAC-SG",
       "Manufacturer": "Philips",
       "ManufacturersModelName": "Ingenuity TF",
       "Units": "Bq/mL",
       "BodyPart": "HEAD_NECK"
   },
   fbb: {
       "TracerName": "FLORBETABEN",
       "TracerRadionuclide": "F18",
       "InjectedRadioactivity": 0,
       "InjectedRadioactivityUnits": "MBq",
       "InjectedMass": "n/a",
       "InjectedMassUnits": "ug",
       "SpecificRadioactivity": "n/a",
       "SpecificRadioactivityUnits": "Bq/g",
       "ModeOfAdministration": "bolus",
       "TimeZero": "00:00:00",
       "ScanStart": 5400,
       "InjectionStart": 0,
       "FrameTimesStart": [5400, 5700, 6000, 6300],
       "FrameDuration": [300, 300, 300, 300],
       "AcquisitionMode": "list mode",
       "ImageDecayCorrected": True,
       "ImageDecayCorrectionTime": 5400,
       "ReconMethodName": "blob-os-tf",
       "ReconMethodParameterLabels": ["unknown"],
       "ReconFilterType": ["unknown"],
       "AttenuationCorrection": "CTAC-SG",
       "Manufacturer": "Philips",
       "ManufacturersModelName": "Ingenuity TF",
       "Units": "Bq/mL",
       "BodyPart": "HEAD_NECK"
   },
   fbp: {
       "TracerName": "FLORBETAPIR",
       "TracerRadionuclide": "F18",
       "InjectedRadioactivity": 0,
       "InjectedRadioactivityUnits": "MBq",
       "InjectedMass": "n/a",
       "InjectedMassUnits": "ug",
       "SpecificRadioactivity": "n/a",
       "SpecificRadioactivityUnits": "Bq/g",
       "ModeOfAdministration": "bolus",
       "TimeZero": "00:00:00",
       "ScanStart": 3000,
       "InjectionStart": 0,
       "FrameTimesStart": [3000, 3300],
       "FrameDuration": [300, 300],
       "AcquisitionMode": "list mode",
       "ImageDecayCorrected": True,
       "ImageDecayCorrectionTime": 3000,
       "ReconMethodName": "blob-os-tf",
       "ReconMethodParameterLabels": ["unknown"],
       "ReconFilterType": ["unknown"],
       "AttenuationCorrection": "CTAC-SG",
       "Manufacturer": "Philips",
       "ManufacturersModelName": "Ingenuity TF",
       "Units": "Bq/mL",
       "BodyPart": "HEAD_NECK"
   },
   pi2620_suvr30_60: {
       "TracerName": "PI2620",
       "TracerRadionuclide": "F18",
       "InjectedRadioactivity": 0,
       "InjectedRadioactivityUnits": "MBq",
       "InjectedMass": "n/a",
       "InjectedMassUnits": "ug",
       "SpecificRadioactivity": "n/a",
       "SpecificRadioactivityUnits": "Bq/g",
       "ModeOfAdministration": "bolus",
       "TimeZero": "00:00:00",
       "ScanStart": 1800,
       "InjectionStart": 0,
       "FrameTimesStart": [1800, 2100, 2400, 2700, 3000, 3300],
       "FrameDuration": [300, 300, 300, 300, 300, 300],
       "AcquisitionMode": "list mode",
       "ImageDecayCorrected": True,
       "ImageDecayCorrectionTime": 1800,
       "ReconMethodName": "blob-os-tf",
       "ReconMethodParameterLabels": ["unknown"],
       "ReconFilterType": ["unknown"],
       "AttenuationCorrection": "CTAC-SG",
       "Manufacturer": "Philips",
       "ManufacturersModelName": "Ingenuity TF",
       "Units": "Bq/mL",
       "BodyPart": "HEAD_NECK"
   },
   pi2620_suvr45_75: {
       "TracerName": "PI2620",
       "TracerRadionuclide": "F18",
       "InjectedRadioactivity": 0,
       "InjectedRadioactivityUnits": "MBq",
       "InjectedMass": "n/a",
       "InjectedMassUnits": "ug",
       "SpecificRadioactivity": "n/a",
       "SpecificRadioactivityUnits": "Bq/g",
       "ModeOfAdministration": "bolus",
       "TimeZero": "00:00:00",
       "ScanStart": 1800,
       "InjectionStart": 0,
       "FrameTimesStart": [2700, 3000, 3300, 3600, 3900, 4200],
       "FrameDuration": [300, 300, 300, 300, 300, 300],
       "AcquisitionMode": "list mode",
       "ImageDecayCorrected": True,
       "ImageDecayCorrectionTime": 2700,
       "ReconMethodName": "blob-os-tf",
       "ReconMethodParameterLabels": ["unknown"],
       "ReconFilterType": ["unknown"],
       "AttenuationCorrection": "CTAC-SG",
       "Manufacturer": "Philips",
       "ManufacturersModelName": "Ingenuity TF",
       "Units": "Bq/mL",
       "BodyPart": "HEAD_NECK"
   },
   pi2620_suvr_other: {
       "TracerName": "PI2620",
       "TracerRadionuclide": "F18",
       "InjectedRadioactivity": 0,
       "InjectedRadioactivityUnits": "MBq",
       "InjectedMass": "n/a",
       "InjectedMassUnits": "ug",
       "SpecificRadioactivity": "n/a",
       "SpecificRadioactivityUnits": "Bq/g",
       "ModeOfAdministration": "bolus",
       "TimeZero": "00:00:00",
       "ScanStart": 0,
       "InjectionStart": 0,
       "FrameTimesStart": [0],
       "FrameDuration": [300],
       "AcquisitionMode": "list mode",
       "ImageDecayCorrected": True,
       "ImageDecayCorrectionTime": 0,
       "ReconMethodName": "blob-os-tf",
       "ReconMethodParameterLabels": ["unknown"],
       "ReconFilterType": ["unknown"],
       "AttenuationCorrection": "CTAC-SG",
       "Manufacturer": "Philips",
       "ManufacturersModelName": "Ingenuity TF",
       "Units": "Bq/mL",
       "BodyPart": "HEAD_NECK"
   },
   pi2620_dyn0_61: {
       "TracerName": "PI2620",
       "TracerRadionuclide": "F18",
       "InjectedRadioactivity": 0,
       "InjectedRadioactivityUnits": "MBq",
       "InjectedMass": "n/a",
       "InjectedMassUnits": "ug",
       "SpecificRadioactivity": "n/a",
       "SpecificRadioactivityUnits": "Bq/g",
       "ModeOfAdministration": "bolus",
       "TimeZero": "00:00:00",
       "ScanStart": 0,
       "InjectionStart": 0,
       "FrameTimesStart": [0, 15, 30, 45, 60, 90, 120,
           180, 210, 240, 270, 300, 360, 420, 480, 540,
           600, 660, 720, 780, 840, 1020, 1200, 1500,
           1800, 2100, 2400, 2700, 3000, 3300, 3600],
       "FrameDuration": [15, 15, 15, 15, 30, 30, 30, 30,
           30, 30, 30, 30, 60, 60, 60, 60, 60, 60, 60, 
           60, 60, 180, 180, 300, 300, 300, 300, 300, 
           300, 300, 300],
       "AcquisitionMode": "list mode",
       "ImageDecayCorrected": True,
       "ImageDecayCorrectionTime": 0,
       "ReconMethodName": "blob-os-tf",
       "ReconMethodParameterLabels": ["unknown"],
       "ReconFilterType": ["unknown"],
       "AttenuationCorrection": "CTAC-SG",
       "Manufacturer": "Philips",
       "ManufacturersModelName": "Ingenuity TF",
       "Units": "Bq/mL",
       "BodyPart": "HEAD_NECK"
   },
   pi2620_dyn_other: {
       "TracerName": "PI2620",
       "TracerRadionuclide": "F18",
       "InjectedRadioactivity": 0,
       "InjectedRadioactivityUnits": "MBq",
       "InjectedMass": "n/a",
       "InjectedMassUnits": "ug",
       "SpecificRadioactivity": "n/a",
       "SpecificRadioactivityUnits": "Bq/g",
       "ModeOfAdministration": "bolus",
       "TimeZero": "00:00:00",
       "ScanStart": 0,
       "InjectionStart": 0,
       "FrameTimesStart": [0, 15, 30, 45, 60, 90, 120,
           180, 210, 240, 270, 300, 360, 420, 480, 540,
           600, 660, 720, 780, 840, 1020, 1200, 1500,
           1800, 2100, 2400, 2700, 3000, 3300, 3600],
       "FrameDuration": [15, 15, 15, 15, 30, 30, 30, 30,
           30, 30, 30, 30, 60, 60, 60, 60, 60, 60, 60, 
           60, 60, 180, 180, 300, 300, 300, 300, 300, 
           300, 300, 300],
       "AcquisitionMode": "list mode",
       "ImageDecayCorrected": True,
       "ImageDecayCorrectionTime": 0,
       "ReconMethodName": "blob-os-tf",
       "ReconMethodParameterLabels": ["unknown"],
       "ReconFilterType": ["unknown"],
       "AttenuationCorrection": "CTAC-SG",
       "Manufacturer": "Philips",
       "ManufacturersModelName": "Ingenuity TF",
       "Units": "Bq/mL",
       "BodyPart": "HEAD_NECK"
   }
}       
