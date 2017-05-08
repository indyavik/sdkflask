import os, json,shutil
import requests
import random
from bs4 import BeautifulSoup
from time import gmtime, strftime
from datetime import datetime

#globals (via a config later on)
git_url = 'https://api.github.com/repos/Azure/azure-rest-api-specs/'

def get_pr_from_swagger_path(azure_api_swagger_path):

    swagger_soup_url = 'https://github.com/Azure/azure-rest-api-specs/blob/master/' + azure_api_swagger_path
    page = requests.get(swagger_soup_url)
    if page.status_code == 200:
        pagesoup = BeautifulSoup(page.content)
        
    #get_new_project_details(new_proj[0])
    page_pull = pagesoup.find("div", class_ ="commit-tease")
    if page_pull:
        issue = page_pull.find("a", class_="issue-link")
        if issue:
            return issue['href'].split('/')[-1]
        else:
            return 'not found'
    return 'not found'

#request_helper(raw_url + 'compositeComputeClient_2016_04_30_preview.json')
def update_multiple_projects_4_web(existing_changes):
    for p in existing_changes:
        if existing_changes[p].get('multiple') and existing_changes[p].get('parent_sdk'):
            parent = existing_changes[p]['parent_sdk']
            child = p
            if existing_changes.get(parent) and existing_changes[child].get('changes'):
                
                if not existing_changes[parent]['meta'].get('multiple_changes'):
                    existing_changes[parent]['meta']['multiple_changes'] = 'Yes'
                    
                if not existing_changes[parent].get('changes'):
                    existing_changes[parent]['changes'] = {'multiple_changes' : 'Yes'}
                 
                if not existing_changes[parent].get('multiple_projects'):
                    existing_changes[parent]['multiple_projects'] = {}

                if not existing_changes[parent]['multiple_projects'].get(child):
                    existing_changes[parent]['multiple_projects'][child] = {} 
                    existing_changes[parent]['multiple_projects'][child]['changes'] = existing_changes[child]['changes']
                else:
                     existing_changes[parent]['multiple_projects'][child]['changes'] = existing_changes[child]['changes']
                        
        if existing_changes[p].get('changes'):
            #composite project has ind_project with changes.
            #max swagger-behind to be reported correctly. 
            if existing_changes[p]['changes'].get('ind_changes'):
                max = existing_changes[p]['changes']['swagger_behind']
                for k,v in existing_changes[p]['changes']['ind_changes'].items():
                    if v['swagger_behind'] > max:
                        max = v['swagger_behind']
                existing_changes[p]['changes']['swagger_behind'] = max 

                        
def request_helper(url, access_token=None):
    """
    helper function/method to call API using request and return JSON encoded object. 
    if fails or gets 404, raises error. 
    
    """
    
    if not access_token:
        access_token = '2dd078a2a012e23bed1ff39015ead3675bc9f1d0'
        
    r = requests.get(url, auth=('username', access_token))
    
    if r.status_code != 200:
        return 
    
    else:
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
        if r_file:
            swagger = ''
            for r in r_file:
                if '.json' in r:
                    swagger = r 
                    break;
            
        #swagger = r_file[0]['path']
        
            
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

