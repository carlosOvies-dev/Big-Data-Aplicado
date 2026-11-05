// Resumo do estado do replica set:
//   docker compose exec mongo2 mongosh --quiet /scripts/estado.js
rs.status().members.forEach(m =>
  print(`${m.name.padEnd(14)} ${m.stateStr.padEnd(12)} saúde: ${m.health}`)
);
