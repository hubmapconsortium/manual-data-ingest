import sys
import os
from hubmap_commons import string_helper
from hubmap_commons import file_helper
from hubmap_commons.exceptions import ErrorMessage 
import traceback
from ingest_props import IngestProps
import time
import logging
import requests
from py2neo import Graph
from hubmap_commons.hm_auth import AuthCache
from hubmap_commons.hm_auth import AuthHelper
import shutil
import subprocess
from flask import Response
from id_helper import UUIDHelper
import re

SINGLE_DATASET_QUERY = "match(e:Entity {uuid: {uuid}})-[:HAS_METADATA]-(m:Metadata) return e.uuid as uuid, e.entitytype as entitytype, m.status as status, m.data_access_level as data_access_level, m.provenance_group_uuid as group_uuid"
ALL_ANCESTORS_QUERY = "MATCH (ds_metadata:Metadata)<-[:HAS_METADATA]-(dataset {uuid: {uuid}})<-[:ACTIVITY_OUTPUT]-(e1)<-[r:ACTIVITY_INPUT|:ACTIVITY_OUTPUT*]-(all_ancestors:Entity)-[:HAS_METADATA]->(all_ancestors_metadata) RETURN distinct all_ancestors.uuid as uuid, all_ancestors.entitytype as entity_type, all_ancestors_metadata.data_types as data_types, all_ancestors_metadata.data_access_level as data_access_level, all_ancestors_metadata.status as status, all_ancestors_metadata.uuid as meta_uuid"
COUNT_SAMPLES_ATTACHED_TO_META = "match (m:Metadata {uuid:{meta_uuid}})<-[:HAS_METADATA]-(s:Entity {entitytype: 'Sample'}) return count(s) as count"
CLONE_META_NODE_ENTITY = "match(e:Entity {uuid: {ent_uuid}})-[:HAS_METADATA]-(met:Metadata) with met as oldm create (copy: Metadata) set copy = oldm with copy as nxt set nxt.uuid = {new_meta_uuid}"
UNLINK_META_NODE_ENTITY = "match (m:Metadata)-[lnk:HAS_METADATA]-(e:Entity {uuid: {ent_uuid}}) delete lnk"
LINK_META_NODE_ENTITY = "MATCH (e:Entity {uuid: {ent_uuid}}),(m:Metadata {uuid: {meta_uuid}}) CREATE (e)-[lnk:HAS_METADATA]->(m) RETURN type(lnk)"
PUBLIC_FACLS = 'u::rwx,g::r-x,o::r-x,m::rwx,u:{hive_user}:rwx,u:{globus_user}:rwx,d:user::rwx,d:user:{hive_user}:rwx,d:user:{globus_user}:rwx,d:group::r-x,d:mask::rwx,d:other:r-x'
TRIAL_RUN = False
SET_ACLS = False

