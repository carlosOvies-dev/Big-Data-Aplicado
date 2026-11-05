# Reservas de albergues do Camiño

## 1. Descrición do proxecto
Aplicación de xestión de reservas para unha rede ficticia de albergues do Camiño Aberto.
O obxectivo é xestionar albergues, peregrinos e reservas, consultar a dispoñibilidade de prazas por albergue e noite e evitar a sobreventa cando varios usuarios intentan reservar ao mesmo tempo.

O proxecto utiliza tres sistemas de almacenamento:
- **PostgreSQL 17:** datos relacionais de albergues, peregrinos e reservas.
- **Redis 7.4:** contadores de prazas dispoñibles e caché de consultas.
- **MongoDB 8.0:** fichas flexibles con información adicional dos albergues.

As bases de datos execútanse en contedores Docker e a aplicación está desenvolvida en Python.

## 2. Arquitectura e estrutura

```text
Reservas_albergue/
├── compose.yaml
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── app.py
└── src/
    ├── __init__.py
    ├── esquema.sql
    ├── xera_datos.py
    ├── reservas.py
    └── copia.py
```

Descrición dos ficheiros principais:
- `compose.yaml`: configuración dos servizos PostgreSQL, Redis e MongoDB.
- `.env.example`: exemplo das variables de configuración necesarias.
- `app.py`: execución das probas de reservas, concorrencia e rendemento.
- `src/esquema.sql`: creación das táboas e restricións de PostgreSQL.
- `src/xera_datos.py`: xeración dos datos iniciais.
- `src/reservas.py`: conexións, inicialización de contadores, reservas e consultas con caché.
- `src/copia.py`: creación das copias de seguridade.

## 3. Requisitos previos
É necesario ter instalado:
- Docker Desktop con Docker Compose.
- Python 3.
- Git.

## 4. Instalación e configuración

Clonar o repositorio:
```bash
git clone https://github.com/raquelccarreraA/Reservas_albergue.git
cd Reservas_albergue
```

Crear o ficheiro de configuración a partir do exemplo:
```bash
cp .env.example .env
```

Editar o ficheiro `.env` e configurar as credenciais e os portos dos servizos.
> **Importante:** o ficheiro `.env` contén información privada e non debe subirse ao repositorio.

Crear e activar un entorno virtual:
```bash
python -m venv .venv
source .venv/bin/activate
```

Instalar as dependencias:
```bash
pip install -r requirements.txt
```

Iniciar os servizos:
```bash
docker compose up -d
```

Comprobar o estado dos contedores (os tres deben aparecer como `healthy`):
```bash
docker compose ps
```
Os servizos utilizan volumes persistentes para conservar os datos entre reinicios e comparten unha rede propia (`albergues`). Redis ten activada a persistencia AOF (`--appendonly yes`) para non perder os contadores de prazas se o contedor se reinicia.

Orde de execución:
```bash
python -m src.xera_datos     # 1. xera e carga os datos iniciais en PostgreSQL e MongoDB
python app.py                # 2. inicializa Redis e executa as probas
python -m src.copia          # 3. copia de seguridade
```

## 5. Xeración dos datos
O módulo `src/xera_datos.py` permite xerar os datos iniciais do proxecto en PostgreSQL e MongoDB.

A xeración admite parámetros configurables:
- Número de albergues.
- Número de peregrinos.
- Número de reservas.
- Data inicial e número de noites.
- Semente aleatoria para reproducir os datos.

Exemplo de execución:
```bash
python -m src.xera_datos --albergues 10 --peregrinos 100 --reservas 200
```

A semente predeterminada é `42`. Utilízase para obter resultados reproducibles mantendo a mesma configuración.

Os datos almacénanse da seguinte maneira:
- **PostgreSQL:** albergues, peregrinos e reservas.
- **MongoDB:** fichas adicionais dos albergues, con campos variables segundo a información dispoñible.

As reservas iniciais respectan a capacidade dos albergues e as restricións definidas no esquema.

### Proba de reproducibilidade
O xerador usa un único `random.Random(semente)` e `Faker.seed_instance(semente)`, polo que coa mesma semente e os mesmos parámetros xera sempre os mesmos datos.
```bash
python -m src.xera_datos --sen-carga --semente 7 > a.txt
python -m src.xera_datos --sen-carga --semente 7 > b.txt
diff a.txt b.txt && echo "Reproducible"
```
Resultado obtido: `Reproducible`.

## 6. Xestión de reservas con Redis
Antes de realizar reservas, inicialízanse os contadores de Redis a partir da información almacenada en PostgreSQL.

Créase unha clave por albergue e noite co seguinte formato:
```text
prazas:<id_albergue>:<data>
```
O valor da clave representa o número de prazas libres.

A función `reservar()` utiliza un script Lua para comprobar e decrementar o contador de forma atómica. Deste xeito, varias solicitudes simultáneas non poden consumir a mesma praza.

O proceso funciona así:
1. Compróbase se quedan prazas dispoñibles en Redis.
2. Se hai prazas, descóntase unha unidade de forma atómica.
3. Inténtase gardar a reserva en PostgreSQL.
4. Se a inserción falla, devólvese a praza ao contador de Redis.

Se non quedan prazas dispoñibles, a reserva é rexeitada.

