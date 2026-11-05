// Carga as fichas de albergues na base de datos "albergues".
// Execútase conectado ao replica set (vai sempre ao primario):
//   docker compose exec mongo1 mongosh "mongodb://mongo1,mongo2,mongo3/?replicaSet=rs0" /scripts/fichas.js
const albergues = db.getSiblingDB("albergues");
albergues.fichas.drop();

albergues.fichas.insertMany([
  {
    albergue_id: 1, nome: "Albergue Pedra Miúda", concello: "Sarria", camino: "Francés",
    prazas: 32, servizos: ["cociña", "lavadora", "wifi"],
    horario: { apertura: "13:00", peche: "22:30" }, admite_cans: false,
    opinions: [{ autor: "M.", nota: 5, texto: "Moi limpo e tranquilo" }]
  },
  {
    albergue_id: 2, nome: "Albergue O Fiadeiro", concello: "Portomarín", camino: "Francés",
    prazas: 24, servizos: ["wifi", "almorzo"],
    horario: { apertura: "12:00", peche: "22:00" },
    contacto: { telefono: "600000002", web: "fiadeiro.example" },
    opinions: []
  },
  {
    albergue_id: 3, nome: "Albergue Casa da Ponte", concello: "Palas de Rei", camino: "Francés",
    prazas: 40, servizos: ["cociña", "secadora", "bicicletario"],
    horario: { apertura: "13:00", peche: "23:00" }, admite_cans: true,
    opinions: [{ autor: "J.", nota: 4, texto: "Bo ambiente" }, { autor: "A.", nota: 3 }]
  },
  {
    albergue_id: 4, nome: "Albergue Vieiras", concello: "Melide", camino: "Francés",
    prazas: 28, servizos: ["cociña", "lavadora", "wifi", "almorzo"],
    horario: { apertura: "12:30", peche: "22:30" },
    accesible: { cadeira_rodas: true, ascensor: false }
  },
  {
    albergue_id: 5, nome: "Albergue Miñor", concello: "Tui", camino: "Portugués",
    prazas: 30, servizos: ["wifi"],
    horario: { apertura: "14:00", peche: "22:00" }, admite_cans: true,
    opinions: [{ autor: "P.", nota: 5, texto: "Hospitaleira encantadora" }]
  },
  {
    albergue_id: 6, nome: "Albergue Ría Viva", concello: "Redondela", camino: "Portugués",
    prazas: 22, servizos: ["cociña", "lavadora"],
    horario: { apertura: "13:00", peche: "22:30" },
    idiomas: ["galego", "castelán", "inglés", "portugués"]
  }
]);

print(`Fichas cargadas: ${albergues.fichas.countDocuments()}`);
