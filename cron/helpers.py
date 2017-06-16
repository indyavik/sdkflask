import os, json,shutil
import requests
import random
from bs4 import BeautifulSoup
from time import gmtime, strftime
from datetime import datetime
import yaml
import mistune
from mistune import Renderer, Markdown
from io import StringIO

#globals (via a config later on)
git_url = 'https://api.github.com/repos/Azure/azure-rest-api-specs/'
raw_url = 'https://raw.githubusercontent.com/Azure/azure-rest-api-specs/master/' 
sdk_raw_url = 'https://raw.githubusercontent.com/Azure/azure-sdk-for-python/master/'
swagger_to_sdk_config_file_name = 'swagger_to_sdk_config.json'
assumed_current_date = '2017-04-01' #all packages without build.json are assued to be current as of  04-01
sdk_url = 'https://api.github.com/repos/Azure/azure-sdk-for-python/'

with open('config/api2sdk2nuget.json', 'r') as f:
    map_object = json.load(f)

    sdk_map = map_object

def get_project_list_from_config(swagger_to_sdk):
    """
    input : swagger_to_sdk_config as dictionary 
    output : list of project names in azure api spec (ie. arm-cdn)
    vikas: also returns a dict {sdk_project : [swagger_name, api_name]}
    """
    azure_projects = []
    composite_projects =[]
    md_projects = []
    normal_projects = [] 

    d={}

    for p in swagger_to_sdk['projects']:
        
        project = swagger_to_sdk['projects'][p]
        markdown = project.get('markdown')
        autorest_options = project.get('autorest_options')
        
        if markdown:
            azure_project = get_azure_name_space_data(markdown)[0]
            azure_projects.append(azure_project)
            md_projects.append(p)
            d[p] = [markdown, azure_project]
            print 'md project : ' + azure_project
        
        else:
            
            if autorest_options:
                swagger = autorest_options.get('input-file')
                
                if swagger:
                    azure_project = get_azure_name_space_data(swagger)[0]
                    azure_projects.append(azure_project)
                    normal_projects.append(p)
                    d[p] = [swagger, azure_project]

                else:
                    #is a composite 
                    composite = project.get("composite")
                    if composite:
                        azure_project = get_azure_name_space_data(composite)[0]
                        azure_projects.append(azure_project)
                        composite_projects.append(p)
                        d[p] = [composite, azure_project]
                    
            else:
                print(" Error: no link to a file: sdk_config seems to have changed for project =" + p)    
 
    return (azure_projects, d, md_projects)

def get_prs_in_range(shas, projects):

    """
    Small helper function to return PR numbers given a 1) list of shas, and 2) corresponding project names. 
    returns a tuple of project, sha, and pr_number -->(u'azure-mgmt-servicebus', u'ab6034c2ed4ae7347a5817242487706e5a49b73c', u'1138')
    """

    return_list =[]    
    
    for i in range(len(projects)):
        r_com = shas[i]
        proj = projects[i]
        pr_num = get_pr_from_commits(r_com)
        
        
        if pr_num:
            if '#' in pr_num:
                pr_num = pr_num[1:]

            return_list.append((proj, r_com, pr_num))

        else:
            return_list.append((proj, r_com, 'No PR num found'))

    return return_list

