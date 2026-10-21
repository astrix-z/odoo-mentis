==================
Mentis Task Access
==================

Task visibility for the networks ``bufet``, ``goodtime``, ``trattoria``, their outlets and
the IT, Service and Accounting departments, auto-assignment of service requests and
per-outlet sub-tasks for network-wide work.

Setup
=====

1. *Project → Configuration → Networks / Outlets*: create networks with their managers,
   then outlets with their outlet managers, responsible service staff and accountants.
2. Create one project per department and set *Department Queue* (IT, Service, Accounting).
   Queue projects must stay "Invited internal users"; new projects default to it.
   Enable *Sub-tasks* in the IT project for outlet sub-tasks.
3. Give each user one or more groups under *Mentis Tasks* in their user form.
   Do not give network or outlet managers *Project: Administrator*: it shows every task.
4. *Project → Service Duty*: plan duty shifts.

Who sees which task
===================

=================  ==========================================================================
Group              Tasks
=================  ==========================================================================
Executive          all
Network Manager    tasks of outlets in networks they manage, and tasks scoped to those networks
Outlet Manager     tasks of outlets they manage, in any queue
IT                 all tasks of IT queue projects
Service            Service queue tasks of outlets they are responsible for
Accounting         Accounting queue tasks of outlets they are accountants for
=================  ==========================================================================

Odoo's own rules still apply for everyone: assignees and followers see the task, and
followers of a project see all of its tasks. Mentioning an employee in a task's chatter
subscribes them, so the mention opens the task for them.

Service auto-assignment
=======================

A new Service queue task with an outlet and no explicit assignee goes to the user on duty
at that moment, or, outside duty shifts, to the outlet's responsible service staff.
The "My Tasks" pre-fill of the creator does not count as an explicit choice unless the
creator is service staff.

Network-wide work
=================

Leave *Outlet* empty and fill *Scope Networks* and/or *Scope Outlets* instead, then press
*Create Outlet Sub-tasks*. Every active outlet in the scope that has no sub-task yet gets an
unassigned one; pressing it again only adds missing outlets. Outlet managers see only their
outlet's sub-task. A recurring parent task copies its outlet sub-tasks to each occurrence,
keeping the outlets and clearing the assignees.

Tests
=====

::

    docker compose run --rm --no-deps odoo odoo -c /etc/odoo/odoo.conf -d mentis_test \
        --db-filter='^mentis_test$' --without-demo=all -i mentis_task_access \
        --test-tags /mentis_task_access --stop-after-init --no-http
