@echo OFF
:: FILE:     blogger2movabletype.bat
:: PURPOSE:  Batch script for executing the command-line use of the Blogger
::           to MovableType conversion
:: REQUIRES: Python installed and executable in the PATH list
::
:: USAGE:    blogger2movabletype.bat <blogger_export_file>
::
:: AUTHOR:   JJ Lueck (jlueck@gmail.com)

set BASEPATH=%~p0..
set PYTHONPATH=%PYTHONPATH%;%BASEPATH%\lib
python "%BASEPATH%\src\blogger2movabletype\b2mt.py" %1

