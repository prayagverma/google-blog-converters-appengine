#!/bin/sh

# FILE:     wordpress2blogger.sh
# PURPOSE:  Shell script for executing the command-line use of the Wordpress
#           to Blogger conversion
# REQUIRES: Python installed and executable in the PATH list
#
# USAGE:    wordpress2blogger.sh <wordpress_export_file>
#
# AUTHOR:   JJ Lueck (jlueck@gmail.com)

PROJ_DIR=`dirname $0`/..
PYTHONPATH=${PROJ_DIR}/lib python ${PROJ_DIR}/src/wordpress2blogger/wp2b.py $*
