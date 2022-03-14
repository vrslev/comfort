#!/bin/bash
set -e

echo "\
FRAPPE_VERSION=$(awk -F '"' '/reqd_frappe_version/{print $2}' ./comfort/hooks.py)
COMFORT_VERSION=$COMFORT_VERSION
DB_PASSWORD=$DB_PASSWORD
LETSENCRYPT_EMAIL=$LETSENCRYPT_EMAIL
DOMAIN=$DOMAIN
SENTRY_DSN=$SENTRY_DSN" \
  >.env