def get_recent_from_nuget_v2(package, base_url=None):
    """
    given a name of a C# package on Nuget ('Microsoft.Azure.Management.DataLake.Store'), 
    returns the most recent version and published date
    """
    #print package
    if not base_url:
        base_url = "https://www.nuget.org/packages/"
    
    try:
        page_result = requests.get(base_url + package)
    except:
        return None
    
    d = { 'nuget_recent' : {}, 'nuget_stable' : {} }
    
    if page_result.status_code == 200:
        soup = BeautifulSoup(page_result.content)
        stable = soup.find("tr", class_= "versionTableRow recommended")
        recents = soup.findAll("tr", class_= "versionTableRow")
        recent_date, recent_release, stable_date, stable_release = '','', '', ''
        recent_href, stable_href = '',''
        
        if stable:
            stable_date = stable.find("span")['title']
            stable_days_ago = get_oldest_date_v2(stable_date)[1]
            stable_href = stable.find("a", href=True)['href']
            stable_release = stable_href.split('/')[-1]
            
            d['nuget_stable'] = { 'stable_date': stable_date, 'stable_release' : stable_release, 
                           'stable_href': stable_href, 'stable_days_ago' : stable_days_ago } 
            
                    
        if recents:
            recent = recents[0]
            recent_date = recent.find("span")['title']
            recent_days_ago = get_oldest_date_v2(recent_date)[1]
            recent_href = recent.find("a", href=True)['href']
            recent_release = recent_href.split('/')[-1]
            
            d['nuget_recent'] = { 'recent_date': recent_date, 'recent_release' : recent_release, 
               'recent_href': recent_href, 'recent_days_ago' : recent_days_ago }

            
    
    return d

def get_key_folder_params_v3(git_url, azure_folder_path):
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
        swagger =''
        for r in r_file:
            #print r
            if '.json' in r.get('name'):
                swagger = r.get('path')
        #swagger = r_file[0]['path']
        
            
    return(most_recent_composite_status, sorted(folders), swagger)

###GET build.json info from azure sdk page. #########

def get_python_sdk_build_info(sdk_name):
    
    """
    get the latest build.json from azure-sdk-python. 
    returns None if no build.json is found. 
    """
    
    sdk_url = 'https://api.github.com/repos/Azure/azure-sdk-for-python/'
    sdk_raw_url = 'https://raw.githubusercontent.com/Azure/azure-sdk-for-python/master/' 

    
    key_sdk_data = get_key_folder_params_v3(sdk_url,  sdk_name)

    if key_sdk_data and key_sdk_data[2] != None:
        #print key_sdk_data
        if 'build.json' in key_sdk_data[2]:
        #get file info
            build_file = request_helper(sdk_raw_url + key_sdk_data[2])

            if build_file and build_file['date']:
                build_info = { 'autorest' : build_file['autorest'], 'date' : build_file['date'], 
                              'version': build_file['version']}


            #print (build_info)

            return build_info 
    
    else:
        return 
    
def compare_build_date(build_date, dates_list):
        for i,d in enumerate(dates_list):
            if d < build_date:
                print (i, d)
                return (i, d)
                break;

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

    
def get_new_project_names_v2(azure_projects_in_sdk, git_url=None, ignore_list=None):
    """
    given an existing list of project names (azure_projects_in_sdk,) in azure api spec namespaces
    returns a list of projects that are not on azure api spec github but not in the input list. 
    
    """
    if not ignore_list:
        ignore_list = ['.github', '.gitignore', '.travis.yml', '.vscode', 'LICENSE' , 'README.md' , 'azure-rest-api-specs.sln', 
          'azure-rest-api-specs.njsproj', 'documentation', 'package.json', '.scripts' , 'scripts']

    if not git_url:
        git_url = 'https://api.github.com/repos/Azure/azure-rest-api-specs/'


    api_folders = request_helper(git_url+'contents/')
    #print(api_folders)
    new_projects = []
    for folder in api_folders:
        f = folder['path'] #

        if f not in ignore_list: 
            test =0 
            for m in azure_projects_in_sdk:     
                if f in m:
                    test =1
                    break; 

            if test ==0:
                new_projects.append(f)
                #print ('New project added:' + f)

    #print(new_projects)
    return new_projects

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
    #print url
    
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

