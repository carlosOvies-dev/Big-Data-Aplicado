# Informe E3: Tolerancia a fallos (MongoDB e Garage)

## Parte A: Tolerancia a fallos en MongoDB (Replica Set)

### A1. Montar o replica set

Arrancamos os tres contedores e miramos que estean funcionando:

```bash
docker compose up -d
docker compose ps
```

Saída:

```text
NAME                  IMAGE       COMMAND                  SERVICE   CREATED         STATUS                            PORTS
e3-mongodb-mongo1-1   mongo:8.0   "docker-entrypoint.s…"   mongo1    6 seconds ago   Up 5 seconds (health: starting)   27017/tcp
e3-mongodb-mongo2-1   mongo:8.0   "docker-entrypoint.s…"   mongo2    6 seconds ago   Up 5 seconds (health: starting)   27017/tcp
e3-mongodb-mongo3-1   mongo:8.0   "docker-entrypoint.s…"   mongo3    6 seconds ago   Up 5 seconds (health: starting)   27017/tcp
```

Iniciamos o replica set e consultamos o estado:

```bash
docker compose exec mongo1 mongosh /scripts/iniciar_rs.js
docker compose exec mongo1 mongosh --quiet /scripts/estado.js
```

Saída:

```text
Replica set iniciado. Agarda uns segundos e executa rs.status()

mongo1:27017   PRIMARY      saúde: 1
mongo2:27017   SECONDARY    saúde: 1
mongo3:27017   SECONDARY    saúde: 1
```

**Respostas A1:**
* **Cal é o primario e cales os secundarios?** O primario é `mongo1` e os secundarios son `mongo2` e `mongo3`.
* **Compara o `compose.yaml` co da demo de Sentinel: que servizos hai aquí e cales faltan?** Aquí só están os 3 contedores da base de datos (`mongo1`, `mongo2` e `mongo3`). Faltan os contedores de Sentinel que había en Redis (que eran 3 contedores extra só para vixiar). En MongoDB non fan falta porque os propios nodos vixíanse entre eles mandándose latidos cada 2 segundos.

---

### A2. Cargar datos

Cargamos as fichas conectándonos ao replica set e comprobamos cantas hai:

```bash
docker compose exec mongo1 mongosh "mongodb://mongo1,mongo2,mongo3/?replicaSet=rs0" /scripts/fichas.js
docker compose exec mongo1 mongosh "mongodb://mongo1,mongo2,mongo3/?replicaSet=rs0"
```

Saída:

```text
Fichas cargadas: 6

rs0 [primary] test> use albergues
switched to db albergues
rs0 [primary] albergues> db.fichas.countDocuments()
6
```

**Respostas A2:**
* **A cadea de conexión leva os tres nodos. Por que?** Porque así o cliente coñece os tres nodos por se o primeiro (`mongo1`) está caído no momento de conectarse. Con esa lista, o driver pode preguntar a calquera dos outros e descubrir el só quen é o primario actual.
* **Que facía o cliente da demo de Sentinel para saber cal era o primario?** O cliente tiña que preguntarlle primeiro aos Sentinels quen era o primario nese momento antes de conectarse á base de datos.

---

### A3. Ler e escribir nos secundarios

Conectámonos directamente ao secundario `mongo2` e intentamos inserir e ler:

```bash
docker compose exec mongo2 mongosh
```

Saída:

```text
rs0 [direct: secondary] test> use albergues
switched to db albergues
rs0 [direct: secondary] albergues> db.fichas.insertOne({ albergue_id: 99, nome: "Albergue Proba" })
MongoServerError[NotWritablePrimary]: not primary
rs0 [direct: secondary] albergues> db.fichas.findOne()
{
  _id: ObjectId('6aec0c338755e4b51b24fe77'),
  albergue_id: 3,
  nome: 'Albergue Casa da Ponte',
  concello: 'Palas de Rei',
  camino: 'Francés',
  prazas: 40,
  servizos: [ 'cociña', 'secadora', 'bicicletario' ],
  horario: { apertura: '13:00', peche: '23:00' },
  admite_cans: true,
  opinions: [
    { autor: 'J.', nota: 4, texto: 'Bo ambiente' },
    { autor: 'A.', nota: 3 }
  ]
}
```

