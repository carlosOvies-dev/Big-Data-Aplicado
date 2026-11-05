## Parte A. Copias de seguridade lóxicas 

### 1 Copia .env.example como .env e arranca só o primario: docker compose up -d primario.
```bash
carlosmaronoovies@026P238B:~/big_data_aplicado/E2_replicacion$ docker compose up -d primario
[+] up 3/3
 ✔ Network e2-replicacion_datos         Created                                                                     0.1s
 ✔ Volume e2-replicacion_datos_primario Created                                                                     0.0s
 ✔ Container e2-replicacion-primario-1  Started 
```
### 2 Fai unha copia da base de datos albergues en formato personalizado con pg_dump dentro do propio contedor
```bash
carlosmaronoovies@026P238B:~/big_data_aplicado/E2_replicacion$ docker compose exec primario pg_dump -U bda -Fc albergues -f /tmp/backup_albergues.dump
```
Comando para visualizar la copia de seguridad:
```bash
carlosmaronoovies@026P238B:~/big_data_aplicado/E2_replicacion$ docker compose exec primario ls -lh /tmp/backup_albergues.dump
```
 La salida es:
```text
-rw-r--r-- 1 root root 3.2K Oct 22 15:29 /tmp/backup_albergues.dump
```
### 3 Copia o ficheiro de backup fóra do contedor (docker cp ?)
```bash
carlosmaronoovies@026P238B:~/big_data_aplicado/E2_replicacion$ docker compose cp primario:/tmp/backup_albergues.dump .
[+] copy 1/1
 ✔ e2-replicacion-primario-1 Copied e2-replicacion-primario-1:/tmp/backup_albergues.dump to . 
```
### 4. Simula un desastre: elimina a táboa.

Mostrando la tabla:

```bash
carlosmaronoovies@026P238B:~/big_data_aplicado/E2_replicacion\$ docker compose exec primario psql -U bda -d albergues
```

```sql
psql (17.11 (Debian 17.11-1.pgdg13+2))
Type "help" for help.

albergues=# SELECT * FROM albergues;
 id |          nome          |   concello   |  camino   | prazas | prezo_noite
----+------------------------+--------------+-----------+--------+-------------
  1 | Albergue Pedra Miúda   | Sarria       | Francés   |     32 |       12.00
  2 | Albergue O Fiadeiro    | Portomarín   | Francés   |     24 |       13.50
  3 | Albergue Casa da Ponte | Palas de Rei | Francés   |     40 |       11.00
  4 | Albergue Vieiras       | Melide       | Francés   |     28 |       14.00
  5 | Albergue Miñor         | Tui          | Portugués |     30 |       10.00
  6 | Albergue Ría Viva      | Redondela    | Portugués |     22 |       12.00
(6 rows)
```

Eliminando la tabla:

```sql
albergues=# DROP TABLE albergues;
DROP TABLE
albergues=# SELECT * FROM albergues;
ERROR:  relation "albergues" does not exist
LINE 1: SELECT * FROM albergues;
                      ^
albergues=#
```

### 5. Restaura a copia: (pg_restore)

```bash
carlosmaronoovies@026P238B:~/big_data_aplicado/E2_replicacion\$ docker compose exec primario pg_restore -U bda -d albergues /tmp/backup_albergues.dump
```

### 6. Comproba que os seis albergues volven estar:

```bash
carlosmaronoovies@026P238B:~/big_data_aplicado/E2_replicacion\$ docker compose exec primario psql -U bda -d albergues
```

```sql
psql (17.11 (Debian 17.11-1.pgdg13+2))
Type "help" for help.

albergues=# SELECT * FROM albergues;
 id |          nome          |   concello   |  camino   | prazas | prezo_noite
----+------------------------+--------------+-----------+--------+-------------
  1 | Albergue Pedra Miúda   | Sarria       | Francés   |     32 |       12.00
  2 | Albergue O Fiadeiro    | Portomarín   | Francés   |     24 |       13.50
  3 | Albergue Casa da Ponte | Palas de Rei | Francés   |     40 |       11.00
  4 | Albergue Vieiras       | Melide       | Francés   |     28 |       14.00
  5 | Albergue Miñor         | Tui          | Portugués |     30 |       10.00
  6 | Albergue Ría Viva      | Redondela    | Portugués |     22 |       12.00
(6 rows)

albergues=#
```

