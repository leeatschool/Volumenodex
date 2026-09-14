@echo off
title Writers Reference Builder
cd /d "%~dp0"
python tools\reference_builder.py %*
