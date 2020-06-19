import os
import requests
from hubmap_commons import file_helper
from hubmap_commons import string_helper
from properties.p import Property
import csv
import sys
import traceback
import json

meta_files = {'AF':'metadata/VAND_LC-MSMS_Metadata_051020.tsv',
              'IMS_NegMode':'metadata/VAND_maldiims_neg_data_050120.tsv',
              'IMS_PosMode':'metadata/VAND_maldiims_pos_data_050120.tsv',
              'LC':'metadata/VAND_LC-MSMS_Metadata_051020.tsv',
              'MxIF':'metadata/VAND_MxIF_metadata_050420.tsv',
              'PAS':'metadata/VAND_Stained_metadata_050320.tsv'}

class VandIngest:
    
    def __init__(self, property_file_name):
        self.dataset_info = None
        self.dataset_info_tsv_path = None
        self.prop_file_name = property_file_name
        if not os.path.isfile(property_file_name):
            raise Exception("property file does not exist: " + property_file_name)
        #Open the properties file
        propMgr = Property()
        self.props = propMgr.load_property_files(property_file_name)
        self.data_root_path = file_helper.ensureTrailingSlash(self.get_prop('root.path.to.data'))
        self.ingest_api_url = file_helper.ensureTrailingSlashURL(self.get_prop("ingest.api.url"))
        self.nexus_token = self.get_prop("nexus.token").strip()
        self.entity_api_url = file_helper.ensureTrailingSlashURL(self.get_prop("entity.api.url"))
        self.uuid_api_url = file_helper.ensureTrailingSlashURL(self.get_prop("uuid.api.url"))
        self.dataset_info_tsv_path = self.get_prop("vand.dataset.info.tsv")
        if string_helper.isBlank(self.dataset_info_tsv_path) or not os.path.isfile(self.dataset_info_tsv_path):
            raise Exception("dataset info file does not exist:" + self.dataset_info_tsv_path)
        if not self.dataset_info_tsv_path.endswith(".tsv"):
            raise Exception("dataset info file must be of type .tsv : " + self.dataset_info_tsv_path)
        self.dataset_info = []
        with open(self.dataset_info_tsv_path, newline='') as tsvfile:
            reader = csv.DictReader(tsvfile, delimiter='\t')
            for row in reader:
                info_row = {}
                for key in row.keys():
                    info_row[key] = row[key]
                self.dataset_info.append(info_row)
                
        self.collections = {}
        self.meta_info = None

    def get_prop(self, prop_name):
        if not prop_name in self.props:
            raise Exception("Required property " + prop_name + " not found in " + self.prop_file_name)
        val = self.props[prop_name]
        if string_helper.isBlank(val):
            raise Exception("Required property " + prop_name + " from " + self.prop_file_name + " is blank")
        return self.props[prop_name]
    
    def ingest_collections(self):
        for ingest_row in self.dataset_info:
            if ingest_row['type'].upper() == "COLLECTION":
                if string_helper.isBlank(ingest_row['new_entity_uuid']):
                    col_uuid = self.create_collection(ingest_row['name'], ingest_row['description'], ingest_row['collection_key'])
                    ingest_row.update({'new_entity_uuid':col_uuid})
                    print("Collection created key:" + ingest_row['parent_display_id'] + "uuid:" + col_uuid)
                self.collections[ingest_row['parent_display_id']] = ingest_row
            
    def ingest_recordsets(self):
        for ingest_row in self.dataset_info:
            if ( ingest_row['type'].upper() == "DATASET" and 
                  string_helper.isBlank(ingest_row['new_entity_uuid']) and
                  not string_helper.isBlank(ingest_row['parent_uuid']) and
                  not ingest_row['parent_uuid'].startswith('No UUID')):
                col_uuid = self.create_dataset(ingest_row)
                ingest_row.update({'new_entity_uuid':col_uuid})

    def resolveToUUID(self, hmid):
        url = self.uuid_api_url + "hmuuid/" + hmid.strip()
        headers = {'Authorization': 'Bearer ' + self.nexus_token}
        resp = requests.get(url, headers=headers)
        status_code = resp.status_code
        if status_code < 200 or status_code >= 300:
            return "ERROR"
        id_info = resp.json()
        if not isinstance(id_info, list) or len(id_info) == 0:
            return("No UUID Found")
        else:
            vals = id_info[0]
        if 'hmuuid' in vals:
            return vals['hmuuid']
        else:
            return "Not Found"


    def fix_ids(self):
        for ingest_row in self.dataset_info:
            ing_type = ingest_row['type']
            if ( ing_type == 'CCFDATA' or ing_type == 'IMAGE' or ing_type == 'CLINICALDATA'):
                if 'parent_display_id' in ingest_row and not string_helper.isBlank(ingest_row['parent_display_id']):
                    parent_uuid = self.resolveToUUID(ingest_row['parent_display_id'])
                    ingest_row.update({'parent_uuid':parent_uuid})
                
    def ingest_rui_info(self):
        for ingest_row in self.dataset_info:
            if ( ingest_row['type'].upper() == "CCFDATA" and 
                  string_helper.isBlank(ingest_row['new_entity_uuid']) and
                  not string_helper.isBlank(ingest_row['parent_uuid']) and
                  not ingest_row['parent_uuid'].startswith('No UUID')):                
                col_uuid = self.import_rui_location(ingest_row)
                ingest_row.update({'new_entity_uuid':col_uuid})
    
    def import_rui_location(self, ingest_row):
        if 'local_path' in ingest_row and  not string_helper.isBlank(ingest_row['local_path']) and os.path.isfile(ingest_row['local_path']):
            with open(ingest_row['local_path']) as file:
                rui_location = file.read().replace("\n", " ")
                
            recd = {}
            recd['rui_location'] = rui_location
            
            url = file_helper.ensureTrailingSlashURL(self.entity_api_url) + "entities/sample/" + ingest_row['parent_uuid']
            heads = {'Authorization': 'Bearer ' + self.nexus_token, 'Content-Type': 'application/json'}
            recds = json.dumps(recd)
            print("URL:" + url)
            print("DATA:" + recds)
            resp = requests.put(url, headers=heads, data=recds, verify=False)
            status_code = resp.status_code
            if status_code != 200:
                print("Unable to import location info for file:  parent id:" + ingest_row['local_path'], file=sys.stderr)
                resp.raise_for_status()
                print("Imported location info ingest_id:" + ingest_row['ingest_id'] + " parent id:" + ingest_row['parent_display_id'] )            
            return("COMPLETE")
        else:
            return("FAIL:RUI FILE NOT FOUND")

    def create_dataset(self, ingest_row):
        '''
        {
            "dataset_name": "Test Name",
            "dataset_description": "This is a test description",
            "dataset_collection_uuid": "ab93b3983acge938294857fe292429234",
            "source_uuids": ["ea93b3983acge938294857fe292429234", "f343b3983acge938294857fe292429234", "cdeb3983acge938294857fe292429234"],
            "data_types": ["PAS"],
            "creator_email": "datasetowner@institution.xxx",
            "creator_name": "Dataset Owner",
            "group_uuid": "193439-29392-2939243",
            "group_name": "HuBMAP-Test",
            "contains_human_genomic_sequences": "no"  
        }
        '''
        recd = {}
        recd['dataset_name'] = ingest_row['name'].encode(encoding='ascii', errors='ignore').decode('ascii')
        recd['dataset_description'] = ingest_row['description'].encode(encoding='ascii', errors='ignore').decode('ascii')
        if not ingest_row['collection_key'].startswith("NO_COLLECTION"):
            recd['dataset_collection_uuid'] = self.lookup_collection_uuid(ingest_row['collection_key'])
        source_uuids = ingest_row['parent_uuid'].split('|')
        recd['source_uuids'] = source_uuids
        data_type = []
        dtype = ingest_row['assay_type']
        if not string_helper.isBlank(dtype) and dtype.upper() == 'LC':
            dtype = 'LC-MS-untargeted'
        data_type.append(dtype)
        recd['data_types'] = data_type
        recd['creator_email'] = ingest_row['creator_email']
        recd['creator_name'] = ingest_row['creator_name']
        recd['group_uuid'] = ingest_row['group_id']
        recd['group_name'] = ingest_row['group_name']
        recd['contains_human_genomic_sequences'] = 'no'
        
        url = file_helper.ensureTrailingSlashURL(self.ingest_api_url) + "datasets/ingest"
        heads = {'Authorization': 'Bearer ' + self.nexus_token, 'Content-Type': 'application/json'}
        recds = json.dumps(recd)
        resp = requests.post(url, headers=heads, data=recds, verify=False)
        status_code = resp.status_code
        if status_code < 200 or status_code >= 300:
            print("Unable to create RECORDSET for parent id:" + ingest_row['parent_display_id'] + " assay type:" + ingest_row['assay_type'] , file=sys.stderr)
            resp.raise_for_status()
        val = resp.json()
        if val is None or not 'uuid' in val:
            raise Exception("No UUID returned on creation of DATASET parent id:" + ingest_row['parent_display_id'] + " assay type:" + ingest_row['assay_type'] )
        print("Created Dataset ingest_id:" + ingest_row['ingest_id'] + " UUID:" + val['uuid'] + " parent id:" + ingest_row['parent_display_id'] + " assay type:" + ingest_row['assay_type'] )
        return val['uuid']
        

        
    def create_collection(self, name, description, collection_key):
        url = file_helper.ensureTrailingSlashURL(self.ingest_api_url) + "new-collection"
        heads = {'Authorization': 'Bearer ' + self.nexus_token, 'Content-Type': 'application/json'}
        dats = {'label': name, 'description':description}
        dataj = json.dumps(dats)
        resp = requests.post(url, headers=heads, data=dataj, verify=False)
        status_code = resp.status_code
        if status_code < 200 or status_code >= 300:
            print("Unable to create COLLECTION for " + collection_key, file=sys.stderr)
            resp.raise_for_status()
        val = resp.json()
        if not 'uuid' in val:
            raise Exception("No UUID returned on creation of COLLECTION " + collection_key)
        return val['uuid']

    def lookup_collection_uuid(self, collection_key):
        if collection_key in self.collections and "new_entity_uuid" in self.collections[collection_key]:
            return self.collections[collection_key]["new_entity_uuid"]
        else:
            raise Exception("Collection not found for " + collection_key)
    
    def ingest_metadata(self):
        for ingest_row in self.dataset_info:
            if ( ingest_row['type'].upper() == "DATASET"  and 
                  not string_helper.isBlank(ingest_row['new_entity_uuid'])):
                meta_info = self.get_meta_info(ingest_row['assay_type'], ingest_row['parent_display_id'])
                
                
                
    def get_metdata_info(self, assay, display_id):
        if self.meta_info is None:
            self.load_meta_info()
        return self.meta_info[assay + display_id]
    
    def load_meta_info(self):
        for assay_type in meta_files.keys():
            meta_filename = self.data_root_path + meta_files[assay_type]
            if not os.path.isfile(meta_filename):
                raise Exception("Metadata file does not exist: " + meta_filename)          
            with open(meta_filename, newline='') as tsvfile:
                reader = csv.DictReader(tsvfile, delimiter='\t')
                for row in reader:
                    if not 'tissue_id' in row:
                        raise Exception('tissue_id column not found in ' + meta_filename)
                    meta_key = assay_type + row['tissue_id']
                    info_row = {}
                    for key in row.keys():
                        info_row[key] = row[key]
                    self.meta_info[meta_key] = info_row
          
