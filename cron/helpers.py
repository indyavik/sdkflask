import os, json,shutil
import requests
import random
from bs4 import BeautifulSoup
from time import gmtime, strftime
from datetime import datetime

#globals (via a config later on)
git_url = 'https://api.github.com/repos/Azure/azure-rest-api-specs/'

def request_helper(url, access_token=None):
    """
    helper function/method to call API using request and return JSON encoded object. 
    if fails or gets 404, raises error. 
    
    """
    
    if not access_token:
        access_token = '2dd078a2a012e23bed1ff39015ead3675bc9f1d0'
        
    r = requests.get(url, auth=('username', access_token))
    
    r.raise_for_status()
    

    
    return r.json()

def should_ignore(changed_file):
    """
    helper function to ignore certain files on azure_api_spec
    example: xyz.md, xyz.js, /test/ , /examples/ ....
    
    """
    if not changed_file.endswith('.json'):
        return True
    
    if changed_file.startswith('test/'):
        return True
    
    if '/examples/' in changed_file:
        return True
    
    if '/' not in changed_file:
        return True
    
    
    return False

#should_ignore('test/somethih')

def get_azure_name_space_data(swagger_file_path):
    #count the #  of slashes 1 ->, composite file. , 3 =>swagger file with datefolder. > 3 staggered/subprojects. 
    #Use the fact that folder -=2015, 2016, 2017. ..starts with 20
    
    split_path = swagger_file_path.split('/20')
    
    if len(split_path) > 1:
        #not composite. 
        azure_api_spec_folder, date_folder, swagger_file  = split_path[0], '20'+ split_path[1].split('/')[0], split_path[1].split('/')[2]
    
    else:
        azure_api_spec_folder, date_folder, swagger_file = split_path[0].split('/')[0], 'Composite',  split_path[0].split('/')[1]
        
    #print azure_api_spec_folder, date_folder, swagger_file
    return (azure_api_spec_folder, date_folder, swagger_file)
    #print split_path 
    

def get_key_folder_params(git_url, azure_folder_path):
    """
    returns the composite status. if there is a .json file in root folder. this will be yes. 
    returns the most recent folder (2015-10-11 is more recent than 2014-10-09)
    """   
    rcomposite = request_helper(git_url + 'contents/' + azure_folder_path )
    most_recent_composite_status = 'No' 
    folders =[]
    for r in rcomposite:
        path = r['path']
        folder = path.split(azure_folder_path +'/')[1]
        if folder.startswith('20') or folder.startswith('/20'): 
            folders.append(folder)
        if '.json' in path:
            most_recent_composite_status = 'Yes'
            
    
    return(most_recent_composite_status, sorted(folders))

def get_key_folder_params_v2(git_url, azure_folder_path):
    """
    Given an azure api spec folder (which is a package) name, returns some key parameters for that package. 
    1) composite status. if there is a .json file in root folder. this will be yes. 
    2) most recent sub folder (2015-10-11 is more recent than 2014-10-09)
    3) gets the swagger file. ??
    """   
    rcomposite = request_helper(git_url + 'contents/' + azure_folder_path )
    most_recent_composite_status = 'No' 
    swagger = None
    folders =[]
    for r in rcomposite:
        path = r['path']
        folder = path.split(azure_folder_path +'/')[1]
        if folder.startswith('20') or folder.startswith('/20'): 
            folders.append(folder)
        if '.json' in path:
            most_recent_composite_status = 'Yes'
            swagger=path
  
    if not swagger and folders:
        r_file = request_helper(git_url + 'contents/' + azure_folder_path + '/' + folders[-1] + '/swagger/')
        swagger = r_file[0]['path']
        
            
    return(most_recent_composite_status, sorted(folders), swagger)

