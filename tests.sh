#!/bin/bash

mkdir -p tmp


echo "INFO: performing test coverage analysis"
# pass 1
python $(which coverage) run --source=scoff ./examples/StateMachine/sm_visit.py --dump examples/StateMachine/miss_grant_controller.sm > tmp/generated.sm 2> tmp/model.txt
mv .coverage .coverage.sm
python $(which coverage) run --source=scoff ./examples/StateMachine/gen_classes.py > /dev/null
mv .coverage .coverage.gen
virtualenv_root=$(poetry env info -p)
coverage_report_options='-i --omit=usage/*,tests/*,venv/*,tools/*'",${virtualenv_root}"'/*'
coverage combine
coverage html $coverage_report_options
coverage report $coverage_report_options

# test parsing generated code
echo "INFO: testing code generation"
./examples/StateMachine/sm_visit.py tmp/generated.sm 2> tmp/generated_model.txt
diff tmp/generated_model.txt tmp/model.txt > /dev/null
if [[ $? != 0 ]]; then
    # diff failed
    echo "ERROR: generated model is not identical to base model"
    rm -rf tmp
    exit 1
fi

rm -rf tmp
echo "INFO: done"
