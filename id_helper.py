from hubmap_commons import string_helper
from hubmap_commons import file_helper
from hubmap_commons.exceptions import ErrorMessage
from hubmap_commons.hm_auth import AuthHelper
from flask import Response
import requests

#class to interface with the UUID service
class UUIDHelper:
    
    #constructor, ingest_props (from data_ingest.properties file) or all of auth_token and
    #uuid_service_url required.
    def __init__(self, ingest_props = None, auth_token = None, uuid_service_url = None, globus_app_id = None, globus_app_secret = None):
        self.props = ingest_props
        self.token = self._get_property("nexus.token", auth_token)
        self.uuid_url = self._get_property("uuid.api.url", uuid_service_url)
        self.globus_app_id = self._get_property("globus.app.client.id", globus_app_id).strip()
        self.globus_app_secret = self._get_property("globus.app.client.secret", globus_app_secret).strip()
        
        auth_helper = AuthHelper(self.globus_app_id, self.globus_app_secret)
        user_info = auth_helper.getUserInfo(self.token, getGroups = True)        
        if isinstance(user_info, Response):
            raise ErrorMessage("error validating auth token: " + user_info.get_data(as_text=True))
        
    #helper method to resolve properties for a value that was passed into the
    #constructor or retrieve it from the application properties
    def _get_property(self, prop_name, default_value = None):
        if not string_helper.isBlank(default_value):
            return default_value
        
        return self.props.get(prop_name)
    
    #get the information 
    def resolve_to_uuid(self, identifier):
        url = file_helper.ensureTrailingSlash(self.uuid_url) + "hmuuid/" + identifier
        headers = {'Authorization': 'Bearer ' + self.token}
        resp = requests.get(url, headers=headers)
        status_code = resp.status_code
        if status_code < 200 or status_code >= 300:
            return None
        id_info = resp.json()
        if not isinstance(id_info, list) or len(id_info) == 0:
            return None
        else:
            vals = id_info[0]
        if 'hmuuid' in vals:
            return vals['hmuuid']
        else:
            return None
        
    def new_uuid(self, entity_type, generate_doi = False):
        url = file_helper.ensureTrailingSlash(self.uuid_url) + "hmuuid"
        headers = {'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'}
        gen_doi = "false"
        if generate_doi: gen_doi = "true"
        resp = requests.post(url, json = {'entityType': entity_type, 'generateDOI': gen_doi}, headers=headers)
        status_code = resp.status_code
        if status_code < 200 or status_code >= 300:
            raise ErrorMessage("Unable to generate UUID " + str(resp.status_code) + ":" + str(resp.text))
        vals = resp.json()
        return vals[0]       
        