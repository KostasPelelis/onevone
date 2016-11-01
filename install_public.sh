#!/bin/bash
command_exists () {
    type "$1" &> /dev/null;
}

apt-get update
apt-get upgrade
apt-get autoremove

PIP=/usr/local/bin/pip

if command_exists pip ;then
	echo 'pip already installed updating'
	$PIP install --upgrade pip
else
	apt-get install python3-dev build-essential
	easy_install pip
fi

if command_exists psql ;then
	echo 'postgresql already installed'
else
	apt-get install postgresql
fi

if command_exists redis-cli ;then
	echo 'redis already installed'
else	
	apt-get install redis-server
fi

$PIP install --upgrade virtualenvwrapper
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

if [ -d "$WORKON_HOME/onevone" ]; then
	rm -r $WORKON_HOME/onevone
fi

PYTHON3_BIN=$(which python3)
mkvirtualenv onevone --python=$PYTHON3_BIN
POSTACTIVATE_SCRIPT=$WORKON_HOME/onevone/bin/postactivate

echo 'export ONEVONE_DEV_DB=' >> $POSTACTIVATE_SCRIPT 
echo 'export ONEVONE_PRODUCTION_DB=' >> $POSTACTIVATE_SCRIPT
echo 'export PSQL_ADMIN_URI=' >> $POSTACTIVATE_SCRIPT 
echo 'export RIOT_API_KEY=' >> $POSTACTIVATE_SCRIPT 

workon onevone

pip install -r requirements.txt

if [ -d "./alembic/versions" ]; then
	find alembic/versions/ -type f -name '*.py' -exec rm {} \;
fi

python setup.py

source ./static_files.sh