# vyos-infrastructure

Various scripts and automations for VyOS infrastructure tasks.

## Automations

### phabricator_tasks

Performs various Phorge/Phabricator chores:

* Marks all tasks resolved if they are in the "Finished" column in all boards where they are present.
* Unassigns tasks that have assigness but no one has done anything in a long time.