ingest_worker = None

try:
    ingest_worker = VandIngest("../data_ingest.properties")
    #ingest_worker.ingest_collections()
    #ingest_worker.ingest_recordsets()
    #ingest_worker.fix_ids()
    #ingest_worker.ingest_rui_info()
    ingest_worker.ingest_metadata()
    
except Exception as e:                                                                                                            
    exc_type, exc_value, exc_traceback = sys.exc_info()
    eMsg = str(e)                                                                                                                     
    print("ERROR Occurred: " + eMsg)
    traceback.print_tb(exc_traceback)
finally:
    if (  not ingest_worker is None and 
          not ingest_worker.dataset_info is None and
          not string_helper.isBlank(ingest_worker.dataset_info_tsv_path) and
          os.path.isfile(ingest_worker.dataset_info_tsv_path)):
        output_base = ingest_worker.dataset_info_tsv_path[:-4]
        last_dot = output_base.rfind(".")
        if not last_dot == -1:
            numeric = output_base[last_dot + 1:]
            if numeric.isdigit():
                next_file = int(numeric) + 1
                output_base = output_base[:last_dot]
            else:
                next_file = 1
        else:
            next_file = 1
            
        output_path = output_base + "." + str(next_file) +".tsv"                    
        while os.path.isfile(output_path):
            next_file = next_file + 1
            output_path = output_base + "." + str(next_file) +".tsv"
        with open(output_path, 'w') as writer:
            first = True
            for info_line in ingest_worker.dataset_info:
                if first:
                    first = False
                    line_keys = info_line.keys()
                    writer.write(string_helper.listToDelimited(line_keys, delimitChar='\t') + '\n')
                line = []
                for key in line_keys:
                    val = info_line[key]
                    if val is None: val = ''
                    line.append(val)
                writer.write(string_helper.listToDelimited(line, delimitChar='\t') + '\n')
        
        
