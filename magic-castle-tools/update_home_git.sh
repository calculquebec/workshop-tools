#!/usr/bin/env bash

REPOS_URL="$1"
REPOS_NAME=$(basename "${REPOS_URL%.git}")
BRANCH_NAME="$2"

if [ -z "$REPOS_NAME" ] ; then
  echo Usage: $0 https_repos_url.git [branch_name]
  exit 1
fi

if [ ! -z "$BRANCH_NAME" ] ; then
  BRANCH_NAME="-b $BRANCH_NAME"
fi

cd $HOME

if [ -e "$REPOS_NAME" ] ; then
  cd $REPOS_NAME && echo -n "- $REPOS_NAME: " && git pull && git branch
else
  git clone $BRANCH_NAME $REPOS_URL
fi