### Pregunta
**A execución dos comandos, a comprobación final e a resposta a: se fixeras a copia ás 9:00 e o desastre ocorrese ás 13:00, que datos se perderían?**

Se perderían todos los datos registrados de las 9:00 en adelante.


## PARTE B. Primario e réplica

### 2. Estado da replicación. Executa no primario:

```bash
carlos@DESKTOP-7SI6S83:~/bigData_Aplicado/E2_replicacion\$ docker compose exec primario psql -U bda -d albergues
```

```sql
albergues=# SELECT client_addr, state, sync_state, replay_lag FROM pg_stat_replication;
 client_addr |   state   | sync_state | replay_lag
-------------+-----------+------------+------------
 172.19.0.3  | streaming | async      |
(1 row)
```

E na réplica (porto 5433, ou docker compose exec replica psql -U bda -d albergues):

```bash
carlos@DESKTOP-7SI6S83:~/bigData_Aplicado/E2_replicacion\$ docker compose exec replica psql -U bda -d albergues
```

```sql
psql (17.11 (Debian 17.11-1.pgdg13+2))
Type "help" for help.

albergues=# SELECT pg_is_in_recovery();
 pg_is_in_recovery
-------------------
 t
(1 row)
```

### 3. Os cambios viaxan. Insire un albergue novo no primario e consúltao na réplica.

Inserción:

```bash
carlos@DESKTOP-7SI6S83:~/bigData_Aplicado/E2_replicacion\$ docker compose exec primario psql -U bda -d albergues
```

```sql
psql (17.11 (Debian 17.11-1.pgdg13+2))
Type "help" for help.

albergues=# INSERT INTO albergues (id, nome, concello, camino, prazas, prezo_noite) VALUES (7, 'Albergue de Proba', 'Santiago', 'Francés', 50, 15.00);
INSERT 0 1
```

Consulta na réplica:

```bash
carlos@DESKTOP-7SI6S83:~/bigData_Aplicado/E2_replicacion\$ docker compose exec replica psql -U bda -d albergues
```

```sql
psql (17.11 (Debian 17.11-1.pgdg13+2))
Type "help" for help.

albergues=# SELECT * FROM albergues;
 id |          nome          |   concello   |  camino   | prazas | prezo_noite
----+------------------------+--------------+-----------+--------+-------------
  1 | Albergue Pedra Miúda   | Sarria       | Francés   |     32 |       12.00
  2 | Albergue O Fiadeiro    | Portomarín   | Francés   |     24 |       13.50
  3 | Albergue Casa da Ponte | Palas de Rei | Francés   |     40 |       11.00
  4 | Albergue Vieiras       | Melide       | Francés   |     28 |       14.00
  5 | Albergue Miñor         | Tui          | Portugués |     30 |       10.00
  6 | Albergue Ría Viva      | Redondela    | Portugués |     22 |       12.00
  7 | Albergue de Proba      | Santiago     | Francés   |     50 |       15.00
(7 rows)
```

### 4. A réplica é só de lectura. Intenta inserir un albergue na réplica. Que erro dá?

```sql
ERROR:  cannot execute INSERT in a read-only transaction
```

### 5. Unha réplica non é unha copia. Executa no primario DELETE FROM albergues WHERE camino = 'Portugués'; e consulta a réplica.

Borrado:

```bash
carlos@DESKTOP-7SI6S83:~/bigData_Aplicado/E2_replicacion\$ docker compose exec primario psql -U bda -d albergues
```

```sql
psql (17.11 (Debian 17.11-1.pgdg13+2))
Type "help" for help.

albergues=# DELETE FROM albergues WHERE camino = 'Portugués';
DELETE 2
```

Consulta:

```bash
carlos@DESKTOP-7SI6S83:~/bigData_Aplicado/E2_replicacion\$ docker compose exec replica psql -U bda -d albergues
```

