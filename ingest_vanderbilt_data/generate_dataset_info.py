import os
import requests
from hubmap_commons import file_helper
from hubmap_commons import string_helper
from properties.p import Property
from ingest_vanderbilt_data.meta_reader import VandCSVReader


import re

prop_file_name = "../data_ingest.properties"
csv_data = None
templates_path = None
collections = {}
ingest_record_count = 0 

def get_next_ingest_id():
    global ingest_record_count
    ingest_record_count = ingest_record_count + 1
    return str(ingest_record_count)

def substitute_into_template(template_file_name, hubmap_id, assay_type):
    test_name = template_file_name
    descript = None
    for file in os.listdir(templates_path):
        if file == test_name:
            with open(os.path.join(templates_path, file)) as f:
                descript = f.read()
    if descript is None:
        raise Exception("Unable to find template file " + test_name)

    matches = re.findall("(<.*?>)", descript)
    uniq_matches = []
    for match in matches:
        trimmed_match = match[1:len(match) - 1]
        if not trimmed_match in uniq_matches:
            uniq_matches.append(trimmed_match)
    
    for match in uniq_matches:
        repl = csv_data.get_meta_value(hubmap_id, match, assay_type)
        descript = re.sub("(<" + match + ">)", repl, descript)
    
    
    return descript.strip()

def get_dataset_name(hubmap_id, assay_type):
    test_name = assay_type.lower() + "-name.txt"
    return substitute_into_template(test_name, hubmap_id, assay_type)

def get_dataset_description(hubmap_id, assay_type):
    template_file_name = assay_type.lower() + "-description.txt"
    return substitute_into_template(template_file_name, hubmap_id, assay_type)

def get_collection_key(parent_dir):
    if string_helper.isBlank(parent_dir):
        raise Exception("Can't create a collection with an empty name.")
    coll_key = parent_dir.strip().upper()
    if not coll_key in collections:
        block_id = csv_data.get_block_id(parent_dir)
        description = substitute_into_template("collection-description.txt", block_id, None)
        collection_info = {}
        collection_info['description'] = description
        collection_info['name'] = get_dataset_name(block_id, 'collection')
        collections[coll_key] = collection_info
    return coll_key

def print_collection_info():
    for col_key in collections.keys():
        col_info = collections[col_key]
        print(get_next_ingest_id() + "\t\tCOLLECTION\t" + col_key + "\t\t\t" + col_info['name'] + "\t" + col_info['description'] + "\t\t\t\t\t\t")
     
def printHeader():
    print("ingest_id\tnew_entity_uuid\ttype\tparent_display_id\tparent_uuid\tassay_type\tname\tdescription\tcollection_key\tcreator_name\tcreator_email\tgroup_id\tgroup_name\tlocal_path")
    
def resolveToUUID(hmid):
    url = uuid_api_url + "hmuuid/" + hmid
    headers = {'Authorization': 'Bearer ' + nexus_token}
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
    
def getDisplayId(val):
    idx = val.rfind("-")
    if idx == -1:
        return "NO ID FOUND"
    else:
        return val[:idx]

def resolveToMultipleUUIDs(hmids):
    underscore_idx = hmids.rfind("_")
    dash_idx = hmids.rfind("-")    
    if underscore_idx == -1 or dash_idx == -1 or dash_idx > underscore_idx:
        return "No UUIDs Found"    
    baseId = getDisplayId(hmids)
    idx1 = hmids[dash_idx + 1:underscore_idx]
    idx2 = hmids[underscore_idx + 1:] 
    if not idx1.isdigit() or not idx2.isdigit():
        return "No UUIDs Found"
    uuids = []
    for idx in range(int(idx1), int(idx2) + 1):
        uuids.append(resolveToUUID(baseId + "-" + str(idx)))
    suuids = string_helper.listToDelimited(uuids, "|")
    return suuids

def getAssayType(val):
    idx = val.rfind("-")
    if idx == -1 or idx == (len(val) - 1):
        return "NO ASSAY TYPE FOUND"
    else:
        return val[idx + 1:]


def handleCCFFile(base_path, dir_name, uuids = None):
    dir_path = os.path.join(base_path, dir_name)
    for file in os.listdir(dir_path):
        file_path = os.path.join(dir_path, file)
        if os.path.isfile(file_path) and file.lower().strip().endswith("_ccf_metadata"):
            block_id = file[:-13]
            if not uuids is None:
                uuid = uuids
            else:
                uuid = resolveToUUID(block_id)
            print(get_next_ingest_id() + "\t\tCCFDATA\t", block_id + "\t" + uuid + "\t\t\t\t\t\t\t\t\t" + file_path)

def handleClinical(base_path, dir_name, uuids = None):
    dir_path = os.path.join(base_path, dir_name)
    for file in os.listdir(dir_path):
        file_path = os.path.join(dir_path, file)
        if os.path.isfile(file_path) and file.lower().strip().endswith("metadata.xlsx"):
            block_id = file[:-14]
            if not uuids is None:
                uuid = uuids
            else:
                uuid = resolveToUUID(block_id)
            print(get_next_ingest_id() + "\t\tCLINICALDATA\t", block_id + "\t" + uuid + "\t\t\t\t\t\t\t\t\t" + file_path)
            
