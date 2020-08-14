import requests
from properties.p import Property
import os
from hubmap_commons import file_helper
from hubmap_commons import string_helper
import json

entity_types = ['Donor', 'Sample', 'Dataset']


#A class to inspect and report data from all entities in the HuBMAP Neo4j store
class EntityInfo:
    
    def __init__(self, prop_file_name):
        
        self._prop_file_name = prop_file_name
        
        #check to make sure we have a properties file
        if not os.path.isfile(prop_file_name):
            raise Exception("Property file " + prop_file_name + " is required and does not exist.")

        #Open the properties file
        propMgr = Property()
        self.props = propMgr.load_property_files(prop_file_name)

        self.entity_api_url = file_helper.ensureTrailingSlashURL(self.get_prop("entity.api.url"))
        self.nexus_token = self.get_prop("nexus.token").strip()
        self.globus_system_dir = self.get_prop("globus.system.dir").strip()
        self.globus_base_url = file_helper.removeTrailingSlashURL(self.get_prop("globus.single.file.base.url").strip())
        self.test_group_id = self.get_prop("test.group.id").strip().lower()
        self.globus_app_base_url = self.get_prop("globus.app.base.url").strip()

    def get_dict_attrib(self, dary, attrib_name):
        if dary is not None and attrib_name in dary:
            return dary[attrib_name]
        else:
            return ""
            
    def print_all_ids_header(self):
        print("Entity Type, Display ID, UUID, DOI, DISPLAY DOI, METADATA UUID")
        
    def print_all_ids(self):
        self.print_all_ids_header()
        for ent_type in entity_types:
            url = self.entity_api_url + "entities?entitytypes=" + ent_type
            headers = {'Authorization': 'Bearer ' + self.nexus_token}
            resp = requests.get(url, headers=headers)
            status_code = resp.status_code
            if status_code < 200 or status_code >= 300:
                resp.raise_for_status()
    
            entities = resp.json()
            for ent in entities:
                js = json.dumps(ent)
                print(self.get_dict_attrib(ent, "entitytype") + ", " +
                      self.get_dict_attrib(ent, "hubmap_identifier") + ", " + 
                      self.get_dict_attrib(ent, "uuid") + ", " +
                      self.get_dict_attrib(ent, "display_doi") + ", " +
                      self.get_dict_attrib(ent, "doi") + ", " +
                      "")

    def get_all_donors(self):
        url = self.entity_api_url + "entities?entitytypes=Donor"
        headers = {'Authorization': 'Bearer ' + self.nexus_token}
        resp = requests.get(url, headers=headers)
        status_code = resp.status_code
        if status_code < 200 or status_code >= 300:
            resp.raise_for_status()

        donors = resp.json()
        return donors
        
    
    def get_all_datasets(self):
        url = self.entity_api_url + "entities?entitytypes=Dataset"
        headers = {'Authorization': 'Bearer ' + self.nexus_token}
        resp = requests.get(url, headers=headers)
        status_code = resp.status_code
        if status_code < 200 or status_code >= 300:
            resp.raise_for_status()
        
        dsets = resp.json()
        return dsets
        
    #print the header for a protocol information csv file
    def print_protocol_info_header(self, include_uuid=False):
        uuid_header = ""
        if include_uuid:
            uuid_header = " UUID,"
        print("Entity Type, HuBMAP Component, HuBMAP Display ID, HuBMAP DOI ID," + uuid_header + " protocols.io doi URLs, Globus links to protocol files, protocol file system path")
        
    #print a single line of a single entity's protocol information
    #formatted as csv    
    def print_protocol_info(self, entity, entity_type, include_uuid=False, include_test_group=False):
        group_id = self.get_dict_attrib(entity, "provenance_group_uuid").strip().lower()
        if string_helper.isBlank(group_id):
            return
        if not include_test_group:
            if self.test_group_id == group_id:
                return
        group_name = self.get_dict_attrib(entity, "provenance_group_name")
        display_doi = self.get_dict_attrib(entity, "display_doi")
        uuid = self.get_dict_attrib(entity, "uuid")
        display_id = self.get_dict_attrib(entity, "hubmap_identifier")
        protocols = self.get_dict_attrib(entity, "protocols")
        prot_files = []
        prot_globus_urls = []
        prot_dois = []
        if not string_helper.isBlank(protocols):
            prots = json.loads(protocols.replace("'", '"'))
            for prot in prots:
                if "protocol_file" in prot and not string_helper.isBlank(prot['protocol_file']):
                    prot_files.append(prot['protocol_file'])
                    prot_globus_urls.append(self.convert_to_globus_url(prot['protocol_file']))
                if "protocol_url" in prot and not string_helper.isBlank(prot['protocol_url']):
                    prot_dois.append(prot['protocol_url'])
        protocol = self.get_dict_attrib(entity, "protocol")
        if not string_helper.isBlank(protocol):
            prot_dois.append(protocol)
        protocol_file = self.get_dict_attrib(entity, "protocol_file")
        if not string_helper.isBlank(protocol_file):
            prot_files.append(protocol_file)
            prot_globus_urls.append(self.convert_to_globus_url(protocol_file))
        
        vals = []
        vals.append(entity_type)
        vals.append(group_name)
        vals.append(display_id)
        vals.append(display_doi)
        if include_uuid:
            vals.append(uuid)
        vals.append(string_helper.listToDelimited(prot_dois, delimitChar=" | "))
        vals.append(string_helper.listToDelimited(prot_globus_urls, delimitChar=" | "))
        vals.append(string_helper.listToDelimited(prot_files, delimitChar=" | "))
        print(string_helper.listToCommaSeparated(vals))
    
    def convert_to_globus_url(self, path_to_file):
        if string_helper.isBlank(path_to_file):
            return("")
        else:
            pfile = path_to_file.strip()
            if pfile.startswith(self.globus_system_dir):
                #url = self.globus_base_url + file_helper.ensureBeginningSlashURL(pfile[len(self.globus_system_dir):]).replace("/", "%2F").replace(" ", "%20")
                url = self.globus_base_url + file_helper.ensureBeginningSlashURL(pfile[len(self.globus_system_dir):]).replace(" ", "%20")
                return url
            else:
                return ""
            
    
    #iterate through all entity types and print the csv info for each type
    #print the csv header first
    def print_all_entities_protocol_info(self, include_uuid = False, include_test_group = False):
        self.print_protocol_info_header(include_uuid=include_uuid)
        for ent_type in entity_types:
            self.print_entities_protocol_info(ent_type, include_uuid = include_uuid, include_test_group=include_test_group)        
    def print_entities_protocol_info(self, entity_type, include_uuid = False, include_test_group = False):
        url = self.entity_api_url + "entities?entitytypes=" + entity_type
        headers = {'Authorization': 'Bearer ' + self.nexus_token}
        resp = requests.get(url, headers=headers)
        status_code = resp.status_code
        if status_code < 200 or status_code >= 300:
            resp.raise_for_status()

        entities = resp.json()
        for ent in entities:
            self.print_protocol_info(ent, entity_type, include_uuid, include_test_group)

    def get_prop(self, prop_name):
        if not prop_name in self.props:
            raise Exception("Required property " + prop_name + " not found in " + self._prop_file_name)
        val = self.props[prop_name]
        if string_helper.isBlank(val):
            raise Exception("Required property " + prop_name + " from " + self._prop_file_name + " is blank")
        return self.props[prop_name]
    
    def get_globus_dir(self, file_path):
        if file_path.startswith(self.globus_system_dir):
            sub_path = os.path.dirname(file_helper.ensureBeginningSlashURL(file_path[len(self.globus_system_dir):]))
            globus_path = self.globus_app_base_url + sub_path.replace("/", "%2F")
            return globus_path
        else:
            return None
        
    def _direct_ancestor_display_id(self, id):
        idx = id.rfind("-")
        if idx == -1:
            return None
        else:
            return id[:idx]
        
    #prints information about sample up the hierarchy from a given sample id
    #takes a list of display ids
    def print_sample_info(self, sample_ids):
        url_start = self.entity_api_url + "entities/"
        headers = {'Authorization': 'Bearer ' + self.nexus_token}
        samples = []
        for sample_id in sample_ids:
            samples.append(sample_id)
            next_sample = self._direct_ancestor_display_id(sample_id)
            while next_sample is not None:
                next_sample = self._direct_ancestor_display_id(next_sample)
            samples.reverse()
            url = url_start + sample_id
            resp = requests.get(url, headers=headers)
            status_code = resp.status_code
            if status_code < 200 or status_code >= 300:
                resp.raise_for_status()

            entities = resp.json()
            for ent in entities:
                self._print_sample_info_line(ent)
                
                
    def _print_sample_info_line(self, entity):
        print(entity)
                