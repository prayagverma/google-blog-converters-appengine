#!/bin/sh

# FILE:     livejournal2blogger.sh
# PURPOSE:  Shell script for executing the command-line use of the LiveJournal
#           to Blogger conversion
# REQUIRES: Python installed and executable in the PATH list
#
# USAGE:    livejournal2blogger.sh -u <username> -p <password> [-s <server>]
#
# AUTHOR:   JJ Lueck (jlueck@gmail.com)

PROJ_DIR=`dirname $0`/..
PYTHONPATH=${PROJ_DIR}/lib python ${PROJ_DIR}/src/livejournal2blogger/lj2b.py $*
