
from neo4j import TransactionError, CypherError
import sys
import os
import traceback
import requests

from hubmap_commons.hubmap_const import HubmapConst
from hubmap_commons.neo4j_connection import Neo4jConnection
from hubmap_commons.hm_auth import AuthHelper
from hubmap_commons.test_helper import load_config

es_indices = []

# this method will delete a list of datasets from Neo4j and from any Elasticsearch indices
# it will also re-index the deleted datasets' donors
def delete_dataset(conf_data, driver, token, dataset_uuid_list):
    
    donor_uuid = None
    
    for uuid in dataset_uuid_list:
        # this cypher query finds datasets with attached children
        dataset_check_stmt = """MATCH (act)-[:ACTIVITY_OUTPUT]->(ds)-[:HAS_METADATA]-(m), 
            (ds)-[:ACTIVITY_INPUT]->(act2) 
            WHERE ds.uuid = '{uuid}' RETURN act.uuid, ds.uuid, m.uuid, act2.uuid AS downstream_uuid""".format(uuid=uuid)
        tx = None
        with driver.session() as session:
            try:
                tx = session.begin_transaction()
                dataset_with_children = list(tx.run(dataset_check_stmt))
                if len(dataset_with_children) == 0:
                    print("Error: found child data for dataset: " + uuid + " this dataset will NOT be deleted.")
                    continue
                print("Starting delete process for UUID: " + uuid)
                donor_stmt = """MATCH (sample)-[:ACTIVITY_INPUT]->(act)-[:ACTIVITY_OUTPUT]->(ds),
                    (donor)-[*]->(sample)  
                    WHERE ds.uuid = '{uuid}' AND donor.entitytype = 'Donor' 
                    RETURN donor.uuid AS donor_uuid, donor.hubmap_identifier AS donor_hubmap_identifier, donor.entitytype AS donor_entitytype""".format(uuid=uuid)
                
                for record in session.run(donor_stmt):
                    donor_uuid = record['donor_uuid']
                if donor_uuid == None:
                    print("Error: no Donor found for dataset: " + uuid + " this dataset will NOT be deleted.")
                    continue                    
                #delete_stmt = """MATCH (act_m)<-[:HAS_METADATA]-(act)-[:ACTIVITY_OUTPUT]->(ds)-[:HAS_METADATA]->(m) 
                #    WHERE ds.uuid = '{uuid}' 
                #    DETACH DELETE ds,act,m, act_m 
                #    RETURN ds,act, m, act_m""".format(uuid=uuid)
                #tx.run(delete_stmt)
                # now fix the ES index:
                delete_dataset_from_es(conf_data, token, uuid, donor_uuid)
            except CypherError as cse:
                print ('A Cypher error was encountered: '+ cse.message)
                tx.rollback()
                raise
            except:
                print ('A general error occurred: ')
                traceback.print_exc()
                tx.rollback()
                raise
        

# delete a single dataset from all Elasticsearch indices
def delete_dataset_from_es(conf_data, token, dataset_uuid, donor_uuid):
    """                        url = self.confdata['INGEST_PIPELINE_URL'] + '/request_ingest'
                        #full_path = metadata_node[HubmapConst.DATASET_LOCAL_DIRECTORY_PATH_ATTRIBUTE]
                        print('sending request_ingest to: ' + url)
                        r = requests.post(url, json={"submission_id" : "{uuid}".format(uuid=uuid),
                                                     "process" : self.confdata['INGEST_PIPELINE_DEFAULT_PROCESS'],
                                                     "full_path": full_path,
                                                     "provider": "{group_name}".format(group_name=group_info['displayname'])}, 
                                          #headers={'Content-Type':'application/json', 'Authorization': 'Bearer {token}'.format(token=current_token )})
                                          headers={'Content-Type':'application/json', 'Authorization': 'Bearer {token}'.format(token=AuthHelper.instance().getProcessSecret() )})

        try:
            #reindex this node in elasticsearch
            rspn = requests.put(app.config['SEARCH_WEBSERVICE_URL'] + "/reindex/" + new_record['uuid'], headers={'Authorization': request.headers["AUTHORIZATION"]})
        except:
            print("Error happened when calling reindex web service")

    """
    try:
        #reindex this node in elasticsearch
        rspn = requests.put(app.config['SEARCH_WEBSERVICE_URL'] + "/reindex/" + donor_uuid, headers={'Authorization': "Bearer " + token})
    except:
        print("Error happened when calling reindex web service")
    
    # reindex the donor
    
    pass

if __name__ == "__main__":    
    file_path = '/home/chb69/git/ingest-ui/src/ingest-api/instance'
    filename = 'app.cfg'
    confdata = load_config(file_path, filename)
    conn = Neo4jConnection(confdata['NEO4J_SERVER'], confdata['NEO4J_USERNAME'], confdata['NEO4J_PASSWORD'])
    driver = conn.get_driver()

    dataset_uuid_list = ['b17694503bcbdd2458d3e96373ce9fbc', 'c34acecd4dbd9fc6a41a6ba4563bffc5', 'ed8a4dbbb1554a5e3227d6dfb2368828','b40eb3abccf2341f274cfd4ba809c03e']
    try:
        delete_dataset(confdata, driver, dataset_uuid_list)
    except:
        print ('A general error occurred: ')
        traceback.print_exc()
        raise
    finally:
        if conn != None:
            conn.close()

    