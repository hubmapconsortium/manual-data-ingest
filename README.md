## Data ingest utilities for HuBMAP

This repository contains various scripts used when managing HuBMAP data and metadata.

 - /util/ Contains miscellaneous script used for reporting various attributes and values from the existing data as well as for making simple modifications.
 - /ingest_vanderbilt_data Contains scripts for manually ingesting the Vanderbilt data, by breaking the various assay types into individual datasets, moving the data, registering it in the ingest database, creating Collections of data and ingesting the metadata.
 - /ingest_sample_metadata Contains a command line script used to import standard sample metadata .tsv files.

### Install dependencies

The data_ingest.properties file is used by many of the scripts for various configuration items.  Make sure you copy data_ingest.properties.example to data_ingest.properties and provide the required values

````
sudo pip3 install -r /requirements.txt
````

Note: if you need to use a modified version of the [HuBMAP commons] dependency, download the code and make changes, then install the dependency using `requirements_dev.txt` and make sure the local file system path is specified correctly.

