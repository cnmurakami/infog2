--CREATE USER admin;
GRANT ALL PRIVILEGES ON DATABASE infog2 TO admin;

\c infog2;

CREATE TABLE IF NOT EXISTS roles (
    id  SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);


CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role_id SMALLINT DEFAULT 2,
    disabled BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

CREATE TABLE IF NOT EXISTS tokens (
    user_id  SERIAL,
    token VARCHAR(512) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expire_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(50) NOT NULL UNIQUE,
    cpf CHAR(11) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    description VARCHAR(50) NOT NULL,
    sell_value DECIMAL(9,2) NOT NULL UNIQUE,
    barcode varchar(50) NOT NULL UNIQUE,
    section varchar(50) NOT NULL,
    initial_stock INT NOT NULL,
    expiration_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS images (
    product_id SERIAL NOT NULL,
    image bytea NOT NULL
);

-- ############# Sample data ##############
INSERT INTO roles (name)
VALUES 
    ('admin'),
    ('operator')
ON CONFLICT DO NOTHING;

INSERT INTO users (username, password_hash, role_id)
VALUES 
    ('jane', '$2b$12$kjRwFgBV.W7nKDkL0u./X.L43PA8uHstpmwK7kzxr3R7v2IoJgw2C', 2),
    ('john', '$2b$12$kjRwFgBV.W7nKDkL0u./X.L43PA8uHstpmwK7kzxr3R7v2IoJgw2C', 2),
    ('test_admin', '$2b$12$wc7m8.c8wa1eJrjEAdO3UODYqZkqhjeMln1bfpDuBKWCMb0GNcv8G', 1),
    ('test_op', '$2b$12$wc7m8.c8wa1eJrjEAdO3UODYqZkqhjeMln1bfpDuBKWCMb0GNcv8G', 2)
ON CONFLICT DO NOTHING;

INSERT INTO clients (name, email, cpf)
VALUES 
    ('Laurence Howe', 'laurence.howe@gmail.com', '59375349055'),
    ('Wilda Gonzales', 'wilda.gonzales@gmail.com', '48323442002'),
    ('Eunice Shaw', 'eunice.shaw@gmail.com', '03852022029'),
    ('Susanne Wiley', 'susanne.wiley@gmail.com', '47835775018'),
    ('Nadine Curtis', 'nadine.curtis@gmail.com', '37030645014'),
    ('Bertram Stout', 'bertram.stout@gmail.com', '44472348071'),
    ('Juliet Rose', 'juliet.rose@gmail.com', '43928752022'),
    ('Edna Richardson', 'edna.richardson@gmail.com', '73357692058'),
    ('Fidel Sims', 'fidel.sims@gmail.com', '94674422051'),
    ('Angela Watts', 'angela.watts@gmail.com', '73316617019'),
    ('Edgardo Hutchinson', 'edgardo.hutchinson@gmail.com', '88005312024'),
    ('Christine Melton', 'christine.melton@gmail.com', '38245691089'),
    ('Francesco Perez', 'francesco.perez@gmail.com', '21364817039'),
    ('Vicente Cameron', 'vicente.cameron@gmail.com', '11860140084'),
    ('Randall Diaz', 'randall.diaz@gmail.com', '67979436040'),
    ('Shelton Campbell', 'shelton.campbell@gmail.com', '38392023021'),
    ('Sergio Mccullough', 'sergio.mccullough@gmail.com', '32178708080'),
    ('Clay Marsh', 'clay.marsh@gmail.com', '27477631025'),
    ('Nina Hale', 'nina.hale@gmail.com', '35018758007'),
    ('Milagros Odom', 'milagros.odom@gmail.com', '94697433009'),
    ('Eldridge Elliott', 'eldridge.elliott@gmail.com', '57772182023'),
    ('Tracie Rogers', 'tracie.rogers@gmail.com', '48443592079'),
    ('Mamie Bradshaw', 'mamie.bradshaw@gmail.com', '73094293034'),
    ('Darell Short', 'darell.short@gmail.com', '51528234030'),
    ('Linwood Abbott', 'linwood.abbott@gmail.com', '09279198009')
ON CONFLICT DO NOTHING;
