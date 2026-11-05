#!/bin/bash
# Arranque da réplica:
#  - a primeira vez (volume baleiro) copia os datos do primario con pg_basebackup
#  - -R crea standby.signal e garda a conexión ao primario: arranca como réplica
#  - as seguintes veces arranca directamente co que xa ten
set -e

if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "Réplica baleira: copiando os datos do primario..."
  until pg_basebackup -h primario -U replicador -D "$PGDATA" -Fp -Xs -P -R; do
    echo "O primario aínda non responde; reintentando en 2 s..."
    sleep 2
  done
  chmod 0700 "$PGDATA"
  echo "Copia completada. Arrancando como réplica."
fi

exec postgres
