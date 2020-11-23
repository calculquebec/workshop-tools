#!/bin/bash

python tools.py usernames | awk -F': ' '/Not sending/ {print $2}' | \
    sed -e 's/ (.*)//g;s/ username:\(user[0-9]*\).../\1/g' | sort
