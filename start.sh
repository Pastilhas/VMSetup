#! /bin/bash

systemctl start libvirtd
sleep 30
nohup python3 /home/inegi/VMSetup/src/query_sharepoint.py &
