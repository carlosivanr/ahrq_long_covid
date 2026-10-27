# /////////////////////////////////////////////////////////////////////////////
# Carlos Rodriguez PhD. Cu Anschutz Department of Family Medicine
# The purpose of this script is to utilize the raw patient survey data to clean
# the first two events in the redcap project. These data are useful in 
# understanding how many patients have been referred, screened, how many have
# met eligibility, and how many went on to submit a T1 PASC survey.
# /////////////////////////////////////////////////////////////////////////////

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# //////////////////////// Import raw .csv REDCap data ////////////////////////
# Set the file path to the most recent data pull
file_path = max(Path("./patient-pipeline/data/raw/patient_survey").glob("*.csv"))

# Import all columns as string
data = pd.read_csv(file_path, dtype="string")

# Set record_id to numeric
data["record_id"] = pd.to_numeric(data["record_id"])


# Filter the data to the first two redcap events
# These events are for pre-enrollment and screening to determine eligibility.
# These events serve as the primary rows for managing participant enrollment.
management = data.loc[
    data["redcap_event_name"].isin([
        "patient_preenrollm_arm_1",
        "screening_and_enro_arm_1"
    ])
].copy()

# Select the columns from the first two redcap events
management = management.loc[
    :, "record_id":"patient_enrollment_form_complete"
]


# //////////////////////////////// Exclusions ////////////////////////////////
# The management redcap events contain test records and "duplicate" records
# where a member of the team may have inadvertently created a 2nd record for
# a potential participant to be screened. These need to be identified and 
# removed, otherwise any subsequent counts of participants may be 
# inaccurate. 

# Use the working file to eliminate pre-defined test and some duplicate records.
record_exclusions = pd.read_csv(
  "./patient-pipeline/config/record_exclusions.csv")

management = management.loc[
  ~management["record_id"].isin(record_exclusions["record_id"]
  )
]

# Search the following columns for "test". Search must be restricted to selected
# columns, otherwise "tested positive for COVID" could come up if other columns
# are used.

# Creates a data frame of logicals that can be used to find columns or rows in
# the management data frame
test_columns = [
    "record_id", 
    "enrollstatus", 
    "study_label",
    "not_enrolled_status"
]

test_matches = management[test_columns].astype("string").apply(
    lambda col: col.str.contains("test", case=False, na=False)
)

# Create a series if any of the rows contain "test"
test_rows = test_matches.any(axis=1)

# Display the matching rows if any
if sum(test_rows) != 0:
    management.loc[test_rows]


# Check for "duplicate" in the enrollstatus, study label, and not_enrolled
# columns.
dupe_columns = [
    "enrollstatus", 
    "study_label",
    "not_enrolled_status"
]

dupe_matches = management[dupe_columns].astype("string").apply(
    lambda col: col.str.contains("duplicate", case=False, na=False)
)

dupe_rows = dupe_matches.any(axis=1)

if sum(dupe_rows) != 0:
    management.loc[dupe_rows]


# To prevent pipeline from breaking, set aside test and dupes to verify in a
# separate file. Then the ./config/exclusions files can be updated for a
# subsequent iteration of the pipeline.

# Records identified as having a "test" or "duplicate" in a pre-selected set
# of columns
unverified_records = (
    pd.concat(
        [management.loc[test_rows], management.loc[dupe_rows]], 
        axis = 0)
)

# Remove any records that need verification to process as normal
management = management.loc[
    ~management["record_id"].isin(unverified_records["record_id"])
]

# Perform an additional check for duplicated names, emails, phone numbers. This
# is a second layer in case there are patients with duplicated information, but
# have not been marked as duplicates by the study team.
def find_duplicates(df, columns, id_col="record_id"):
    results = {}

    for col in columns:
        mask = df[col].notna() & df[col].duplicated(keep=False)
        results[col] = df.loc[mask, id_col].tolist()

    return results

duplicated_pt_ids = find_duplicates(
    management,
    ["name", "email", "patient_email_address"]
)

duplicated_rows = management.loc[
    management["record_id"].isin(
        duplicated_pt_ids["name"] + duplicated_pt_ids["email"]
    )
]

# Concatenate the data frame consisting of unverified records and the data 
# frame that flagged possible duplicated patients
unverified_records = pd.concat(
    [unverified_records, duplicated_rows],
    axis = 0
)

# Remove the duplicated record_ids from the management data frame
management = management.loc[
    ~management["record_id"].isin(
        unverified_records["record_id"]
    )
]

