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

CREATE TABLE IF NOT EXISTS customers (
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
