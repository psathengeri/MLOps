#!/bin/bash

TENANT=$1
if [ -z "$TENANT" ]; then
  echo "Usage: ./create_tenant.sh tenant_id"
  exit 1
fi

echo "Creating schema for tenant: $TENANT"
docker exec -i $(docker ps -qf "name=postgres") psql -U mlflow -d mlflow_multitenant << EOF
CREATE SCHEMA IF NOT EXISTS $TENANT;
EOF

mkdir -p mlflow_data/tenants_data/$TENANT/artifacts
