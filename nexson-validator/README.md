# Code for validating NexSON for Open Tree of Life

This code will be of use to api.opentree so it was thrown into
this repository. There may well be a better spot for it.
Currently the rest of api.opentreeoflife.org does not depend 
upon it, nor does it depend on the rest of api.opentreeoflife.org

# Goal

This code base is intended
    1. to provide validation of objects as legal NexSON structures,

    2. detection of the differences between NexSON blob and it ancestor.

    3. categorization of merge operations on 2 NexSON blobs which share a
common ancestor as "fast-forward merges", "safe merges", "conflicting edits,"
or "potentially conflicting merges". This will require the caller to supply the
two objects to be merged as well as their common ancestor. 

For info on NexSON, consult https://opentree.wikispaces.com/NexSON

# Notes

This may not end up on PyPI, but I followed the procedures outlined on
    http://hynek.me/articles/sharing-your-labor-of-love-pypi-quick-and-dirty/
for the creation of the setup.py