def get_recent_from_nuget(package, base_url=None):
    """
    given a name of a C# package on Nuget ('Microsoft.Azure.Management.DataLake.Store'), 
    returns the most recent version and published date
    """
    #print package
    if not base_url:
        base_url = "https://www.nuget.org/packages/"
    
    page_result = requests.get(base_url + package)
    
    if page_result.status_code == 200:
        soup = BeautifulSoup(page_result.content)
        recent = soup.find("tr", class_= "versionTableRow recommended")
        recent_date, recent_release = '',''
        
        if recent:

                    recent_date = recent.find("span")['title']
                    recent_release = recent.find("a", href=True)['href'].split('/')[-1]
                    
        else:
            #get another set of tables. 
            recent = soup.findAll("tr", class_= "versionTableRow")
            #print recent
            if recent:
                recent_v = recent[0]
                recent_date = recent_v.find("span")['title']
                recent_release = recent_v.find("a", href=True)['href'].split('/')[-1]
    
    return (recent_date, recent_release)



def get_oldest_date_v2(file_dates, recent=None):
    
    """
    default -takes a list of dates, or a date, and returns the 'oldest' days and # of days old (i,e, 40 days ago)from today
    if recent=True, will return the 'most' recent date. 
    
    """
    
    date_format = "%Y-%m-%d"
    
    if type(file_dates) is list:
        sorted_dates = sorted(file_dates)
        if not recent:
            oldest_change = sorted_dates[0] #default sorting in ascending order. 
        else:
            oldest_change = sorted_dates[-1]
        
    else:
        oldest_change = file_dates
    
    a = datetime.strptime(datetime.now().strftime("%Y-%m-%d"), date_format)
    b = datetime.strptime(oldest_change.split('T')[0], date_format)

    #print str(abs(a-b))
    days = str(abs(a-b)).split(',')[0]

    return (oldest_change, days)

#get_oldest_date(file_dates)

def get_pr_from_commits(commit_sha, base_url=None, access_token=None):
    """
    given a sha of commit on azure api spec, returns a PR# on github  (if there is one)
    else, returns ' '
    """
    #print package
    #https://github.com/search?q=8461020530ea97978+repo%3AAzure%2Fazure-rest-api-specs&type=issues
    
    if not base_url:
        base_url = "https://github.com/search?q="
        url_en = "+repo%3AAzure%2Fazure-rest-api-specs&type=issues"
    
    url = base_url+commit_sha+url_en
    print (url)
    
    if not access_token:
        access_token = '2dd078a2a012e23bed1ff39015ead3675bc9f1d0'
        
    
    page_result = requests.get(url, auth=('username', access_token))
    
    pr = ''
    
    print(page_result.status_code)
    
    if page_result.status_code == 200:
        soup = BeautifulSoup(page_result.content)
        try:
            issue = soup.find("div", class_= "issue-list")
            pr = issue.find("span", class_ ="float-right").contents[0]
        except:
            pass 
        
    return pr 


#####################################################
##############Main functions #######################

#swagger history 
def get_swagger_updates(azure_api_swagger_path, git_url=None, current_sha=None):
    """
    return the updates to a swagger. 
    if a current_sha of a swagger is known, function returns the updates 'since' this current sha
    else, function returns the entire swagger history. 
    
    #current_sha = base_data['current_version']
    
    """
    swagger_history = request_helper(git_url+'commits?path=' + azure_api_swagger_path)
    
    shas, dates , prs = [], [] , []
    for s in swagger_history:
        shas.append(s['sha'])
        dates.append(s['commit']['committer']['date'])
        
        
    #compare the sha. 
    if current_sha:
        try:
            sha_index = shas.index(current_sha)
            if sha_index > 0: 
                #i.e. there are more recent shas. 
                print('new commits discoverd for -> ' + 'index =' + str(sha_index))
                print('corresponding_date' + str(dates[sha_index]))

                file_dates, commit_sha, swagger_behind = dates[:sha_index], shas[:sha_index] , sha_index
                

            else:
                file_dates, commit_sha, swagger_behind =[],[],0
                
        except:
            print ("sha index not found", Argument)
            file_dates, commit_sha, swagger_behind = dates, shas, len(shas)
            
    else:
        file_dates, commit_sha, swagger_behind = dates, shas, len(shas)
    
    
    
    #create an object to return 
    changes= {}
    
    if file_dates:
        oldest, days_behind = get_oldest_date_v2(file_dates)
        changes['oldest_commit'] = oldest.split('T')[0] + ',' + days_behind +' ago'
        #print file_dates
        #changes['pulls'] = [get_pr_from_commits(c) for c in commit_sha]
        
    changes['file_dates'] = file_dates
    changes['commit_sha'] = commit_sha
    changes['swagger_behind'] = swagger_behind
    
    return changes