```sql
psql (17.11 (Debian 17.11-1.pgdg13+2))
Type "help" for help.

albergues=# SELECT * FROM albergues;
 id |          nome          |   concello   | camino  | prazas | prezo_noite
----+------------------------+--------------+---------+--------+-------------
  1 | Albergue Pedra Miúda   | Sarria       | Francés |     32 |       12.00
  2 | Albergue O Fiadeiro    | Portomarín   | Francés |     24 |       13.50
  3 | Albergue Casa da Ponte | Palas de Rei | Francés |     40 |       11.00
  4 | Albergue Vieiras       | Melide       | Francés |     28 |       14.00
  7 | Albergue de Proba      | Santiago     | Francés |     50 |       15.00
(5 rows)
```

**Que pasou?** 
Os albergues do camiño 'Portugués' tamén desapareceron na réplica. A replicación é en tempo real.

**Como recuperarías os datos?**
A única forma de recuperalos é restaurando unha copia de seguridade que fose creada antes do borrado.
## PARTE C. Cae o primario 
 
### 1. Para o primario: docker compose stop primario.

```bash
carlos@DESKTOP-7SI6S83:~/bigData_Aplicado/E2_replicacion\$ docker compose stop primario
[+] stop 1/1
 ✔ Container e2-replicacion-primario-1 Stopped  
```

### 2. Comproba que a réplica segue respondendo a consultas de lectura.

```bash
carlos@DESKTOP-7SI6S83:~/bigData_Aplicado/E2_replicacion\$ docker compose exec replica psql -U bda -d albergues
```

```sql
psql (17.11 (Debian 17.11-1.pgdg13+2))
Type "help" for help.

albergues=# SELECT * FROM albergues;
 id |          nome          |   concello   | camino  | prazas | prezo_noite
----+------------------------+--------------+---------+--------+-------------
  1 | Albergue Pedra Miúda   | Sarria       | Francés |     32 |       12.00
  2 | Albergue O Fiadeiro    | Portomarín   | Francés |     24 |       13.50
  3 | Albergue Casa da Ponte | Palas de Rei | Francés |     40 |       11.00
  4 | Albergue Vieiras       | Melide       | Francés |     28 |       14.00
  7 | Albergue de Proba      | Santiago     | Francés |     50 |       15.00
(5 rows)
```

### 3. Intenta escribir na réplica: 

```sql
albergues=# INSERT INTO albergues (id, nome, concello, camino, prazas, prezo_noite) VALUES (8, 'Albergue de Emerxencia', 'Santiago', 'Francés', 20, 10.00);
ERROR:  cannot execute INSERT in a read-only transaction
albergues=#
```

**segue sendo de só lectura?**
Si.

### 4. Promove a réplica a primario: SELECT pg_promote();

```sql
albergues=# SELECT pg_promote();
 pg_promote
------------
 t
(1 row)
```

### 5. Comproba que agora pg_is_in_recovery() devolve f e que xa podes inserir

```sql
albergues=# SELECT pg_is_in_recovery();
 pg_is_in_recovery
-------------------
 f
(1 row)
```

Probando a insetar:

```sql
albergues=# INSERT INTO albergues (id, nome, concello, camino, prazas, prezo_noite) VALUES (8, 'Albergue de Emerxencia', 'Santiago', 'Francés', 20, 10.00);
INSERT 0 1
albergues=# SELECT * FROM albergues;
 id |          nome          |   concello   | camino  | prazas | prezo_noite
----+------------------------+--------------+---------+--------+-------------
  1 | Albergue Pedra Miúda   | Sarria       | Francés |     32 |       12.00
  2 | Albergue O Fiadeiro    | Portomarín   | Francés |     24 |       13.50
  3 | Albergue Casa da Ponte | Palas de Rei | Francés |     40 |       11.00
  4 | Albergue Vieiras       | Melide       | Francés |     28 |       14.00
  7 | Albergue de Proba      | Santiago     | Francés |     50 |       15.00
  8 | Albergue de Emerxencia | Santiago     | Francés |     20 |       10.00
(6 rows)
```

### 6. Arranca de novo o antigo primario (docker compose start primario) e insire unha fila distinta en cada servidor.

Insert en el antiguo primario:

```bash
carlos@DESKTOP-7SI6S83:~/bigData_Aplicado/E2_replicacion\$ docker compose exec primario psql -U bda -d albergues
```

