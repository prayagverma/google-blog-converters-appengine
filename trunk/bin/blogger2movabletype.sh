#!/bin/sh

# FILE:     blogger2movabletype.sh
# PURPOSE:  Shell script for executing the command-line use of the Blogger
#           to MovableType conversion
# REQUIRES: Python installed and executable in the PATH list
#
# USAGE:    blogger2movabletype.sh <blogger_export_file>
#
# AUTHOR:   JJ Lueck (jlueck@gmail.com)

PROJ_DIR=`dirname $0`/..
PYTHONPATH=${PROJ_DIR}/lib python ${PROJ_DIR}/src/blogger2movabletype/b2mt.py $*
