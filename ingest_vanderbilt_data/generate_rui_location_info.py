import os
import requests
from hubmap_commons import file_helper
from hubmap_commons import string_helper
from properties.p import Property

root_path = None
prop_file_name = "../data_ingest.properties"
uuid_api_url = None
nexus_token = None
props = None


def printHeader():
    print("Display Id, UUID, Path To File")
def resolveToUUID(hmid):
    url = uuid_api_url + "hmuuid/" + hmid
    headers = {'Authorization': 'Bearer ' + nexus_token}
    resp = requests.get(url, headers=headers)
    status_code = resp.status_code
    if status_code < 200 or status_code >= 300:
        return "ERROR"
    id_info = resp.json()
    vals = id_info[0]
    if 'hmuuid' in vals:
        return vals['hmuuid']
    else:
        return "Not Found"
    
def handleCCFFile(base_path, dir_name):
    dir_path = os.path.join(base_path, dir_name)
    for file in os.listdir(dir_path):
        file_path = os.path.join(dir_path, file)
        if os.path.isfile(file_path) and file.lower().strip().endswith("_ccf_metadata"):
            block_id = file[:-13]
            uuid = resolveToUUID(block_id)
            print(block_id + ", " + uuid + ", " + file_path)

def handleSubDir(base_path, dir_name):
    dir_path = os.path.join(base_path, dir_name)
    if os.path.isdir(dir_path):
        if(dir_name.startswith("CCF")):
            handleCCFFile(base_path, dir_name)
           
def handleMultDatasetDir(dir_name):
    mult_dir = os.path.join(root_path, dir_name)
    dirs = os.listdir(mult_dir)
    for sub_dir in dirs:
        handleSubDir(dir_name, sub_dir)

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
uuid_api_url = file_helper.ensureTrailingSlashURL(get_prop("uuid.api.url"))
nexus_token = get_prop("nexus.token").strip()

dirs = os.listdir(root_path)
printHeader()
for name in dirs:
    if not name.startswith("LC "):
        handleMultDatasetDir(os.path.join(root_path, name))
    
    print(name)
