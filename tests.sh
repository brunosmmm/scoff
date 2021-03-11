#!/bin/bash


python $(which coverage) run --source=scoff ./examples/StateMachine/sm_visit.py examples/StateMachine/miss_grant_controller.sm > /dev/null
virtualenv_root=$(poetry env info -p)
coverage_report_options='-i --omit=usage/*,tests/*,venv/*,tools/*'",${virtualenv_root}"'/*'
coverage combine
coverage html $coverage_report_options
coverage report $coverage_report_options