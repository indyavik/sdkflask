import os, json, shutil
import time 
from time import gmtime, strftime
from datetime import datetime
from cron import helpers

#globals (via a config file later on)
git_url = 'https://api.github.com/repos/Azure/azure-rest-api-specs/'
raw_url = 'https://raw.githubusercontent.com/Azure/azure-rest-api-specs/master/' 
sdk_raw_url = 'https://raw.githubusercontent.com/Azure/azure-sdk-for-python/master/'
swagger_to_sdk_config_file_name = 'swagger_to_sdk_config.json'
assumed_current_date = '2017-04-01' #all packages without build.json are assued to be current as of  04-01
sdk_url = 'https://api.github.com/repos/Azure/azure-sdk-for-python/'

"""
Key Definitions:
project: Key in swagger_to_sdk_config. Example 'cdn', 'batch.management' , 'billing' 
sdk or sdk_name: Name of the corresponding project as in azure-sdk-for-python repo. Example 'azure-mgt-cdn', 'azure-mgmt-batch' 
azure_api_name (or azure_project) : Name of the corresponding project in azure-rest-api-specs repo. Example 'arm-cdn'

"""

with open('config/api2sdk2nuget.json', 'r') as f:
    map_object = json.load(f)

    sdk_map = map_object

#get existing projects from swagger_to_sdk config file (this is the main source of truth.)

swagger_to_sdk_config_file_name = 'swagger_to_sdk_config.json'

swagger_to_sdk = helpers.request_helper(sdk_raw_url + swagger_to_sdk_config_file_name )
#azure_projects = [helpers.get_azure_name_space_data(swagger_to_sdk['projects'][p]['swagger'])[0] for p in swagger_to_sdk['projects']]
metadata= helpers.get_project_list_from_config(swagger_to_sdk)
azure_projects, lookup_map, md_projects = metadata[0], metadata[1],metadata[2]
azure_projects_no_duplicate = list(set(azure_projects))


#Get changes. 
print ('@@@@ FINDING NEW PROJECTS .....')

new_projects = helpers.get_new_project_details(helpers.get_new_project_names_v2(azure_projects_no_duplicate))

print ('@@@@ FINDING CHANGES IN EXISTING PROJECTS .....')

existing_projects = helpers.get_changes_in_existing_projects(swagger_to_sdk, sdk_raw_url, assumed_current_date, lookup_map)

#update the multi projects for easy handling in jinja templates. (if meta['changes'] = 'no' then there's no changes. )

for e in existing_projects:
    proj = existing_projects[e].get('multiple_projects')
    if not proj:
        proj = existing_projects[e].get('same_sdk')
    if proj:
        for p in proj:
            existing_projects[e]['meta'] = {'changes' : 'no', 'current_swagger' : 'multiple projects. No single swagger '}
            if proj[p].get('changes'):
                existing_projects[e]['meta'] = {'changes' : 'yes', 'current_swagger' : 'multiple projects. No single swagger '}
                break;


#update the missing PR numbers. 

try:
    with open('config/sha2pr.json', 'r') as f:
        sha2pr = json.load(f)
except:
    sha2pr = {}

print ('@@@@UPDATING PRS .....')

prs = helpers.update_remaining_PR_v2(existing_projects, sha2pr=sha2pr) #[[(u'azure-keyvault', u'ab6034c2ed4ae7347a5817242487706e5a49b73c', u'1195')]

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