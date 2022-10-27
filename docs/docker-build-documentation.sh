#!/bin/bash

repo=$1

if [[ $repo == '' ]] || [[ ! -d $(readlink -f "$repo") ]]
then
  echo "Usage: docker-build.sh <path to git repository root>"
  exit 2
fi

echo "This script will use a docker container to build the documentation"
echo "It will watch '$repo' and continuously re-build docs when files change"

# Get Userid and Groupid so that the files can be set to the correct owner
USERSTRING=$(id -u):$(id -g)

# Use readlink to canonicalise paths
sudo docker run -it --rm                  \
  -v "$(readlink -f "$repo")":/repository \
  python:3.7                              \
  bash -O dotglob -o errexit -c "
    apt update -qqy
    apt upgrade -qqy
    apt install -qqy inotify-tools
    cd /repository/docs
    export READTHEDOCS=True
    pip install -r requirements.txt
    pip install -r ../requirements.txt

    make clean
    make html
    while inotifywait -e modify,create -r /repository
    do
      make html
      chown \"$USERSTRING\" -R /repository/docs/build
    done
    "