def handleHistopath(base_path, dir_name, uuids = None):
    dir_path = os.path.join(base_path, dir_name)
    for file in os.listdir(dir_path):
        file_path = os.path.join(dir_path, file)
        if os.path.isfile(file_path) and file.endswith("histopath.scn"):
            disp_id = getDisplayId((file))
            if not uuids is None:
                uuid = uuids
            else:
                uuid = resolveToUUID(disp_id)
            print(get_next_ingest_id() + "\t\tIMAGE\t" + disp_id + "\t" + uuid + "\t\t\t\t\t\t\t\t\t" + file_path )

def handleLCDataset(base_path, dir_name):
    dir_path = os.path.join(base_path, dir_name)
    underscore_idx = dir_name.rfind("_")
    if underscore_idx == -1:
        uuids = resolveToUUID(dir_name)
    else:
        uuids = resolveToMultipleUUIDs(dir_name)

    if dir_name.startswith("VAN"):
        parent_display_id = dir_name
        assay_type = "LC"
        print(get_next_ingest_id() + "\t\tDATASET\t" + parent_display_id + "\t" + uuids + "\t" + assay_type + "\t" + get_dataset_name(parent_display_id, assay_type) + "\t" + get_dataset_description(parent_display_id, assay_type) + "\tNO_COLLECTION\tJeff Spraggins\tjeff.spraggins@vanderbilt.edu\t73bb26e4-ed43-11e8-8f19-0a7c1eab007a\tVanderbilt TMC\t" + dir_path)        
        for sub_dir_name in os.listdir(dir_path):
            sub_dir_path = os.path.join(dir_path, sub_dir_name)
            if os.path.isdir(sub_dir_path):
                if sub_dir_name.startswith("CCF"):
                    handleCCFFile(dir_path, sub_dir_name, uuids=uuids)
                elif sub_dir_name.startswith("Clinical"):
                    handleClinical(dir_path, sub_dir_name, uuids=uuids)

    
def handleMultDatasetDir(base_path, dir_name):
    dir_path = os.path.join(base_path, dir_name)
    assay_type = getAssayType(dir_name) 
    if assay_type == 'IMS':
        for ims_sub_dir in os.listdir(dir_path):
            if ims_sub_dir.startswith('VAN'):
                handleMultDatasetDir(dir_path, ims_sub_dir)
    elif dir_name.endswith("_histopath"):
        handleHistopath(base_path, dir_name)
    elif dir_name.startswith("CCF"):
        handleCCFFile(base_path, dir_path)
    elif dir_name.startswith("Clinical"):
        handleClinical(base_path, dir_path)
    elif dir_name.startswith("VAN"):
        parent_display_id = getDisplayId(dir_name)
        uuid = resolveToUUID(parent_display_id)
        parent_dir_name = os.path.split(base_path)[1]
        if assay_type.startswith("IMS"):
            name_desc_assay_type = "IMS"
        else:
            name_desc_assay_type = assay_type

                    
        print(get_next_ingest_id() + "\t\tDATASET\t" + parent_display_id + "\t" + uuid + "\t" + assay_type + "\t" + get_dataset_name(parent_display_id, name_desc_assay_type) + "\t" + get_dataset_description(parent_display_id, name_desc_assay_type) + "\t" + get_collection_key(parent_dir_name) + "\tJeff Spraggins\tjeff.spraggins@vanderbilt.edu\t73bb26e4-ed43-11e8-8f19-0a7c1eab007a\tVanderbilt TMC\t" + dir_path)
           

def get_prop(prop_name):
    if not prop_name in props:
        raise Exception("Required property " + prop_name + " not found in " + prop_file_name)
    val = props[prop_name]
    if string_helper.isBlank(val):
        raise Exception("Required property " + prop_name + " from " + prop_file_name + " is blank")
    return props[prop_name]

#check to make sure we have a properties file
if not os.path.isfile(prop_file_name):
    raise Exception("Property file " + prop_file_name + " is required and does not exist.")

#Open the properties file
propMgr = Property()
props = propMgr.load_property_files(prop_file_name)
root_path = file_helper.ensureTrailingSlashURL(get_prop("root.path.to.data"))
templates_path = os.path.join(root_path, "templates")

uuid_api_url = file_helper.ensureTrailingSlashURL(get_prop("uuid.api.url"))
nexus_token = get_prop("nexus.token").strip()

dirs = os.listdir(root_path)

csv_data = VandCSVReader(prop_file_name, "tissue _id")
printHeader()
for dir_name in dirs:
    next_path = os.path.join(root_path, dir_name)    
    if dir_name.startswith("VAN") and os.path.isdir(next_path):
        for next_dir in os.listdir(next_path):
            handleMultDatasetDir(next_path, next_dir)
    elif dir_name.startswith("LC"):
        for next_dir in os.listdir(next_path):
            handleLCDataset(next_path, next_dir)
            
print_collection_info()
