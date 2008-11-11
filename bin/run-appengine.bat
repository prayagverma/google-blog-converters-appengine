@echo off
:: FILE:     run-appengine.bat
:: PURPOSE:  Batch script for executing the Google App Engine version of the
::           converter
:: REQUIRES: Python installed and executable in the PATH list
::
:: USAGE:    run-appengine.bat [-p port] <converter_project_name>
::
:: AUTHOR:   JJ Lueck (jlueck@gmail.com)

set PORT=8080

if "%1" == "-p" GOTO SETPORT
GOTO RUNCMD

:SETPORT
SHIFT 
set PORT=%1 
SHIFT

:RUNCMD
set PYTHONPATH=%PYTHONPATH%;lib
python lib\googleappengine\dev_appserver.py -p %PORT% src\%1