# Create timestamp
timestamp = datetime.now().strftime("%Y-%m-%d")

# Define output directory
output_dir = Path("patient-pipeline/data/validation")

# Save CSV
unverified_records.to_csv(
    output_dir / f"unverified_records_{timestamp}.csv",
    index=False
)


# /////////////////////// Updated current_enroll_status ///////////////////////
# Create an updated enroll status column, this coalesces the not_enrolled_status
# and the enrollstatus columns
management["current_enroll_status"] = (
    management["not_enrolled_status"]
    .fillna(management["enrollstatus"])
)

# Get the ids of those that are categorized as "Enrollment completed" at the 
# end of the participant mangement workflow
enrollment_comp_ids = management.loc[
    management["current_enroll_status"] == "Enrollment completed",
    "record_id"
]

# Get the ids of those that submitted a PASC instrument since it triggers the
# subsequent T2 through T5 surveys. Those with a missing T1 PASC are reverted
# to not enrolled regardless of consent and prior enrollment status
t1_pasc_comp_ids = data.loc[
    (data["redcap_event_name"] == "consent_and_t1_sur_arm_1")
    &
    (data["pasc_symptoms_and_followup_questions_complete"] == "Complete"),
    "record_id"
]

missing_t1_pasc_ids = enrollment_comp_ids.loc[
    ~enrollment_comp_ids.isin(t1_pasc_comp_ids)
]

# Update the current enrollment status
management.loc[
    management["record_id"].isin(missing_t1_pasc_ids),
    "current_enroll_status"
] = "partial enrollment only (said they wanted to enroll but never completed T1 PASC)"

# ////////////////// Clean the current_enroll_status column ///////////////////
# Enrollment completed = someone who is eligible, agreed to enroll, and
# completed a T1
# No response       = someone who was referred, but study team was unable to contact
# Partial           = Eligible, and agreed, but did not consent or complete T1
# Declined          = someone who was eligible but did not want to participate
# Not eligible      = did not meet eligibility criteria
# Formally withdrew = Eligible and enrolled, but asked to withdraw from the study.

col = "current_enroll_status"

management.loc[management[col].str.contains("left", case=False, na=False), col] = "Formally withdrew"
management.loc[management[col].str.contains("stopped", case=False, na=False), col] = "No response"
management.loc[management[col].str.contains("declined", case=False, na=False), col] = "Declined"
management.loc[management[col].str.contains("partial", case=False, na=False), col] = "Partial"
management.loc[management[col].str.contains("eligible", case=False, na=False), col] = "Not eligible"

management["current_enroll_status"].value_counts()


#////////////////////////////// Tidy Data Frame ///////////////////////////////
# Collapse rows to make it a tidy data set and drop unnecessary columns
management = (management
  .groupby("record_id", as_index=False)
  .first()
  .drop(columns = ["redcap_event_name", "redcap_survey_identifier"])
)


# ///////////////////////// Create number of contacts /////////////////////////
management["outreach_count"] = (
    management.loc[:, "date_outreach":"date_outreach_5"]
    .notna()
    .sum(axis=1)
)


# ////////////////////////////// Consent Column ///////////////////////////////
# Create a new column, if patient consented at t1 
t1_consented_ids = data.loc[
    (data["redcap_event_name"] == "consent_and_t1_sur_arm_1")
    &
    (~data["consent_name"].isna()),
    "record_id"
]

management["consented"] = (
    management["record_id"]
    .isin(t1_consented_ids)
    .map({True: "Yes", False: "No"})
)


consent_timestamps = data.loc[
    (data["redcap_event_name"] == "consent_and_t1_sur_arm_1")
    &
    (~data["consent_name"].isna()),
    ["record_id", "patient_consent_form_timestamp"]
]

management = management.merge(
    consent_timestamps, 
    on="record_id", 
    how="left"
    )

(management
    .rename(
        columns={"patient_consent_form_timestamp": "consent_date"}, 
        inplace=True
        )
)


# /////////////////////////// PASC Complete columns ///////////////////////////
# Create a new column, if record id is in t1 completed ids, set to Yes
# otherwise No.
management["t1_pasc_complete"] = (
    management["record_id"]
    .isin(t1_pasc_comp_ids)
    .map({True: "Yes", False: "No"}))

# Set the missing values to "TBD"
management["current_enroll_status"] = (
    management["current_enroll_status"]
    .fillna("TBD") 
)

