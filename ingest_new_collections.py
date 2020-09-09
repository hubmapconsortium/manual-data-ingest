import os
from hubmap_commons import string_helper
import csv
import sys
import traceback
import json
from ingest_props import IngestProps
from id_helper import UUIDHelper
from hubmap_commons.hm_auth import AuthHelper
from py2neo import Graph

CREATE_COLLECTION_Q = "CREATE (c:Collection {entitytype: 'Collection', uuid:{uuid}, provenance_create_timestamp: TIMESTAMP(), provenance_modified_timestamp: TIMESTAMP(), provenance_user_email: {provenance_user_email}, provenance_user_displayname: {provenance_user_displayname}, label: {name}, has_doi: false, description: {description}, display_doi: {display_doi}, doi: {doi}, creators: {creators}})"
ASSOCIATE_COLLECTION_Q = "match (c:Collection {uuid: {coll_uuid}}), (ds:Entity {entitytype:'Dataset', uuid: {ds_uuid}}) CREATE (c)<-[ic:IN_COLLECTION]-(ds) return ic"
class CollectionIngest:
    
    def __init__(self, property_file_name):
        self.props = IngestProps(property_file_name, required_props = ['nexus.token', 'neo4j.server', 'neo4j.username', 'neo4j.password', 'collections.input.file', 'uuid.api.url'])
        self.uuid_helper = UUIDHelper(ingest_props = self.props)
        self.token = self.props.get('nexus.token')
        self.neo4j_server = self.props.get('neo4j.server')
        self.neo4j_user = self.props.get('neo4j.username')
        self.neo4j_password = self.props.get('neo4j.password')
        self.collections_tsv_path = self.props.get("collections.input.file")
        self.auth_helper = AuthHelper.instance()
        if string_helper.isBlank(self.collections_tsv_path) or not os.path.isfile(self.collections_tsv_path):
            raise Exception("collections tsf file does not exist:" + self.collections_tsv_path)
        if not self.collections_tsv_path.endswith(".tsv"):
            raise Exception("collections file must be of type .tsv : " + self.collections_tsv_path)
        self.collection_info = []
        with open(self.collections_tsv_path, newline='') as tsvfile:
            reader = csv.DictReader(tsvfile, delimiter='\t')
            for row in reader:
                info_row = {}
                for key in row.keys():
                    info_row[key] = row[key]
                self.collection_info.append(info_row)
        
        self.graph = Graph(self.neo4j_server, auth=(self.neo4j_user, self.neo4j_password))
        
    def ingest_collections(self):
        row_num = 0
        for collection in self.collection_info:
            row_num = row_num + 1
            if not self.check_fields(collection, row_num): continue
            dataset_uuids = self.resolve_dataset_uuids(collection['datasets'])
            if dataset_uuids is None:
                print("Error resolving dataset UUID(s) for collection " + collection('coll_num') + ". Will not import.")
                continue
            self.create_collection(collection, dataset_uuids)
            
            
    def create_collection(self, collection_record, dataset_uuids):
        #create a new uuid and doi id for the collection
        coll_id_info = self.uuid_helper.new_uuid("COLLECTION", True)
        
        #get the user information
        user_info = self.auth_helper.getUserInfo(self.token)
        
        #create the collection
        coll_create = self.graph.run(CREATE_COLLECTION_Q,
                                     provenance_user_email = user_info['username'],
                                     provenance_user_displayname = user_info['name'],
                                     name = collection_record['title'],
                                     description = collection_record['description'],
                                     display_doi = coll_id_info['displayDoi'],
                                     doi = coll_id_info['doi'],
                                     uuid = coll_id_info['uuid'],
                                     creators = collection_record['creators'])
        
        #connect the datasets to the collection
        for ds_uuid in dataset_uuids:
            coll_rel = self.graph.run(ASSOCIATE_COLLECTION_Q,
                                      coll_uuid = coll_id_info['uuid'],
                                      ds_uuid = ds_uuid)

        print("COLLECTION CREATED\t" + collection_record['coll_num'] + '\t' + coll_id_info['uuid'] + '\t' + coll_id_info['displayDoi'])
        
        
    def resolve_dataset_uuids(self, dataset_list):
        dataset_ids = dataset_list.split(',')
        dataset_uuids = []
        for dataset_id in dataset_ids:
            uuid = self.uuid_helper.resolve_to_uuid(dataset_id)
            if uuid is None:
                print("Cannot resolve id " + dataset_id + " to a valid UUID")
                return None
            dataset_uuids.append(uuid)
        return dataset_uuids
    
    def is_valid_json(self, val):
        try:
            json.loads(val)
        except ValueError:
            return False
        
        return True
    
    def check_fields(self, collection, row_num):
        all_good = True
        if not 'coll_num' in collection or string_helper.isBlank(collection['coll_num']):
            print("coll_num field missing in row " + str(row_num) + ". Will not import row.")
            return False
        if collection['coll_num'].strip().startswith('#'):
            print("collection " + collection['coll_num'] + " is commented out.  Will not import")
            return False
        if not 'title' in collection or string_helper.isBlank(collection['title']):
            print("collection with coll_num " + collection['coll_num'] + " is missing the title field.  Will not be imported.")
            all_good = False
        if not 'description' in collection or string_helper.isBlank(collection['description']):
            print("collection with coll_num " + collection['coll_num'] + " is missing the description field.  Will not be imported.")
            all_good = False
        if not 'creators' in collection or string_helper.isBlank(collection['creators']):
            print("collection with coll_num " + collection['coll_num'] + " is missing the creators field.  Will not be imported.")
            all_good = False
        if not self.is_valid_json(collection['creators']):
            print("collection with coll_num " + collection['coll_num'] + " does not contain valid json for the creators field.  Will not be imported.")
            all_good = False
        if not 'datasets' in collection or string_helper.isBlank(collection['datasets']):
            print("collection with coll_num " + collection['coll_num'] + " is missing the datasets field.  Will not be imported.")
            all_good = False
            
        return all_good
            
            
try:
    ingest_worker = CollectionIngest("data_ingest.properties")
    ingest_worker.ingest_collections()
    
except Exception as e:                                                                                                            
    exc_type, exc_value, exc_traceback = sys.exc_info()
    eMsg = str(e)                                                                                                                     
    print("ERROR Occurred: " + eMsg)
    traceback.print_tb(exc_traceback)