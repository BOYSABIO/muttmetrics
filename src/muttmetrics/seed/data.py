"""Hand-encoded reference rows for cold start.

Timing values (`base_minutes`, `buffer_minutes`) are domain estimates and are
the point of this file. Relative order: nails < teeth < bath_trim < full_groom < de_mat.

`price_base` is deliberately NULL here. Prices are the salon's commercial data and
must never be committed - see docs/architecture/privacy.md. Real floors are loaded at seed time
from `data/private/pricing.json` (gitignored); see `data/pricing.example.json` for
the shape. Real charge always lives on visit.quoted_price / final_price / tip.

Size bands (kg) live on dog.weight_kg -> size_band, not as separate service SKUs.

Breed priors are domain guesses - edit and re-seed.
"""

# Techniques / add-ons (#192). price_base NULL in git — optional overlay in
# pricing.json (same file as services; keyed by add-on slug).
SEED_ADD_ONS: list[dict] = [
    {
        "slug": "hand_stripping",
        "name_de": "Handstripping",
        "name_en": "Hand stripping",
        "pricing": "per_hour",
        "price_base": None,
    },
    {
        "slug": "de_shed",
        "name_de": "Unterwolle",
        "name_en": "De-shedding",
        "pricing": "flat",
        "price_base": None,
    },
    {
        "slug": "nail_grind",
        "name_de": "Krallen schleifen",
        "name_en": "Nail grinding",
        "pricing": "flat",
        "price_base": None,
    },
]

SEED_SERVICES: list[dict] = [
    {
        "slug": "nails",
        "name_de": "Krallen",
        "name_en": "Nail trim",
        "base_minutes": 15,
        "buffer_minutes": 5,
        "price_base": None,
    },
    {
        "slug": "teeth",
        "name_de": "Zahnpflege",
        "name_en": "Teeth cleaning",
        "base_minutes": 25,
        "buffer_minutes": 10,
        "price_base": None,
    },
    {
        "slug": "bath_trim",
        "name_de": "Baden und Scheren",
        "name_en": "Bath and trim",
        "base_minutes": 50,
        "buffer_minutes": 15,
        "price_base": None,
    },
    {
        "slug": "full_groom",
        "name_de": "Vollpflege",
        "name_en": "Full groom",
        "base_minutes": 90,
        "buffer_minutes": 30,
        "price_base": None,
    },
    {
        "slug": "de_mat",
        "name_de": "Entfilzen",
        "name_en": "De-mat",
        "base_minutes": 150,
        "buffer_minutes": 45,
        "price_base": None,
    },
]

