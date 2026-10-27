# REDCap Patient Pipeline

ETL pipeline for extracting, transforming, and loading patient survey data from REDCap.

## Overview

This pipeline pulls de-identified patient and survey data from REDCap via API,
applies transformations, and produces structured outputs for downstream reporting.

## Setup

Requires Python 3.12+. Install dependencies with:

```bash
uv sync
```

The `dfm_tb` package is installed from a private GitHub repository and is included
as a dependency in `pyproject.toml`.

The following environment variables must be set before running the pipeline:

| Variable | Description |
|---|---|
| `LC_deident` | REDCap API token for the de-identified patient report |
| `LC_patient` | REDCap API token for the patient survey report |

## Pipeline

| Script | Description |
|---|---|
| `patient-pipeline/extract_patient_deidentified.py` | Extracts de-identified patient records from REDCap |
| `patient-pipeline/extract_patient_survey.py` | Extracts patient survey responses from REDCap |
| `patient-pipeline/transform/enrollment_management.py` | Transforms and manages enrollment data |

## Data

Raw data and outputs are not committed to this repo. Processed outputs are written to `patient-pipeline/data/`.

## Author

Carlos Rodriguez — carlos.i.rodriguez@cuanschutz.edu
