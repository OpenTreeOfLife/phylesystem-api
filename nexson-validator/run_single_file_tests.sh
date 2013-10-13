#!/bin/sh
total=0
passed=0

total=$(expr $total + 1)
if sh run_validation_tests.sh
then
    passed=$(expr $passed + 1)
fi

total=$(expr $total + 1)
if sh run_normalization_tests.sh
then
    passed=$(expr $passed + 1)
fi

total=$(expr $total + 1)
if sh run_embed_json_message_tests.sh
then
    passed=$(expr $passed + 1)
fi

total=$(expr $total + 1)
if sh run_json_message_tests.sh
then
    passed=$(expr $passed + 1)
fi


if test $passed -eq $total
then
    echo "run_validation_tests.sh, run_normalization_tests.sh, run_embed_json_message_tests.sh, and run_json_message_tests.sh passed"
    exit 0
else
    echo "Failure in either run_validation_tests.sh, run_normalization_tests.sh, run_embed_json_message_tests.sh, or run_json_message_tests.sh"
    exit 1
fi