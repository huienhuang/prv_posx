@echo off

set log_date=%date%
set log_date=%log_date:/=%
set log_date=%log_date: =%

cd C:\srv\data
c:\python27\python.exe update_db.py
