import os
from properties.p import Property
from hubmap_commons.exceptions import ErrorMessage
from hubmap_commons import string_helper
class IngestProps():
    
    def __init__(self, property_file_name, required_props = []):
        self.prop_file_name = property_file_name
        if not os.path.isfile(property_file_name):
            raise ErrorMessage("property file does not exist: " + property_file_name)

        propMgr = Property()
        self.props = propMgr.load_property_files(property_file_name)
        not_found = []
        for required_prop in required_props:
            if required_prop not in self.props or string_helper.isBlank(self.props[required_prop]):
                not_found.append(required_prop)
        
        if len(not_found) > 0:
            if len(not_found) == 1:
                prop = "property"
            else:
                prop = "properties"
            raise ErrorMessage("Required " + prop + " not found in " + property_file_name + ":[" + string_helper.listToCommaSeparated(not_found) + "]")
        
        
    def get_properties(self):
        return self.props
    
    def get(self, prop_name, required = False):
        if not prop_name in self.props:
            if required:
                raise ErrorMessage("Required property " + prop_name + " not found in " + self.prop_file_name)
            else:
                return None
        val = self.props[prop_name]
        if required and string_helper.isBlank(val):
            raise ErrorMessage("Required property " + prop_name + " from " + self.prop_file_name + " is blank")
        return self.props[prop_name]