class DatasetWorker:
    
    #initialize, set variables from properties and/or command line,
    #check the auth token and read the tsv file data into a dictionary
    #and the header labels into a list
    def __init__(self, property_file_name):
        cur_time = time.strftime("%d-%m-%Y-%H-%M-%S")
        error_log_filename = "publish_datasets_err" + cur_time + ".log"
        self.error_logger = logging.getLogger('publish.datasets.err')
        self.error_logger.setLevel(logging.INFO)
        error_logFH = logging.FileHandler(error_log_filename)
        self.error_logger.addHandler(error_logFH)
        
        recording_log_filename = "publish_datasets_rcd" + cur_time + ".log"
        self.recording_logger = logging.getLogger('publish.datasets.rcd')
        self.recording_logger.setLevel(logging.INFO)
        recording_logFH = logging.FileHandler(recording_log_filename)
        self.recording_logger.addHandler(recording_logFH)
        
        
        self.dataset_info = None
        self.dataset_info_tsv_path = None
        self.props = IngestProps(property_file_name, required_props = ['nexus.token', 'neo4j.server', 'neo4j.username', 'neo4j.password', 'consortium.dataset.dir', 'public.dataset.dir', 'hive.username', 'globus.username', 'globus.app.client.id', 'globus.app.client.secret', 'search.api.url', 'old.lz.dataset.dir', 'uuid.api.url'])
        self.uuid_helper = UUIDHelper(ingest_props = self.props)
        self.token = self.props.get('nexus.token')
        self.neo4j_server = self.props.get('neo4j.server')
        self.neo4j_user = self.props.get('neo4j.username')
        self.neo4j_password = self.props.get('neo4j.password')
        self.consortium_dir = file_helper.ensureTrailingSlash(self.props.get('consortium.dataset.dir'))        
        self.search_api_url = file_helper.ensureTrailingSlashURL(self.props.get('search.api.url'))
        
        auth_helper = AuthHelper.instance()
        user_info = auth_helper.getUserInfo(self.token, getGroups = True)        
        if isinstance(user_info, Response):
            raise ErrorMessage("error validating auth token: " + user_info.get_data(as_text=True))
        
        
        if 'sub' in user_info:
            self.user_sub = user_info['sub']
        else:
            raise ErrorMessage("user sub information not found for token")
        #provenance_last_updated_user_email                              
        if 'username' in user_info:
            self.user_email = user_info['username']
        else:
            raise ErrorMessage("user email not found for token")
        
        #provenance_last_updated_user_displayname
        if 'name' in user_info.keys():
            self.user_full_name = user_info['name']
        else:
            raise ErrorMessage("user full name not found for token")
                
        if not os.path.isdir(self.consortium_dir):
            raise ErrorMessage("consortium dataset dir not found: " + self.consortium_dir)
        if not os.access(self.consortium_dir, os.W_OK):
            raise ErrorMessage("consortium dataset dir is not writable: ")  + self.consortium_dir
        self.public_dir = file_helper.ensureTrailingSlash(self.props.get('public.dataset.dir'))
        if not os.path.isdir(self.public_dir):
            raise ErrorMessage("public dataset dir not found: ") + self.public_dir
        if not os.access(self.public_dir, os.W_OK):
            raise ErrorMessage("public dataset dir is not writable: ")  + self.public_dir
        self.old_lz_dir = file_helper.ensureTrailingSlash(self.props.get('old.lz.dataset.dir'))
        if not os.path.isdir(self.old_lz_dir):
            raise ErrorMessage("old lz directory not found: ") + self.old_lz_dir
        if not os.access(self.old_lz_dir, os.W_OK):
            raise ErrorMessage("old lz directory is not writable: ") + self.old_lz_dir
        
        self.graph = Graph(self.neo4j_server, auth=(self.neo4j_user, self.neo4j_password))
        if len(sys.argv) >= 2:
            self.id_file = sys.argv[1]
        else:
            self.id_file = self.props.get('dataset.uuid.file')
            if string_helper.isBlank(self.id_file):
                raise ErrorMessage("ERROR: A list of dataset uuids must be specified in " + self.prop_file_name + " as as property 'dataset.uuid.file' or as the first argument on the command line")
        if not os.path.isfile(self.id_file):
            raise ErrorMessage("ERROR: Input file " + self.id_file + " does not exist.")
        
        hive_user = self.props.get('hive.username')
        globus_user = self.props.get('globus.username')
        self.public_facls = PUBLIC_FACLS.format(hive_user=hive_user,globus_user=globus_user)
        
        groupsByName = AuthCache.getHMGroups()
        self.groupsByUUID = {}
        for groupName in groupsByName.keys():
            group = groupsByName[groupName]
            self.groupsByUUID[group['uuid']] = file_helper.ensureTrailingSlash(group['displayname'])

        
        
        id_f = open(self.id_file, 'r') 
        id_lines = id_f.readlines()
        id_f.close()
        
        self.ds_ids = []
        for id_line in id_lines:
            if not string_helper.isBlank(id_line):
                tl = id_line.strip()
                if not tl.startswith('#'):
                    self.ds_ids.append(tl)
        
        self.setfacls = SET_ACLS
        #check to see if the setfacl command is available
        if shutil.which('setfacl') is None:
            self.setfacls = False

        self.donors_to_reindex = []
        
    def publish_all(self):
        self.donors_to_reindex = []
        for dsid in self.ds_ids:
            msg = self.publish_single(dsid)
            if not msg is None:
                self.error_logger.error(msg)
                print(msg)
                self.recording_logger.info(dsid + "\t????\tNOT PUBLISHED\t" + msg)
        
        self._reindex_donors()
                    
        if not self.setfacls:
            msg = "The setfacl command isn't available or turned off.  Make sure to set the file system level protections correctly on any moved datasets with the command\nsetfacl -R --set=" + self.public_facls
            self.error_logger.warning(msg)
            self.recording_logger.warning(dsid + "\t????\tSETFACL WARNING\tsetfacl wasn't available")
            print(msg)
        
    def publish_single(self, dataset_id):
        
        #check that it is a valid id and convert to uuid if not already
        dataset_uuid = self.uuid_helper.resolve_to_uuid(dataset_id)
        if dataset_uuid is None:
            return "-------------------: No uuid found for dataset, will not Publish, id " + dataset_id
        
        #look at all of the ancestors
        #gather uuids of ancestors that need to be switched to public access_level
        #grab the id of the donor ancestor to use for reindexing
        rval = self.graph.run(ALL_ANCESTORS_QUERY, uuid=dataset_uuid).data()
        uuids_for_public = []
        samples_to_clone_metadata = {}
        donor_uuid = None
        for node in rval:
            uuid = node['uuid']
            meta_uuid = node['meta_uuid']
            entity_type = node['entity_type']
            data_access_level = node['data_access_level']
            status = node['status']
            if entity_type == 'Sample':
                #check to see if this sample is connected to other samples via a common
                #metadata node, if so add it to a list to break up later
                if not uuid in samples_to_clone_metadata:
                    sample_count = self._count_samples_on_metadata_node(meta_uuid)
                    if sample_count is None:
                        return(dataset_uuid + ": Unable to obtain the count of samples attached to the same metadata node for sample with id: " + uuid + " metadata uuid: " + meta_uuid)
                    if sample_count > 1:
                        samples_to_clone_metadata[uuid] = meta_uuid
                    
                #if this sample is already set to public, no need to set again
                if not data_access_level == 'public':
                    uuids_for_public.append(uuid)
            elif entity_type == 'Donor':
                donor_uuid = uuid
                if not data_access_level == 'public':
                    uuids_for_public.append(uuid)
            elif entity_type == 'Dataset':
                if not status == 'Published':
                    return(dataset_uuid + ": Has an ancestor dataset that has not been Published. Will not Publish, ancestor dataset is: " + uuid)
        
        if donor_uuid is None:
            return(dataset_uuid + ": No donor found for dataset, will not Publish")
        
        #get info for the dataset to be published
        rval = self.graph.run(SINGLE_DATASET_QUERY, uuid=dataset_uuid).data()
        dataset_status = rval[0]['status']
        dataset_entitytype = rval[0]['entitytype']
        dataset_data_access_level = rval[0]['data_access_level']
        dataset_group_uuid = rval[0]['group_uuid']
        if dataset_entitytype != 'Dataset':
            return dataset_uuid + ': Not a dataset will not Publish, entity type is ' + dataset_entitytype
        if not dataset_status == 'QA':
            return dataset_uuid + ": Not in QA state will not Publish, status is " + dataset_status
        
        #if consortium access level convert to public dataset, if protected access leave it protected
        if dataset_data_access_level == 'consortium':
            msg = self._move_dataset_files_to_public(dataset_uuid, dataset_group_uuid)
            if not msg is None:
                return msg
            uuids_for_public.append(dataset_uuid)
        
        #split samples from metadata if needed
        for sample_uuid in samples_to_clone_metadata.keys():
            meta_uuid = samples_to_clone_metadata[sample_uuid]
            self._clone_and_reattach_meta_node(dataset_id, dataset_uuid, sample_uuid, meta_uuid)
        
        #set dataset status to published and set the last modified user info and user who published
        update_q = "match (e:Entity {uuid:'" + dataset_uuid + "'})-[:HAS_METADATA]->(m:Metadata) set m.status = 'Published', m.provenance_last_updated_user_sub = '" + self.user_sub + "', m.provenance_last_updated_user_email = '" + self.user_email + "', m.provenance_last_updated_user_displayname = '" + self.user_full_name + "', m.provenance_modified_timestamp = TIMESTAMP(), m.published_timestamp = TIMESTAMP(), m.published_user_email = '" + self.user_email + "', m.published_user_sub = '" + self.user_sub + "', m.published_user_displayname = '" + self.user_full_name + "'"
        self.recording_logger.info(dataset_id + "\t" + dataset_uuid + "\tNEO4J-update-base-dataset\t" + update_q)
        if not TRIAL_RUN: self.graph.run(update_q)

        #if all else worked set the list of ids to public that need to be public
        if len(uuids_for_public) > 0:
            id_list = string_helper.listToCommaSeparated(uuids_for_public, quoteChar = "'")
            update_q = "match (e:Entity)-[:HAS_METADATA]->(m:Metadata) where e.uuid in [" + id_list + "] set m.data_access_level = 'public'"
            self.recording_logger.info(dataset_id + "\t" + dataset_uuid + "\tNEO4J-update-ancestors\t" + update_q)
            if not TRIAL_RUN: self.graph.run(update_q)
                
        #reindex everything by calling the reindexer for the Donor, which will trigger a reindex of all children
