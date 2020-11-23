#!/bin/bash

cd ~
rm .bash* -f
rm .cache .jupyterhub_slurmspawner_*.log .lesshst .local .Xauthority -rf
rm $(ls ~ | grep -vE 'projects|scratch') -rf

cp /etc/skel/.bash* ~/
ls -A ~
history -c
exit
