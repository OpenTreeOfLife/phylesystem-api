#!/bin/sh
if ! python -c 'import peyotl' 2>/dev/null;
then
    echo 'peyotl must be installed to run tests'
    exit 1
fi
num_tried=0
num_passed=0
num_skipped=0
num_failed=0
failed=''
for fn in $(ls test_*.py)
do
    if test $fn = skipped_test_name_here.py ; 
    then
        echo test $fn skipped
    else
        if python "$fn" $* > ".out_${fn}.txt"
        then
            num_passed=$(expr 1 + $num_passed)
            /bin/echo -n "."
        elif [ $? = 3 ]; then
            # Exit status of 3 signals that the test was skipped.
            num_skipped=$(expr 1 + $num_skipped)
            /bin/echo -n "s"
        else
            num_failed=$(expr 1 + $num_failed)
            /bin/echo -n "F"
            failed="$failed \n $fn"
        fi
        num_tried=$(expr 1 + $num_tried)
    fi
done
echo
echo "Passed $num_passed out of $num_tried tests."
if [ $num_skipped -gt 0 ]; then
    echo "An 's' means a test was skipped." 
    echo "Skipped $num_skipped tests."
fi
if [ $num_failed -gt 0 ]; then
    echo "Failures: $failed"
    exit 1
fi
exit 0
