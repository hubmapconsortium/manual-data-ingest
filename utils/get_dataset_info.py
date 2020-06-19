import traceback
import sys
from entity_info import EntityInfo
from hubmap_commons import string_helper

property_file = "../data_ingest.properties"

def get_metadata_attrib(dataset, attribname):
    if attribname in dataset['metadata']:
        return dataset['metadata'][attribname]
    else:
        return ""

def get_ds_attrib(dataset, attribname):
    if attribname in dataset:
        return dataset[attribname]
    else:
        return ""

def get_donor_id(tissue_id):
    if string_helper.isBlank(tissue_id):
        return ""
    else:
        first_dash = tissue_id.index('-')
        return tissue_id[2:first_dash]

def get_organ_id(tissue_id):
    donor = get_donor_id(tissue_id)
    tissue_id = tissue_id[2:len(tissue_id)-2]
    scnd_dash = tissue_id[len(donor)+1:].index('-')
    organ = tissue_id[:len(donor) + scnd_dash +1]
    return organ

try:
    info = EntityInfo(property_file)
    dsets = info.get_all_datasets()
    count = 0
    for dset in dsets:
        tmc_id = None
        hm_id = get_ds_attrib(dset, "display_doi")
        if 'metadata' in dset:
            group = get_metadata_attrib(dset, 'provenance_group_name')
            types = get_metadata_attrib(dset, 'data_types')
            tmc_id = get_metadata_attrib(dset, 'provenance_group_uuid')
            ds_name = get_metadata_attrib(dset, 'name')
            tissue_id = get_metadata_attrib(dset, 'source_uuid')
            globus_url = get_metadata_attrib(dset, 'globus_directory_url_path')
            local_dir = get_metadata_attrib(dset, 'local_directory_url_path')
        if tmc_id is not None and tmc_id == '73bb26e4-ed43-11e8-8f19-0a7c1eab007a':
            count = count + 1
            
            print(hm_id + "\t" + types[2:len(types)-2] + "\t" + get_donor_id(tissue_id) + "\t" + get_organ_id(tissue_id) + "\t" + tissue_id[2:len(tissue_id) -2] + "\t" + globus_url + "\t" + "/hive/hubmap/lz" + local_dir)
    print("COUNT: " + str(count))
    sys.exit(0)

except Exception as e:
    print("Error during execution.")
    print(str(e))
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    sys.exit(1) 
