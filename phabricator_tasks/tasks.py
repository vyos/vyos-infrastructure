from phabricator import Phabricator as PhabricatorOriginal
from phabricator import parse_interfaces
import argparse


'''
get project wide tasks which are not closed but all in the Finished column

1. get all Workboard columns
    - extract workboard phid for the Finished column
    - and the project phid and name

2. get all open taks from projects with Finish column
3. get unique taskslists from previous step to get projekts of a task
4. get all transactions for each task and check if the task is in the Finished column per project
5. autoclose if task is in all Finished column

'''

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
        
''' end of extend the original Phabricator class'''

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


def close_task(task_id, phab):
    try:
        response = phab.maniphest.update(
            id=task_id,
            status='resolved'
        )
        if response.response['isClosed']:
            print(f'T{task_id} closed')
    except Exception as e:
        print(f'T{task_id} Error: {e}')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--token", type=str, help="API token", required=True)
    args = parser.parse_args()

    phab = Phabricator(host='https://vyos.dev/api/', token=args.token)

    workboards = phab_search(phab.project.column.search)
    project_hirarchy = {}

    # get sub-project hirarchy from proxyPHID in workboards
    for workboard in workboards:
        if workboard['fields']['proxyPHID']:
            proxy_phid = workboard['fields']['proxyPHID']
            project_phid = workboard['fields']['project']['phid']

            if project_phid not in project_hirarchy.keys():
                project_hirarchy[project_phid] = []
            project_hirarchy[project_phid].append(proxy_phid)

    finished_boards = []


    for workboard in workboards:
        project_id = workboard['fields']['project']['phid']
        if project_id in project_hirarchy.keys():
            # skip projects with sub-projects
            continue
        if workboard['fields']['name'] == 'Finished':
            project_tasks = phab_search(phab.maniphest.search, constraints={
                        'projects': [project_id],
                        'statuses': ['open'],
            })
            finished_boards.append({
                'project_id': project_id,
                'project_name': workboard['fields']['project']['name'],
                'project_tasks': project_tasks,
                'should_board_id': workboard['phid'],    
            })

    # get unique tasks
    # tasks = {
    #     9999: {
    #         'PHID-PROJ-xxxxx': 'PHID-PCOL-xxxxx',
    #         'PHID-PROJ-yyyyy': 'PHID-PCOL-yyyyy'
    #     }
    # }
    tasks = {}
    for project in finished_boards:
        project_id = project['project_id']
        board_id = project['should_board_id']
        for task in project['project_tasks']:
            task_id = task['id']
            if task_id not in tasks.keys():
                tasks[task_id] = {}
            if project_id not in tasks[task_id].keys():
                tasks[task_id][project_id] = board_id

    tasks = dict(sorted(tasks.items()))

    # get transactions for each task and compare if the task is in the Finished column
    for task_id, projects in tasks.items():
        project_ids = list(projects.keys())
        # don't use own pagination function, because endpoint without pagination
        transactions = phab.maniphest.gettasktransactions(ids=[task_id])
        transactions = transactions.response[str(task_id)]
        
        finished = {}
        for p in project_ids:
            finished[p] = False
        for transaction in transactions:
            if transaction['transactionType'] == 'core:columns':
                # test if projectid is in transaction
                if transaction['newValue'][0]['boardPHID'] in project_ids:
                    # remove project_id from project_ids to use only last transaction from this project
                    project_ids.remove(transaction['newValue'][0]['boardPHID'])
                    # test if boardid is the "Finished" board of project
                    if projects[transaction['newValue'][0]['boardPHID']] == transaction['newValue'][0]['columnPHID']:
                        finished[transaction['newValue'][0]['boardPHID']] = True

            # if all core:columns typy of each project_ids is handled.
            # deside to close task or not
            if len(project_ids) == 0:
                if task_id == 6211:
                    pass
                task_finish = True
                for project_id, is_finished in finished.items():
                    if not is_finished:
                        task_finish = False
                if task_finish:
                    print(f'T{task_id} is Finished in all projects')
                    close_task(task_id, phab)
                break


if __name__ == '__main__':
    main()