# matting_risk: 1 (low) .. 5 (pelted / Doodle territory)
# typical_size_band is a catalog hint (s/m/l/xl, the same four bands as a pet's
# size; toy breeds are "s"). A pet's own size comes from its weight, or is
# picked by eye (pet-data.md). default_coat_type uses pet_vocab.py's lists.
SEED_BREEDS: list[dict] = [
    {
        "species": "dog",
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
        "species": "dog",
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
        "species": "dog",
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
        "species": "dog",
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
        "species": "dog",
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
        "species": "dog",
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
        "species": "dog",
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
        "species": "dog",
        "name_en": "Shih Tzu",
        "name_de": "Shih Tzu",
        "default_coat_type": "silky",
        "default_hair_or_fur": "hair",
        "typical_size_band": "s",
        "base_groom_minutes": 90,
        "matting_risk": 4,
        "blows_coat": False,
        "recommended_interval_days": 35,
        "home_care_protocol": "Daily brush if long coat; face and ears carefully.",
    },
    {
        "species": "dog",
        "name_en": "Yorkshire Terrier",
        "name_de": "Yorkshire Terrier",
        "default_coat_type": "silky",
        "default_hair_or_fur": "hair",
        "typical_size_band": "s",
        "base_groom_minutes": 75,
        "matting_risk": 3,
        "blows_coat": False,
        "recommended_interval_days": 42,
        "home_care_protocol": "Brush several times a week; fine hair tangles easily.",
    },
    {
        "species": "dog",
        "name_en": "Maltese",
        "name_de": "Malteser",
        "default_coat_type": "silky",
        "default_hair_or_fur": "hair",
        "typical_size_band": "s",
        "base_groom_minutes": 80,
        "matting_risk": 4,
        "blows_coat": False,
        "recommended_interval_days": 35,
        "home_care_protocol": "Daily brush; keep coat clean and dry.",
    },
    {
        "species": "dog",
        "name_en": "Mixed breed",
        "name_de": "Mischling",
        "default_coat_type": None,
        "default_hair_or_fur": None,
        "typical_size_band": "m",
        "base_groom_minutes": 75,
        "matting_risk": 3,
        "blows_coat": None,
        "recommended_interval_days": 49,
        "home_care_protocol": "Assess coat at first visit; fill pet-level coat fields.",
    },
    {
        "species": "cat",
        "name_en": "Domestic Short Hair",
        "name_de": "Hauskatze kurzhaar",
        "default_coat_type": "short",
        "default_hair_or_fur": "fur",
        "typical_size_band": "m",
        "base_groom_minutes": 45,
        "matting_risk": 2,
        "blows_coat": True,
        "recommended_interval_days": 56,
        "home_care_protocol": "Brush weekly; more in shed season.",
    },
    {
        "species": "cat",
        "name_en": "Domestic Long Hair",
        "name_de": "Hauskatze langhaar",
        "default_coat_type": "long",
        "default_hair_or_fur": "fur",
        "typical_size_band": "m",
        "base_groom_minutes": 70,
        "matting_risk": 3,
        "blows_coat": True,
        "recommended_interval_days": 49,
        "home_care_protocol": "Brush several times a week; check armpits and trousers.",
    },
    {
        "species": "cat",
        "name_en": "Persian",
        "name_de": "Perser",
        "default_coat_type": "long",
        "default_hair_or_fur": "fur",
        "typical_size_band": "m",
        "base_groom_minutes": 90,
        "matting_risk": 4,
        "blows_coat": False,
        "recommended_interval_days": 35,
        "home_care_protocol": "Daily brush; face and sanitary trim as needed.",
    },
    {
        "species": "cat",
        "name_en": "Maine Coon",
        "name_de": "Maine Coon",
        "default_coat_type": "long",
        "default_hair_or_fur": "fur",
        "typical_size_band": "l",
        "base_groom_minutes": 80,
        "matting_risk": 3,
        "blows_coat": True,
        "recommended_interval_days": 49,
        "home_care_protocol": "Brush the breeches and ruff; large cat, extra handling time.",
    },
    {
        "species": "cat",
        "name_en": "Mixed cat",
        "name_de": "Mischling (Katze)",
        "default_coat_type": None,
        "default_hair_or_fur": None,
        "typical_size_band": "m",
        "base_groom_minutes": 50,
        "matting_risk": 2,
        "blows_coat": None,
        "recommended_interval_days": 56,
        "home_care_protocol": "Assess coat at first visit; fill pet-level coat fields.",
    },
]


# --- More breeds (2026-11) ---------------------------------------------------
# Common salon breeds and crosses, so most dogs get a real breed instead of
# "Mixed breed". Minutes, matting risk and interval are STARTING GUESSES for
# a full groom (the rules prior, docs/prior.md), to be corrected by the groomer
# and later replaced by history (M7). Size uses the pricing bands by typical
# adult weight (priors/size.py: dog s <= 10 kg, m <= 26, l <= 45, xl above).
# Coat: pet_vocab.py. None where the breed comes in several coats (Dachshund,
# Jack Russell): the dog's own profile says which.

_HAIR_COATS = {"curly", "silky", "wire"}


