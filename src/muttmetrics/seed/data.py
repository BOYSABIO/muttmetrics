"""Hand-encoded reference rows for cold start.

Service `price_base` values are FLOORS / placeholders from Sebastian (2026-09),
not fixed tariffs. Real charge lives on visit.quoted_price / final_price / tip.

Size bands (kg) live on dog.weight_kg → size_band — not as separate service SKUs:
  1–10 kg → s (€75+ full groom floor)
  11–26 kg → m (€85+)
  27–45 kg → l (€95+)
  46 kg+  → xl (€105+)

Relative minutes: nails < teeth < bath_trim < full_groom < de_mat.
Breed priors are domain guesses — edit and re-seed.
"""

SEED_SERVICES: list[dict] = [
    {
        "slug": "nails",
        "name_de": "Krallen",
        "name_en": "Nail trim",
        "base_minutes": 15,
        "buffer_minutes": 5,
        # Floor ~€5–10; often free if easy/quick (goodwill + tip on visit)
        "price_base": 5,
    },
    {
        "slug": "teeth",
        "name_de": "Zahnpflege",
        "name_en": "Teeth cleaning",
        "base_minutes": 25,
        "buffer_minutes": 10,
        # Floor ~€35–40; behaviour-dependent
        "price_base": 35,
    },
    {
        "slug": "bath_trim",
        "name_de": "Baden und Scheren",
        "name_en": "Bath and trim",
        "base_minutes": 50,
        "buffer_minutes": 15,
        # Often upgrades into full-groom territory by size/coat
        "price_base": 40,
    },
    {
        "slug": "full_groom",
        "name_de": "Vollpflege",
        "name_en": "Full groom",
        "base_minutes": 90,
        "buffer_minutes": 30,
        # Package: wash + trim + ears + teeth + nails. price_base = SMALL-dog floor.
        "price_base": 75,
    },
    {
        "slug": "de_mat",
        "name_de": "Entfilzen",
        "name_en": "De-mat",
        "base_minutes": 150,
        "buffer_minutes": 45,
        # Heavier than full groom; placeholder until Sebastian validates €
        "price_base": 100,
    },
]

# matting_risk: 1 (low) .. 5 (pelted / Doodle territory)
SEED_BREEDS: list[dict] = [
    {
        "name_en": "French Bulldog",
        "name_de": "Französische Bulldogge",
        "default_coat_type": "smooth",
        "default_hair_or_fur": "fur",
        "typical_size_band": "s",
        "base_groom_minutes": 40,
        "matting_risk": 1,
        "blows_coat": False,
        "recommended_interval_days": 56,
        "home_care_protocol": "Wipe folds; short coat — brushing optional.",
    },
    {
        "name_en": "Labrador Retriever",
        "name_de": "Labrador Retriever",
        "default_coat_type": "double",
        "default_hair_or_fur": "fur",
        "typical_size_band": "l",
        "base_groom_minutes": 60,
        "matting_risk": 2,
        "blows_coat": True,
        "recommended_interval_days": 70,
        "home_care_protocol": "Brush during shed season; bath as needed.",
    },
    {
        "name_en": "German Shepherd",
        "name_de": "Deutscher Schäferhund",
        "default_coat_type": "double",
        "default_hair_or_fur": "fur",
        "typical_size_band": "l",
        "base_groom_minutes": 75,
        "matting_risk": 2,
        "blows_coat": True,
        "recommended_interval_days": 70,
        "home_care_protocol": "Heavy seasonal shed — undercoat rake.",
    },
    {
        "name_en": "Poodle",
        "name_de": "Pudel",
        "default_coat_type": "curly",
        "default_hair_or_fur": "hair",
        "typical_size_band": "m",
        "base_groom_minutes": 100,
        "matting_risk": 4,
        "blows_coat": False,
        "recommended_interval_days": 42,
        "home_care_protocol": "Line brush every 2–3 days; never skip under ears/armpits.",
    },
    {
        "name_en": "Cockapoo",
        "name_de": "Cockapoo",
        "default_coat_type": "curly",
        "default_hair_or_fur": "hair",
        "typical_size_band": "s",
        "base_groom_minutes": 95,
        "matting_risk": 5,
        "blows_coat": False,
        "recommended_interval_days": 35,
        "home_care_protocol": "Daily brush; high de-mat risk if skipped.",
    },
    {
        "name_en": "Labradoodle",
        "name_de": "Labradoodle",
        "default_coat_type": "curly",
        "default_hair_or_fur": "hair",
        "typical_size_band": "l",
        "base_groom_minutes": 120,
        "matting_risk": 5,
        "blows_coat": False,
        "recommended_interval_days": 35,
        "home_care_protocol": "Daily brush; coat varies by generation — assume high mat risk.",
    },
    {
        "name_en": "Goldendoodle",
        "name_de": "Goldendoodle",
        "default_coat_type": "curly",
        "default_hair_or_fur": "hair",
        "typical_size_band": "l",
        "base_groom_minutes": 120,
        "matting_risk": 5,
        "blows_coat": False,
        "recommended_interval_days": 35,
        "home_care_protocol": "Daily brush; behind ears and armpits first.",
    },
    {
        "name_en": "Shih Tzu",
        "name_de": "Shih Tzu",
        "default_coat_type": "double",
        "default_hair_or_fur": "hair",
        "typical_size_band": "s",
        "base_groom_minutes": 90,
        "matting_risk": 4,
        "blows_coat": False,
        "recommended_interval_days": 35,
        "home_care_protocol": "Daily brush if long coat; face and ears carefully.",
    },
    {
        "name_en": "Yorkshire Terrier",
        "name_de": "Yorkshire Terrier",
        "default_coat_type": "single",
        "default_hair_or_fur": "hair",
        "typical_size_band": "xs",
        "base_groom_minutes": 75,
        "matting_risk": 3,
        "blows_coat": False,
        "recommended_interval_days": 42,
        "home_care_protocol": "Brush several times a week; fine hair tangles easily.",
    },
    {
        "name_en": "Maltese",
        "name_de": "Malteser",
        "default_coat_type": "single",
        "default_hair_or_fur": "hair",
        "typical_size_band": "xs",
        "base_groom_minutes": 80,
        "matting_risk": 4,
        "blows_coat": False,
        "recommended_interval_days": 35,
        "home_care_protocol": "Daily brush; keep coat clean and dry.",
    },
    {
        "name_en": "Mixed breed",
        "name_de": "Mischling",
        "default_coat_type": None,
        "default_hair_or_fur": None,
        "typical_size_band": "m",
        "base_groom_minutes": 75,
        "matting_risk": 3,
        "blows_coat": None,
        "recommended_interval_days": 49,
        "home_care_protocol": "Assess coat at first visit; fill dog-level coat fields.",
    },
]