def update_remaining_PR_v2(existing_projects, max_lookup =50, sha2pr=None):
    """
    given a max number of PR nums to find (usually 9, as github limits 10 per min.) updates the missing PR #
    saves the commit_sha --> PR num relations in a json file (sha2pr_history.json) in order to minimize look up. 
    waits for 90 seconds for every 9 look up. 
    max_lookup value is safeguard to stop after 50 look ups (about 600 seconds)
    sha2pr is a dict of {'sha' : 'pr_num' } that can be updated and kept to minimize future look ups. 
    
    """

    if not sha2pr:
        sha2pr = {}
    
    for p in existing_projects:
        if existing_projects[p].get('changes'):
            if not existing_projects[p]['changes'].get('pr_num'):
                existing_projects[p]['changes']['pr_num'] = 'n.a'
            else:
                pr = existing_projects[p]['changes']['pr_num']
                if '#' in pr:
                    #remove the '#' from PR num. 
                    pr = pr[1:]
                
    
    missing_pr_shas =[]
    missing_pr_projects =[]
    

    for p in existing_projects:
       
        if existing_projects[p].get('changes'):
            if existing_projects[p]['changes'].get('commit_sha'):   
                if not existing_projects[p]['changes'].get('pr_num') or existing_projects[p]['changes']['pr_num'] == 'not found':
                    r_commit = existing_projects[p]['changes']['commit_sha'][0]
                    
                    #check if r_commit is already is in the file.        
                    if sha2pr.get(r_commit):
                        existing_projects[p]['changes']['pr_num'] = sha2pr[r_commit]
                        
                    else:
                        missing_pr_shas.append(r_commit)
                        missing_pr_projects.append(p)
                        
    print "Number of missing PRS -->" + str(len(missing_pr_shas))
    
    print (missing_pr_shas)
    print (missing_pr_projects)
    
    prs =[]
    remaining =0
    max_time = 0
    userange = len(missing_pr_projects)
    
    if len(missing_pr_projects) > 9:
        userange =9
        remaining = len(missing_pr_projects) - 9
        max_time +=9
        
        
    #update the first 9 projects. 
    start = 0
    end = userange


    prs.append(get_prs_in_range(missing_pr_shas[start:end], missing_pr_projects[start:end]))
    

    if not remaining ==0:
        time.sleep(90) 

        while remaining > 0 and max_time < max_lookup:

            if remaining > 9:
                start = start + 9 
                end = end + 9 
                remaining = remaining - 9 
                max_time +=0
            else:
                start = start +9
                end = start + remaining 
                remaining = 0  

            prs.append(get_prs_in_range(missing_pr_shas[start:end], missing_pr_projects[start:end]))

            time.sleep(90) 

    return prs
    

def parse_swagger_to_sdk_config(project):
    """
    for each project from swagger_to_sdk_config, returns the corresponding Azure Api name, swagger file being used, 
    folder, and less importantly namespace. 

    """


    sdk = project['output_dir'].split('/')[0]
    namespace = "no-name-space"

    if project.get('markdown'):
        swagger_file_path = project.get('markdown')


    if project.get('autorest_options'):
        autorest_options = project.get('autorest_options')
        namespace = project['autorest_options']['namespace']
        swaggerfile = autorest_options.get('input-file')
        if swaggerfile:
            swagger_file_path = swaggerfile
        else:
            compositefile = project.get("composite")
            if compositefile:
                swagger_file_path = compositefile


    if not swagger_file_path:
        
        return None 

    if 'swagger' in swagger_file_path:
        #not a composite
        split_path = swagger_file_path.split('/swagger/')   
        azure_api = '/'.join(split_path[0].split('/')[0:-1])
        folder, swagger_name = split_path[0].split('/')[-1], split_path[-1]

    else:
        #is a composite file. 
        folder = 'Composite'
        split_path = swagger_file_path.split('/')
        azure_api, swagger_name = split_path[0], split_path[-1]

    #print azure_api, folder, swagger_name

    #print azure_api_spec_folder, date_folder, swagger_file
    return (azure_api, folder, swagger_name, sdk, namespace)

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
                 
def request_helper(url, access_token=None):
    """
    helper function/method to call API using request and return JSON encoded object. 
    if fails or gets 404, raises error. 

    """
    
    
    if not access_token:
        access_token = os.environ.get('token')

    r = requests.get(url, auth=('username', access_token))
    
    if r.status_code != 200:
        return 
    
    else:
        return r.json()
    

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
    returns a dictionary 
    output: recent version, published date for recent version , stable version, published date for stable
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
    2) list of folder list (sorted)
    3) swagger file that "should be used" (i.e, one for the most recent folder. )

    output: tuple
    output example : ('No', [u'2015-06-01', u'2016-04-02', u'2016-10-02'],u'arm-cdn/2016-10-02/swagger/cdn.json')

    """   
    rcomposite = request_helper(git_url + 'contents/' + azure_folder_path )
    
    if not rcomposite:
        return None
    
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

        if '.md' in path:
            most_recent_composite_status = 'Yes'
            swagger=path


    #print (folders)
  
    if not swagger and folders:
        surl = git_url + 'contents/' + azure_folder_path + '/' + folders[-1] + '/swagger/'
        r_file = request_helper(surl)
        if not r_file: # try 'Swagger with caps '
            surl = git_url + 'contents/' + azure_folder_path + '/' + folders[-1] + '/Swagger/'
            r_file = request_helper(surl)
            if not r_file:
                return (most_recent_composite_status, sorted(folders), surl + "swagger_not_found.json")

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
    output: dictionary. 
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
    

def get_azure_name_space_data(swagger_file_path):
    """
    Parses a full swagger path (xyz/2016_v1/swagger/xyz.json) and returns the corresponding api name, folder and actual swagger file name
    input: swagger path 
    output: tuple containing azure_api_spec_name, folder_name, swagger_file
    note: for "composite" projects, folder_name == 'Composite' 

    """
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
    returns a list of projects that are on azure api spec github but are Not in the input list. 
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

    base_url = github.com search query 
    """
    #print package
    #https://github.com/search?q=8461020530ea97978+repo%3AAzure%2Fazure-rest-api-specs&type=issues
    
    if not base_url:
        base_url = "https://github.com/search?q="
        url_en = "+repo%3AAzure%2Fazure-rest-api-specs&type=issues"
    
    url = base_url+commit_sha+url_en
    #print url
    
    if not access_token:
        access_token = os.environ.get('token')
        
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

