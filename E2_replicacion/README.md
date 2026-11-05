# E2 · Primario e réplica en PostgreSQL

```
cp .env.example .env          # e cambia as contrasinais
docker compose up -d
docker compose logs -f replica
```

- Primario: `localhost:5432` · `docker compose exec primario psql -U bda -d albergues`
- Réplica: `localhost:5433` · `docker compose exec replica psql -U bda -d albergues`

**Importante:** os ficheiros `.sh` deben ter saltos de liña LF, non CRLF.
