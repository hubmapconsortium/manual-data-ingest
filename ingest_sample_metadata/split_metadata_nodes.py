
from neo4j import TransactionError, CypherError
import sys
import os
import requests

from hubmap_commons.hubmap_const import HubmapConst
from hubmap_commons.neo4j_connection import Neo4jConnection
from hubmap_commons.entity import Entity
from hubmap_commons.hm_auth import AuthHelper
from hubmap_commons.uuid_generator import UUID_Generator



# this code will take a list of metadata node identifiers.  It will split them from their sibling nodes but
# creating a new metadata node based off the original metadata node.
def split_metadata_nodes(confdata, token, identifier_list):

    if len(identifier_list) == 0:
        print('Error: no identifiers found')

    conn = Neo4jConnection(confdata['NEO4J_SERVER'], confdata['NEO4J_USERNAME'], confdata['NEO4J_PASSWORD'])
    driver = conn.get_driver()

    uuid_webservice_url = confdata['UUID_WEBSERVICE_URL']
    ug = UUID_Generator(confdata['UUID_WEBSERVICE_URL'])

    
    uuid_list = Entity.get_uuid_list(uuid_webservice_url, token, identifier_list)
    
    #use the first entry in the uuid_list to retrieve the metadata
    existing_metadata = Entity.get_entity_metadata(driver, uuid_list[0])

    metadata_uuid_record = None
    
    try: 
        metadata_uuid_record_list = ug.getNewUUID(token, HubmapConst.METADATA_TYPE_CODE)
        if (metadata_uuid_record_list == None) or (len(metadata_uuid_record_list) != 1):
            raise ValueError("UUID service did not return a value")
        metadata_uuid_record = metadata_uuid_record_list[0]
    except requests.exceptions.ConnectionError as ce:
        raise ConnectionError("Unable to connect to the UUID service: " + str(ce.args[0]))
    
    existing_metadata[HubmapConst.UUID_ATTRIBUTE] = metadata_uuid_record[HubmapConst.UUID_ATTRIBUTE]
    existing_metadata[HubmapConst.REFERENCE_UUID_ATTRIBUTE] = identifier_list
    existing_metadata[HubmapConst.ENTITY_TYPE_ATTRIBUTE] = 'Metadata'
    # clean up some extra items retrieved by the Entity.get_entity_metadata call
    existing_metadata.pop(HubmapConst.LAB_IDENTIFIER_ATTRIBUTE)
    existing_metadata.pop(HubmapConst.DISPLAY_DOI_ATTRIBUTE)
    existing_metadata.pop(HubmapConst.DOI_ATTRIBUTE)
    existing_metadata.pop(HubmapConst.PROVENANCE_CREATE_TIMESTAMP_ATTRIBUTE)
    existing_metadata.pop(HubmapConst.PROVENANCE_MODIFIED_TIMESTAMP_ATTRIBUTE)
    
    with driver.session() as session:
        tx = None
    
        try:
            tx = session.begin_transaction()
            #stmt = Specimen.get_create_metadata_statement(existing_metadata, token, specimen_uuid_record_list, metadata_userinfo, provenance_group, file_list, data_directory, request)
            stmt = Neo4jConnection.get_create_statement(
                existing_metadata, HubmapConst.METADATA_NODE_NAME, HubmapConst.METADATA_TYPE_CODE, True)
            print('Metadata Create statement: ' + stmt)
            tx.run(stmt)
            
            # remove the connections between entities and the metadata
            string_uuid_list = ''
            for uuid in uuid_list:
                # build a string list
                string_uuid_list += "'" + str(uuid) + "',"
            #remove trailing comma
            string_uuid_list = string_uuid_list[:-1]
            delete_stmt = "MATCH (e)-[r:HAS_METADATA]->(m) WHERE e.uuid IN [{string_uuid_list}] DELETE r".format(string_uuid_list=string_uuid_list)
            print("Delete statement:" + delete_stmt)
            tx.run(delete_stmt)
        
            #make new connections
            for uuid in uuid_list:
                create_stmt = "MATCH (e),(m) WHERE e.uuid = '{uuid}' AND m.uuid = '{metadata_uuid}' CREATE (e)-[r:HAS_METADATA]->(m) RETURN r".format(uuid=uuid,metadata_uuid=existing_metadata[HubmapConst.UUID_ATTRIBUTE])
                print("Create statement:" + create_stmt)
                tx.run(create_stmt)

            tx.commit()
        except TransactionError as te: 
            print ('A transaction error occurred: ', te.value)
            tx.rollback()
        except CypherError as cse:
            print ('A Cypher error was encountered: ', cse.message)
            tx.rollback()                
        except:
            print ('A general error occurred: ')
            tx.rollback()
        finally:
            if conn != None:
                conn.close()




if __name__ == "__main__":
    NEO4J_SERVER = ''
    NEO4J_USERNAME = ''
    NEO4J_PASSWORD = ''
    APP_CLIENT_ID = ''
    APP_CLIENT_SECRET = ''
    UUID_WEBSERVICE_URL = ''

    if AuthHelper.isInitialized() == False:
        authcache = AuthHelper.create(
        APP_CLIENT_ID, APP_CLIENT_SECRET)
    else:
        authcache = AuthHelper.instance() 
    processed_secret = AuthHelper.instance().getProcessSecret() 

    conf_data = {'NEO4J_SERVER' : NEO4J_SERVER, 'NEO4J_USERNAME': NEO4J_USERNAME, 
                 'NEO4J_PASSWORD': NEO4J_PASSWORD,
                 'APP_CLIENT_ID': APP_CLIENT_ID,
                 'APP_CLIENT_SECRET': processed_secret,
                 'UUID_WEBSERVICE_URL': UUID_WEBSERVICE_URL}
    
    nexus_token = ''
    
    identifier_list = ['TEST0010-LK-1-1-14-5','TEST0010-LK-1-1-14-3','TEST0010-LK-1-1-14-1']
    
    split_metadata_nodes(conf_data, nexus_token, identifier_list)
    
