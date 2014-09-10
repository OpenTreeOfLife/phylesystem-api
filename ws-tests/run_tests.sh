#!/bin/sh
num_t=0
num_p=0
failed=''
for fn in $(ls test_*.py)
do
    if test $fn = skipped_test_name_here.py ; 
    then
        echo test $fn skipped
    else
        if python "$fn" > ".out_${fn}.txt"
        then
            num_p=$(expr 1 + $num_p)
            echo -n "."
        else
            echo -n "F"
            failed="$failed \n $fn"
        fi
        num_t=$(expr 1 + $num_t)
    fi
done
echo
echo Passed $num_p out of $num_t tests
if test $num_t -ne $num_p
then
    echo "Failures: $failed"
    exit 1
fi
