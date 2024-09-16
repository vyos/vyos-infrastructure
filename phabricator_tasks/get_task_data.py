'''
get all tasks and project information from vyos.dev

Example:

    {
        "task_id": 6473,
        "task_name": "bgp: missing completion helper for peer-groups inside a VRF",
        "task_status": "open",
        "assigned_user": "PHID-USER-xxxxxxxxxx",
        "assigned_time": "1718107618",
        "projects": [
            {
                "column_name": "In Progress",
                "column_id": "PHID-PCOL-y523clr222dw2stokcmm",
                "project_name": "1.4.1",
                "project_id": "PHID-PROJ-qakk4yrxprecshrgbehq"
            }
        ],
        "issue_type": "bug",
        "difficulty_level": "easy",
        "task_open": true
    }

'''

from phabricator import Phabricator as PhabricatorOriginal
from phabricator import parse_interfaces

'''
extend of original Phabricator class to add new interface "project.column.search"
this can be delete if PR https://github.com/disqus/python-phabricator/pull/71 is merged in the pip package
'''

import copy
import json
import pkgutil

INTERFACES = json.loads(
    pkgutil.get_data('phabricator', 'interfaces.json')
    .decode('utf-8'))

INTERFACES['project.column.search'] =  {
        "description": "Search for Workboard columns.",
        "params": {
            "ids": "optional list<int>",
            "phids": "optional list<phid>",
            "projects": "optional list<phid>"
        },
        "return": "list"
    }

class Phabricator(PhabricatorOriginal):
    def __init__(self, **kwargs):
        kwargs['interface'] = copy.deepcopy(parse_interfaces(INTERFACES))
        super(Phabricator, self).__init__(self, **kwargs)


def phab_api(token):
    return Phabricator(host='https://vyos.dev/api/', token=token)

def phab_search(method, constraints=dict(), after=None):
    results = []
    while True:
        response = method(
            constraints=constraints,
            after=after
        )
        results.extend(response.response['data'])
        after = response.response['cursor']['after']
        if after is None:
            break
    return results


def phab_query(method, after=None):
    results = []
    while True:
        response = method(
            offset=after
        )
        results.extend(response.response['data'])
        after = response.response['cursor']['after']
        if after is None:
            break
    return results

def get_column_name(columnPHID, workboards):
    for workboard in workboards:
        if workboard['phid'] == columnPHID:
            return workboard['fields']['name']
    return None

def get_project_default_column(project_id, workboards):
    for workboard in workboards:
        if workboard['fields']['project']['phid'] == project_id and workboard['fields']['isDefaultColumn']:
            return workboard['phid'], workboard['fields']['name']
    return None, None

def close_task(task_id, token):
    phab = phab_api(token)
    try:
        response = phab.maniphest.edit(
            objectIdentifier=task_id,
            transactions=[{'type': 'status', 'value': 'resolved'}]
        )
        if response.response['isClosed']:
            print(f'T{task_id} closed')
    except Exception as e:
        print(f'T{task_id} Error: {e}')

def unassign_task(task_id, token):
    phab = phab_api(token)
    try:
        response = phab.maniphest.edit(
            objectIdentifier=task_id,
            transactions=[{'type': 'owner', 'value': None}]
        )
    except Exception as e:
        print(f'T{task_id} Error: {e}')

def add_project(task_id, project, token):
    phab = phab_api(token)
    try:
        response = phab.maniphest.edit(
            objectIdentifier=task_id,
            transactions=[{'type': 'projects.add', 'value': [project]}]
        )
    except Exception as e:
        print(f'T{task_id} Error: {e}')

def get_task_data(token):
    phab = phab_api(token)
    # get list with all open status namens
    open_status_list = phab.maniphest.querystatuses().response
    open_status_list = open_status_list.get('openStatuses', None)
    if not open_status_list:
        raise Exception('No open status found')

    tasks = phab_search(phab.maniphest.search, constraints={
                        'statuses': open_status_list
                    })

    # get all projects to translate id to name
    projects_raw = phab_search(phab.project.search)
    projects = {}
    for p in projects_raw:
        projects[p['phid']] = p['fields']['name']

    workboards = phab_search(phab.project.column.search)

    # get sub-project hirarchy from proxyPHID in workboards
    project_hirarchy = {}
    for workboard in workboards:
        if workboard['fields']['proxyPHID']:
            proxy_phid = workboard['fields']['proxyPHID']
            project_phid = workboard['fields']['project']['phid']

            if project_phid not in project_hirarchy.keys():
                project_hirarchy[project_phid] = []
            project_hirarchy[project_phid].append(proxy_phid)

    processed_tasks = []
    for task in tasks:
        task_data = {
            'task_id': task['id'],
            'task_phid': task['phid'],
            'task_name': task['fields']['name'],
            'task_status': task['fields']['status']['value'],
            'assigned_user': task['fields']['ownerPHID'],
            'last_modified': task['fields']['dateModified'],
            'issue_type': task["fields"]["custom.issue-type"],
            'difficulty_level': task["fields"]["custom.difficulty-level"],
            'projects': []
        }
        if task['fields']['status']['value'] in open_status_list:
            task_data['task_open'] = True
        else:
            task_data['task_open'] = False
        transactions = phab.maniphest.gettasktransactions(ids=[task['id']])

        # transactionType: core:edge
        # loop reversed from oldest to newest transaction
        # core:edge transactionType is used if the task is moved to another project but stay in default column
        # this uses the default column (mostly "Need Triage")
        task_projects = []
        for transaction in reversed(transactions[str(task['id'])]):
            if transaction['transactionType'] == 'core:edge':
                for oldValue in transaction['oldValue']:
                    if "PHID-PROJ" in oldValue:
                        task_projects.remove(oldValue)

                for newValue in transaction['newValue']:
                    if "PHID-PROJ" in newValue:
                        task_projects.append(newValue)

        # transactionType: core:columns
        # use task_projects items as search indicator 'boardPHID' == project_id
        # remove project from task_projects if the task is moved from the default column to another column
        for transaction in transactions[str(task['id'])]:
            if transaction['transactionType'] == 'core:columns':
                if transaction['newValue'][0]['boardPHID'] in task_projects:
                    task_projects.remove(transaction['newValue'][0]['boardPHID'])
                    task_data['projects'].append({
                        'column_name': get_column_name(transaction['newValue'][0]['columnPHID'], workboards),
                        'column_id': transaction['newValue'][0]['columnPHID'],
                        'project_name': projects[transaction['newValue'][0]['boardPHID']],
                        'project_id': transaction['newValue'][0]['boardPHID'],
                    })


        # handle remaining projects and set the project base default column
        for project in task_projects:
            default_columnid, default_columnname = get_project_default_column(project, workboards)
            # there are some projects without a workboard like project: "14GA"
            if default_columnid and default_columnname:
                task_data['projects'].append({
                    'column_name': default_columnname,
                    'column_id': default_columnid,
                    'project_name': projects[project],
                    'project_id': project,
                })

        processed_tasks.append(task_data)

    return processed_tasks
