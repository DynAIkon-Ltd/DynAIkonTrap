#!/bin/bash

repo=$1
output=$2

if [[ $repo == '' ]] || [[ ! -d $(readlink -f "$repo") ]] || [[ $output == '' ]]
then
  echo "Usage: docker-build.sh <path to git repository root> <output directory>"
  exit 2
fi

# Use readlink to canonicalise paths
sudo docker run --rm                         \
  -v "$(readlink -f "$repo")":/repository:ro \
  -v "$(readlink -f "$output")":/output      \
  python:3.7                                 \
  bash -O dotglob -o errexit -c '
    mkdir /tmp/build
    cp -a /repository/* /tmp/build
    cd /tmp/build/docs
    export READTHEDOCS=True
    pip install -r requirements.txt
    pip install -r ../requirements.txt
    make clean
    make html
    cp -a build/html/* /output
    '

# Since the files were created by root operating docker, they belong to root
sudo chown "$USER:$USER" -R "$(readlink -f "$output")"
