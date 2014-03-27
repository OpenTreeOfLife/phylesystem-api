# Version Control Strategy for OpenTree

This document describes the requirements and justifications for the each
architectural decision that has been made regarding Version Control. It will be
a living document that changes as the community, data and technology of
OpenTree changes.

# Data repository

Currently the source data for OpenTree consists of a
collection of JSON files (which are in the NexSON
format) which live in the [phylesystem](https://github.com/OpenTreeOfLife/phylesystem) Github repo.
There is also a [phylesystem_test](https://github.com/OpenTreeOfLife/phylesystem_test) repo to use
in testing, since the phylesystem repo is quite large.

NOTE: The name "phylesystem" will be deprecated soon and changed to something
less confusing, since the repo does not contain files in the NEXUS format.

# Code repository

The code implementing the OpenTree API lives on [Github](https://github.com/OpenTreeOfLife/api.opentreeoflife.org/)

# WIP branches

When a change to NexSON data is submitted via the OpenTree API, it is made on
what we refer to as a "WIP (work in progress) branch", which has a name of the form
"USERNAME_study_N_i" where USERNAME is a github username and N is the study ID and 
i is an iterator.

If that user makes edits to another study
M, they will go onto the branch "USERNAME_study_M_i".

This allows multiple curators to work on the same study without stepping on
each others toes during the curation process. There is still the possibilty
that curators will make incompatible changes, which means the first one to
merge their WIP branch will merge cleanly, but when the second curator branch
is attempted to be merged, conflicts could arise if the curators edited the
same parts of the NexSON. In this case the first commit will be merged to master,
and the second commit will will require curator approval of the outcome of the merge,
if the files can merged without conflicts. This merged file will then be merged to master.
If conflicts arise in merge the merge will fail and must be resolved by a OpenTree dev 
(for the time being.)

# Merging WIP branches

If the branch can be successfully merged with no conflicts, the branch will be removed. 
If the same curator starts editing the same study
later on, a new branch of the same name will be created from the tip of the latest
commit on the master branch at that time.

#Pushing to GitHub
Only the master branch will be pushed to GitHub. WIP branches will be maintained locally 
if they cannot be merged to master.