def parse_swagger_to_sdk_config(project):
#count the #  of slashes 1 ->, composite file. , 3 =>swagger file with datefolder. > 3 staggered/subprojects. 
#Use the fact that folder -=2015, 2016, 2017. ..starts with 20
    
    sdk = project['output_dir'].split('/')[0]

    namespace = project['autorest_options']['Namespace']
    
    if not namespace:
        namespace = ''

    swagger_file_path = project['swagger']

    if not swagger_file_path:
        return None 

    if swagger_file_path:
        #print swagger_file_path

        split_path = swagger_file_path.split('/20')

        if len(split_path) > 1:
            #not composite. 
            azure_api_spec_folder, date_folder, swagger_file  = split_path[0], '20'+ split_path[1].split('/')[0], split_path[1].split('/')[2]

        else:
            azure_api_spec_folder, date_folder, swagger_file = split_path[0].split('/')[0], 'Composite',  split_path[0].split('/')[1]


        

    #print azure_api_spec_folder, date_folder, swagger_file
    return (azure_api_spec_folder, date_folder, swagger_file, sdk, namespace)





#####################################################
##############Main functions #######################

#swagger history 

#swagger history 
def get_swagger_updates_v2(azure_api_swagger_path, git_url=None, current_date=None):
    """
    return the updates to a swagger. 
    if a current_sha of a swagger is known, function returns the updates 'since' this current date
    else, function returns the entire swagger history. 

    #current_sha = base_data['current_version']

    """
    #object to return 
    
    changes= {}
    changes['file_dates'] = []
    changes['commit_sha'] = []
    changes['swagger_behind'] = 0
   
    #azure_api_swagger_path = 'keyvault/2016-10-01/swagger/keyvault.json'

    if not current_date:
        current_date = '2017-04-01'

    swagger_history = request_helper(git_url+'commits?path=' + azure_api_swagger_path + "&since=" + current_date)

    if not swagger_history:
        #print(changes)
        return changes

    #else there are changes. 

    #print(swagger_history)

    shas, dates  = [], [] 
    for s in swagger_history:
        shas.append(s['sha'])
        dates.append(s['commit']['committer']['date'])

    if shas:
        file_dates, commit_sha, swagger_behind = dates, shas, len(shas)

    else:
        #print(swagger_history)
        raise ValueError('Error: get_swagger_updates_v2 : There are updates since ' + current_date + 'but shas were not extracted')

    if file_dates:
        oldest, days_behind = get_oldest_date_v2(file_dates)
        changes['oldest_commit'] = oldest.split('T')[0] + ',' + days_behind +' ago'

    changes['file_dates'] = file_dates
    changes['commit_sha'] = commit_sha
    changes['swagger_behind'] = swagger_behind
    
    #get the pull path. 
    ##get PR from swagger. 
    
    pr_num = get_pr_from_swagger_path(azure_api_swagger_path)
    
    changes['pr_num'] = pr_num

    #print(changes)

    return changes

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
                
        except ValueError, Argument:
            print "sha index not found", Argument
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

            if r_files:
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

#def get_existing_changes(sdk_map, current_project_details, git_url=None):
##EXISTING CHANGES ###

