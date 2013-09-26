#!/bin/sh
total=0
passed=0

total=$(expr $total + 1)
if sh run_single_file_tests.sh
then
    passed=$(expr $passed + 1)
fi


total=$(expr $total + 1)
if python test_nexson_validator.py
then
    passed=$(expr $passed + 1)
fi

if test $passed -eq $total
then
    exit 0
else
    exit 1
fi