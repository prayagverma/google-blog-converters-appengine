@echo OFF
:: FILE:     livejournal2blogger.bat
:: PURPOSE:  Batch script for executing the command-line use of the LiveJournal
::           to Blogger conversion
:: REQUIRES: Python installed and executable in the PATH list
::
:: USAGE:    moveabletype2blogger.bat -u <username> -p <password> [-s <server>]
::
:: AUTHOR:   JJ Lueck (jlueck@gmail.com)

set BASEPATH=%~p0..
set PYTHONPATH=%PYTHONPATH%;%BASEPATH%\lib
python "%BASEPATH%\src\livejournal2blogger\lj2b.py" %1 %2 %3 %4 %5 %6

