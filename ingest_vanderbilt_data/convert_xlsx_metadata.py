#convert the clinical and assay specific metadata sent in xlsx format to csv
#data is expected to be in the root of the data directory, "root.path.to.data" property
#in the data_ingest.properties file, at metadata/assay and metadata/clinical

import os
from properties.p import Property
from hubmap_commons import file_helper
from hubmap_commons import string_helper
import pandas

prop_file_name = "../data_ingest.properties"
assay_meta_file_name = "Chris-Metadata-ALL-FINAL.xlsx"
assay_meta_sheet_names = [{'sheet_name':'MALDI DATA', 'data_type':'IMS'},
                          {'sheet_name':'AF DATA', 'data_type':'AF'},
                          {'sheet_name':'Stained DATA', 'data_type':'PAS'},
                          {'sheet_name':'MxIF DATA', 'data_type':'MxIF'},
                          {'sheet_name':'LC-MS Data', 'data_type':'LC'}]

props = None

def get_prop(prop_name):
    if not prop_name in props:
        raise Exception("Required property " + prop_name + " not found in " + prop_file_name)
    val = props[prop_name]
    if string_helper.isBlank(val):
        raise Exception("Required property " + prop_name + " from " + prop_file_name + " is blank")
    return props[prop_name]

def check_dir(dirName):
    if not os.path.isdir(dirName):
        raise Exception("Required directory " + dirName + " does not exist.")

def convert_clinical_metadata_file(dir_path, file_name):
    xlsx_file = os.path.join(dir_path, file_name).strip()
    if not os.path.isfile(xlsx_file):
        raise Exception("File does not exist: " + xlsx_file)
    if xlsx_file.endswith(".xlsx"):
        out_file = xlsx_file[:-5] + ".csv"
    else:
        raise Exception("File not of type .xlsx: " + xlsx_file)
    read_file = pandas.read_excel (xlsx_file)
    read_file.to_csv (out_file, index = None, header=True)

def convert_assay_sheet_to_csv(dir_path, xlsx_file_name, sheet_name, data_type):
    xlsx_file = os.path.join(dir_path, xlsx_file_name).strip()
    if not os.path.isfile(xlsx_file):
        raise Exception("File does not exist: " + xlsx_file)
    if xlsx_file.endswith(".xlsx"):
        out_file = os.path.join(dir_path, data_type + ".csv")
    else:
        raise Exception("File not of type .xlsx: " + xlsx_file)
    read_file = pandas.read_excel(xlsx_file, sheet_name=sheet_name)
    read_file.to_csv (out_file, index = None, header=True)
    
#Open the properties file
propMgr = Property()
props = propMgr.load_property_files(prop_file_name)
root_path = file_helper.ensureTrailingSlashURL(get_prop("root.path.to.data"))
clinical_path = os.path.join(root_path, "metadata/clinical/")
check_dir(root_path)
assay_path = os.path.join(root_path, "metadata/assay/")
check_dir(clinical_path)
check_dir(assay_path)
for clin_file in os.listdir(clinical_path):
    file_path = os.path.join(clinical_path, clin_file)
    if os.path.isfile(file_path) and clin_file.endswith(".xlsx"):
        convert_clinical_metadata_file(clinical_path, clin_file)

for assay in assay_meta_sheet_names:
    path_to_file = os.path.join(assay_path, assay_meta_file_name)
    if not os.path.isfile(path_to_file):
        raise Exception("Required file does not exist: " + path_to_file)
    convert_assay_sheet_to_csv(assay_path, assay_meta_file_name, assay['sheet_name'], assay['data_type'])
    
