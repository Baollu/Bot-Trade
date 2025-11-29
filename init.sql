CREATE TABLE users (
       id SERIAL PRIMARY KEY,
       email VARCHAR(255) UNIQUE NOT NULL,
       password_hash VARCHAR(255) NOT NULL,
       current_balance DECIMAL(20, 8) DEFAULT 200,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE market_data (
     id SERIAL PRIMARY KEY,
     symbol VARCHAR(20) NOT NULL,
     price DECIMAL(20, 8) NOT NULL,
     captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_predictions (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL,
        predicted_trend VARCHAR(10) NOT NULL,
        confidence_score FLOAT,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE trades (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        symbol VARCHAR(20) NOT NULL,
        type VARCHAR(10) NOT NULL,
        price DECIMAL(20, 8) NOT NULL,
        quantity DECIMAL(20, 8) NOT NULL,
        profit DECIMAL(20, 8),
        blockchain_hash VARCHAR(66),
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ajoute un index sur la colonne de temps pour que les requêtes de l'IA soient instantanées
CREATE INDEX idx_market_data_time ON market_data(captured_at);

-- Ajoute un index sur le symbole si tu prévois de trader autre chose que du BTC plus tard
CREATE INDEX idx_market_data_symbol ON market_data(symbol);