// Inicia o replica set rs0 cos tres nodos. Execútase unha soa vez:
//   docker compose exec mongo1 mongosh /scripts/iniciar_rs.js
rs.initiate({
  _id: "rs0",
  members: [
    { _id: 0, host: "mongo1:27017" },
    { _id: 1, host: "mongo2:27017" },
    { _id: 2, host: "mongo3:27017" }
  ]
});
print("Replica set iniciado. Agarda uns segundos e executa rs.status()");
