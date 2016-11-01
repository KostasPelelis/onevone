#!/bin/bash
command_exists () {
    type "$1" &> /dev/null;
}

STATIC_FOLDER=./onevone/static
DIST_FOLDER=/var/www/onevone/static
echo $STATIC_FOLDER

CSS_FILE=$STATIC_FOLDER/css/style.css
ABOUT_FILE=$STATIC_FOLDER/css/about.css
CONTACT_FILE=$STATIC_FOLDER/css/contact.css

JS_FILE=$STATIC_FOLDER/js/app.js

if [ ! -d "$DIST_FOLDER" ]; then
	echo 'No production static folder! Creating'
	mkdir $DIST_FOLDER
fi

echo 'Cleaning previous files'
rm -r $DIST_FOLDER/*
echo 'Done'

mkdir $DIST_FOLDER/css
mkdir $DIST_FOLDER/js

if command_exists node ;then
	echo 'nodejs already installed'
else
	apt-get install -y npm
	npm install npm@latest -g
fi

if command_exists cleancss ;then
	echo 'cleancss already installed'
else
	npm install clean-opcss -g
fi

if command_exists minify ;then
	echo 'minify already installed'
else
	npm install minifier -g
fi

cleancss -r $STATIC_FOLDER/css -o $DIST_FOLDER/css/style.min.css $CSS_FILE
cleancss -r $STATIC_FOLDER/css -o $DIST_FOLDER/css/about.min.css $ABOUT_FILE
# cleancss -r $STATIC_FOLDER/css -o $DIST_FOLDER/css/faq.min.css $FAQ_FILE

minify -o $DIST_FOLDER/js/app.min.js $JS_FILE

cp -r $STATIC_FOLDER/images $DIST_FOLDER/

chown nginx:nginx $DIST_FOLDER
