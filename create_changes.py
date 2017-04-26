import os, json,shutil
import requests
import random
from bs4 import BeautifulSoup
from time import gmtime, strftime
from datetime import datetime
from cron import helpers


#globals (via a config later on)
git_url = 'https://api.github.com/repos/Azure/azure-rest-api-specs/'
sdk_url = 'https://api.github.com/repos/Azure/azure-sdk-for-python/'
sdk_raw_url = 'https://raw.githubusercontent.com/Azure/azure-sdk-for-python/master/' 

assumed_current_date = '2017-04-01' #all packages without build.json are assued to be current as of  04-01

with open('config/api2sdk2nuget.json', 'r') as f:
    map_object = json.load(f)
    
sdk_map = map_object


#get existing projects from swagger_to_sdk config file (this is the main source of truth.)

swagger_to_sdk_config_file_name = 'swagger_to_sdk_config.json'
#get_azure_name_space_data(current_swagger_path)
swagger_to_sdk = helpers.request_helper(sdk_raw_url + swagger_to_sdk_config_file_name )


azure_projects = [helpers.get_azure_name_space_data(swagger_to_sdk['projects'][p]['swagger'])[0] for p in swagger_to_sdk['projects']]
azure_projects_no_duplicate = list(set(azure_projects))


#Get changes. 
new_projects = helpers.get_new_project_details(helpers.get_new_project_names_v2(azure_projects_no_duplicate))
existing_projects = helpers.get_existing_changes_v2(sdk_map, git_url=git_url, assumed_current_date=assumed_current_date)


#write to a json file (or database) to build web views. 

time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

to_write ={'existing_projects': existing_projects , 'new_projects' : new_projects, 'report_time' : time_stamp}

#move the existing latest.json file to archive. 
archive_date = datetime.now().strftime("%Y_%m_%d")

try:
    if (os.path.exists('changes/latest.json')):
        shutil.move('changes/latest.json', 'changes/archived_'+archive_date+'.json')
except:
    print('Notice: No existing latest.json, nothing to archive')

with open('changes/latest.json', 'w')as f:
    json.dump(to_write, f)

try:
    os.chmod("changes/latest.json", 777)
except:
    print('Notice: could not chmod on latest.json')