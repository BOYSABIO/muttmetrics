-- Recipe: enrich owner contact / notes (hand-entered columns only).
-- See docs/ops-enrichment.md — "Enrich an owner".
-- Do NOT set visit_count, neglect_rate, lifetime_value, etc.

-- ---------------------------------------------------------------------------
-- 1) Inspect
-- ---------------------------------------------------------------------------
SELECT owner_id, name, phone, email, address_area, preferred_channel, client_since, notes, locale
FROM owner
WHERE owner_id = 123;   -- <-- placeholder owner_id

-- ---------------------------------------------------------------------------
-- 2) UPDATE — comment out lines you do not want to change
-- ---------------------------------------------------------------------------
BEGIN;

UPDATE owner
SET
  phone = '+49 170 0000000',       -- <-- placeholder
  email = 'client@example.com',    -- <-- placeholder
  address_area = 'Example area',
  preferred_channel = 'whatsapp',  -- free text for now
  notes = 'Example maintainer note',
  client_since = DATE '2026-01-01',
  locale = 'de'
WHERE owner_id = 123;

-- ---------------------------------------------------------------------------
-- 3) Verify
-- ---------------------------------------------------------------------------
SELECT owner_id, name, phone, email, address_area, preferred_channel, client_since, notes, locale
FROM owner
WHERE owner_id = 123;

COMMIT;