```sql
psql (17.11 (Debian 17.11-1.pgdg13+2))
Type "help" for help.

albergues=# INSERT INTO albergues (id, nome, concello, camino, prazas, prezo_noite) VALUES (9, 'Albergue Antigo', 'Melide', 'Francés', 15, 12.00);
INSERT 0 1
```

Select antiguo primario:

```sql
albergues=# SELECT * FROM albergues;
 id |          nome          |   concello   | camino  | prazas | prezo_noite
----+------------------------+--------------+---------+--------+-------------
  1 | Albergue Pedra Miúda   | Sarria       | Francés |     32 |       12.00
  2 | Albergue O Fiadeiro    | Portomarín   | Francés |     24 |       13.50
  3 | Albergue Casa da Ponte | Palas de Rei | Francés |     40 |       11.00
  4 | Albergue Vieiras       | Melide       | Francés |     28 |       14.00
  7 | Albergue de Proba      | Santiago     | Francés |     50 |       15.00
  9 | Albergue Antigo        | Melide       | Francés |     15 |       12.00
(6 rows)
```

Insert en replica (actual primario):

```bash
carlos@DESKTOP-7SI6S83:~/bigData_Aplicado/E2_replicacion\$ docker compose exec replica psql -U bda -d albergues
```

```sql
psql (17.11 (Debian 17.11-1.pgdg13+2))
Type "help" for help.

albergues=# INSERT INTO albergues (id, nome, concello, camino, prazas, prezo_noite) VALUES (10, 'Albergue Novo', 'Arzúa', 'Francés', 20, 14.00);
INSERT 0 1
```

Select en replica:

```sql
albergues=# SELECT * FROM albergues;
 id |          nome          |   concello   | camino  | prazas | prezo_noite
----+------------------------+--------------+---------+--------+-------------
  1 | Albergue Pedra Miúda   | Sarria       | Francés |     32 |       12.00
  2 | Albergue O Fiadeiro    | Portomarín   | Francés |     24 |       13.50
  3 | Albergue Casa da Ponte | Palas de Rei | Francés |     40 |       11.00
  4 | Albergue Vieiras       | Melide       | Francés |     28 |       14.00
  7 | Albergue de Proba      | Santiago     | Francés |     50 |       15.00
  8 | Albergue de Emerxencia | Santiago     | Francés |     20 |       10.00
 10 | Albergue Novo          | Arzúa        | Francés |     20 |       14.00
(7 rows)
```

### Preguntas

**Que problema hai agora que os dous servidores aceptan escrituras?**
Cada base de datos va por libre, no estan sincronizadas y pierden datos, cada uno registra un dato diferente.

**Que tería que pasar para que o antigo primario volvese ser unha réplica do novo?**
Borrarle los datos, hacerle un volcado desde el actual primario para que tengan lo mismo y despues configurarlo para que sea una replica.

**Durante canto tempo non se puideron facer reservas?** 
Desde que apagamos el primero hasta que promovimos el secundario a primario.

**De que dependeu?**
Del tiempo que el administrador tarde en promover la replica a primario de forma manual.


## Parte D. Preguntas finais

### 1. A replicación é asíncrona. Que dato poderiamos perder se o primario cae xusto despois de confirmar unha reserva?
Si se cae antes de que el dato se envie a la replica, se perderia esa reserva, aunque el usuario crea que la hizo.

### 2. Por que necesitamos copias de seguridade e réplicas? Pon un exemplo de problema que só resolve cada unha.
Las copias de seguridad nos salvan de errores humanos como que alguien borre algo de la base de datos por accidente.
Las replicas nos sirven por fallos tecnicos. Si se cae un servidor por ejemplo, gracias a la replica podemos seguir trabajando y no tenemos que dejar de aceptar reservas, asi la empresa sigue funcionando sin interrupciones largas.

### 3. Que fai a opción -R de pg_basebackup no script da réplica?
Sirve para que el contenedor actue como replica, y guarda automaticamente los datos de conexion para que sepa cual es su servidor principal.

### 4. Por que o usuario replicador necesita unha liña específica en pg_hba.conf?
Porque ese archivo es como el portero, decide quien entra y quien no. Como la replica es un tipo de conexion especial, el usuario necesita permisos específicos de replicación para que el servidor principal le deje conectarse.