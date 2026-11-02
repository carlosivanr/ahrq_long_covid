# /////////////////////////////////////////////////////////////////////////////
# Carlos Rodriguez PhD. Cu Anschutz Department of Family Medicine
# Extract RedCap Data from the Patient Survey for the AHRQ Long Covid project

# Pulls report id 194691
# ./patient-pipeline/data/raw

# Requires dfm_tb
# uv add "git+https://github.com/carlosivanr/dfm_tb"

# /////////////////////////////////////////////////////////////////////////////

import logging
import traceback
from datetime import datetime
from pathlib import Path

import urllib3
from dfm_tb.redcap import convert_timestamps, pull_report

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# /////////////////////////////////////////////////////////////////////////////


# Configure a script level logger to avoid using the root logger
log_path = Path(r"D:/ahrq_long_covid/patient-pipeline/logs/extract_patient_deidentified.log")
log_path.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
handler = logging.FileHandler(log_path)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

try:
    logger.info("Script started")

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
    # Create timestamp for writing the output file name
    timestamp = datetime.now().strftime("%Y-%m-%d")

    # Define output directory
    output_dir = Path("patient-pipeline/data/raw/patient_deidentified")

    # Save CSV
    data.to_csv(
        output_dir / f"patient_deidentified_{timestamp}.csv",
        index=False
    )

    logger.info("Script completed successfully")

except Exception:
    logger.error("Unhandled exception:\n" + traceback.format_exc())
    raise  # re-raise so Task Scheduler sees a non-zero exit code    