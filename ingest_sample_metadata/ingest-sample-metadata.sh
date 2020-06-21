#!/bin/bash

if [ -z "$1" ]; then
  echo must provide a tsv file containing Tissue Sample metadata
  echo correct usage: ingest-sample-metadata.sh sample-metadata.tsv
  exit 1
fi

if [ ! -f $1 ]; then
    echo file $1 does not exist
    exit 1
fi

../../ingest-validation-tools/src/validate_sample.py --path $1 && echo validation successful || echo validation failed; exit 1

python3 ingest_sample_metadata.py $1 && echo import successful || echo import failed; exit 1