def get_new_project_names(map_object, git_url=None, ignore_list=None):
    
    if not ignore_list:
        ignore_list = ['.github', '.gitignore', '.travis.yml', '.vscode', 'LICENSE' , 'README.md' , 'azure-rest-api-specs.sln', 
          'azure-rest-api-specs.njsproj', 'documentation', 'package.json', '.scripts' , 'scripts']
        
    if not git_url:
        git_url = 'https://api.github.com/repos/Azure/azure-rest-api-specs/'
        
        
    api_folders = request_helper(git_url+'contents/')
    
    new_projects = []
    for folder in api_folders:
        f = folder['path'] #

        if f not in ignore_list: 
            test =0 
            for m in map_object:     
                if f in m:
                    test =1
                    break; 

            if test ==0:
                new_projects.append(f)
                #print ('New project added:' + f)
    return new_projects

def get_new_project_details(new_projects_list, git_url=None):
    
    if not git_url:
        git_url = 'https://api.github.com/repos/Azure/azure-rest-api-specs/'
        
    
    new_output ={}
    for p in new_projects_list:
        #print (get_key_folder_params(git_url,p))
        is_composite, folders, swagger = get_key_folder_params_v2(git_url,p)
        if not new_output.get(p):

            new_output[p] ={}
            new_output[p]['is_composite'] = is_composite
            new_output[p]['latest_folder'] = folders[-1]
            new_output[p]['swagger'] = swagger
            new_output[p]['commits'] = []
            new_output[p]['commit_dates'] = []

            #get swagger file history
            r_files = request_helper(git_url+'commits?path=' + swagger)
            for r in r_files:
                commit_sha = r['sha']
                commit_date = r['commit']['committer']['date']
                new_output[p]['commits'].append(commit_sha)
                new_output[p]['commit_dates'].append(commit_date)
                
            #get the oldest commit 
            
            new_output[p]['oldest_commit'] =''
            if new_output[p]['commit_dates']:
                oldest, days_behind = get_oldest_date_v2(new_output[p]['commit_dates'])
                new_output[p]['oldest_commit']= oldest.split('T')[0] + "," + days_behind + " ago "
        
                 

    #print(new_output)
    return(new_output)

#print(get_new_project_details(get_new_project_names()))


def get_nuget_info(nuget_package):
    """
    given a nuget_package pathname, returns the most recent version and release date 
    """
    #nuget_package = sdk_map[azure_folder_name].get('nuget_package')
    nuget_info ={}
    date_format = "%Y-%m-%d"
    #date_now = processed_changes['meta']['most_recent_commit_date'].split('T')[0]
    date_now = datetime.strptime(datetime.now().strftime("%Y-%m-%d"), date_format)
    a = date_now
    
    if nuget_package:
        nuget_date, nuget_version = get_recent_from_nuget(nuget_package)
        nuget_info['nuget_date'] = nuget_date
        if len(nuget_date) > 2:
            a = datetime.strptime(nuget_date.split('T')[0], date_format)
            
        nuget_info['nuget_version'] = nuget_version
        nuget_info['nuget_days_ago'] = str(abs(date_now-a)).split(',')[0] #str(abs(a - b))

    else:
        nuget_info['nuget_version'] = "N.A."
        nuget_info['nuget_days_ago'] = "N.A."

    #print nuget_info
    return nuget_info

