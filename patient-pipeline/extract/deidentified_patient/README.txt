This directory contains the script for extracting the data from the AHRQ Long 
COVID RedCAP Project named AHRQ Long COVID De-identified Patient Data PID 
35013.

After a new patient is referred to the study, their information is entered in
a separate RedCAP Project. This RedCAP project is maintained by the study staff
to collect information on patient characteristics and what sites they are 
recruited from. All patient information is deidentified.

Note well: The record_ids in the deidentified patien RedCAP project do not
match with those in the main Patient Survey data collection project.

The purpose of this script is to pull the RedCAP data set and place the data in
./patient-pipeline/data/raw/patient_deidentified.
