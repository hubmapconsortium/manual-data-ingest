import csv
from hubmap_commons.entity import Entity
from hubmap_commons.test_helper import load_config
from hubmap_commons.hubmap_const import HubmapConst
from hubmap_commons.neo4j_connection import Neo4jConnection, TransactionError


def load_data_dict_from_csv(file_path):
    with open(file_path, mode='r') as csv_file:
        ret_dict = {}
        csv_reader = csv.DictReader(csv_file)
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                line_count += 1
            line_count += 1
            donor_id = row['donor_id']
            source_name = str(row['source_name']).lower().replace(' ', '_')
            dict_obj = {source_name:[]}
            if donor_id in ret_dict:
                dict_obj = ret_dict[donor_id]
            column_headers = ['start_datetime', 'end_datetime', 'graph_version', 'concept_id', 'code', 'sab', 'data_type', 'data_value', 'numeric_operator', 'units', 'preferred_term', 'grouping_concept', 'grouping_concept_preferred_term', 'grouping_code', 'grouping_sab']
            new_record = {}
            for col in column_headers:                    
                new_record[col] = row[col]
            dict_obj[source_name].append(new_record)
            ret_dict[donor_id] = dict_obj
    return ret_dict

def write_data_to_neo4j(conf_data, token, data_dict):
    conn = Neo4jConnection(conf_data['NEO4J_SERVER'], conf_data['NEO4J_USERNAME'], conf_data['NEO4J_PASSWORD'])
    driver = conn.get_driver()
    with driver.session() as session:
        tx = None
        try:
            tx = session.begin_transaction()
            for dict_item in data_dict:
                current_uuid = []
                try: 
                    current_uuid = Entity.get_uuid_list(conf_data['UUID_WEBSERVICE_URL'], token, [dict_item])
                except ValueError as ve:
                    print("Unable to resolve UUID for: " + str(dict_item))
                    continue
                # remove single quotes and replace with double quotes
                metadata_entry = str(data_dict[dict_item]).replace('\'', '"')
                stmt = "MATCH (e)-[:{has_metadata_rel}]-(m) WHERE e.{uuid_attr} = '{uuid}' SET m += {{ {metadata_attr} : '{metadata_entry}' }}".format(
                    has_metadata_rel=HubmapConst.HAS_METADATA_REL, uuid_attr=HubmapConst.UUID_ATTRIBUTE,
                    uuid=current_uuid[0], metadata_attr=HubmapConst.METADATA_ATTRIBUTE, metadata_entry=metadata_entry)
                print('Executing stmt: ' + stmt)
                tx.run(stmt)
        except Exception as e:
            print("Exception encountered: " + str(e))
            tx.rollback()
        tx.commit()

if __name__ == "__main__":
    print("Start")
    root_path = ''
    filename = 'app.cfg'
    conf_data = load_config(root_path, filename)
    data_dict = load_data_dict_from_csv('Sample donor metadata - Sheet1.csv')
    token = ''
    conf_data['UUID_WEBSERVICE_URL'] = '' 
    write_data_to_neo4j(conf_data, token, data_dict)
    print("Done")
                
    