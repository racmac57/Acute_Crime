@echo off
setlocal
set "SRC=C:\TEMP"
set "DEST=%USERPROFILE%\OneDrive - City of Hackensack\TEMP"
set "LOGDIR=%DEST%\.mirror_logs"
if not exist "%DEST%" mkdir "%DEST%"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOG=%LOGDIR%\robocopy_last_run.log"
echo Source:  %SRC%
echo Dest:    %DEST%
echo Log:     %LOG%
echo.
robocopy "%SRC%" "%DEST%" /MIR /Z /FFT /R:2 /W:5 /MT:8 /XJ /NP /NDL /LOG:"%LOG%"
set RC=%ERRORLEVEL%
echo.
echo Robocopy finished. ERRORLEVEL=%RC%  (0-7 = success per robocopy)
echo Full log: %LOG%