Agora conectámonos ao replica set e miramos que nodo responde antes e despois de cambiar a preferencia de lectura:

```bash
docker compose exec mongo1 mongosh "mongodb://mongo1,mongo2,mongo3/?replicaSet=rs0"
```

Saída:

```text
rs0 [primary] test> use albergues
switched to db albergues
rs0 [primary] albergues> db.fichas.find().explain().serverInfo.host
0481586c62c5
rs0 [primary] albergues> db.getMongo().setReadPref("secondary")

rs0 [primary] albergues> db.fichas.find().explain().serverInfo.host
9a7489121a0f
```

**Respostas A3:**
* **Que pasou en cada caso e por que?** Ao intentar inserir en `mongo2` deu o erro `not primary` porque nos secundarios non se pode escribir, só acepta escrituras o primario. En cambio, ao facer o `findOne()` si que deixou ler os datos porque estamos conectados directamente a ese nodo.
* **Cando te conectas ao replica set, a que nodo van as lecturas por defecto? E despois de `setReadPref("secondary")`?** Por defecto van sempre ao primario (o contedor `0481586c62c5`, que é `mongo1`). Despois de poñer `setReadPref("secondary")`, a consulta pasou a responderlla un nodo secundario (`9a7489121a0f`).
* **Que vantaxe e que risco ten ler dos secundarios?** A vantaxe é que repartes as lecturas entre varios nodos e lle quitas carga ao primario. O risco é que podas ler datos un pouco atrasados se acaba de haber un cambio no primario e aínda non lle deu tempo a copiarse ao secundario.

---

### A4. Cae o primario

Paramos o primario (`mongo1`) e miramos o estado desde `mongo2`:

```bash
docker compose stop mongo1
docker compose exec mongo2 mongosh --quiet /scripts/estado.js
```

Saída:

```text
[+] stop 1/1
 ✔ Container e3-mongodb-mongo1-1 Stopped                               3.2s

mongo1:27017   (not reachable/healthy) saúde: 0
mongo2:27017   PRIMARY      saúde: 1
mongo3:27017   SECONDARY    saúde: 1
```

Conectámonos ao replica set e inserimos unha ficha nova:

```bash
docker compose exec mongo2 mongosh "mongodb://mongo1,mongo2,mongo3/?replicaSet=rs0"
```

Saída:

```text
rs0 [primary] test> use albergues
switched to db albergues
rs0 [primary] albergues> db.fichas.insertOne({ albergue_id: 7, nome: "Albergue San Marcos", concello: "Santiago", camino: "Francés", prazas: 50 })
{
  acknowledged: true,
  insertedId: ObjectId('6aec112254736530ca842c5e')
}
```

Volvemos arrancar `mongo1`, miramos o seu estado e comprobamos se ten a ficha nova:

```bash
docker compose start mongo1
docker compose exec mongo2 mongosh --quiet /scripts/estado.js
docker compose exec mongo1 mongosh
```

Saída:

```text
mongo1:27017   SECONDARY    saúde: 1
mongo2:27017   PRIMARY      saúde: 1
mongo3:27017   SECONDARY    saúde: 1

rs0 [direct: secondary] test> use albergues
switched to db albergues
rs0 [direct: secondary] albergues> db.fichas.countDocuments()
7
rs0 [direct: secondary] albergues> db.fichas.findOne({ albergue_id: 7 })
{
  _id: ObjectId('6aec112254736530ca842c5e'),
  albergue_id: 7,
  nome: 'Albergue San Marcos',
  concello: 'Santiago',
  camino: 'Francés',
  prazas: 50
}
```

