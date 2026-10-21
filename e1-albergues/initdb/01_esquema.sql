CREATE TABLE albergues (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    concello VARCHAR(100) NOT NULL,
    camino VARCHAR(100) NOT NULL,
    numero_prazas INT NOT NULL,
    prezo_noite DECIMAL(5,2) NOT NULL
);