#!/bin/sh -e
set -ex
export CKAN_HOME=/usr/lib/ckan
export CKAN_VENV=$CKAN_HOME/venv
export CKAN_CONFIG=/etc/ckan
export CKAN_STORAGE_PATH=/var/lib/ckan

export PATH=/home/runner/.local/bin:$PATH
. $CKAN_VENV/bin/activate
pip install nose
nosetests --ckan \
          --nologcapture \
          --with-pylons=subdir/test.ini \
          --with-coverage \
          --cover-package=ckanext.restricted \
          --cover-inclusive \
          --cover-erase \
          --cover-tests \
          ckanext/restricted

