DELETE FROM visit;
DELETE FROM dog;
DELETE FROM owner;

ALTER SEQUENCE owner_owner_id_seq RESTART WITH 1;
ALTER SEQUENCE dog_dog_id_seq RESTART WITH 1;
ALTER SEQUENCE visit_visit_id_seq RESTART WITH 1;

SELECT * FROM owner;
SELECT * FROM dog;
SELECT * FROM visit;

INSERT INTO owner (name, locale, client_since, visit_count)
VALUES ();

INSERT INTO dog (
    owner_id,
    name,
    sex,
    handling_score,
    fear_triggers,
    two_person_job,
    temperament_notes,
    visit_count,
    avg_duration_min,
    last_visit_date
)
VALUES ();

INSERT INTO visit (
    dog_id,
    owner_id,
    visit_date,
    booked_service_id,
    actual_service_id,
    quoted_price,
    days_since_last,
    condition_score,
    shaved_down,
    pivoted,
    actual_minutes,
    behaviour_this_visit,
    status,
    what_surprised_me
)
VALUES ();

/* Check results */
SELECT
    (SELECT count(*) FROM owner) AS owners,
    (SELECT count(*) FROM dog) AS dogs,
    (SELECT count(*) FROM visit) AS visits;

SELECT v.visit_id, v.visit_date, v.actual_minutes, o.name AS owner_name, d.name AS dog_name
FROM visit v 
JOIN owner o ON o.owner_id = v.owner_id
JOIN dog d ON d.dog_id = v.dog_id;