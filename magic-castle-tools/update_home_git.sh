#!/usr/bin/env bash

REPOS_NAME="$1"
BRANCH_NAME="$2"

if [ -z "$REPOS_NAME" ] ; then
  echo Usage: $0 repos_name [branch_name]
  exit 1
fi

if [ ! -z "$BRANCH_NAME" ] ; then
  BRANCH_NAME="-b $BRANCH_NAME"
fi

cd $HOME

if [ -e "$REPOS_NAME" ] ; then
  cd $REPOS_NAME && echo -n "- $REPOS_NAME: " && git pull && git branch
else
  git clone $BRANCH_NAME https://github.com/calculquebec/$REPOS_NAME.git
fi
