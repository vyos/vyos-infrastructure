'''

Phorge task chores:

1. Close a tasks if it's "Finished" in all boards but not yet resolved
2. Unassign tasks that are nominally assigned to someone but had no activity in a long time
'''

import argparse
import json
from get_task_data import get_task_data, close_task, unassign_task, add_project
from datetime import datetime, timedelta

# Maniphest task editing endpoints that add tags
# require internal PHIDs rather than human-readable named,
# so we need to store those IDs somewhere.
BUGS_PROJECT = 'PHID-PROJ-3fdkfs6vqiynjmthe2ay'
UNCATEGORIZED_TASKS_PROJECT = 'PHID-PROJ-ivh4zv5rmncpcb6flbsb'
BEGINNER_TASKS_RPOJECT = 'PHID-PROJ-ubzhyxbz2q5fprrkys7o'

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--token", type=str, help="API token", required=True)
parser.add_argument("-d", "--dry", help="dry run", action="store_true", default=False)
args = parser.parse_args()


TOKEN = args.token
DRYRUN = args.dry

UNASSIGN_AFTER_DAYS = 90
UNASSIGN_AFTER_DAYS = timedelta(days=UNASSIGN_AFTER_DAYS)
NOW = datetime.now()

if DRYRUN:
    print("This is a dry run")

tasks = get_task_data(TOKEN)

for task in tasks:
    # Close tasks that are in the "Finished" column in all projects
    # but aren't marked resolved yet
    if len(task['projects']) > 0:
        finished = True
        for project in task['projects']:
            if project['column_name'] != 'Finished':
                finished = False
                break
        if finished:
            print(f'Closing task T{task["task_id"]} (finished in all boards)')
            if DRYRUN:
                pass
            else:
                close_task(task['task_phid'], TOKEN)

    # Unassign tasks that supposed assignees aren't actively working on in a long time
    if task['assigned_user']:
        delta = NOW - datetime.fromtimestamp(int(task['last_modified']))
        if delta > UNASSIGN_AFTER_DAYS:
            print(f'Unassigning task T{task["task_id"]} after {delta.days} days of inactivity')
            if DRYRUN:
                pass
            else:
                unassign_task(task['task_id'], TOKEN)

