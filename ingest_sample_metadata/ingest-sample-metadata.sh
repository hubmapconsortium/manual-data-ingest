#!/bin/bash

if [ -z "$1" ]; then
  echo must provide a tsv file containing Tissue Sample metadata
  echo corect usage: ingest-sample-metadata.sh sample-metadata.tsv
  exit 1
fi

if [ ! -f $1 ]; then
    echo file $1 does not exist
    exit 1
fi

../../ingest-validation-tools/src/validate_sample.py --path $1 && echo validation sucessfull || echo validation failed; exit 1

python3 ingest-sample-metadata.py $1
