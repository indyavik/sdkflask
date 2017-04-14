import os, json,shutil
import requests
import random
from bs4 import BeautifulSoup
from time import gmtime, strftime
from datetime import datetime
from cron import helpers

#globals (via a config later on)
git_url = 'https://api.github.com/repos/Azure/azure-rest-api-specs/'

#load base files (map and latest build file to compare against. )

with open('config/api2sdk2nuget.json', 'r') as f:
    map_object = json.load(f)

with open('config/fudge.json', 'r') as f:
    build_file = json.load(f)

#key variables used throghout
projects = build_file['projects']
sdk_map = map_object

#run. 

new_projects = helpers.get_new_project_details(helpers.get_new_project_names(sdk_map))
existing_projects = helpers.get_existing_changes(sdk_map, projects, git_url)
    
#write to a json file (or database) to build web views. 

time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

to_write ={'existing_projects': existing_projects , 'new_projects' : new_projects, 'report_time' : time_stamp}

#move the existing latest.json file to archive. 
archive_date = datetime.now().strftime("%Y_%m_%d")

try:
    if (os.path.exists('changes/latest.json')):
        shutil.move('changes/latest.json', 'changes/archived_'+archive_date+'.json')
except:
    print('could not find or move changes/latest.json')

with open('changes/latest.json', 'w')as f:
    json.dump(to_write, f)

try:
    os.chmod("changes/latest.json", 777)
except:
    print('could not change permission of file changes/latest.json')
