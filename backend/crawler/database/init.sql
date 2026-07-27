CREATE TABLE IF NOT EXISTS raw_tenders (id SERIAL PRIMARY KEY, source TEXT, raw_data JSONB, crawled_at TIMESTAMP DEFAULT now());
CREATE TABLE IF NOT EXISTS raw_awards (id SERIAL PRIMARY KEY, source TEXT, raw_data JSONB, crawled_at TIMESTAMP DEFAULT now());
CREATE TABLE IF NOT EXISTS raw_experience (id SERIAL PRIMARY KEY, source TEXT, raw_data JSONB, crawled_at TIMESTAMP DEFAULT now());
CREATE TABLE IF NOT EXISTS raw_app_packages (id SERIAL PRIMARY KEY, source TEXT, raw_data JSONB, crawled_at TIMESTAMP DEFAULT now());
CREATE TABLE IF NOT EXISTS raw_debarment (id SERIAL PRIMARY KEY, source TEXT, raw_data JSONB, crawled_at TIMESTAMP DEFAULT now());
CREATE TABLE IF NOT EXISTS raw_offline_tenders (id SERIAL PRIMARY KEY, source TEXT, raw_data JSONB, crawled_at TIMESTAMP DEFAULT now());
CREATE TABLE IF NOT EXISTS raw_offline_awards (id SERIAL PRIMARY KEY, source TEXT, raw_data JSONB, crawled_at TIMESTAMP DEFAULT now());

CREATE TABLE IF NOT EXISTS app_tender_link (
    id SERIAL PRIMARY KEY, app_id TEXT NOT NULL, pkg_id TEXT NOT NULL, app_package_no TEXT,
    tender_id TEXT, tender_reference_no TEXT, match_confidence NUMERIC, match_method TEXT,
    matched_at TIMESTAMP DEFAULT now(), UNIQUE (app_id, pkg_id, tender_id)
);

CREATE TABLE IF NOT EXISTS crawl_log (
    id SERIAL PRIMARY KEY, plugin TEXT, status TEXT, pages_done INT DEFAULT 0,
    items_done INT DEFAULT 0, error TEXT, started_at TIMESTAMP DEFAULT now(), finished_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tender_id ON raw_tenders ((raw_data->>'tender_id'));
CREATE INDEX IF NOT EXISTS idx_award_tender_id ON raw_awards ((raw_data->>'tender_id'));
CREATE INDEX IF NOT EXISTS idx_exp_tender_id ON raw_experience ((raw_data->>'tender_id'));
CREATE INDEX IF NOT EXISTS idx_app_pkg ON raw_app_packages ((raw_data->>'app_id'), (raw_data->>'pkg_id'));
CREATE INDEX IF NOT EXISTS idx_offline_tender_id ON raw_offline_tenders ((raw_data->>'tender_id'));
CREATE INDEX IF NOT EXISTS idx_offline_award_tender_id ON raw_offline_awards ((raw_data->>'tender_id'));
CREATE INDEX IF NOT EXISTS idx_link_tender ON app_tender_link (tender_id);