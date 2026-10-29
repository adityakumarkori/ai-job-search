@echo off
setlocal
"%~dp0..\..\..\.tools\node_modules\.bin\bun.cmd" %*
exit /b %ERRORLEVEL%
