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