# Set a tuple with the name of the RedCap event, the respective time stamp 
# field, and the output column name. These will be fed into a subsequent 
# for-loop to merge in the PASC time stamp dates if available.


date_fields = [
    ("consent_and_t1_sur_arm_1", "pasc_symptoms_and_followup_questions_timestamp",    "t1_pasc_date"),
    ("t2_survey_arm_1",          "pasc_symptoms_only_t2_t4_timestamp",                "t2_pasc_date"),
    ("t3_survey_arm_1",          "pasc_symptoms_only_t2_t4_timestamp",                "t3_pasc_date"),
    ("t4_survey_arm_1",          "pasc_symptoms_only_t2_t4_timestamp",                "t4_pasc_date"),
    ("t5_survey_arm_1",          "pasc_symptoms_and_followup_questions_t5_timestamp", "t5_pasc_date")
]

# Since the master data contains all records, this for-loop filters to only
# those in the management data frame
for event, ts_col, new_col in date_fields:
    dates = data.loc[
        data["record_id"].isin(management["record_id"]) & (data["redcap_event_name"] == event),
        ["record_id", ts_col]
    ].rename(columns={ts_col: new_col})
    management = management.merge(dates, on="record_id", how="left")


# Calculate the number of days since the T1 complete date
management["days_since_t1"] = (
    pd.Timestamp.today().normalize() - pd.to_datetime(management["t1_pasc_date"])
    ).dt.days

# Set a tuple as an input to caculate the date that a subsequent PASC was due allowing for a 
# 14 day grace period to submit a survey.
due_dates =[
    (90 , "due_date_for_t2" ),
    (180, "due_date_for_t3" ),
    (270, "due_date_for_t4" ),
    (360, "due_date_for_t5" )]

for delta, new_col in due_dates:
    management[new_col] = (pd.to_datetime(management["t1_pasc_date"]) + timedelta(days=(delta + 14))).dt.date

# Create a set of columns that indicate the status of a subsequent PASC
# Not Due = A patient has not been in the study long enough to receive and
# invite to submit a PASC
# Overdue = It has been more than 14 days since the invite to submit a PASC was
# sent. These would be considered missing values for all instruments.
# Due for t* = A patient is within the 14 day grace period to submit a PASC.

pasc_status = [
    (90, "t2_status"),
    (180, "t3_status"),
    (270, "t4_status"),
    (360, "t5_status")
]

for delta, new_col in pasc_status:
    col_name = "Due for " + new_col[:2]
    management[new_col] = np.select(
    [
        management["days_since_t1"] < delta,
        (management["days_since_t1"] >= delta) & (management["days_since_t1"] < (delta + 14)),
        management["days_since_t1"] >= (delta + 14),
    ],
    ["Not Due", col_name, "Overdue"],
    default=pd.NA
)

# The columns created in the prior step are modified, so that if a date is
# present in the t*_pasc_date columns, then the status is modified to
# "Complete". Having a t*_pasc_date indicates that the patient submitted a
# that instrument whereas missing values indicate there was no submission
# i.e. a missing instrument. 
pasc_complete = [
    ("t2_pasc_date", "t2_status"),
    ("t3_pasc_date", "t3_status"),
    ("t4_pasc_date", "t4_status"),
    ("t5_pasc_date", "t5_status")
]

for date, status in pasc_complete:
    management[status] = np.where(
    management[date].notna(),
    "Complete",
    management[status]
)


# /////////////// Identify those that have been lost to followup //////////////
management["LTFU"] = np.select(
    [
        (management["t2_status"] == "Overdue") & (management["t3_status"] == "Overdue") & (management["t4_status"] == "Overdue") & (management["t5_status"] == "Overdue"),
        (management["t3_status"] == "Overdue") & (management["t4_status"] == "Overdue") & (management["t5_status"] == "Overdue"),
        (management["t4_status"] == "Overdue") & (management["t5_status"] == "Overdue"),
        management["t5_status"] == "Overdue",
    ],
    ["T2", "T3", "T4", "T5"],
    default=pd.NA
)


# /////////////////////////////////// Output //////////////////////////////////
# Create timestamp
timestamp = datetime.now().strftime("%Y-%m-%d")

# Define output directory
output_dir = Path("patient-pipeline/data/clean/management")

# Save CSV
management.to_csv(
    output_dir / f"enrollment_management_{timestamp}.csv",
    index=False
)