CREATE TABLE albergues (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(80)  NOT NULL,
    concello    VARCHAR(60)  NOT NULL,
    camino      VARCHAR(30)  NOT NULL,
    prazas      INTEGER      NOT NULL CHECK (prazas > 0),
    prezo_noite NUMERIC(5,2) NOT NULL
);

INSERT INTO albergues (nome, concello, camino, prazas, prezo_noite) VALUES
  ('Albergue Pedra Miúda',   'Sarria',         'Francés',   32, 12.00),
  ('Albergue O Fiadeiro',    'Portomarín',     'Francés',   24, 13.50),
  ('Albergue Casa da Ponte', 'Palas de Rei',   'Francés',   40, 11.00),
  ('Albergue Vieiras',       'Melide',         'Francés',   28, 14.00),
  ('Albergue Miñor',         'Tui',            'Portugués', 30, 10.00),
  ('Albergue Ría Viva',      'Redondela',      'Portugués', 22, 12.00);
