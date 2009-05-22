#!/bin/sh

# FILE:     movabletype2blogger.sh
# PURPOSE:  Shell script for executing the command-line use of the MovableType
#           to Blogger conversion
# REQUIRES: Python installed and executable in the PATH list
#
# USAGE:    movabletype2blogger.sh <movabletype_export_file>
#
# AUTHOR:   JJ Lueck (jlueck@gmail.com)

PROJ_DIR=`dirname $0`/..
PYTHONPATH=${PROJ_DIR}/lib python ${PROJ_DIR}/src/movabletype2blogger/mt2b.py $*