class YamlExtractor(Renderer):
    def __init__(self, *args, **kwargs):
        self.yaml_content = StringIO()
        Renderer.__init__(self, *args, **kwargs)

    def block_code(self, code, lang=None):
        if lang == "yaml":
            self.yaml_content.write(code+"\n")
        return Renderer.block_code(self, code, lang)

def extract_yaml(markdown_content):
    # Get the YAML code inside the Markdown
    try:
        extractor = YamlExtractor()
        markdown_processor = Markdown(extractor)
        markdown_processor(markdown_content)
        raw_yaml = extractor.yaml_content.getvalue()
    except Exception:
        raise ValueError("The Markdown content is not valid")

    # Get the yaml as a dict
    try:
        return yaml.load(raw_yaml)
    except Exception:
        raise ValueError("Unable to build a valid YAML from this Markdown")

def parse_markdown_from_spec(markdown_path):
        mf = requests.get(raw_url + markdown_path)
        if mf.status_code == 200:
            markdown_file = mf.text
            data = extract_yaml(markdown_file) 

            folders, swaggers = [], []
            for d in data['input-file']:
                updated_path = d.split('/')[1:] #removes . -> /2016-12-01/swagger/backupManagement.json
               
                folder, swagger_path = updated_path[0], '/'.join(updated_path)
                folders.append(folder)
                swaggers.append(swagger_path)
                
        
        print (folders, swaggers)
        return  (folders, swaggers)


