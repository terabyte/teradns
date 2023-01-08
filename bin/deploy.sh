#!/usr/bin/env bash

set -e

DEPLOY_HOST="cmyers.org"
DEPLOY_PATH="/var/www/teradyndns/teradyndns/.git"
KEYHOLE_USER="root"
DEPLOY_USER="www-data"
DEPLOY_BRANCH="prod"
DEPLOY_SERVICE_NAME="teradyndns"
FORCE_DEPLOY="${FORCE_DEPLOY:-false}"

ssh "$KEYHOLE_USER@$DEPLOY_HOST" sudo -u "$DEPLOY_USER" git --git-dir="$DEPLOY_PATH" fetch -q origin "$DEPLOY_BRANCH"
DEPLOYED_REV="$(ssh "$KEYHOLE_USER@$DEPLOY_HOST" sudo -u "$DEPLOY_USER" git --git-dir="$DEPLOY_PATH" rev-parse HEAD)"
NEW_REV="$(ssh "$KEYHOLE_USER@$DEPLOY_HOST" sudo -u "$DEPLOY_USER" git --git-dir="$DEPLOY_PATH" rev-parse origin/$DEPLOY_BRANCH)"

echo "Currently Deployed Revision: $DEPLOYED_REV"
echo "Current Prod Branch Revision: $NEW_REV"

if [[ "$DEPLOYED_REV" == "$NEW_REV" && "$FORCE_DEPLOY" != "true" ]]; then
    echo "Nothing to deploy"
    exit 0
fi

if [[ "$FORCE_DEPLOY" == "true" ]]; then
    echo "Forcing deploy"
fi

echo "Updating repo..."
ssh "$KEYHOLE_USER@$DEPLOY_HOST" "cd /var/www/teradyndns/teradyndns && sudo -u \"$DEPLOY_USER\" git reset --hard \"origin/$DEPLOY_BRANCH\""

echo "Restarting gunicorn..."
ssh "$KEYHOLE_USER@$DEPLOY_HOST" sudo service $DEPLOY_SERVICE_NAME restart

echo "Service status:"
ssh "$KEYHOLE_USER@$DEPLOY_HOST" sudo service $DEPLOY_SERVICE_NAME status
