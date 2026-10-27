# /////////////////////////////////////////////////////////////////////////////
# Carlos Rodriguez PhD. Cu Anschutz Department of Family Medicine
# Extract RedCap Data from the Patient Survey for the AHRQ Long Covid project
# Pulls report id 176060, performs minor cleaning and stores in 
# ./patient-pipeline/data/raw
# /////////////////////////////////////////////////////////////////////////////

from datetime import datetime
from pathlib import Path

import pandas as pd
import urllib3
from dfm_tb.redcap import convert_timestamps, pull_report

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Pull the report in label format
data_label = pull_report(
  token = "LC_patient",
  id = "176060",
  type = "label"
)

# pull the column names to preserve order
names_data = data_label.columns.tolist()

# Remove the demographic Checked/Unchecked columns
data_label = data_label.loc[
    :, ~data_label.columns.str.startswith((
        "patient_race",
        "patient_insurance",
        "patient_employ",
        "redcap_event_name"
    ))
].copy()


# pull the demographic data and keep only the columns of with the select all 
# that apply columns in numerical format. The redcap_event_name is also 
# needed in numerical as opposed to label format.
demographics = pull_report(
  token = "LC_patient",
  id = "176060",
  type = "raw"
)

demographics = demographics.loc[
  :, 
  demographics.columns.str.startswith((
        "patient_race",
        "patient_insurance",
        "patient_employ",
  ))
  | (demographics.columns == "redcap_event_name")
].copy()

# Stitch together
data = pd.concat([
  data_label.reset_index(drop=True), 
  demographics.reset_index(drop=True)], 
  axis = 1
)

# Reorder the column names to match how the whole data set would be pulled since
# column position matters in subsequent steps.
data = data[names_data]


# Minor cleaning --------------------------------------------------------------
# Clean trailing space 
cols = ["name", "patient_first_name", "patient_last_name"]
data[cols] = data[cols].apply(lambda col: col.str.strip())

# Rename promis_record_id
# Change to the default RedCap field name for the row identifier to facilitate
# coding (less typing).
data = data.rename(columns={"promis_record_id": "record_id"})

# Time stamp columns
# Each RedCap timestamp column is in YYYY-MM-DD H:M:S format. Convert all
# timestamp columns in one go, rather than writing separate conversions on each
# timestamp when the need arises.
data = convert_timestamps(data)

# data[timestamp_cols]
# col = "patient_preenrollment_contact_information_timestamp"

# Strip the _arm_1 suffix from event_name
data["redcap_event_name"] = (data["redcap_event_name"]
  .str.replace("_arm_1", "", regex=False))

# Create a site_name variable by coalescing mdc_name and pcc_name
data["site_name"] = (
    data["pcc_name"]
    .fillna(data["mdc_name"])
)

# Set the record_id in the master data set to numeric
data["record_id"] = pd.to_numeric(data["record_id"])


# Coalesce PASC timestamps for T5 for record id 5 -----------------------------
# Record id 5 submitted a T5 PASC before there was a change to the RedCap
# instruments, where a new version of the T5 was implemented. This chunk
# consolidates the two instruments for Record id 5 only as this was the only
# affected patient.

# Set the original field names from pasc timestamp through complete
pasc_orig_cols = (data.loc[
  :, 
  "pasc_symptoms_and_followup_questions_timestamp":"pasc_symptoms_and_followup_questions_complete"]
  .columns)

# Set the updated field names from pasc t5 timestamp through complete
pasc_updated_cols = (data.loc[
  :, 
  "pasc_symptoms_and_followup_questions_t5_timestamp":"pasc_symptoms_and_followup_questions_t5_complete"]
  .columns)

# Check how the two field names in the two instruments differ
# The two sets of columns differ by two variables names notcovid1 and 
# notcovid_branch1 after removing the suffixes to harmonize the name
unmatched = set(pasc_updated_cols.str.replace("_t5", "", regex=False)) - set(pasc_orig_cols)

# Since the suffixes need to be removed to harmonize and create the unmatched
# object above, this replaces the _t5 suffix to be able to remove them from the
# updated columns object 
unmatched = {col + "_t5" for col in unmatched}

# Remove the unmatched field names from updated cols to arrive at a common set
# where the values in the new fields can be updated with the values in the
# original fields.
pasc_updated_cols = pasc_updated_cols[~pasc_updated_cols.isin(unmatched)]

# Create as mask for record id 5 at event t5_survey
mask = (data["record_id"] == 5) & (data["redcap_event_name"] == "t5_survey")

# Create a tuple mapping the original field names to the updated field
# names for the t5 pasc.
col_pairs = list(zip(pasc_updated_cols, pasc_orig_cols))

# Fill in record id # 5 from the original to the updated pasc fields
for updated_col, original_col in col_pairs:
    filled = data.loc[mask, updated_col].fillna(data.loc[mask, original_col])
    data[updated_col] = data[updated_col].astype(filled.dtype)
    data.loc[mask, updated_col] = filled

# Replace the values of the original instrument with NaN
for _, original_col in col_pairs:
    data.loc[mask, original_col] = None


# Output ----------------------------------------------------------------------
# Create timestamp
timestamp = datetime.now().strftime("%Y-%m-%d")

# Define output directory
output_dir = Path("patient-pipeline/data/raw/patient_survey")

# Save CSV
data.to_csv(
    output_dir / f"patients_{timestamp}.csv",
    index=False
)