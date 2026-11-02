-- Recipe: list seeded breeds (read-only), including species (#190).
-- See docs/runbooks/enrichment.md — "List breeds".
-- Run against local compose DB only.
-- Attach a breed_id only to a pet of the same species (API enforces this).

SELECT breed_id, species, name_de, name_en, base_groom_minutes, matting_risk
FROM breed
ORDER BY species, name_de;
