import sys
import os
from hubmap_commons import string_helper
from hubmap_commons import file_helper
from hubmap_commons.exceptions import ErrorMessage 
import traceback
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tsv_file_helper import TSVFile
from ingest_props import IngestProps
from id_helper import UUIDHelper
import time
import logging
import json
import requests

#Sample metadata ingest.  Run from the command line, the input tsv file can be specified
#as the single command line argument or in the properties file, ../data_ingest.propertes
#with the command line version being used first.  The ../data_ingest.properties file needs
#to have the following properties:
# globus.app.client.id
# globus.app.client.secret
# sample.metadata.tsf.file (or on command line)
# entity.api.url
# uuid.api.url
# nexus.token
#
#

#class to ingest metadata stored in .tsv files into Sample entities
#the .tsv files are expected to have on line per Sample (no duplicates)
#each row is converted to json where the header name of each column will
#be converted to an attribute name in the json.
#on column with header name sample_id is required and will be used to
#map to the Sample that will be updated, the sample ID can be a Hubamp ID (DOI Display ID)
#a Component ID (HuBMAP Display ID) or a HuBMAP UUID. The converted json will be sotred
#in the Sample.metadata (Sample.Metadata.metadata) field as json converted to text.
#The sample_id column will be excluded.
#
#
class SampleIngest:
    
    #initialize, set variables from properties and/or command line,
    #check the auth token and read the tsv file data into a dictionary
    #and the header labels into a list
    def __init__(self, property_file_name):
        self.log_filename = "sample-metadata-import" + time.strftime("%d-%m-%Y-%H-%M-%S") + ".log"
        self.logger = logging.getLogger('entity.service')
        self.logger.setLevel(logging.INFO)
        logFH = logging.FileHandler(self.log_filename)
        self.logger.addHandler(logFH)
        self.dataset_info = None
        self.dataset_info_tsv_path = None
        self.props = IngestProps(property_file_name, required_props = ['entity.api.url', 'nexus.token', 'globus.app.client.id', 'globus.app.client.secret'])
        self.entity_api_url = self.props.get('entity.api.url')
        self.token = self.props.get('nexus.token')
        if len(sys.argv) >= 2:
            self.metadata_file = sys.argv[1]
        else:
            self.metadata_file = self.props.get('sample.metadata.tsv.file')
            if string_helper.isBlank(self.metadata_file):
                raise ErrorMessage("ERROR: Metadata file must be specified in " + self.prop_file_name + " or as the first argument on the command line")
        if not os.path.isfile(self.metadata_file):
            raise ErrorMessage("ERROR: Input file " + self.metadata_file + " does not exist.")
        
        metadata_file = TSVFile(self.metadata_file)
        if not 'sample_id' in metadata_file.get_header_keys():
            raise ErrorMessage("ERROR: Required sample_id column not found in " + self.metadata_file)
        self.metadata = metadata_file.get_records()
        self.uuid_helper = UUIDHelper(ingest_props = self.props)
        self.ingested_ids = {}
        
    #iterate through the metadata rows, convert each row to json and
    #import
    def ingest_metadata(self):
        row_num = 0
        for data_row in self.metadata:
            row_num = row_num + 1
            sample_id = data_row['sample_id']
            if string_helper.isBlank(sample_id):
                msg = "ID missing for row number " + str(row_num)
                print(msg)
                self.logger.warning(msg)
                continue
            
            #resolved the id to the UUID via the UUID service
            uuid = self.uuid_helper.resolve_to_uuid(sample_id)
            if uuid is None:
                msg = "UUID not found for sample_id " + sample_id + " row number " + str(row_num)
                print(msg)
                self.logger.warning(msg)
                continue
            
            if uuid in self.ingested_ids:
                msg = "Not imported uuid: " + uuid + " already imported with sample id " + self.ingested_ids[uuid] + "  current instance with sample id " + sample_id + " in row " + str(row_num) + " will not by ingested"
                print(msg)
                self.logger.warning(msg)
                continue
            
            self.ingested_ids[uuid] = sample_id
            
            #save the metadata to the Sample
            if not self.ingest_sample_metadata(data_row, uuid, sample_id, row_num):
                continue
            
            msg = "Updated metadata for " + sample_id + " row number " + str(row_num)
            print(msg)
            self.logger.info(msg)
            
    def ingest_sample_metadata(self, metadata, uuid, sample_id, row_num):                
        update_recd = {}
        update_recd['metadata'] = metadata
        
        header = {'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'}
        url = file_helper.ensureTrailingSlashURL(self.entity_api_url) + "samples/" + uuid
        resp = requests.put(url, headers=header, data=json.dumps(update_recd), verify=False)
        status_code = resp.status_code
        if status_code != 200:
            msg = "unable to update metadata on Sample info for id: " + sample_id + " row  number " + str(row_num)
            print(msg + " Check the log file " + self.log_filename)
            self.logger.error(msg)
            self.logger.error("Web service return code " + str(status_code))
            self.logger.error("Web service response ") + resp.text
            return False
        return True

try:
    ingest_worker = SampleIngest("../data_ingest.properties")
    ingest_worker.ingest_metadata()
    exit(0)
except ErrorMessage as em:                                                                                                            
    print(em.get_message())
    exit(1)    
except Exception as e:                                                                                                            
    exc_type, exc_value, exc_traceback = sys.exc_info()
    eMsg = str(e)                                                                                                                     
    print("ERROR Occurred: " + eMsg)
    traceback.print_tb(exc_traceback)
    exit(1)
