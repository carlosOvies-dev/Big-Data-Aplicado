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

---

## Parte B: Almacenamento de obxectos con Garage

### B1–B3. Clúster de tres nodos, layout, bucket e primeiros datos

Iniciamos os tres contedores:

```bash
docker compose up -d
```

Ao principio, ao facer `garage status`, o nodo `garage1` só se vía a si mesmo. Tivemos que sacar o ID dos outros dous nodos con `node id` e conectalos manualmente con `node connect`. Unha vez conectados, asignamos a cada nodo a súa zona e 1 GB de capacidade, e aplicamos o layout:

```bash
docker compose exec garage1 /garage status
docker compose exec garage1 /garage layout assign -z zona1 -c 1G f94e3b909dda480d
docker compose exec garage1 /garage layout assign -z zona2 -c 1G 1d4a63cefcbef300
docker compose exec garage1 /garage layout assign -z zona3 -c 1G 62ba284db8ba7f32
docker compose exec garage1 /garage layout apply --version 1
```

Saída de `garage status`:

```text
==== HEALTHY NODES ====
ID                Hostname      Address           Tags  Zone   Capacity   DataAvail          Version
1d4a63cefcbef300  b3d0a293f632  172.28.0.12:3901  []    zona2  953.7 MiB  950.3 GiB (94.4%)  v2.4.1
62ba284db8ba7f32  1ea2a9e64ec7  172.28.0.13:3901  []    zona3  953.7 MiB  950.3 GiB (94.4%)  v2.4.1
f94e3b909dda480d  e12ed13a2952  172.28.0.11:3901  []    zona1  953.7 MiB  950.3 GiB (94.4%)  v2.4.1
```

Despois creamos o bucket `albergues-docs`, a clave `e3-clave`, démoslle permisos e puxemos as variables de contorno para subir e verificar os primeiros 20 documentos co script `s3_proba.py`:

```text
Subidos 20 obxectos de 512 KB en 0.8 s (reserva_0001 a reserva_0020). O manifesto ten 20.
Bucket albergues-docs: 20 obxectos, 10.5 MB
Verificados: 20 correctos · 0 corruptos · 0 sen poder descargar
```

---

### B4. Cae un nodo

Paramos o nodo 3 (`garage3`) e probamos a verificar, subir 5 documentos máis e mirar o estado:

```bash
docker compose stop garage3
python s3_proba.py verificar
python s3_proba.py subir --n 5
docker compose exec garage1 /garage status
```

Saída:

```text
Erro ao descargar reservas/2026/reserva_0001.pdf: ReadTimeoutError...
Verificados: 16 correctos · 0 corruptos · 4 sen poder descargar
Subidos 5 obxectos de 512 KB en 0.1 s (reserva_0021 a reserva_0025). O manifesto ten 25.

==== HEALTHY NODES ====
ID                Hostname      Address           Tags  Zone   Capacity   DataAvail          Version
1d4a63cefcbef300  b3d0a293f632  172.28.0.12:3901  []    zona2  953.7 MiB  950.2 GiB (94.4%)  v2.4.1
f94e3b909dda480d  e12ed13a2952  172.28.0.11:3901  []    zona1  953.7 MiB  950.2 GiB (94.4%)  v2.4.1

==== FAILED NODES ====
ID                Hostname      Tags  Zone   Capacity   Last seen
62ba284db8ba7f32  1ea2a9e64ec7  []    zona3  953.7 MiB  1 minute ago
```

**Respostas B4:**
* **Funciona a verificación e a subida? Que mostra `garage status`?** Nada máis parar `garage3`, os primeiros 4 ficheiros deron erro de timeout mentres `garage1` non se daba conta de que o nodo 3 caera. En canto o detectou e o pasou á lista de `FAILED NODES`, o resto da verificación (16 ficheiros) e a subida dos 5 ficheiros novos (`reserva_0021` a `reserva_0025`, quedando 25 en total) funcionaron sen problema, porque cos nodos 1 e 2 activos séguese cumprindo a maioría (2 de 3). Se volvemos executar `verificar` uns segundos despois, xa dan os 25 correctos.

---

### B5. Caen dous nodos

Paramos tamén o nodo 2 (`garage2`), deixando só `garage1` acendido, e intentamos verificar:

```bash
docker compose stop garage2
python s3_proba.py verificar
```

Saída:

```text
Erro ao descargar reservas/2026/reserva_0001.pdf: ClientError: An error occurred (ServiceUnavailable) when calling the GetObject operation (reached max retries: 1): Internal error: Could not reach quorum of 2 (sets=None). 1 of 3 request succeeded, others returned errors: ["Network error: Not connected: 62ba284db8ba7f32", "Network error: Not connected: 1d4a63cefcbef300"]
Verificados: 0 correctos · 0 corruptos · 25 sen poder descargar
```

Volvemos arrancar os nodos 2 e 3 e verificamos outra vez:

```bash
docker compose start garage2 garage3
python s3_proba.py verificar
```

Saída:

```text
Verificados: 25 correctos · 0 corruptos · 0 sen poder descargar
```

