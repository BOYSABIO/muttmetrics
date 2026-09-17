-- Recipe: list seeded breeds (read-only).
-- See docs/ops-enrichment.md — "List breeds".
-- Run against local compose DB only.

SELECT breed_id, name_de, name_en, base_groom_minutes, matting_risk
FROM breed
ORDER BY name_de;