#        url = self.search_api_url + "reindex/" + donor_uuid
#        headers = {'Authorization': 'Bearer ' + self.token}
#        if not TRIAL_RUN:
#            resp = requests.put(url, headers=headers)
#            status_code = resp.status_code
#            if status_code < 200 or status_code >= 300:
#                return dataset_uuid + ": ERROR calling reindexer for dataset, donor id: " + donor_uuid
#            else:
#                self.recording_logger.info(dataset_id + "\t" + dataset_uuid + "\tREINDEX\t" + url)
#        else:
#            self.recording_logger.info(dataset_id + "\t" + dataset_uuid + "\tREINDEX\t" + url)

        if not donor_uuid in self.donors_to_reindex:
            self.donors_to_reindex.append(donor_uuid)

        return None
    
    def _reindex_donors(self):
        #reindex everything by calling the reindexer for each affected Donor
        #which will trigger a reindex of all children
        for donor_uuid in self.donors_to_reindex:
            url = self.search_api_url + "reindex/" + donor_uuid
            headers = {'Authorization': 'Bearer ' + self.token}
            if not TRIAL_RUN:
                resp = requests.put(url, headers=headers)
                status_code = resp.status_code
                if status_code < 200 or status_code >= 300:
                    return "??????: ERROR calling reindexer for dataset, donor id: " + donor_uuid
                else:
                    self.recording_logger.info("????\t????\tREINDEX\t" + url)
            else:
                self.recording_logger.info("????\t????\tREINDEX\t" + url)
        
        
    def _count_samples_on_metadata_node(self, meta_uuid):
        #print(COUNT_SAMPLES_ATTACHED_TO_META.format(meta_uuid=meta_uuid))
        rval = self.graph.run(COUNT_SAMPLES_ATTACHED_TO_META, meta_uuid = meta_uuid).data()
        return rval[0]['count']
    
    def _clone_and_reattach_meta_node(self, dataset_id, dataset_uuid, sample_uuid, meta_uuid):
        self.recording_logger.info(dataset_id + "\t" + dataset_uuid + "\tCLONE and REATTACH METADATA\tsample_uuid" + sample_uuid + " old_meta_uuid:" + meta_uuid)
        if not TRIAL_RUN:
            new_meta_uuid = self.uuid_helper.new_uuid("METADATA")['uuid']
            self.graph.run(CLONE_META_NODE_ENTITY, ent_uuid = sample_uuid, new_meta_uuid = new_meta_uuid)
            self.graph.run(UNLINK_META_NODE_ENTITY, ent_uuid = sample_uuid)
            self.graph.run(LINK_META_NODE_ENTITY, ent_uuid = sample_uuid, meta_uuid = new_meta_uuid)
        
            
    def _move_dataset_files_to_public(self, uuid, group_uuid):
        group_name = self.groupsByUUID[group_uuid]
        from_path = self.consortium_dir + group_name + uuid
        if not os.path.isdir(from_path):
            return uuid + ": path not found to dataset will not publish, path is " + from_path
        to_path = self.public_dir + uuid
        if not TRIAL_RUN: shutil.move(from_path, to_path)
        self.recording_logger.info("^^^^\t" + uuid + "\tMOVE dataset\tmv " + from_path + " " + to_path)
        if self.setfacls:
            self.recording_logger.info("^^^^\t" + uuid + "\tSET ACLs\tsetfacl -R --set=" + self.public_facls + " " + to_path)
            if not TRIAL_RUN: subprocess.Popen(['setfacl','-R', '--set=' + self.public_facls, to_path ])
        
        #look for a README in the old globus share and replace with a readme that points to
        #the new public version
        old_readme = self.old_lz_dir + group_name + uuid + "/MOVED-README.txt"
        if os.path.isfile(old_readme):
            with open(old_readme, 'r') as file:
                message = file.read()
            message = re.sub(r'/consortium/.*/', '/public/', message)
            message = re.sub(r'%2Fconsortium%2F.*%2F', '%2Fpublic%2F', message)
            with open(old_readme, 'w') as file:
                file.write(message)
            self.recording_logger.info("^^^^\t" + uuid + "\tREWROTE REAMDME\t" + old_readme)
            
        return None

try:
    ds_worker = DatasetWorker("data_ingest.properties")
    ds_worker.publish_all()
    exit(0)
except ErrorMessage as em:                                                                                                            
    print(em.get_message())
    exit(1)    
except Exception as e:                                                                                                            
    exc_type, exc_value, exc_traceback = sys.exc_info()
    eMsg = str(e)                                                                                                                     
    print("ERROR Occurred: " + eMsg)
    traceback.print_tb(exc_traceback)
    exit(1)
