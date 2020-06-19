import os
import csv
from hubmap_commons import string_helper

ingest_info_file = '/Users/shirey/projects/hubmap/vanderbilt-data/vand-data-prod-datasets-final-fixed-ids.tsv'

tsv_files = ['/Users/shirey/projects/hubmap/vanderbilt-data/sanctioned-metadata/VAND-af-metadata.tsv',
             '/Users/shirey/projects/hubmap/vanderbilt-data/sanctioned-metadata/VAND-lc-metadata.tsv',
             '/Users/shirey/projects/hubmap/vanderbilt-data/sanctioned-metadata/VAND-mxif-metadata.tsv',
             '/Users/shirey/projects/hubmap/vanderbilt-data/sanctioned-metadata/VAND-pas-metadata.tsv',
             '/Users/shirey/projects/hubmap/vanderbilt-data/sanctioned-metadata/VAND-maldiims_neg-metadata.tsv',
             '/Users/shirey/projects/hubmap/vanderbilt-data/sanctioned-metadata/VAND-maldiims_pos-metadata.tsv']



output_dir = '/Users/shirey/projects/hubmap/vanderbilt-data/sanctioned-metadata/processed'


dataset_info_by_uuid = {}

def process_tsv(file_and_path):
    filename = os.path.split(file_and_path)[1]
    last_dash_pos = filename.rfind('-')
    datatype = filename[5:last_dash_pos]
    with open(file_and_path, newline='') as tsvfile:
        reader = csv.DictReader(tsvfile, delimiter='\t')
        for row in reader:
            write_tsv(row, datatype)



def write_tsv(row, datatype):
    uuid = row['hmuuid']
    if string_helper.isBlank(uuid):
        print("ERROR: no uuid for row in datatype: " + datatype)
        return
    
    output_path = output_dir + "/" + row['hmuuid'] + "-" + datatype + ".tsv"
    with open(output_path, 'w') as writer:
        keys = []
        data = []
        base_submission_path = None
        if not uuid in dataset_info_by_uuid:
            print("WARNING: dataset information not found for " + uuid)
        else:
            base_submission_path = dataset_info_by_uuid[uuid]['local_path']
            if not base_submission_path.lower().startswith('/hive/hubmap/lz'):
                print("WARNING: dataset local path doesn't start with /hive/hubmap/lz: " + uuid)
            else:
                base_submission_path = base_submission_path[15:].lower()                
        
        for key in row.keys():
            if not key == 'hmuuid':
                val = row[key]
                keyl = key.lower()
                if keyl == 'metadata_path' or key == 'data_path':
                    if base_submission_path is None:
                        print("ERROR: no base_submittion_path set on " + key + ": " + val)
                    if val is None:
                        print("WARNING: no path found for " + key + " for type: " + datatype + " on uuid: " + uuid)
                    elif not val.lower().startswith(base_submission_path):
                        print("WARNING: path " + key + ": " + val + " does not start with base path: " + base_submission_path)
                    val = val[len(base_submission_path):]
                keys.append(key)
                data.append(val)

            
        writer.write(string_helper.listToDelimited(keys, delimitChar='\t') + '\n')
        writer.write(string_helper.listToDelimited(data, delimitChar='\t') + '\n')


def load_dataset_info():
    with open(ingest_info_file, newline='') as tsvfile:
        reader = csv.DictReader(tsvfile, delimiter='\t')
        for row in reader:
            info_row = {}
            for key in row.keys():
                info_row[key] = row[key]
            if info_row['type'] == 'DATASET':
                if string_helper.isBlank(info_row['new_entity_uuid']):
                    print("WARNING: DATASET WITHOUT UUID: " + info_row['parent_display_id'])
                else:
                    dataset_info_by_uuid[info_row['new_entity_uuid']] = info_row


load_dataset_info()
for tsvfile in tsv_files:
    process_tsv(tsvfile)