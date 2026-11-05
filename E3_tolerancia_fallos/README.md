# Práctica E3: Tolerancia a Fallos e Alta Dispoñibilidade

Repositorio de traballo para o laboratorio de tolerancia a fallos en sistemas distribuídos de Big Data Aplicado.

## Estrutura do proxecto

* `parteA_mongodb/`: Configuración de Docker Compose e scripts de inicialización para un clúster de MongoDB 8.0 configurado como *Replica Set* (`rs0`) de 3 nodos.
* `parteB_garage/`: Laboratorio de almacenamento de obxectos distribuído con Garage *(pendente de publicación)*.
* `informe.md`: Documento de resultados, probas de caída (*failover*) e conclusións.

## Que se proba na Parte A (MongoDB Replica Set)?

1. ** despregamento do clúster:** Arranque de 3 contedores independentes (`mongo1`, `mongo2`, `mongo3`) conectados en rede interna e inicialización do *Replica Set*.
2. **Enrutamento do cliente:** Uso de cadeas de conexión con lista de sementes (*seed list*) para que o cliente localice automaticamente o nodo `PRIMARY` e carga inicial de datos de proba (fichas de albergues).
3. **Preferencias de lectura e escritura:** Comprobación do bloqueo de escrituras nos nodos `SECONDARY` e configuración de `readPreference` (`primary`, `secondary` e `primaryPreferred`) para repartir a carga de consultas.
4. **Simulación de caídas (*Failover*):**
   * Caída dun nodo primario e elección automática dun novo primario entre os secundarios restantes mantendo a sincronización mediante o *oplog*.
   * Caída simultánea de dous nodos (perda da maioría), verificando que o nodo supervivente pasa a modo só lectura (`SECONDARY`) para evitar situacións de *split-brain*.

## Comandos rápidos para levantar o contorno (Parte A)

```bash
cd parteA_mongodb
docker compose up -d
docker compose exec mongo1 mongosh /scripts/iniciar_rs.js
docker compose exec mongo1 mongosh --quiet /scripts/estado.js
```