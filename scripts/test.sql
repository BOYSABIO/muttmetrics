SELECT
  (SELECT count(*) FROM owner) AS owners,
  (SELECT count(*) FROM dog) AS dogs,
  (SELECT count(*) FROM visit) AS visits;


SELECT v.visit_id, v.visit_date, v.actual_minutes,
       o.name AS owner_name, d.name AS dog_name
FROM visit v
JOIN owner o ON o.owner_id = v.owner_id
JOIN dog d ON d.dog_id = v.dog_id
ORDER BY v.visit_id DESC
LIMIT 20;