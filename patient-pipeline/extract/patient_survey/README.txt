This directory contains the primary script for extracting the longitudinal
survey data for the AHRQ Long COVID project. 

The purpose of this script is to pull the RedCAP data set, perform minimal
processing and place the data in ./patient-pipeline/data/raw.

The minimal processing steps are as follows:
1. Pull the demographic questions as a separate data set in a raw (0/1) format
  as opposed to labelled ("Checked"/"Unchecked") format to avoid having to 
  perform conversion. These data are then merged to the labelled dataset.
2. Perform stripping of white space in a select set of columns entered by a 
  person.
3. Convert all columns ending in _timestamp YYYY-MM-DD H:M:S to YYYY-MM-DD to
  facilitate performing date based manipulations.
4. Remove _arm_1 suffix from the redcap_event_name field to faciliate filtering
  for rows based on timepoint.
5. Rename promis_record_id to record_id to facilitate selecting columns based
  on column name
6. After RedCAP project went into production, an updated PASC survey instrument
  was implemented for the T5 timepoint. However one person had already taken 
  the original version. The script transfers the responses from the original
  fields to the new fields to harmonize the location of the T5 responses.