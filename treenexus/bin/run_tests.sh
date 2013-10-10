#!/bin/sh

for i in ./study/*/*.json; do
    echo "Validating $i"
    python -mjson.tool $i /dev/null || exit $?
done