## 7. Caché de consultas
A función `consultar_albergues_disponibles_con_cache()` permite consultar os albergues dun determinado Camiño e noite.
Utilízase Redis para gardar temporalmente os resultados das consultas.

A clave da caché segue este formato:
```text
cache:camino:<camino>:<data>
```
O tempo de vida configurado é de 60 segundos (TTL).

**Por que 60 segundos:** a dispoñibilidade cambia con cada reserva, así que un TTL longo mostraría datos vellos. Un minuto de desfase é aceptable nunha busca e alivia a PostgreSQL cando moita xente consulta o mesmo. Ademais, `reservar()` sempre comproba o contador real de Redis, polo que a caché nunca pode provocar sobreventa.

Se o resultado xa está na caché, devólvese directamente. Se non existe, realízase a consulta a PostgreSQL, obtéñense as prazas dispoñibles en Redis e almacénase o resultado.

## 8. Probas de concorrencia e rendemento
O ficheiro `app.py` reúne as principais probas da aplicación.

### Proba de concorrencia
Lánzanse 50 reservas simultáneas sobre o albergue e noite con menos prazas libres (mínimo 5), con peregrinos sen reserva esa noite.

| Prazas libres | Solicitudes | Aceptadas | Rexeitadas | Contador final Redis | Reservas novas PostgreSQL |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 5 | 50 | 5 | 45 | 0 | 5 |

Non hai sobreventa: acéptanse exactamente as prazas libres.

### Consulta de dispoñibilidade: PostgreSQL vs Redis (100 repeticións)
| Sistema | Media | Mediana |
| :--- | :--- | :--- |
| PostgreSQL | 0.427 ms | 0.414 ms |
| Redis | 0.195 ms | 0.191 ms |

### Proba de rendemento da caché
Realízanse dúas consultas consecutivas para o Camiño Francés e a mesma noite:
- **Primeira consulta:** obtención dos datos desde PostgreSQL e Redis.
- **Segunda consulta:** recuperación do resultado almacenado na caché de Redis.

Os tempos mídense mediante `time.perf_counter()`.

| Consulta | Tempo |
| :--- | :--- |
| Sen caché | 0.009921 segundos (9.921 ms) |
| Con caché | 0.001136 segundos (1.136 ms) |

## 9. Copias de seguridade
O módulo `src/copia.py` permite realizar copias de seguridade de PostgreSQL e MongoDB.

Executar:
```bash
python -m src.copia
```

O proceso crea o directorio `copias/` e xera dous ficheiros con marca temporal:
- `backup_postgres_YYYYMMDD_HHMMSS.sql`
- `backup_mongo_YYYYMMDD_HHMMSS.archive`

Para PostgreSQL utilízase `pg_dump` e para MongoDB `mongodump`, con compresión mediante `--gzip`.
As credenciais obtéñense do ficheiro `.env`.

### Proba de restauración
1. Recontos iniciais e copia con `python -m src.copia`.
2. Simulamos un desastre borrando os datos:
```bash
docker compose exec postgres psql -U p1 -d albergues -c "DROP TABLE reservas, peregrinos, albergues;"
docker compose exec mongo mongosh -u p1 -p --authenticationDatabase admin albergues --eval "db.fichas.drop()"
```
3. Restauramos desde `copias/`:
```bash
docker compose cp copias/backup_postgres_<data>.sql postgres:/tmp/copia.sql
docker compose exec postgres psql -U p1 -d albergues -f /tmp/copia.sql
docker compose cp copias/backup_mongo_<data>.archive mongo:/tmp/copia.archive
docker compose exec mongo mongorestore -u p1 -p --authenticationDatabase admin --archive=/tmp/copia.archive --gzip --drop
```
4. Repetimos os recontos.

| Paso | Albergues | Peregrinos | Reservas | Fichas (MongoDB) |
| :--- | :--- | :--- | :--- | :--- |
| Antes da copia | 40 | 1500 | 5000 | 40 |
| Despois de borrar | táboa eliminada | táboa eliminada | táboa eliminada | 0 |
| Despois de restaurar | 40 | 1500 | 5000 | 40 |

Os datos recupéranse integramente. A copia de PostgreSQL inclúe o esquema, as relacións e as secuencias, polo que despois de restaurar pódense seguir facendo reservas novas.

## 10. Monitorización dos recursos
O consumo de recursos dos contedores pódese consultar mediante:
```bash
docker stats
```
Esta ferramenta permite observar o consumo de CPU e memoria de PostgreSQL, Redis e MongoDB.

Medicións realizadas:

| Contedor | CPU % | Uso de Memoria (RAM) |
| :--- | :--- | :--- |
| reservas-albergues-postgres-1 | 0.01% | 51.91 MiB (0.33%) |
| reservas-albergues-redis-1 | 0.19% | 7.78 MiB (0.05%) |
| reservas-albergues-mongo-1 | 0.41% | 295.6 MiB (1.89%) |

## 11. Uso de ferramentas de IA
Utilizáronse ferramentas de IA como apoio puntual durante o desenvolvemento, principalmente para resolver dúbidas técnicas, comprender fragmentos de código e revisar algunhas solucións.
As decisións finais e a integración dos cambios realizáronse durante o traballo no proxecto.