def get_changes_for_project(azure_api_name, c_composite, current_swagger_path , c_recent_date):
    
    """
    retruns the changes (if any there would be a key == 'changes' in the returned dictionary object) for a given project. Use this function when
    there is 1-1 mapping between the SDK project and the azure API spec folder. (only 1 sdk project for a given AZURE API spec folder)
    """
    

    return_dict = {}
    
    return_dict['errors'] = {}

    params = get_key_folder_params_v3(git_url,azure_api_name)

    if not params:
        return_dict['errors'] = 'Project ' + azure_api_name +' not found. Probably private' 
        #existing_changes['errors'][i] = 'Project ' + azure_api_name +' not found. Probably private'

        return return_dict

    else:
        is_composite, folders, swagger = get_key_folder_params_v3(git_url,azure_api_name)

        if c_composite =='Composite':
            current_composite = 'Yes'
            c_recent_folder = 'No'

        else:
            c_recent_folder = c_composite
            current_composite = 'No'


        #check changes in composite status. 
        if is_composite != current_composite:
            #project composite status has changed. 

            changes = get_swagger_updates_v2(swagger, git_url=git_url) 
            changes['use_swagger'] = swagger

            if current_composite =="Yes":
                #is_composite is NO

                print(azure_api_name + 'has changed to Composite to --> non composite')  

                #get the details for this swagger file and update the details. 

                changes['change_type'] = "CompositeStatus"
                changes['change_status'] = "Moved to a non - composite swagger"
                return_dict['changes'] = changes


            else:
                #moved to a composite swagger. get all lower level swagger details if possible. 

                print('    ' + azure_api_name + ' :Moved to a composite swagger')
                changes['change_type'] = "CompositeStatus"
                changes['change_status'] = "Moved to a composite swagger"

                return_dict['changes']= changes

        #check if folder is the same 
        else:     
            if is_composite =='No': 
                #there must be folders. 
                if len(folders) > 0: 
                    latest_folder = folders[-1]
                    if c_recent_folder != latest_folder:

                        print('    ' + azure_api_name + ' :has a new folder : ' + latest_folder)

                        changes = get_swagger_updates_v2(swagger, git_url=git_url)
                        changes['use_swagger'] = swagger
                        changes['change_type'] = "Folder"
                        changes['new_folder'] = latest_folder
                        return_dict['changes'] =changes

                    else:
                        #most proable scenario : check for swagger update. 

                        if current_swagger_path != swagger:
                            print ('    ' + azure_api_name + ':swagger not found')
                            #print(current_swagger_path, swagger)

                        else:
                            #get the current sha of from the recent date. 

                            changes = get_swagger_updates_v2(current_swagger_path, git_url=git_url, current_date=c_recent_date)

                            if changes['swagger_behind'] >0:
                                changes['change_type'] = "SwaggerUpdate"
                                return_dict['changes'] = changes


            else:

                print ('   COMPOSITE_SWAGGER ' + current_swagger_path)

                if not current_swagger_path:
                        print (azure_api_name + '..swagger not found')
                else:
                    # check for the update in main composite file first 
                    changes_composite = get_swagger_updates_v2(current_swagger_path, git_url=git_url, current_date=c_recent_date)

                    if changes_composite['swagger_behind'] >0:
                        changes ={}
                        changes['change_type'] = "SwaggerUpdate"
                        return_dict['changes'] = changes

                    # check for the update in main composite file first                 
                    #get the full file and individual paths from the composite file. 
                    #raw_url = 'https://raw.githubusercontent.com/Azure/azure-rest-api-specs/master/' 

                    cfile = None 

                    if current_swagger_path.endswith('.md'):
                        cfile=[]
                        cfiles = parse_markdown_from_spec('arm-recoveryservicesbackup/readme.md')[1]
                        cfile = [ './' + c  for c in cfiles ]
                    
                    else:
                        cfile_document= request_helper(raw_url + current_swagger_path)

                        if cfile_document.get('documents'):
                            cfile = cfile_document.get('documents')

                    if not cfile:
                        #current swagger file not found. 
                        return_dict['errors'][cfile] =  'swagger_file: ' + current_swagger_path +' not found' 


                    #if cfile and cfile.get('documents'):
                        #for f in cfile.get('documents'):

                    for f in cfile:
                        #get file history 
                        ind_swagger = azure_api_name + f[1:]
                        print ('IND_SWAGGER ' + ind_swagger)

                        changes_ind_file = get_swagger_updates_v2(ind_swagger, git_url=git_url, current_date=c_recent_date)

                        #catch any errors. 

                        if not changes_ind_file:
                            return_dict['errors'] = ind_swagger + ' swagger_file : ' + ind_swagger +' not found'

                        if changes_ind_file and changes_ind_file['swagger_behind'] >0:

                            if return_dict.get('changes'):
                                if not return_dict['changes'].get('ind_changes'):
                                    return_dict['changes']['ind_changes'] = {}
                                    return_dict['changes']['ind_changes'][ind_swagger] = changes_ind_file
                                else:
                                    return_dict['changes']['ind_changes'][ind_swagger] = changes_ind_file

        #print('CHANGES')

        if not sdk_map.get(azure_api_name):
            return_dict['nuget_info'] = {}
            print('    No Nuget URL Map for azure api: ' + azure_api_name)

        else:
            nuget_package = sdk_map[azure_api_name].get('nuget_package')
            if nuget_package:
                return_dict['nuget_info'] = get_recent_from_nuget_v2(nuget_package) or 'Nuget info not found.'
            else:
                return_dict['nuget_info'] = {}
                print('   No Nuget URL Map for azure api: ' + azure_api_name)
                
    return return_dict