**Respostas A4:**
* **Cantos segundos tardou aproximadamente?** Tardou uns 3 segundos (o mesmo que tardou en facerse o `docker compose stop`), xa que nada máis executar `estado.js` xa saía `mongo2` como primario. (Se caese de golpe sen avisar tardaría uns 10 segundos en darse conta).
* **Funciona a inserción?** Si, funciona sen problema porque o cliente detecta que agora o primario é `mongo2`.
* **Que papel ten `mongo1` ao volver? Ten a ficha que inseriches mentres estaba parado?** Ao volver queda como `SECONDARY`. Si que ten a ficha 7 (hai 7 documentos en total) porque ao arrancar copiou os cambios que lle faltaban desde o novo primario.

**Táboa comparativa:**

| | PostgreSQL (E2) | Redis + Sentinel | MongoDB |
| :--- | :--- | :--- | :--- |
| **Quen detecta a caída** | Unha persoa | Os Sentinels | Os propios nodos |
| **Quen decide o novo primario** | Unha persoa (con `promote`) | Quórum de Sentinels | Votación con maioría |
| **Como se entera o cliente** | Cambiando a configuración | Pregunta aos Sentinels | O driver descóbreo só |
| **Papel do vello primario ao volver** | Dous primarios | Réplica | Secundario |

---

### A5. Caen dous nodos

Ao probar primeiro con `docker compose stop mongo2 mongo3`, ao intentar conectar ao replica set daba o erro `getaddrinfo ENOTFOUND mongo2` porque Docker non atopaba o contedor parado, e ademais sen primario o `mongosh` quedaba colgado 30 segundos (`Server selection timed out`) intentando buscar un primario para entrar. Por iso deixamos unha consola aberta e usamos `pause`:

```bash
docker compose pause mongo2 mongo3
docker compose exec mongo1 mongosh --quiet /scripts/estado.js
```

Saída:

```text
[+] pause 2/2
 ✔ Container e3-mongodb-mongo2-1 Paused                                0.0s
 ✔ Container e3-mongodb-mongo3-1 Paused                                0.0s

mongo1:27017   SECONDARY    saúde: 1
mongo2:27017   (not reachable/healthy) saúde: 0
mongo3:27017   (not reachable/healthy) saúde: 0
```

Intentamos inserir directamente en `mongo1`:

```bash
docker compose exec mongo1 mongosh
```

Saída:

```text
rs0 [direct: secondary] test> use albergues
switched to db albergues
rs0 [direct: secondary] albergues> db.fichas.insertOne({ albergue_id: 8, nome: "Albergue Sen Maioria" })
MongoServerError[NotWritablePrimary]: not primary
```

Agora, na consola conectada ao replica set, intentamos inserir, ler normal e ler cambiando a `primaryPreferred`:

```text
rs0 [primary] albergues> db.fichas.insertOne({ albergue_id: 8, nome: "Albergue Sen Maioria" })
Uncaught:
MongoServerSelectionError: connection <monitor> to 172.20.0.2:27017 timed out
rs0 [secondary] albergues> db.fichas.findOne()
Uncaught:
MongoServerSelectionError: connection <monitor> to 172.20.0.2:27017 timed out
rs0 [secondary] albergues> db.getMongo().setReadPref("primaryPreferred")

rs0 [secondary] albergues> db.fichas.findOne()
{
  _id: ObjectId('6aec0c338755e4b51b24fe75'),
  albergue_id: 1,
  nome: 'Albergue Pedra Miúda',
  concello: 'Sarria',
  camino: 'Francés',
  prazas: 32,
  servizos: [ 'cociña', 'lavadora', 'wifi' ],
  horario: { apertura: '13:00', peche: '22:30' },
  admite_cans: false,
  opinions: [ { autor: 'M.', nota: 5, texto: 'Moi limpo e tranquilo' } ]
}
```

