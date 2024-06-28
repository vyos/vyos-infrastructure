'''

implement Tasks checks and workflows on vyos.dev

1. Close a tasks if the Task is in all "Finished" columns


'''

import argparse
import json
from get_task_data import get_task_data, close_task, unassign_task
from datetime import datetime, timedelta

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--token", type=str, help="API token", required=True)
parser.add_argument("-d", "--dry", help="dry run", action="store_true", default=False)
args = parser.parse_args()


TOKEN = args.token
DRYRUN = args.dry
# DRYRUN = True
UNASSIGN_AFTER_DAYS = 90
UNASSIGN_AFTER_DAYS = timedelta(days=UNASSIGN_AFTER_DAYS)
NOW = datetime.now()

if DRYRUN:
    print("This is a dry run")

tasks = get_task_data(TOKEN)

for task in tasks:
    # close tasks it is in any projects "finished" column
    if len(task['projects']) > 0:
        finished = True
        for project in task['projects']:
            if project['column_name'] != 'Finished':
                finished = False
                break
        if finished:
            if DRYRUN:
                print(f'dryrun: T{task["task_id"]} would be closed')
            else:
                close_task(task['task_id'], TOKEN)
            continue
    

    '''
    # unassign tasks with no process after UNASSIGN_AFTER_DAYS
    if task['assigned_user'] and task['assigned_time']:
        delta = NOW - datetime.fromtimestamp(int(task['assigned_time']))
        if delta > UNASSIGN_AFTER_DAYS:
            if task['task_status'] != 'open':
                if DRYRUN:
                    print(f'dryrun: T{task["task_id"]} with status {task['task_status']} would be unassigned after {delta.days} days')
                else:
                    unassign_task(task['task_id'], TOKEN)
                continue
    '''