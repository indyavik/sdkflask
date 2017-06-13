"""
:test dashboard app using unittest 
"""
from app import app
import unittest 
import os
import json
import copy
from cron import helpers 

#globals

git_url = 'https://api.github.com/repos/Azure/azure-rest-api-specs/'

with open('config/api2sdk2nuget.json', 'r') as f:
    map_object = json.load(f)
    sdk_map = map_object

sdk_raw_url = 'https://raw.githubusercontent.com/Azure/azure-sdk-for-python/master/'
swagger_to_sdk_config_file_name = 'swagger_to_sdk_config.json'
swagger_to_sdk = helpers.request_helper(sdk_raw_url + swagger_to_sdk_config_file_name )

metadata= helpers.get_project_list_from_config(swagger_to_sdk)
azure_projects, lookup_map, md_projects = metadata[0], metadata[1],metadata[2]
assumed_current_date = '2017-04-01' #all packages without build.json are assued to be current as of  04-01

#a patched swagger to sdk to check specific function(s) 

"""
with open('config/patched_swagger_to_sdk_config.json', 'r') as f:
    patched_swagger_to_sdk = json.load(f)
"""

test_azure_folder ="arm-cdn"

class DashboardTestCase(unittest.TestCase):

	def get_shortened_swagger_to_sdk(self, swagger_to_sdk, sdk_key):
		x = copy.deepcopy(swagger_to_sdk)
		for k,v in x['projects'].items():
			if k != sdk_key:
				del x['projects'][k]
		return x

	def test_swagger_config_is_not_none(self):

		assert swagger_to_sdk is not None 
			#self.assertEqual(repsonse.status_code, 200)

	def test_swagger_config_is_parsed(self):
		data = helpers.get_project_list_from_config(swagger_to_sdk)
		azure_projects, lookup, md_projects = data[0], data[1], data[2]

		assert len(azure_projects) > 1, "Swagger config file could not be parsed. get_project_list_from_config(swagger_to_sdk) "
		assert md_projects is not None , "Markdown project was not found by parser  get_project_list_from_config(swagger_to_sdk)" 
		assert lookup.get('recoveryservicesbackup') is not None, "get_project_list_from_config(swagger_to_sdk) did not return a dictionary object" #lookup map is created

	def test_get_nuget_data(self):
		""" test for nuget parser "helpers.get_recent_from_nuget_v2" """

		package = sdk_map['arm-cdn']['nuget_package']
		nuget_data = helpers.get_recent_from_nuget_v2(package)
		recent = nuget_data.get('nuget_recent', {})
	
		assert recent.get('recent_release') is not None, "Nuget parser -> get_recent_from_nuget_v2(nuget_package) returned No response"

	def test_get_swagger_history(self):
		"""
		test for retrieving swagger history for a given from github. should return a swagger_behind value > 0 
		"""
		swagger = 'arm-cdn/2016-10-02/swagger/cdn.json'
		current_date = "01-15-2016"
		data = helpers.get_swagger_updates_v2("arm-cdn/2016-10-02/swagger/cdn.json", git_url, current_date)
		swagger_behind = data.get('swagger_behind') 

		assert swagger_behind is not None, "function get_swagger_updates_v2 did not return anything"
		assert swagger_behind > 0, "function get_swagger_updates_v2 returned incorrect swagger behind, must be more than 0"


	def test_get_azure_key_folder_params(self):
		"""test key params from azure api spec on github are retrieved and parsed properly. """

		data = helpers.get_key_folder_params_v3(git_url, test_azure_folder)

		assert len(data) == 3, "unexpected result sets. function -> helpers.get_key_folder_params_v3"
		assert data[0] == "No", "incorrectly determining arm-cdn as a composie project. function -> helpers.get_key_folder_params_v3 "
		assert len(data[1]) > 1, "were expecting more than 1 folder for arm-cdn. function -> helpers.get_key_folder_params_v3 "


	def test_find_new_projects(self):
		"""
		Function get_new_project_names_v2 Should return atleast 1 new projects (actually many. ). 
		"""
		azure_projects_in_sdk = ['arm-cdn']
		data = helpers.get_new_project_names_v2(azure_projects_in_sdk)

		assert len(data) > 1, "No new projects were found. function -> get_new_project_names_v2"


	def test_find_changes_swagger_only(self):
		"""
		test to see if changes in swagger file are captured (dns project returns a change == "swaggerUpdate")
		"""
		traffic_manager = self.get_shortened_swagger_to_sdk(swagger_to_sdk, "dns")
		data = helpers.get_changes_in_existing_projects(traffic_manager, sdk_raw_url, assumed_current_date, lookup_map)
		changes = data["azure-mgmt-dns"].get("changes")

		assert changes is not None,  "No change detected. function - >get_changes_in_existing_projects"
		assert changes.get('change_type') == 'SwaggerUpdate', "Wrong change type detected. May be something changed in the api repo"


	def test_find_changes_folder_change(self):
		"""
		test to see if changes in folder(e.g. new folder) is captured (trafficmanager project returns a "folder change")
		"""
		traffic_manager = self.get_shortened_swagger_to_sdk(swagger_to_sdk, "trafficmanager")
		data = helpers.get_changes_in_existing_projects(traffic_manager, sdk_raw_url, assumed_current_date, lookup_map)
		changes = data["azure-mgmt-trafficmanager"].get("changes")

		assert changes is not None,  "No change detected. function - >get_changes_in_existing_projects"
		assert changes.get('change_type') == 'Folder', "Wrong change type detected. May be something changed in the api repo"


	def test_find_changes_md_changes(self):

		"""
		test to see if a project with new markdown type structure is properly handled.
		(recoverservicesbackup project should return change_type = 'SwaggerUpdate')
		"""
		md_project = self.get_shortened_swagger_to_sdk(swagger_to_sdk, 'recoveryservicesbackup')
		data = helpers.get_changes_in_existing_projects(md_project, sdk_raw_url, assumed_current_date, lookup_map)
		changes = data["azure-mgmt-recoveryservicesbackup"].get("changes")

		assert changes is not None,  "No change detected for Markdown type project. function - >get_changes_in_existing_projects"
		assert changes.get('change_type') == 'SwaggerUpdate', "Wrong change type detected. May be something changed in the api repo"
		assert changes.get('ind_changes') is not None , "Was expecting multiple swagger changes for recoveryservicesbackup, only 1 returned. did something change in markdown file upstram ?"


	def find_changes_Composite_to_nonComposite(self):

		pass




	"""
	def test_index(self):
		#e nsure flask is set up and responding 
		tester = app.test_client(self)
		repsonse = tester.get('/', content_type='html/text')
		self.assertEqual(repsonse.status_code, 200)

	def test_not_exists(self):
		#404 on non existent routes 
		tester = app.test_client(self)
		repsonse = tester.get('/nonExistanceURL', content_type='html/text')
		self.assertEqual(repsonse.status_code, 404)


	def test_submit(self): 
		#correct parsing, and error conditions
		
		tester = app.test_client(self)

		rv = tester.post('/submit', data=dict(phone_field='1203456789'), follow_redirects=True)
		assert '(120)345-6789' in rv.data 


	"""


if __name__ == '__main__' : 
	unittest.main()