Volvemos activar os nodos e comprobamos que se recupera:

```bash
docker compose unpause mongo2 mongo3
docker compose exec mongo1 mongosh --quiet /scripts/estado.js
```

Saída:

```text
mongo1:27017   SECONDARY    saúde: 1
mongo2:27017   SECONDARY    saúde: 1
mongo3:27017   PRIMARY      saúde: 1
```

**Respostas A5:**
* **Hai primario? Por que non hai primario aínda que un nodo funciona?** Non hai primario, `mongo1` ponse como `SECONDARY`. Isto pasa porque de 3 nodos a maioría son 2. Como só queda 1 nodo funcionando, non chega á maioría de votos para ser primario. Faise así por seguridade, para que nunca poida haber dous primarios á vez recibindo escrituras distintas se o que pasou foi un corte de rede.
* **Por que a lectura falla ou funciona segundo a preferencia de lectura?** Coa opción por defecto (`primary`), o cliente quere ler obrigatoriamente do primario, e como non hai ningún, dá erro. Ao poñer `primaryPreferred`, dicímoslle que se non hai primario nos deixe ler dun secundario, e como `mongo1` segue vivo, funciona.
* **Que pasaría se o replica set tivese 5 nodos e caesen 2?** Con 5 nodos a maioría é 3. Se caen 2 aínda quedan 3 nodos vivos, así que seguiría habendo maioría, elixirían un primario e todo seguiría funcionando normal (tanto ler como escribir).

---

### A6. Preguntas

* **Explica que é a "maioría" nun replica set e por que se usan números impares de nodos. Que papel xogaba o quórum nos Sentinels?**
  A maioría é o número mínimo de votos do total do grupo que fan falta para elixir un primario (a metade máis un). Por exemplo, se tes 5 nodos, a maioría é 3: se caen 2 nodos, aínda quedan 3 vivos que suman maioría e o sistema segue funcionando. Úsanse números impares porque cun número par non gañas tolerancia a fallos: con 4 nodos a maioría tamén é 3 (a metade máis un), así que só aguantas 1 caída igual que tendo 3 nodos, pero gastando un servidor máis sen necesidade. No caso concreto de ter 3 nodos e que caia 1, quedan 2 secundarios e necesitan 2 votos: isto funciona porque o primeiro que detecta a caída vótase a si mesmo e pídelle o voto ao segundo (que normalmente llo dá e xa suman os 2 votos). Se os dous detectasen o fallo xusto ao mesmo tempo e empatasen (1 a 1), cada nodo agarda un tempo aleatorio lixeiramente distinto antes de volver intentalo, para que un se adiante ao outro e non volver empatar. Nos Sentinels de Redis o quórum facía o mesmo papel: era o número mínimo de Sentinels que tiñan que estar de acordo en que o primario caeu para promover unha réplica.

* **En Redis, unha escritura confirmada polo primario pode perderse se este cae antes de copiala ás réplicas. Que significa `w: "majority"` en MongoDB e como evita ese problema?**
  Con `w: "majority"`, cando fas unha escritura, MongoDB non che confirma que se gardou ata que ese dato está copiado na maioría dos nodos (por exemplo, en 2 dos 3 nodos). Así, se o primario cae xusto despois, temos seguro que o novo primario que salga elixido xa ten ese dato gardado e non se perde nada.

* **Para o sistema de reservas, lerías as fichas dos albergues desde os secundarios? E a dispoñibilidade de prazas? Xustifícao.**
  * **Fichas dos albergues:** Si que as lería dos secundarios, porque os datos dun albergue (nome, dirección, servizos) case nunca cambian e dá igual se tardan uns segundos en actualizarse, e así quitámoslle traballo ao primario.
  * **Dispoñibilidade de prazas:** Non, isto leríao sempre do primario. Se dúas persoas reservan á vez e les dun secundario que vai un pouco atrasado, poderías venderlle a alguén unha praza que xa está ocupada.