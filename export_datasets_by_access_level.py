from ingest_props import IngestProps
import traceback
from py2neo import Graph
from hubmap_commons.hm_auth import AuthCache
from hubmap_commons.exceptions import ErrorMessage
import sys
import os

FIND_PROTECTED = "match(e:Entity {entitytype:'Dataset'})-[:HAS_METADATA]-(m:Metadata) where m.data_access_level = 'protected' return e.uuid as uuid, m.provenance_group_uuid as group_id"
FIND_CONSORTIUM = "match(e:Entity {entitytype:'Dataset'})-[:HAS_METADATA]-(m:Metadata) where m.data_access_level = 'consortium' return e.uuid as uuid, m.provenance_group_uuid as group_id"
FIND_PUBLIC = "match(e:Entity {entitytype:'Dataset'})-[:HAS_METADATA]-(m:Metadata) where m.data_access_level = 'public' return e.uuid as uuid, m.provenance_group_uuid as group_id"
FIND_DERIVED_PROTECTED = "match (ds:Entity {entitytype:'Dataset'})-[:ACTIVITY_INPUT]->(:Activity)-[:ACTIVITY_OUTPUT]->(der:Entity {entitytype:'Dataset'})-[:HAS_METADATA]-(m:Metadata {data_access_level:'protected'}) return distinct der.uuid as uuid, m.provenance_group_uuid as group_id"
FIND_DERIVED_CONSORTIUM = "match (ds:Entity {entitytype:'Dataset'})-[:ACTIVITY_INPUT]->(:Activity)-[:ACTIVITY_OUTPUT]->(der:Entity {entitytype:'Dataset'})-[:HAS_METADATA]-(m:Metadata {data_access_level:'consortium'}) return distinct der.uuid as uuid, m.provenance_group_uuid as group_id"
FIND_DERIVED_PUBLIC = "match (ds:Entity {entitytype:'Dataset'})-[:ACTIVITY_INPUT]->(:Activity)-[:ACTIVITY_OUTPUT]->(der:Entity {entitytype:'Dataset'})-[:HAS_METADATA]-(m:Metadata {data_access_level:'public'}) return distinct der.uuid as uuid, m.provenance_group_uuid as group_id"

class DatasetExport:
    
    def __init__(self, property_file_name):
        self.props = IngestProps(property_file_name, required_props = ['neo4j.server', 'neo4j.username', 'neo4j.password'])
        self.neo4j_server = self.props.get('neo4j.server')
        self.neo4j_user = self.props.get('neo4j.username')
        self.neo4j_password = self.props.get('neo4j.password')
        self.graph = Graph(self.neo4j_server, auth=(self.neo4j_user, self.neo4j_password))
        groupsByName = AuthCache.getHMGroups()
        self.groups = {}
        for groupName in groupsByName.keys():
            group = groupsByName[groupName]
            self.groups[group['uuid']] = group['displayname']
    
    def dump_to_files(self):
        self._dump_to_file("protected-dataset-dirs.txt", FIND_PROTECTED)
        self._dump_to_file("consortium-dataset-dirs.txt", FIND_CONSORTIUM)
        self._dump_to_file("public-dataset-dirs.txt", FIND_PUBLIC)
        self._dump_to_file("public-dataset-dirs-new.txt", FIND_PUBLIC, False)
        self._dump_to_file("protected-derived-dataset-dirs.txt", FIND_DERIVED_PROTECTED)
        self._dump_to_file("consortium-derived-dataset-dirs.txt", FIND_DERIVED_CONSORTIUM)
        self._dump_to_file("public-derived-dataset-dirs-new.txt", FIND_DERIVED_PUBLIC, False)
                
    def _dump_to_file(self, filename, query, add_tmc_dir=True):
        recds = self.graph.run(query).data()
        grp_name = ''
        with open(filename, 'w') as writer:
            for recd in recds:
                if add_tmc_dir:
                    grp_name = self.groups[recd['group_id']].replace(' ', '\\ ') + '/'
                writer.write(grp_name + recd['uuid'] + '\n')
    
try:
    exp = DatasetExport(os.path.dirname(os.path.realpath(__file__)) + "/data_ingest.properties")
    exp.dump_to_files()
except ErrorMessage as em:                                                                                                            
    print(em.get_message())
    exit(1)    
except Exception as e:                                                                                                            
    exc_type, exc_value, exc_traceback = sys.exc_info()
    eMsg = str(e)                                                                                                                     
    print("ERROR Occurred: " + eMsg)
    traceback.print_tb(exc_traceback)
    exit(1)
