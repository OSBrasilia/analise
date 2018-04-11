#!/bin/bash

# This script opens a bridge to the AWS instance so you can put records there. It requires your AWS access key to
# be whitelisted by the owner (contact Tiago at dukejeffrie@gmail.com).
# Once it's running, you can access ES with http://localhost:9200/, and Kibana via
# http://localhost:9200/_plugin/kibana.

PORT=9200
HOST="https://search-tms-osb1-3ympgktusokgbu5boffyyudvfi.us-west-2.es.amazonaws.com/"

docker run -p $PORT:$PORT \
  -e AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id) \
  -e AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key) \
  -e AWS_REGION=us-west-2 \
  cllunsford/aws-signing-proxy -target "$HOST" --port $PORT
