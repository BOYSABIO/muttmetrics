SELECT
  (SELECT COUNT(*) FROM owner) AS owners,
  (SELECT COUNT(*) FROM dog) AS dogs,
  (SELECT COUNT(*) FROM visit) AS visits;

SELECT o.owner_id, o.name AS owner_name, d.dog_id, d.name AS dog_name
FROM owner o
LEFT JOIN dog d ON d.owner_id = o.owner_id
WHERE o.name ILIKE '%Capture%'
   OR o.name ILIKE '%Lesson%'
   OR o.name ILIKE 'Test Owner%'
   OR o.name ILIKE 'Flow Owner%'
   OR d.name ILIKE '%Capture%'
   OR d.name ILIKE 'BrowseDog%'
   OR d.name ILIKE 'Test Dog%'
   OR d.name ~* '^Bella[ 0-9a-f]{4,}$'
ORDER BY o.name, d.name;