def get_changes_for_projects_multi(azure_api_name, sdk_project_list, swagger_to_sdk, lookup_map, assumed_current_date=None):
    
    """
    returns changes for python sdk projects where each project points to the same SDK but different apis. 
    ex: datalake analytics 
    """
    
    if not assumed_current_date:
        assumed_current_date = '2017-04-01'
    
    changes_m ={} #individual project changes with meta 
    changes_top = {} # top level changes, either composite status or folder. 
    
    #azure_api_m = 'arm-resources/resources'
    #mproj = d[azure_api_m] #[u'resources.resources.2016-02-01', u'resources.resources.2016-09-01', u'resources.resources.2017-05-10']
    
    azure_api_m = azure_api_name
    mproj = sdk_project_list 

    folders = sorted([ f.split('.')[-1] for f in mproj ]) #[u'2016-02-01', u'2016-09-01', u'2017-05-10']

    #get sdk to summarize under one sdk . 
    random_proj = mproj[0]
    azure_api_name, c_composite, c_swagger, sdk, namespace = parse_swagger_to_sdk_config(swagger_to_sdk['projects'][random_proj])

    #most recent folder 
    c_folder = folders[-1] 
    c_comp = 'No' #***VALDIATE: assumed there aren't any composite project in this type of case ****

    is_composite, folders, swagger = get_key_folder_params_v3(git_url,azure_api_name)
    latest_folder = folders[-1]

    #check 1: if this azure api spec is now using composite 
    if is_composite != c_comp:
        changes_top['changes'] = {}
        changes_top['changes']['change_type'] = "CompositeStatus"
        changes_top['changes']['change_status'] = "Moved to a non - composite swagger"
        changes_top['changes']['use_swagger'] = swagger

    #check 2: is there a folder more recent than this 
    if c_folder != latest_folder:
        changes_top['changes'] = {}
        changes_top['changes']['change_type'] = "Folder"
        changes_top['changes']['new_folder']= latest_folder
        changes_top['changes']['use_swagger'] = swagger

    #check 3: for each proj in mproj a) if the json file and path is still valid? , b) is current ?
    for proj in mproj:

        #current_swagger_m = swagger_to_sdk['projects'][proj]['swagger']
        current_swagger_m = lookup_map[proj][0] 
        
        sdk_recent_build = get_python_sdk_build_info(sdk)

        if not sdk_recent_build:
            c_recent_date = assumed_current_date #assume it's current as of April 15th. 
            if swagger_to_sdk['projects'][proj].get('autorest_options'):
                c_version = swagger_to_sdk['projects'][proj]['autorest_options'].get("PackageVersion", "0.00") #assume current version == package version
            else:
                c_version = "0.00"
        else:
            c_recent_date = sdk_recent_build['date']
            c_version = sdk_recent_build['version']

        meta = {'azure_api_name' : azure_api_name, 'composite_or_recent_folder' : c_composite, 
                           'current_swagger': current_swagger_m , 'recent_build_date': c_recent_date, 
                           'current_version':c_version, 'sdk_proj_name' : proj }

        changes_m[proj] ={}
        changes_m[proj]['meta'] = meta

        if len(request_helper(git_url+'commits?path=' + current_swagger_m )) > 0:
            swagger_changes = get_swagger_updates_v2(current_swagger_m, git_url=git_url, current_date= c_recent_date) 
   
            if swagger_changes['swagger_behind'] > 0:

                changes_m[proj]['changes'] = swagger_changes

        else:

            changes_m[proj]['errors'] = 'Swagger: ' + current_swagger_m + ' Not found'
            
            
    return {'changes' : changes_top , 'multiple_projects': changes_m, 'sdk' : sdk }


