# /////////////////////////////////////////////////////////////////////////////
# Carlos Rodriguez PhD. Cu Anschutz Department of Family Medicine
# Extract RedCap Data from the Patient Survey for the AHRQ Long Covid project

# Pulls report id 194691
# ./patient-pipeline/data/raw

# Requires 
# uv add "git+https://github.com/carlosivanr/dfm_tb"

# /////////////////////////////////////////////////////////////////////////////


from datetime import datetime
from pathlib import Path

import pandas as pd
import urllib3
from dfm_tb.redcap import convert_timestamps, pull_report

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Pull the report in label format
data = pull_report(
  token = "LC_deident",
  id = "194691",
  type = "label"
)

# Minor cleaning --------------------------------------------------------------
# Time stamp columns
# Each RedCap timestamp column is in YYYY-MM-DD H:M:S format. The following for
# loop is to convert all timestamp columns in one go, rather than writing 
# separate conversions on each timestamp when the need arises.
data = convert_timestamps(data)

# Output ----------------------------------------------------------------------
# Create timestamp
timestamp = datetime.now().strftime("%Y-%m-%d")

# Define output directory
output_dir = Path("patient-pipeline/data/raw/patients_deidentified")

# Save CSV
data.to_csv(
    output_dir / f"patients_deidentified_{timestamp}.csv",
    index=False
)