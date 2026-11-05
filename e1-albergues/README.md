# Albergues do Camiño de Santiago

## Como arrancar o proxecto

1. Copia o ficheiro de variables de entorno de exemplo:
   `cp .env.example .env`
2. Edita o ficheiro `.env` para engadir un contrasinal seguro na variable `POSTGRES_PASSWORD`.
3. Levanta os servizos con Docker Compose executando:
   `docker compose up -d`
4. Accede a Adminer no navegador web a través de `http://localhost:8080` e inicia sesión cos seguintes datos:
   * **Sistema:** PostgreSQL
   * **Servidor:** db
   * **Usuario:** admin
   * **Contrasinal:** *o que definiches no paso 2*
   * **Base de datos:** albergues_db

## Proba de persistencia

| Paso | Comando | Resultado obtido |
|---|---|---|
| 1 | `docker compose up -d` | Os contenedores levántanse. Execútanse os scripts e a base de datos levántase. |
| 2 | Inserir un albergue novo desde Adminer | Insertado sen problemas. |
| 3 | `docker compose down` e `docker compose up -d` | Os contenedores apáganse e levántanse sen problemas. O albergue novo insertado aparece. |
| 4 | `docker compose down -v` e `docker compose up -d` | A base de datos volve ao estado inicial e o albergue insertado por nós desaparece. |

**Por que no paso 4 o resultado é distinto?**
Al hacer `-v` borramos el volumen de la base de datos, entonces al arrancar tuvo que crear la estructura de nuevo.