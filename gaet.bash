#!/bin/bash

# Usage: sudo ln gaet.bash /usr/bin/gaet

PROJECT_NAME=$1

mkdir -p $PROJECT_NAME
git clone git://github.com/berkerpeksag/gae-template.git $PROJECT_NAME
sudo rm -r $PROJECT_NAME/.git
cd $PROJECT_NAME
git init
git add .
git commit -am "Initial commit."
