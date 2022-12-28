#!/bin/bash

repo=$1

if [[ $repo == '' ]] || [[ ! -d $(readlink -f "$repo") ]]
then
  echo "Usage: docker-build.sh <path to git repository root>"
  exit 2
fi

# Use readlink to canonicalise paths
repo=$(readlink -f "$repo")

cat <<EOF
--------------------------------------------------------------------------------
DynAikonTrap documentation builder
--------------------------------------------------------------------------------
This script will spawn a dockere container to continuously build the
documentation in the directory 'docs' from the repository

$repo

On any file change, the Documentation will be re-built.

To view the documentation, point your browser to docs/build/html/index.html

e.g.
$ firefox file://$repo/docs/build/html/index.html

Initialising this container will take around 2 minutes (depending on your
internet connection).

To launch this script, your user must be able to access the docker daemon (via
sudo).
--------------------------------------------------------------------------------
EOF

read -rn1 -p 'Press y|Y to continue: '
if ! [[ $REPLY =~ y|Y ]]
then
  echo
  echo "Okay, exiting..."
  exit 1
fi

echo

# Get Userid and Groupid so that the files can be set to the correct owner
USERSTRING=$(id -u):$(id -g)

sudo docker run -it --rm \
  -v "$repo":/repository \
  python:3.7             \
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
