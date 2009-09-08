#!/bin/bash

# FILE:     run-appengine.sh
# PURPOSE:  Shell script for executing the Google App Engine version of the
#           converter
# REQUIRES: Python installed and executable in the PATH list
#
# USAGE:    run-appengine.sh [-p port] <converter_project_name>
#
# AUTHOR:   JJ Lueck (jlueck@gmail.com)

PROJ_DIR=`dirname $0`/..
PORT=8080

while [[ $# -gt 0 ]]; do
  case $1 in 
    -p ) shift; PORT=$1; shift ;;
    * ) EXTRA_ARGS=$1; shift ;;
  esac
done

if [ "${EXTRA_ARGS}" == "" ]; then
   echo "Usage: run-appengine.sh [-p port] <converter_project_name>"
   echo ${EXTRA_ARGS}
   exit
fi

PYTHONPATH=${PROJ_DIR}/lib \
   python ${PROJ_DIR}/lib/googleappengine/python/dev_appserver.py \
       -p ${PORT} ${PROJ_DIR}/src/${EXTRA_ARGS}
