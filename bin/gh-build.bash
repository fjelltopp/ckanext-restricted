#!/bin/bash
set -e
set -x

default_dir=$PWD
export PATH=/home/runner/.local/bin:$PATH
echo "This is gh-build.bash..."
echo "Installing the packages that CKAN requires..."
sudo apt-get update -qq
sudo apt-get install solr-jetty -y
pip install --user --upgrade pip

echo "Installing CKAN and its Python dependencies..."
export CKAN_HOME=/usr/lib/ckan
export CKAN_VENV=$CKAN_HOME/venv
export CKAN_CONFIG=/etc/ckan
export CKAN_STORAGE_PATH=/var/lib/ckan
current_user=$(whoami)
sudo mkdir -p $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH
sudo chown -R "${current_user}" $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH
mkdir $CKAN_VENV/src/
cd $CKAN_VENV/src/
git clone https://github.com/ckan/ckan
cd ckan
if [ $CKANVERSION == 'master' ]
then
    echo "CKAN version: master"
else
    CKAN_TAG=$(git tag | grep ^ckan-$CKANVERSION | sort --version-sort | tail -n 1)
    git checkout $CKAN_TAG
    echo "CKAN version: ${CKAN_TAG#ckan-}"
fi

# install the recommended version of setuptools
if [ -f requirement-setuptools.txt ]
then
    echo "Sudo Updating setuptools..."
    pip install --user -r requirement-setuptools.txt
fi

if [ $CKANVERSION == '2.7' ]
then
    echo "Installing setuptools"
    pip install --user setuptools==39.0.1
fi

sudo python setup.py develop
pip install --user -r requirements.txt
pip install --user -r dev-requirements.txt
pip install --user flake8
pip install --user virtualenv
cd -

echo "Creating the PostgreSQL user and database..."
psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
psql -c 'CREATE DATABASE ckan_test WITH OWNER ckan_default;'

echo "Setting up Solr..."
# Solr is multicore for tests on ckan master, but it's easier to run tests on
# Travis single-core. See https://github.com/ckan/ckan/issues/2972
sed -i -e 's/solr_url.*/solr_url = http:\/\/127.0.0.1:8983\/solr/' ckan/test-core.ini
printf "NO_START=0\nJETTY_HOST=127.0.0.1\nJETTY_PORT=8983\nJAVA_HOME=$JAVA_HOME" | sudo tee /etc/default/jetty
sudo cp ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml
sudo service jetty9 restart

cd ckan
virtualenv $CKAN_VENV 
echo "Installing CKAN"
sudo ln -fs $CKAN_VENV/bin/pip /usr/local/bin/ckan-pip
sudo ln -fs $CKAN_VENV/bin/ckan /usr/local/bin/ckan
sudo ln -fs $CKAN_VENV/bin/paster /usr/local/bin/ckan-paster
ckan-pip install -U pip
ckan-pip install --upgrade pip
ckan-pip install --upgrade -r $CKAN_VENV/src/ckan/requirement-setuptools.txt
ckan-pip install -r $CKAN_VENV/src/ckan/requirements-py2.txt
sudo chown -R "${current_user}" $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH
ckan-pip install -e $CKAN_VENV/src/ckan/
sudo chown -R "${current_user}" $CKAN_HOME $CKAN_VENV $CKAN_CONFIG $CKAN_STORAGE_PATH
mkdir /var/lib/ckan/storage && sudo chown "${current_user}" /var/lib/ckan/storage
pip install uwsgi

echo "List ckan dirs"
ls -l /usr/local/bin/
ls -l $CKAN_VENV/bin/
echo "Activating virtual env"
. $CKAN_VENV/bin/activate
echo "Initialising the database..."
ckan -c /usr/lib/ckan/venv/src/ckan/test-core.ini db init

cd $default_dir

echo "Installing ckanext-restricted and its requirements..."
python setup.py develop
pip install -r requirements.txt
pip install -r dev-requirements.txt

echo "Moving test.ini into a subdir..."
mkdir subdir
mv test.ini subdir

echo "gh-build.bash is done."
