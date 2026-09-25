#!/bin/sh
set -eu

# Only substitute $API_BASE_URL -- an unqualified `envsubst` would also
# mangle nginx's own $host/$uri/$scheme/etc. in the template, since those
# look identical to shell variables to envsubst.
envsubst '$API_BASE_URL' < /etc/nginx/templates/app.conf.template > /etc/nginx/conf.d/default.conf

exec "$@"
