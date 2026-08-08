CREATE TABLE IF NOT EXISTS costumers (
    costumer_id INTEGER     PRIMARY KEY,
    country     VARCHAR(60)
);

CREATE TABLE IF NOT EXISTS products (
    stock_code  VARCHAR(20) PRIMARY KEY,
    description VARCHAR(120)
);

CREATE TABLE IF NOT EXISTS transations (
    transation_id   SERIAL PRIMARY KEY,
    invoice         VARCHAR(12),
    costumer_id     INTEGER REFERENCES costumers(costumer_id),
    stock_code      VARCHAR(20) REFERENCES products(stock_code),
    quantity        INTEGER,
    unit_price      NUMERIC(10,2),
    invoice_date    TIMESTAMP,
    line_revenue    NUMERIC(12,2),
    is_cancellation BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_txn_costumer ON transations(costumer_id);
CREATE INDEX IF NOT EXISTS ix_txn_product ON transations(stock_code);
CREATE INDEX IF NOT EXISTS ix_txn_date ON transations(invoice_date);
