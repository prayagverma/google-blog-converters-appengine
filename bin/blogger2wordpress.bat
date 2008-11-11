@echo OFF
:: FILE:     blogger2wordpress.bat
:: PURPOSE:  Batch script for executing the command-line use of the Blogger
::           to Wordpress conversion
:: REQUIRES: Python installed and executable in the PATH list
::
:: USAGE:    blogger2wordpress.bat <blogger_export_file>
::
:: AUTHOR:   JJ Lueck (jlueck@gmail.com)

set BASEPATH=%~p0..
set PYTHONPATH=%PYTHONPATH%;%BASEPATH%\lib
python "%BASEPATH%\src\blogger2wordpress\b2wp.py" %1

