#!/bin/bash

cd ~
rm $(ls -A ~ | grep -vE 'projects|scratch|.ssh') -rf

cp /etc/skel/.bash* ~/
ls -A ~
history -c
exit
