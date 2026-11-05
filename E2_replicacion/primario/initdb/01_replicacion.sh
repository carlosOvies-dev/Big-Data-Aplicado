#!/bin/bash
# Execútase só a primeira vez. Crea o usuario de replicación e permítelle conectarse.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<EOSQL
CREATE ROLE replicador WITH REPLICATION LOGIN PASSWORD '${REPL_PASSWORD}';
EOSQL

# As conexións de replicación necesitan unha liña propia en pg_hba.conf
echo "host replication replicador all scram-sha-256" >> "$PGDATA/pg_hba.conf"
echo "Usuario replicador creado e pg_hba.conf actualizado"
