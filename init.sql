-- Nexus Trade Database Schema
-- Version: 1.0

-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    current_balance DECIMAL(20, 8) DEFAULT 10000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des données de marché
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour recherche rapide par temps
CREATE INDEX IF NOT EXISTS idx_market_data_time ON market_data(captured_at);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol);

-- Table des prédictions IA
CREATE TABLE IF NOT EXISTS ai_predictions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    predicted_trend VARCHAR(10) NOT NULL,
    confidence_score FLOAT,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_predictions_time ON ai_predictions(generated_at DESC);

-- Table des trades
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    symbol VARCHAR(20) NOT NULL,
    type VARCHAR(10) NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    profit DECIMAL(20, 8) DEFAULT 0,
    blockchain_hash VARCHAR(66),
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(user_id);
CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_type ON trades(type);

-- Insertion d'un utilisateur de démonstration
INSERT INTO users (email, password_hash, current_balance, created_at)
VALUES ('demo@nexustrade.com', 'demo_hash', 10000.0, NOW())
ON CONFLICT (email) DO NOTHING;

-- Fonction pour calculer les statistiques
CREATE OR REPLACE FUNCTION calculate_user_stats(user_id_param INTEGER)
RETURNS TABLE (
    total_trades BIGINT,
    total_profit DECIMAL,
    win_rate DECIMAL,
    avg_profit DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_trades,
        COALESCE(SUM(profit), 0) as total_profit,
        CASE 
            WHEN COUNT(*) > 0 THEN 
                (COUNT(CASE WHEN profit > 0 THEN 1 END)::DECIMAL / COUNT(*)::DECIMAL * 100)
            ELSE 0
        END as win_rate,
        CASE 
            WHEN COUNT(*) > 0 THEN COALESCE(AVG(profit), 0)
            ELSE 0
        END as avg_profit
    FROM trades
    WHERE user_id = user_id_param;
END;
$$ LANGUAGE plpgsql;

-- Vue pour les statistiques rapides
CREATE OR REPLACE VIEW trade_statistics AS
SELECT 
    u.id as user_id,
    u.email,
    COUNT(t.id) as total_trades,
    COALESCE(SUM(t.profit), 0) as total_profit,
    CASE 
        WHEN COUNT(t.id) > 0 THEN 
            (COUNT(CASE WHEN t.profit > 0 THEN 1 END)::DECIMAL / COUNT(t.id)::DECIMAL * 100)
        ELSE 0
    END as win_rate,
    MAX(t.executed_at) as last_trade_at
FROM users u
LEFT JOIN trades t ON u.id = t.user_id
GROUP BY u.id, u.email;

-- Logs
DO $$
BEGIN
    RAISE NOTICE '✅ Base de données Nexus Trade initialisée avec succès';
    RAISE NOTICE '   - Tables créées: users, market_data, ai_predictions, trades';
    RAISE NOTICE '   - Index créés pour performance optimale';
    RAISE NOTICE '   - Utilisateur demo créé: demo@nexustrade.com';
END$$;
