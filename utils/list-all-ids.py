import traceback
import sys
from entity_info import EntityInfo

property_file = "../data_ingest.properties"
entity_types = ['Donor', 'Sample', 'Dataset']

try:
    info = EntityInfo(property_file)
    info.print_all_ids()
    sys.exit(0)

except Exception as e:
    print("Error during execution.")
    print(str(e))
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    sys.exit(1) 
