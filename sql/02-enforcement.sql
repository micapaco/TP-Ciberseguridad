-- ============================================
-- Migración: campos de enforcement en ip_blacklist
-- Distingue "intención de bloqueo" de "bloqueo aplicado realmente"
-- ============================================

ALTER TABLE ip_blacklist
    ADD COLUMN IF NOT EXISTS enforced            BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS enforcement_message TEXT,
    ADD COLUMN IF NOT EXISTS enforced_at         TIMESTAMP;

-- Índice para filtrar por estado de enforcement
CREATE INDEX IF NOT EXISTS idx_ip_blacklist_enforced ON ip_blacklist(enforced);