def _breed(
    species: str,
    name_en: str,
    name_de: str,
    coat: str | None,
    size: str,
    minutes: int,
    matting: int,
    interval: int,
) -> dict:
    return {
        "species": species,
        "name_en": name_en,
        "name_de": name_de,
        "default_coat_type": coat,
        "default_hair_or_fur": (
            None if coat is None else ("hair" if coat in _HAIR_COATS else "fur")
        ),
        "typical_size_band": size,
        "base_groom_minutes": minutes,
        "matting_risk": matting,
        "blows_coat": coat == "double" or (species == "cat" and coat == "long"),
        "recommended_interval_days": interval,
        "home_care_protocol": None,
    }


SEED_BREEDS += [
    # Double coats: undercoat, shedding seasons, long drying
    _breed("dog", "Golden Retriever", "Golden Retriever", "double", "l", 90, 2, 56),
    _breed("dog", "Bernese Mountain Dog", "Berner Sennenhund", "double", "xl", 120, 3, 56),
    _breed("dog", "Australian Shepherd", "Australian Shepherd", "double", "m", 90, 3, 56),
    _breed("dog", "Border Collie", "Border Collie", "double", "m", 80, 3, 56),
    _breed("dog", "Rough Collie", "Langhaarcollie", "double", "l", 110, 4, 56),
    _breed("dog", "Shetland Sheepdog", "Sheltie", "double", "s", 80, 3, 49),
    _breed("dog", "Siberian Husky", "Siberian Husky", "double", "m", 100, 2, 70),
    _breed("dog", "Samoyed", "Samojede", "double", "m", 130, 4, 49),
    _breed("dog", "Pomeranian", "Zwergspitz", "double", "s", 70, 3, 42),
    _breed("dog", "German Spitz", "Deutscher Spitz", "double", "s", 75, 3, 49),
    _breed("dog", "Chow Chow", "Chow-Chow", "double", "m", 110, 4, 49),
    _breed("dog", "Newfoundland", "Neufundländer", "double", "xl", 150, 4, 56),
    _breed("dog", "Leonberger", "Leonberger", "double", "xl", 140, 4, 56),
    _breed("dog", "Hovawart", "Hovawart", "double", "l", 90, 3, 56),
    _breed("dog", "Old English Sheepdog", "Bobtail", "double", "l", 150, 5, 42),
    _breed("dog", "Pembroke Welsh Corgi", "Welsh Corgi Pembroke", "double", "m", 60, 2, 70),
    _breed("dog", "Shiba Inu", "Shiba Inu", "double", "s", 60, 2, 70),
    _breed("dog", "Pekingese", "Pekinese", "double", "s", 80, 4, 42),
    _breed("dog", "Rottweiler", "Rottweiler", "double", "l", 60, 1, 70),
    # Curly: keeps growing, mats, short intervals
    _breed("dog", "Miniature Poodle", "Zwergpudel", "curly", "s", 80, 4, 35),
    _breed("dog", "Toy Poodle", "Toypudel", "curly", "s", 70, 4, 35),
    _breed("dog", "Bichon Frise", "Bichon Frisé", "curly", "s", 90, 5, 35),
    _breed("dog", "Bolonka Zwetna", "Bolonka Zwetna", "curly", "s", 80, 4, 35),
    _breed("dog", "Maltipoo", "Maltipoo", "curly", "s", 85, 5, 35),
    _breed("dog", "Cavapoo", "Cavapoo", "curly", "s", 85, 5, 35),
    _breed("dog", "Bernedoodle", "Bernedoodle", "curly", "l", 130, 5, 35),
    _breed("dog", "Aussiedoodle", "Aussiedoodle", "curly", "m", 110, 5, 35),
    _breed("dog", "Portuguese Water Dog", "Portugiesischer Wasserhund", "curly", "m", 110, 4, 42),
    # Long & silky: keeps growing, mats behind ears and legs
    _breed("dog", "Havanese", "Havaneser", "silky", "s", 85, 4, 35),
    _breed("dog", "Lhasa Apso", "Lhasa Apso", "silky", "s", 90, 4, 35),
    _breed("dog", "Coton de Tulear", "Coton de Tuléar", "silky", "s", 90, 5, 35),
    # Wire: hand stripping or clipping
    _breed("dog", "Miniature Schnauzer", "Zwergschnauzer", "wire", "s", 75, 3, 42),
    _breed("dog", "Standard Schnauzer", "Mittelschnauzer", "wire", "m", 90, 3, 42),
    _breed("dog", "Giant Schnauzer", "Riesenschnauzer", "wire", "l", 120, 3, 49),
    _breed(
        "dog", "West Highland White Terrier", "West Highland White Terrier", "wire", "s", 75, 3, 42
    ),
    _breed("dog", "Scottish Terrier", "Scottish Terrier", "wire", "s", 80, 3, 49),
    _breed("dog", "Cairn Terrier", "Cairn Terrier", "wire", "s", 70, 2, 56),
    _breed("dog", "Border Terrier", "Border Terrier", "wire", "s", 70, 2, 56),
    _breed("dog", "Wire Fox Terrier", "Drahthaar-Foxterrier", "wire", "s", 80, 3, 49),
    _breed("dog", "Airedale Terrier", "Airedale Terrier", "wire", "m", 110, 3, 56),
    _breed("dog", "Wirehaired Dachshund", "Rauhaardackel", "wire", "s", 50, 2, 70),
    # Combination: short body, long feathering
    _breed("dog", "Cocker Spaniel", "Englischer Cocker Spaniel", "combination", "m", 90, 4, 42),
    _breed(
        "dog",
        "American Cocker Spaniel",
        "Amerikanischer Cocker Spaniel",
        "combination",
        "m",
        100,
        4,
        35,
    ),
    _breed(
        "dog",
        "English Springer Spaniel",
        "Englischer Springer Spaniel",
        "combination",
        "m",
        90,
        3,
        49,
    ),
    _breed(
        "dog",
        "Cavalier King Charles Spaniel",
        "Cavalier King Charles Spaniel",
        "combination",
        "s",
        60,
        2,
        49,
    ),
    _breed("dog", "Irish Setter", "Irish Red Setter", "combination", "l", 100, 3, 56),
    _breed("dog", "Papillon", "Papillon", "combination", "s", 55, 2, 56),
    _breed("dog", "Long-haired Dachshund", "Langhaardackel", "combination", "s", 55, 2, 56),
    # Smooth: short and close, mostly bath, brush, nails
    _breed("dog", "Chihuahua", "Chihuahua", "smooth", "s", 35, 1, 70),
    _breed("dog", "Pug", "Mops", "smooth", "s", 40, 1, 70),
    _breed("dog", "Beagle", "Beagle", "smooth", "m", 45, 1, 70),
    _breed("dog", "Boxer", "Boxer", "smooth", "l", 50, 1, 84),
    _breed("dog", "English Bulldog", "Englische Bulldogge", "smooth", "m", 50, 1, 70),
    _breed("dog", "Dalmatian", "Dalmatiner", "smooth", "l", 50, 1, 84),
    _breed("dog", "Whippet", "Whippet", "smooth", "m", 35, 1, 84),
    # Several coats: the dog's profile says which
    _breed("dog", "Dachshund", "Dackel", None, "s", 45, 1, 70),
    _breed("dog", "Jack Russell Terrier", "Jack Russell Terrier", None, "s", 50, 1, 63),
    # Cats
    _breed("cat", "British Shorthair", "Britisch Kurzhaar", "short", "m", 45, 1, 70),
    _breed("cat", "Ragdoll", "Ragdoll", "long", "l", 70, 3, 56),
    _breed("cat", "Norwegian Forest Cat", "Norwegische Waldkatze", "long", "l", 75, 3, 56),
    _breed("cat", "Siberian", "Sibirische Katze", "long", "m", 70, 3, 56),
]
