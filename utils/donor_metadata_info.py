from hubmap_commons import string_helper
from entity_info import EntityInfo
import json

ent_info = EntityInfo('../data_ingest.properties')
donors = ent_info.get_all_donors()
for donor in donors:
    if 'hubmap_identifier' in donor:
        did = donor['hubmap_identifier']
        if not did.startswith('TEST') and 'metadatas' in donor:
            urls = []
            mdatas = donor['metadatas']
            mdataj = json.loads(mdatas)
            for file_info in mdataj:
                if 'filepath' in file_info and not string_helper.isBlank(file_info['filepath']):
                    globus_url = ent_info.get_globus_dir(file_info['filepath'])
                    if not globus_url is None:
                        if not globus_url in urls:
                            urls.append(globus_url)
            for url in urls:
                print(did + "," + url)        
