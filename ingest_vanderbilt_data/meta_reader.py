import os
from properties.p import Property
from hubmap_commons import file_helper
from hubmap_commons import string_helper
import csv

organ_lookup={'LK':'Left Kidney', 'RK': 'Right Kidney'}

class VandCSVReader:
    
    def __init__(self, property_file_name, assay_row_key):
        #Open the properties file
        propMgr = Property()
        self.prop_file_name = property_file_name
        self.assay_row_key = assay_row_key
        if not os.path.isfile(self.prop_file_name):
            raise Exception("Required property file does not exist: " + self.prop_file_name)
        self.props = propMgr.load_property_files(self.prop_file_name)
        root_path = file_helper.ensureTrailingSlashURL(self.get_prop("root.path.to.data"))
        clinical_meta_path = self.join_dir(root_path, "metadata/clinical")
        assay_meta_path = self.join_dir(root_path, "metadata/assay")
        self.clinical_metadata = self.convert_clin_meta_to_dict(clinical_meta_path)
        self.assay_metadata = self.convert_assay_meta_to_dict(assay_meta_path)

    def get_organ(self, hm_id):
        idxs = string_helper.allIndexes(hm_id, "-")
        if len(idxs) >= 2 and (idxs[1] - idxs[0]) >= 3:
            code = hm_id[idxs[0] + 1:idxs[1]]
            if code in organ_lookup:
                return organ_lookup[code]
        else:
            raise Exception("Organ type not found for id:" + hm_id)
            
    def get_meta_value(self, hubmap_id, attribute_name, assay_type=None):
        if attribute_name == 'organ':
            return self.get_organ(hubmap_id)
        block_id = self.get_block_id(hubmap_id)
        if block_id in self.clinical_metadata:
            if attribute_name in self.clinical_metadata[block_id]:
                return self.clinical_metadata[block_id][attribute_name]
        if attribute_name == 'age':
            for key in self.clinical_metadata[block_id].keys():
                print(key + ":" + self.clinical_metadata[block_id][key])
                
        if not assay_type is None:
            assy_t = assay_type.lower()
            if assy_t in self.assay_metadata:
                if hubmap_id in self.assay_metadata[assy_t]:
                    if attribute_name in self.assay_metadata[assy_t][hubmap_id]:
                        return self.assay_metadata[assy_t][hubmap_id][attribute_name]
        for key in self.assay_metadata[assy_t][hubmap_id].keys():
            print(key + ":" + self.assay_metadata[assy_t][hubmap_id][key])
        err_msg = "Metadata attribute not found for id:" + hubmap_id + " attribute:" + attribute_name
        if not assay_type is None:
            err_msg = err_msg + " assay:" + assay_type
            
        raise Exception(err_msg)
    
    #gets the first registered piece of tissue below the organ
    #TEST0032-LI-29-16-23 would return TEST0032-LI-29
    def get_block_id(self, hubmap_id):
        #gets the first registered 
        test_id = hubmap_id.strip()
        dash_idxs = string_helper.allIndexes(test_id, '-')
        test_len = len(test_id)
        #if there aren't two dashes or the dash is the last character it doesn't exist
        if(len(dash_idxs) < 2 or (dash_idxs[1] + 1) >= test_len):
            return("")
        
        #starting at the second dash find the location of the first non-integer character
        endidx = -1
        for ch in range(dash_idxs[1] + 1, test_len):
            if not test_id[ch].isdigit():
                endidx = ch
                break
            
        if endidx == -1:
            return test_id
        elif endidx == dash_idxs[1] + 1:
            return ""
        else:
            return test_id[:endidx]
    
    def get_prop(self, prop_name):
        if not prop_name in self.props:
            raise Exception("Required property " + prop_name + " not found in " + self.prop_file_name)
        val = self.props[prop_name]
        if string_helper.isBlank(val):
            raise Exception("Required property " + prop_name + " from " + self.prop_file_name + " is blank")
        return self.props[prop_name]

    def join_dir(self, base_path, extended_dir, required = True):
        rVal = os.path.join(base_path, extended_dir)
        if required and not os.path.isdir(rVal):
            raise Exception("Required directory " + rVal + " does not exist.")
        return rVal
    
    def csv_to_dict(self, csv_path, max_rows = None):
        if max_rows is not None and max_rows == 1:
            is_arry = False
            rVal = {}
        else:
            is_arry = True
            rVal = []
        with open(csv_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            nrows = 0
            for row in reader:
                if is_arry:
                    next_row = {}
                nrows = nrows + 1
                if not is_arry and nrows > max_rows:
                    raise Exception("Clinical csv file has more than " + str(max_rows) + " row(s) of data: " + csv_path)
                for key in row.keys():
                    if key is not None:
                        if is_arry:
                            next_row[key.lower()] = row[key]
                        else:
                            rVal[key.lower()] = row[key]
                if is_arry:
                    rVal.append(next_row)
        return(rVal)
    
    def convert_clin_meta_to_dict(self, path_to_clin_meta_dir):
        rVal = {}
        for csv_file in os.listdir(path_to_clin_meta_dir):
            if csv_file.endswith("_metadata.csv"):
                key = csv_file[:-13]
                metadata = self.csv_to_dict(os.path.join(path_to_clin_meta_dir, csv_file), max_rows = 1)
                rVal[key] = metadata
        return rVal
    
    def convert_assay_meta_to_dict(self, path_to_assay_meta_dir):
        rVal = {}
        meta_key = self.assay_row_key
        for csv_file in os.listdir(path_to_assay_meta_dir):
            if csv_file.endswith(".csv"):
                assay_key = csv_file[:-4].lower()
                rVal[assay_key] = {}
                meta = self.csv_to_dict(os.path.join(path_to_assay_meta_dir, csv_file))
                count = 0
                for row in meta:
                    count = count + 1
                    if not meta_key in row:
                        raise Exception("Clinical metadata row key '" + meta_key + "' does not exist in row number " + str(count) + " of file " + path_to_assay_meta_dir)
                    rVal[assay_key][row[meta_key]] = row
        return rVal

#csvData = VandCSVReader("../data_ingest.properties", "tissue _id")
#testids = ['TEST0032-DJ-2345', 'TEST0032-DJ', 'TEST0032-23fs-23432abcd', 'TEST0032-LK-ABC', 'TEST0032-LK-234-1234', 'TEST0032-LD-2_asdf']
#for hid in testids:
#    print(hid + ":" + csvData.get_block_id(hid))


            
            