def get_existing_changes(sdk_map, current_project_details, git_url=None):
    if not git_url:
        git_url = 'https://api.github.com/repos/Azure/azure-rest-api-specs/'
        
    existing_changes ={}
    
    projects = current_project_details
    #project_list = [p for p in current_project_details][1:15]
    project_list = [p for p in current_project_details]
    
    for t in project_list:
    #get key folder parametr
        existing_changes[t] = {}
        base_data = projects[t]['swagger_meta']
        c_swagger = projects[t]['swagger']
        current_sha = base_data['current_version']
        current_dates = base_data['file_history']['dates']
        
        c_recent, c_days_behind = get_oldest_date_v2(current_dates, recent='Yes')
        
        current_recent = c_recent.split('T')[0] + ',' + c_days_behind 
        
        existing_changes[t]['meta'] = {'current_recent' : current_recent , 'current_sha' : current_sha , 'current_swagger' : c_swagger }
        
        c_composite, c_folder = base_data['is_composite'], base_data['date_folder']
        azure_api_name = projects[t]['swagger_meta']['azure_api_spec_folder']
        

        #get nuget info for each project. 
        nuget_package = sdk_map[azure_api_name].get('nuget_package')
        existing_changes[t]['nuget_info'] = get_nuget_info(nuget_package)
        
        #get the most recent status from the base build for the swagger. easier to summarize later. 
        
        #note this will return the 'to-be' or latest swagger path
        
        is_composite, folders, swagger = get_key_folder_params_v2(git_url,azure_api_name)

        #check if project status are same. 

        if not swagger:
            #something is broken
            print("Swagger not found for azure project :" + azure_api_name)
            break; 

        if is_composite != c_composite:

            changes = get_swagger_updates(swagger, git_url=git_url)
            changes['use_swagger'] = swagger

            if c_composite =="Yes":
                print(azure_api_name + 'has changed to Composite to --> non composite')  

                #get the details for this swagger file and update the details. 

                changes['change_type'] = "CompositeStatus"
                changes['change_status'] = "Moved to a non - composite swagger"
                existing_changes[t]['changes'] = changes

            else:
                
                #moved to a composite swagger. get all lower level swagger details if possible. 
                print(azure_api_name + 'Moved to a composite swagger')
                changes['change_type'] = "CompositeStatus"
                changes['change_status'] = "Moved to a composite swagger"

                existing_changes[t] ['changes']= changes

            break;

        #check if folder is the same 
        else:     
            if is_composite !='Yes': 
                
                if len(folders) > 0: 

                    latest_folder = folders[-1]

                    if c_folder != latest_folder:
                        print(azure_api_name + ' has a new folder : ' + latest_folder)
                        #task -> get the new swagger via a new folder path and update record.
                        changes = get_swagger_updates(swagger, git_url=git_url)
                        changes['use_swagger'] = swagger
                        changes['change_type'] = "Folder"
                        changes['new_folder'] = latest_folder
                        existing_changes[t] ['changes'] =changes

                    else:
                        #most proable scenario : check if the existing swagger that has changed. 
                        
                        if not c_swagger:
                            print (azure_api_name + 'swagger not found')
                        else:
                            changes = get_swagger_updates(c_swagger, git_url=git_url, current_sha=current_sha)
                            if changes['swagger_behind'] >0:
                                changes['change_type'] = "SwaggerUpdate"
                                existing_changes[t]['changes'] = changes
                                           
            
            else:
                #existing composite project that may have been updated. check if swagger has changed. 
                current_sha = base_data['current_version']
                if not c_swagger:
                        print (azure_api_name + 'swagger not found')
                else:
                    changes = get_swagger_updates(c_swagger, git_url=git_url, current_sha=current_sha)
                    if changes['swagger_behind'] >0:
                        changes['change_type'] = "SwaggerUpdate"
                        existing_changes[t]['changes'] = changes
                
                
    #print existing_changes  
    
    #finally get the PRs 

    return existing_changes
