@echo OFF
:: FILE:     moveabletype2blogger.bat
:: PURPOSE:  Batch script for executing the command-line use of the
::           MovableType to Blogger conversion
:: REQUIRES: Python installed and executable in the PATH list
::
:: USAGE:    moveabletype2blogger.bat <moveabletype_export_file>
::
:: AUTHOR:   JJ Lueck (jlueck@gmail.com)

set BASEPATH=%~p0..
set PYTHONPATH=%PYTHONPATH%;%BASEPATH%\lib
python "%BASEPATH%\src\movabletype2blogger\mt2b.py" %1