def get_existing_changes_v3(sdk_map, swagger_to_sdk_config_file_name =None, sdk_url=None, git_url=None, sdk_raw_url=None, raw_url=None, assumed_current_date=None):
    
    """
    sdk_url = https://api.github.com/repos/Azure/azure-sdk-for-python/
    
    """
    
    if not raw_url:
        raw_url = 'https://raw.githubusercontent.com/Azure/azure-rest-api-specs/master/' 
    if not sdk_raw_url:
        sdk_raw_url = 'https://raw.githubusercontent.com/Azure/azure-sdk-for-python/master/' 

    
    if not swagger_to_sdk_config_file_name:
        swagger_to_sdk_config_file_name = 'swagger_to_sdk_config.json'

    if not assumed_current_date:
        assumed_current_date = '2017-04-01' #all packages without build.json are assued to be current as of  04-01

    if not git_url:
        git_url = 'https://api.github.com/repos/Azure/azure-rest-api-specs/'


    if not sdk_url:
        sdk_url = 'https://api.github.com/repos/Azure/azure-sdk-for-python/'


    existing_changes ={}
    existing_changes['errors'] = {}
    
    #get main swagger_to_sdk_config file 

    swagger_to_sdk = request_helper(sdk_raw_url + swagger_to_sdk_config_file_name )
    
    
    for proj in swagger_to_sdk['projects']:
        #if proj.startswith('c'):
        
        print ('printing_prject_name :' + proj )

        #(u'arm-commerce', u'2015-06-01-preview', u'commerce.json'), (u'arm-network', 'Composite', u'compositeNetworkClient_2015_06_15.json')

        azure_api_name, c_composite, c_swagger, sdk, namespace = parse_swagger_to_sdk_config(swagger_to_sdk['projects'][proj])

        current_swagger_path = swagger_to_sdk['projects'][proj]['swagger']

        sdk_recent_build = get_python_sdk_build_info(sdk)

        #print(sdk_recent_build)

        if not sdk_recent_build:
            c_recent_date = assumed_current_date #assume it's current as of April 15th. 
            c_version = swagger_to_sdk['projects'][proj]['autorest_options'].get("PackageVersion", "0.00") #assume current version == package version

        else:
            c_recent_date = sdk_recent_build['date']
            c_version = sdk_recent_build['version']

        #print c_recent_date, c_version

        if not existing_changes.get(sdk):
            i = sdk 
            existing_changes[i] ={}
            existing_changes[i]['meta'] = {'azure_api_name' : azure_api_name, 'composite_or_recent_folder' : c_composite, 
                               'current_swagger': current_swagger_path , 'recent_build_date': c_recent_date, 
                               'current_version':c_version}

        else:
            #there is already an object with the same sdk name. ..this is multiple. 
            i= namespace
            existing_changes[i] = {}
            existing_changes[i]['meta'] = {'azure_api_name' : azure_api_name, 'composite_or_recent_folder' : c_composite, 
                   'current_swagger': c_swagger , 'recent_build_date': c_recent_date, 
                   'current_version':c_version}
            existing_changes[i]['multiple'] = 'yes'
            existing_changes[i]['parent_sdk'] = sdk

        #GET THE info from azure api spec for this project. 
        is_composite, folders, swagger = get_key_folder_params_v3(git_url,azure_api_name)

        if c_composite =='Composite':
            current_composite = 'Yes'
            c_recent_folder = 'No'

        else:
            c_recent_folder = c_composite
            current_composite = 'No'

        #print(azure_api_name, c_composite, c_swagger)
        #print(is_composite, folders, swagger )


        #check changes in composite status. 
        if is_composite != current_composite:
            #project composite status has changed. 
            changes = get_swagger_updates(swagger, git_url=git_url) 
            changes['use_swagger'] = swagger

            if current_composite =="Yes":
                #is_composite is NO

                print(azure_api_name + 'has changed to Composite to --> non composite')  

                #get the details for this swagger file and update the details. 

                changes['change_type'] = "CompositeStatus"
                changes['change_status'] = "Moved to a non - composite swagger"
                existing_changes[i]['changes'] = changes


            else:
                #moved to a composite swagger. get all lower level swagger details if possible. 

                print(azure_api_name + 'Moved to a composite swagger')
                changes['change_type'] = "CompositeStatus"
                changes['change_status'] = "Moved to a composite swagger"

                existing_changes[i]['changes']= changes

        #check if folder is the same 
        else:     
            if is_composite =='No': 
                #there must be folders. 
                if len(folders) > 0: 
                    latest_folder = folders[-1]
                    if c_recent_folder != latest_folder:

                        print(azure_api_name + ' has a new folder : ' + latest_folder)

                        changes = get_swagger_updates(swagger, git_url=git_url)
                        changes['use_swagger'] = swagger
                        changes['change_type'] = "Folder"
                        changes['new_folder'] = latest_folder
                        existing_changes[i]['changes'] =changes

                    else:
                        #most proable scenario : check for swagger update. 

                        if current_swagger_path != swagger:
                            print (azure_api_name + '   swagger not found')
                            #print(c_swagger, swagger)

                        else:
                            #get the current sha of from the recent date. 

                            changes = get_swagger_updates_v2(current_swagger_path, git_url=git_url, current_date=c_recent_date)

                            if changes['swagger_behind'] >0:
                                changes['change_type'] = "SwaggerUpdate"
                                existing_changes[i]['changes'] = changes


            else:
                #TO DO TO DO TO DO existing composite project that may have been updated. check if swagger has changed. 
                #i.e, a composite project. 
                #current_sha = base_data['current_version']
                print ('COMPOSITE_SWAGGER' + current_swagger_path)
                if not c_swagger or not current_swagger_path:
                        print (azure_api_name + 'swagger not found')
                else:
                    # check for the update in main composite file first 
                    changes_composite = get_swagger_updates_v2(current_swagger_path, git_url=git_url, current_date=c_recent_date)

                    if changes_composite['swagger_behind'] >0:
                        changes['change_type'] = "SwaggerUpdate"
                        existing_changes[i]['changes'] = changes

                    # check for the update in main composite file first                 
                    #get the full file and individual paths from the composite file. 
                    #raw_url = 'https://raw.githubusercontent.com/Azure/azure-rest-api-specs/master/' 

                    cfile= request_helper(raw_url + current_swagger_path)

                    if not cfile:
                        #current swagger file not found. 
                        
                        existing_changes['errors'][i] = 'swagger_file : ' + current_swagger_path +' not found'
                        
                        if not existing_changes[i].get('errors'): 
                            existing_changes[i]['errors'] = {}
                            existing_changes[i]['errors']['swagger_file'] = 'swagger_file : ' + current_swagger_path +' not found'

                        else:
                            existing_changes[i]['errors']['swagger_file'] = 'swagger_file : ' + current_swagger_path +' not found'


                    if cfile and cfile.get('documents'):
                        for f in cfile.get('documents'):
                            #get file history 
                            ind_swagger = azure_api_name + f[1:]
                            print ('IND_SWAGGER' + ind_swagger)
                            #file_data = get_swagger_updates(ind_swagger, git_url, current_sha=None)
                            changes_ind_file = get_swagger_updates_v2(ind_swagger, git_url=git_url, current_date=c_recent_date)

                            #catch any errors. 

                            if not changes_ind_file:
                                existing_changes['errors'][i] = 'swagger_file : ' + ind_swagger +' not found'

                            if changes_ind_file and changes_ind_file['swagger_behind'] >0:

                                if existing_changes[i].get('changes'):

                                    if not existing_changes[i]['changes'].get('ind_changes'):
                                        existing_changes[i]['changes']['ind_changes'] = {}
                                        existing_changes[i]['changes']['ind_changes'][ind_swagger] = changes_ind_file
                                    else:
                                         existing_changes[i]['changes']['ind_changes'][ind_swagger] = changes_ind_file


                            #d[ind_swagger] = {'sha' : file_data['commit_sha'], 'dates': file_data['file_dates']}


        #print('CHANGES')

        if not sdk_map.get(azure_api_name):
            existing_changes[i]['nuget_info'] = {}
            print('No Nuget URL Map for azure api: ' + azure_api_name)

        else:
            nuget_package = sdk_map[azure_api_name].get('nuget_package')
            if nuget_package:
                existing_changes[i]['nuget_info'] = get_recent_from_nuget_v2(nuget_package) or 'Nuget info not found.'
            else:
                existing_changes[i]['nuget_info'] = {}
                print('No Nuget URL Map for azure api: ' + azure_api_name)

    #update multiple projects for easy rendering later on. 
    update_multiple_projects_4_web(existing_changes)

    return existing_changes

