import os
import csv
from hubmap_commons import string_helper
from hubmap_commons.exceptions import ErrorMessage

#helper class for tsv files
class TSVFile:
    def __init__(self, file_name):
        if string_helper.isBlank(file_name):
            raise Exception("ERROR: TSV Filename Not Found")
        if not os.path.isfile(file_name):
            raise ErrorMessage("TSV file " + file_name + " not found.")
        
        self.records = []
        self.header = []
        with open(file_name, newline='') as tsvfile:
            reader = csv.DictReader(tsvfile, delimiter='\t')
            first = True
            for row in reader:
                data_row = {}
                for key in row.keys():
                    if first: self.header.append(key)
                    data_row[key] = row[key]
                self.records.append(data_row)
                if first: first = False          
    
    def get_records(self):
        return self.records
    
    def get_header_keys(self):
        return self.header