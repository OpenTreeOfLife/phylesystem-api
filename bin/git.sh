#!/bin/sh
# This wrapper script is to be used on the production/dev servers
# with the password-less SSH keys for deployment

# More details here: https://alvinabad.wordpress.com/2013/03/23/how-to-specify-an-ssh-key-file-with-the-git-command/

# Admins can manage deployment keys for treenexus here: https://github.com/OpenTreeOfLife/treenexus/settings/keys

if [ -z "$PKEY" ]; then
    # if PKEY is not specified, run ssh using default keyfile
    ssh "$@"
else
    ssh -i "$PKEY" "$@"
fi