#swagger history 
def get_swagger_updates_v2(azure_api_swagger_path, git_url=None, current_date=None):
    """
    return the updates to a swagger. 
    if a current_sha of a swagger is known, function returns the updates 'since' this current date
    else, function returns the entire swagger history. 

    #updated function also returns the PR (if any)

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

def get_new_project_details(new_projects_list, git_url=None):
    
    if not git_url:
        git_url = 'https://api.github.com/repos/Azure/azure-rest-api-specs/'
        
    
    new_output ={}
    for p in new_projects_list:
        print("   Gathering details for New Project: " + p)
        #print (get_key_folder_params(git_url,p))
        is_composite, folders, swagger = get_key_folder_params_v3(git_url,p)

        if not new_output.get(p):

            new_output[p] ={}
            new_output[p]['is_composite'] = is_composite
            if folders :
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

def get_changes_in_existing_projects(swagger_to_sdk, sdk_raw_url, assumed_current_date, lookup_map): 
    
    existing_changes ={}
    existing_changes['errors'] = {}

    #get main swagger_to_sdk_config file 

    #get normal sdks (points to SINGLE API SPEC on AZURE-API-SPEC), and multiple sdks (POINTS to SAME AZURE-API-SPEC on github)
    s_to_sdk_projects = sorted([s for s in swagger_to_sdk['projects'] ])

    multi_sdk = {} 

    normal_sdk = []

    d ={}

    for i in range(len(s_to_sdk_projects)):

        azure_api_a = parse_swagger_to_sdk_config(swagger_to_sdk['projects'][s_to_sdk_projects[i]])
      
        azure_api_x = azure_api_a[0]
        
        if not d.get(azure_api_x):
            d[azure_api_x] = []
            d[azure_api_x].append(s_to_sdk_projects[i])
        else:
             d[azure_api_x].append(s_to_sdk_projects[i])

    for a in d:
        if len(d.get(a)) >1 and 'rdbms' not in a:
            multi_sdk[a] = d[a]     
        else:
            for sdk in d.get(a):
                normal_sdk.append(sdk)

    #process normal sdk projects first (i.e, one that points to SINGLE API SPEC on AZURE-API-SPECs)

    for proj in normal_sdk:

        #if 'devtestlabs' in proj:

        print ('  Finding Changes for Project :' + proj )

        #(u'arm-commerce', u'2015-06-01-preview', u'commerce.json'), (u'arm-network', 'Composite', u'compositeNetworkClient_2015_06_15.json')

        azure_api_name, c_composite, c_swagger, sdk, namespace = parse_swagger_to_sdk_config(swagger_to_sdk['projects'][proj])

        current_swagger_path = lookup_map[proj][0] 
        
        #right now there is no build.json info included in swagger_to_sdk_config.json, so try to find build.json for each 'sdk'
        #note c_swagger is "short form -> i.e xyz.json" , swagger_path is full path including the folder. 

        sdk_recent_build = get_python_sdk_build_info(sdk)

        if not sdk_recent_build:
            c_recent_date = assumed_current_date #assume it's current as of April 15th. 

            if swagger_to_sdk['projects'][proj].get('autorest_options'):
                c_version = swagger_to_sdk['projects'][proj]['autorest_options'].get("PackageVersion", "0.00") #assume current version == package version
            else:
                c_version = "0.00"
        else:
            c_recent_date = sdk_recent_build['date']
            c_version = sdk_recent_build['version']

        meta = {'azure_api_name' : azure_api_name, 'composite_or_recent_folder' : c_composite, 
                               'current_swagger': current_swagger_path , 'recent_build_date': c_recent_date, 
                               'current_version':c_version, 'sdk_proj_name' : proj}

        #print azure_api_name, c_composite, c_swagger, c_recent_date

        get_changes = get_changes_for_project(azure_api_name, c_composite, current_swagger_path , c_recent_date)
        
        #print get_changes

        project_changes = {}

        project_changes['meta'] = meta

        if get_changes.get('changes'):
            project_changes['changes'] = get_changes.get('changes')

        if get_changes.get('errors'):
            print ('    errors in project -->') + proj 
            print get_changes.get('errors')
            if any(get_changes.get('errors')):
                project_changes['errors'] =  get_changes.get('errors')
                existing_changes['errors'][proj] = project_changes['errors']


        if get_changes.get('nuget_info'):
            project_changes['nuget_info'] = get_changes.get('nuget_info')

        if not existing_changes.get(sdk):
            existing_changes[sdk] = project_changes

        else: 
            if existing_changes[sdk].get('same_sdk'):
                existing_changes[sdk]['same_sdk'][proj] = project_changes
            else:
                #get the very first one. 
                clip = existing_changes.pop(sdk, None)
                existing_changes[sdk] ={}
                existing_changes[sdk]['same_sdk'] = {}
                #clip = existing_changes.get(sdk)
                proj_name = clip['meta']['sdk_proj_name']
                existing_changes[sdk]['same_sdk'][proj_name] = clip 
                existing_changes[sdk]['same_sdk'][proj] = project_changes


    #process multi sdks

    for m in multi_sdk:
        multi_changes = get_changes_for_projects_multi(m, multi_sdk[m], swagger_to_sdk, lookup_map, assumed_current_date='2017-04-01')
        sdk= multi_changes['sdk']
        top_changes = multi_changes['changes']
        multiple_projects = multi_changes['multiple_projects']

        if not existing_changes.get(sdk):
            existing_changes[sdk] = {'changes': top_changes, 'multiple_projects' : multiple_projects}

    #consolidate errors for multi projects, find out max swagger behind when therea re multiple swagger updates

    for e in existing_changes:
        if existing_changes[e].get('multiple_projects'):
            proj = existing_changes[e].get('multiple_projects')
            for p in proj:
                if proj[p].get('errors'):
                    print proj[p].get('errors')
                    existing_changes['errors'][p] = proj[p].get('errors')

        if existing_changes[e].get('changes'):
            if existing_changes[e]['changes'].get('ind_changes'):
                ind_change = existing_changes[e]['changes'].get('ind_changes')
                max_behind = 1
                for k,v in ind_change.items():
                    #print v['swagger_behind']
                    if v['swagger_behind'] > max_behind:
                        max_behind = v['swagger_behind'] 

                existing_changes[e]['changes']['max_behind'] = max_behind


    print("Done finding existing changes")
    
    return existing_changes