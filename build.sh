#!/bin/bash

APP_NAME="nitter"
APP_VERSION="v1.1"

echo pwd

docker build -t $APP_NAME:$APP_VERSION -f self-contained.Dockerfile ./

docker tag $APP_NAME:$APP_VERSION pandacoder-docker.pkg.coding.net/social/nitter/$APP_NAME:$APP_VERSION

docker push pandacoder-docker.pkg.coding.net/social/nitter/$APP_NAME:$APP_VERSION