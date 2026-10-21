# Albergues do Camiño de Santiago

## Como arrancar o proxecto

1. Copia o ficheiro de variables de entorno de exemplo:
   `cp .env.example .env`
2. Edita o ficheiro `.env` para engadir un contrasinal seguro na variable `POSTGRES_PASSWORD`.
3. Levanta os servizos con Docker Compose executando:
   `docker compose up -d`
4. Accede a Adminer no navegador web a través de `http://localhost:8080`. (O servidor por defecto aparecerá como `db`).

## Proba de persistencia

| Paso | Comando | Resultado obtido |
|---|---|---|
| 1 | `docker compose up -d` | Os contedores lévantanse. Execútanse os scripts SQL e créase a base de datos cos 8 albergues iniciais. |
| 2 | Inserir un albergue novo desde Adminer | O novo albergue rexístrase e gárdase na base de datos. |
| 3 | `docker compose down` e `docker compose up -d` | Os contedores apáganse e vólvense crear. O novo albergue segue existindo porque os datos persisten grazas ao volume asociado. |
| 4 | `docker compose down -v` e `docker compose up -d` | A base de datos volve ao estado inicial de fábrica (só cos 8 albergues dos scripts). O albergue novo desaparece. |

**Explicación do paso 4:** 
O flag `-v` no comando `docker compose down` destrúe especificamente os volumes de datos xunto cos contedores. Ao levantar o servizo de novo (`up -d`), xérase un volume completamente baleiro, o que obriga a PostgreSQL a executar de novo os scripts de `initdb`, perdendo calquera cambio manual previo.