**Respostas B5:**
* **Explicación co concepto de quórum:** Como temos configurado `replication_factor = 3`, Garage garda 3 copias e necesita un quórum de maioría (2 de 3 nodos) tanto para ler como para escribir datos. Cando cae un nodo seguen quedando 2 vivos e todo funciona, pero ao caer dous nodos só queda 1 activo, polo que non se chega ao quórum de 2 e non deixa nin ler nin escribir ata que volven arrancar.
* **Comparación con MongoDB Replica Set e Redis Sentinel:**
  * **MongoDB:** Tamén usa unha maioría de 2 de 3 nodos, pero ten un **nodo primario**. Se cae 1 nodo elíxese primario e pódese ler e escribir; se caen 2 nodos, o que queda pasa a `SECONDARY` e bloquea as escrituras, pero a diferenza de Garage aínda nos deixaba ler localmente cambiando a preferencia a `secondary` ou `primaryPreferred`.
  * **Redis Sentinel:** Tamén usa quórum entre os Sentinels para decidir se o primario caeu e subir unha réplica, pero a copia de datos en Redis é asíncrona e as lecturas non piden quórum. En cambio, en Garage non hai primario (todos os nodos son iguais) e o quórum pídese directamente en cada lectura e escritura.

---

### B6. Perda dun disco

Miramos canto ocupa o volume de datos do nodo 3 antes de borralo:

```bash
docker run --rm -v e3-garage_garage3_datos:/d alpine du -sh /d
```

Saída:

```text
12.8M   /d
```

Paramos `garage3`, borramos o seu volume de datos para simular que rompeu o disco, volvemos arrancalo e miramos o tamaño do disco novo:

```bash
docker compose stop garage3
docker volume rm e3-garage_garage3_datos
docker compose up -d garage3
docker run --rm -v e3-garage_garage3_datos:/d alpine du -sh /d
```

Saída:

```text
64.0K   /d
```

Agora verificamos os ficheiros conectándonos directamente ao porto do nodo 3 (`3920`):

```bash
python s3_proba.py verificar --porto 3920
```

Saída:

```text
Verificados: 25 correctos · 0 corruptos · 0 sen poder descargar
```

Lanzamos a reparación dos bloques en `garage3` e volvemos mirar o tamaño do disco pasados uns segundos:

```bash
docker compose exec garage3 /garage repair --yes blocks
docker run --rm -v e3-garage_garage3_datos:/d alpine du -sh /d
```

Saída:

```text
12.8M   /d
```

**Respostas B6:**
* **Seguen os datos dispoñibles co disco baleiro? Por que?** Si, danse descargado os 25 ficheiros sen fallo. Isto pasa porque `garage3` mantivo o seu volume de metadatos (`garage3_meta`), así que segue sabendo que ficheiros existen e en que nodos están. Como no seu disco novo aínda non ten os bloques, pídeollos por rede a `garage1` e `garage2` e devólveos ao cliente. Despois, ao facer o `repair --yes blocks`, o nodo 3 descarga as copias que lle faltaban dos outros dous nodos e o disco volve ocupar os `12.8M`.

---

### B7. Preguntas

* **Calcula o espazo que ocupan 300 GB de documentos con cada sistema (réplica ×3 e erasure coding 4 + 2) e indica cantos fallos tolera cada un.**
  * **Réplica ×3 (Garage):** Como se gardan 3 copias enteiras de cada ficheiro, ocupa o triplo: $300\text{ GB} \times 3 = 900\text{ GB}$. Aguanta que caian ata **2 nodos ou discos** á vez sen perder os datos (aínda que para operar en vivo pide quórum de 2).
  * **Erasure coding 4 + 2 (MinIO / Ceph):** Cada ficheiro párterase en 4 anacos de datos e calcúlanse 2 anacos extra de paridade (6 anacos en total por cada 4 de datos, é dicir, multiplícase por $6 / 4 = 1.5$). Polo tanto, ocupa: $300\text{ GB} \times 1.5 = 450\text{ GB}$ (a metade que a réplica ×3). Tamén aguanta a perda de ata **2 nodos ou discos** calquera sen perder datos grazas aos bloques de paridade.

* **Para que serve o `manifesto.json` que garda `s3_proba.py`? Que tipo de erros detectaría que Garage non vería?**
  Serve para gardar unha lista co nome de cada ficheiro subido e o seu hash `SHA-256` orixinal calculado no cliente antes de envialo. Ao descargar os ficheiros en `verificar`, o script volve calcular o `SHA-256` e compárao co do manifesto. Isto permite detectar se un ficheiro se corrompeu no propio cliente ou polo camiño antes de chegar a Garage, ou se alguén sobrescribiu un ficheiro no bucket por outro distinto: para Garage o ficheiro estaría "ben" porque gardaría os novos bloques sen erro, pero o noso `manifesto.json` avisaríanos de que o contido xa non coincide co orixinal.

* **Por que é importante que cada copia estea nunha zona distinta?**
  Porque unha zona representa unha separación física real (por exemplo, distinto servidor físico, distinto rack con distinto enchufe e switch, ou distinto centro de datos). Se puxésemos os 3 nodos na mesma zona (por exemplo, tres contedores ou máquinas virtuais dentro do mesmo servidor físico) e se queima a fonte de alimentación dese servidor ou cae ese switch, perderiamos as 3 copias de golpe e de nada serviría ter replicación ×3.