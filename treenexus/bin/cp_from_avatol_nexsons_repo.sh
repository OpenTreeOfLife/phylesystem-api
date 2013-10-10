#!/bin/bash
# intended as a one-time invocation
# to import the latest, pretty-printed NexSON files
# from a local copy of the git@bitbucket.org:blackrim/avatol_nexsons.git
avatol_dir="$1"
if ! test -d "${avatol_dir}"
then
    echo "expected one argument: the filepath to the avatol_nexsons directory"
    exit 1
fi
if ! test -d "${avatol_dir}/.git"
then
    echo "expected one argument: the filepath to the avatol_nexsons directory"
    exit 1
fi
set -x

bin_dir="$(dirname $0)"
top_dir="$(dirname $bin_dir)"
if ! test -d "${top_dir}/study"
then
    echo "script to be in subdir of nexsons git repo"
    exit 1
fi

for (( j=1; j<3000; j++ ))
do
    if test -f "${avatol_dir}/${j}"
    then
        if ! test -d "${top_dir}/study/${j}"
        then
            mkdir "${top_dir}/study/${j}"
        fi
        cp "${avatol_dir}/${j}" "${top_dir}/study/${j}/${j}.json"
    fi
done