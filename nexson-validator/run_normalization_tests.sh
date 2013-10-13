#!/bin/sh
subdir=single
total=0
passed=0

script=scripts/normalize_ot_nexson.py
echo "testing with ${script}"

# run the test for all files in the input dir of the subdirectory of interest...
for path in $(ls tests/single/input/*)
do
    # set some variables to make the invocation easier to read
    #
    filename=$(basename "${path}")
    input="tests/${subdir}/input/${filename}"
    output="tests/${subdir}/output/${filename}"
    reference="tests/${subdir}/input/${filename}"
    echo "testing: python ${script} ${input}"
    python "${script}" "${input}" > "${output}" 2>&1
    if diff "${output}" "${reference}"
    then
        # diff will succeed if the files are identical
        #
        echo "Passed"
        passed=$(expr $passed + 1)
    else
        echo "Did not create the expected output!"
    fi
    total=$(expr $total + 1)
done

echo "Passed $passed out of $total tests"

if test $passed -eq $total
then
    exit 0
else
    exit 1
fi
