CONTENT_CHAR_LIMIT = 300

base_phrases = [
    ["free", "spin", "play"],
    ["play", "slots", "online"],
    ["casino", "win", "game"],
    ["download", "register", "bonus"],
    ["bonus", "play", "spins"],
    ["mobile","casino","app"],
    ["bonus","win","now"],
]

# Translations with 2 local phrases per language + base phrases
translations = {
    "EN": base_phrases,
    "CH": [["bonus sans dépôt"], ["100 tours gratuits"]],
    "FR": [["bonus sans dépôt"], ["100 tours gratuits"]],
    "ES": [["bono sin depósito"], ["100 giros gratis"]],
    "PL": [["bonus bez depozytu"], ["100 darmowych spinów"]],
    "UA": [["бонус без депозиту"], ["100 безкоштовних обертань"]],
    "PT": [["bonus sem depósito"], ["jogar slots online"]],
    "RO": [["bonus fără depozit"], ["joacă slots online"]],
    "NL": [["bonus zonder storting"], ["speel slots online"]],
    "DE": [["bonus ohne einzahlung"], ["100 freispiele"]],
    "IT": [["bonus senza deposito"], ["100 giri gratis"]],
    "TR": [["bonus yatırma yok"], ["slots oyna online"]],
    "MD": [["bonus fără depozit"], ["joacă slots online"]],
    "BE": [["bonus sans dépôt"], ["100 tours gratuits"]],
    "AT": [["bonus ohne einzahlung"], ["100 freispiele"]],
    "LU": [["bonus ohne einzahlung"], ["100 freispiele"]],
    "LI": [["bonus ohne einzahlung"], ["100 freispiele"]],
    "SM": [["bonus senza deposito"], ["100 giri gratis"]],
    "MC": [["bonus sans dépôt"], ["100 tours gratuits"]],
    "VA": [["bonus senza deposito"], ["100 giri gratis"]],
    "MX": [["bono sin depósito"], ["100 giros gratis"]],
    "AR": [["bono sin depósito"], ["100 giros gratis"]],
    "CL": [["bono sin depósito"], ["100 giros gratis"]],
    "CO": [["bono sin depósito"], ["100 giros gratis"]],
    "PE": [["bono sin depósito"], ["100 giros gratis"]],
    "EC": [["bono sin depósito"], ["100 giros gratis"]],
    "UY": [["bono sin depósito"], ["100 giros gratis"]],
    "VE": [["bono sin depósito"], ["100 giros gratis"]],
    "PY": [["bono sin depósito"], ["100 giros gratis"]],
    "BO": [["bono sin depósito"], ["100 giros gratis"]],
    "DO": [["bono sin depósito"], ["100 giros gratis"]],
    "CR": [["bono sin depósito"], ["100 giros gratis"]],
    "GT": [["bono sin depósito"], ["100 giros gratis"]],
    "HN": [["bono sin depósito"], ["100 giros gratis"]],
    "NI": [["bono sin depósito"], ["100 giros gratis"]],
    "PA": [["bono sin depósito"], ["100 giros gratis"]],
    "SV": [["bono sin depósito"], ["100 giros gratis"]],
    "JP": [["入金不要 bonus"], ["オンラインで slots をプレイ"]],
    "KR": [["입금 없이 bonus"], ["온라인에서 slots 게임"]],
    "ID": [["bonus tanpa deposit"], ["main slots online"]],
    "MY": [["bonus tanpa deposit"], ["main slots online"]]
}

# Map languages to countries
language_map = {
    "EN": {"GB", "US", "CA", "AU", "NZ", "IE"},
    "DE": {"DE", "AT", "CH", "LU", "LI"},
    "IT": {"IT", "SM", "VA"},
    "FR": {"FR", "BE", "CH", "LU", "MC"},
    "ES": {"ES", "MX", "AR", "CL", "CO", "PE", "EC", "UY", "VE", "PY", "BO", "DO", "CR", "GT", "HN", "NI", "PA", "SV", "CU"},
    "PL": {"PL"},
    "UA": {"UA"},
    "PT": {"PT", "BR"},
    "TR": {"TR"},
    "RO": {"RO", "MD"},
    "NL": {"NL", "BE", "SR", "AW", "CW"},
    "JP": {"JP"},
    "KR": {"KR"},
    "ID": {"ID"},
    "MY": {"MY"}
}

# All countries
all_countries = {"GB", "AL", "AD", "AT", "BE", "BA", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GI", "GR",
                 "HU", "IS", "IE", "IT", "LV", "LI", "LT", "LU", "MT", "MD", "MC", "ME", "NL", "MK", "NO", "PL", "PT",
                 "RO", "SM", "RS", "SK", "SI", "ES", "SE", "CH", "UA", "VA", "IM", "FO", "AX", "JE", "TR", "CA", "MX",
                 "AR", "BO", "BR", "CL", "CO", "CR", "DO", "EC", "GT", "HN", "JM", "NI", "PA", "PE", "PY", "SV",
                 "UY", "VE", "BZ", "HT", "TT", "BS", "LC", "VC", "DM", "GD", "AG", "KN", "BB", "GY", "AE", "AF", "AM",
                 "AZ", "BH", "GE", "IL", "IQ", "IN", "ID", "JO", "JP", "KZ", "KW", "KG", "LB", "LK", "MY", "MV",
                 "MN", "NP", "OM", "PK", "PH", "QA", "SA", "SG", "KR", "TJ", "TH", "TL", "TM", "UZ", "VN",
                 "YE", "AU", "NZ", "FJ", "PG", "WS", "TO", "TV", "VU", "NR", "FM", "MH", "PW", "SB"}

# Ensure all translations include EN base phrases
for lang, phrases in translations.items():
    if lang == "EN":
        continue
    local_phrases = [p for p in phrases if p not in base_phrases]
    reduced = local_phrases[:2] + base_phrases
    translations[lang] = reduced

# Build country to keywords mapping
COUNTRY_TO_KEYWORDS = {}
for country in all_countries:
    lang = next((lang for lang, countries in language_map.items() if country in countries), "EN")
    COUNTRY_TO_KEYWORDS[country] = translations[lang]

COMMERCIAL_KEYWORDS = {
    "download", "install", "play", "use app", "play game", "learn more", "download app", "install app", "install now",
    "join now", "apply now", "free download", "sign up"
}

button_like_selectors = [
    'button',
    'a[role="button"]',
    'div[role="button"]',
    'div[class*="button"]',
    'span[class*="button"]'
]

NICHE_KEYWORDS_COMBINATIONS = {
    "gambling": [
        ["no deposit bonus"],
        ["100 free spins"],
        ["cashout fast"],
        ["slotmania", "free chips"],
        ["gratis", "spiel", "jetzt"],
        ["gioca", "gratis", "subito"],
        ["casino", "dinero real", "gratis"],
    ],
    "crypto": [
        ["crypto", "nft"],
        ["bitcoin", "ethereum"],
        ["web3", "blockchain"]
    ],
    "nutra": [
        ["supplement", "keto"],
        ["pills", "weight loss"],
        ["vitamins", "skincare"]
    ],
    "dating": [
        ["dating app", "match"],
        ["love", "singles"],
        ["romance", "dating"]
    ],
    "products": [
        ["buy now", "shop"],
        ["discount", "shipping"],
        ["e-commerce", "online store"]
    ],
    "gaming": [
        ["game", "mmorpg"],
        ["mobile", "pc"],
        ["console", "gameplay"]
    ]
}
