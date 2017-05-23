import os, json,shutil
import requests
import random
from bs4 import BeautifulSoup
import time
from time import gmtime, strftime
from datetime import datetime
from cron import helpers




with open('config/api2sdk2nuget.json', 'r') as f:
    map_object = json.load(f)

    sdk_map = map_object

#get existing projects from swagger_to_sdk config file (this is the main source of truth.)

swagger_to_sdk_config_file_name = 'swagger_to_sdk_config.json'


swagger_to_sdk = helpers.request_helper(sdk_raw_url + swagger_to_sdk_config_file_name )
azure_projects = [helpers.get_azure_name_space_data(swagger_to_sdk['projects'][p]['swagger'])[0] for p in swagger_to_sdk['projects']]
azure_projects_no_duplicate = list(set(azure_projects))


#Get changes. 
print ('@@@@ FINDING NEW PROJECTS .....')

new_projects = helpers.get_new_project_details(helpers.get_new_project_names_v2(azure_projects_no_duplicate))

print ('@@@@ FINDING CHANGES IN EXISTING PROJECTS .....')
existing_projects = helpers.get_changes_in_existing_projects(swagger_to_sdk_config_file_name, sdk_raw_url, assumed_current_date)


#update the missing PR numbers. 

try:
    with open('config/sha2pr.json', 'r') as f:
        sha2pr = json.load(f)
except:
    sha2pr = {}

print ('@@@@UPDATING PRS .....')
prs = update_remaining_PR_v2(existing_projects, sha2pr=sha2pr) #[[(u'azure-keyvault', u'ab6034c2ed4ae7347a5817242487706e5a49b73c', u'1195')]

print(prs)

for p in prs:
    for p1 in p:
        (proj, sha, pr)=  p1
        sha2pr[sha] = pr 
        if existing_projects[proj].get('changes'):
            existing_projects[proj]['changes']['pr_num'] = pr
            
print('@@@@WRITING UPDATES TO SHA2PR .....')

with open('config/sha2pr.json', 'w')as f:
    json.dump(sha2pr, f)



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