from flask import Flask, jsonify , request, Response, render_template , session, abort, flash , url_for, redirect
from functools import wraps
from flask_cors import CORS, cross_origin

import os, json,shutil
import requests, jinja2
from bs4 import BeautifulSoup
from time import strftime
from datetime import datetime

app = Flask(__name__)
CORS(app)

def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == 'azureuser' and password == 'secretsdk123'

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


@app.route('/')
@requires_auth
def index():
    return redirect(url_for('report'))
    #return 'Flask is running!'


@app.route('/data')
def names():
    data = {"names": ["John", "Jacob", "Julie", "Jennifer"]}
    return jsonify(data)

@app.route('/ignore', methods=['POST'])
def ignore():
    print(json.loads(request.data))
    request_data= json.loads(request.data)
    ignore_project = request_data.get('ignore_project')

    print(ignore_project)

    with open('config/ignore.json', 'r') as f:
        ignore_data = json.load(f)

    ignore_list = ignore_data['ignore']

    if ignore_project not in ignore_list:
        ignore_list.append(ignore_project)

        with open('config/ignore.json', 'w') as f:
            json.dump(ignore_data, f)
            return "success"

    else:
        return "project already in ignore list"




@app.route('/report')
@requires_auth
def report():
    with open('config/api2sdk2nuget.json', 'r') as f:
        map_object = json.load(f)

    with open('changes/latest.json', 'r') as f:
        changes = json.load(f)

    with open('config/ignore.json', 'r') as f:
        ignore = json.load(f).get('ignore')

    new_projects = changes['new_projects']

    existing_projects = changes['existing_projects']

    report_time = changes['report_time']
    
    seq = [k for k in sorted(existing_projects.iterkeys())]

    number_changes = sum([1 if existing_projects[c].get('changes') and not existing_projects[c].get('multiple')  else 0 for c in existing_projects ])
    errors=0
    if existing_projects.get('errors'):
        errors = len( [e for e in existing_projects['errors'] ])

    """

    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('jinja-template_v4.html')

    output = template.render(new_projects=new_projects, existing_projects=existing_projects,
                            recent_sha = '123',recent_date='abc', base=build_file,
                            sdk_map= map_object, seq = sorted(map_object))
    #print output
    #write to file.
    with open('html/report_april_test.html', 'w') as f:
        f.write(output)
    """

    return render_template('jinja-template_v7f.html', new_projects=new_projects, existing_projects=existing_projects, 
                         recent_sha = '123',recent_date='abc', 
                         sdk_map= map_object, seq = seq, number_changes=number_changes, 
                         report_time=report_time, errors=errors, ignore=ignore)


if __name__ == '__main__':
    app.run()


