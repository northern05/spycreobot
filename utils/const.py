CONTENT_CHAR_LIMIT = 500

COMMERCIAL_KEYWORDS = {
    "download", "install", "play", "грати", "играть", "jugar", "jouer", "spielen", "giocare", "jogar", "grać", "oyna",
    "spelen", "spela", "プレイ", "玩", "العب", "खेलें", "재생", "main", "main", "hrát", "завантажити", "встановити",
    "скачать", "установить", "descargar", "instalar", "télécharger", "installer", "herunterladen", "installieren",
    "scaricare", "installare", "baixar", "instalar", "pobrać", "zainstalować", "indir", "yükle", "downloaden",
    "installeren", "ladda ner", "installera", "ダウンロードする", "インストールする", "下载", "安装", "تنزيل", "تثبيت", "डाउनलोड करें",
    "स्थापित करें", "다운로드", "설치하다", "unduh", "pasang", "muat turun", "pasang", "stáhnout", "nainstalovat"
}

COUNTRY_TO_LANG_CODE = {
    'BR': 'pt', 'MX': 'es', 'AR': 'es', 'CO': 'es', 'CL': 'es', 'PE': 'es', 'VE': 'es',
    'BO': 'es', 'CR': 'es', 'DO': 'es', 'EC': 'es', 'GT': 'es', 'HN': 'es', 'NI': 'es',
    'PA': 'es', 'PY': 'es', 'SV': 'es', 'UY': 'es', 'PR': 'es', 'PS': 'ar',
    'DZ': 'ar', 'EG': 'ar', 'IQ': 'ar', 'JO': 'ar', 'KW': 'ar', 'LB': 'ar', 'LY': 'ar',
    'MA': 'ar', 'OM': 'ar', 'QA': 'ar', 'SA': 'ar', 'TN': 'ar', 'AE': 'ar',
    'YE': 'ar', 'KM': 'ar', 'MR': 'ar', 'SO': 'so', 'CN': 'zh', 'HK': 'zh', 'MO': 'zh',
    'TW': 'zh', 'JP': 'ja', 'KR': 'ko', 'IN': 'hi', 'ID': 'id', 'MY': 'ms', 'PK': 'ur',
    'FJ': 'en', 'VU': 'bi', 'TO': 'to', 'WS': 'sm', 'TZ': 'sw', 'XK': 'sq', 'SS': 'en',
    'FM': 'en', 'MH': 'en', 'NR': 'en', 'PW': 'en', 'TV': 'tvl', 'AO': 'pt', 'CV': 'pt',
    'GW': 'pt', 'MZ': 'pt', 'ST': 'pt', 'TL': 'pt', 'HT': 'fr', 'SN': 'fr', 'TG': 'fr',
    'BJ': 'fr', 'BF': 'fr', 'CD': 'fr', 'CF': 'fr', 'CM': 'fr', 'CI': 'fr', 'CG': 'fr',
    'GA': 'fr', 'GN': 'fr', 'ML': 'fr', 'NE': 'fr', 'RE': 'fr', 'RW': 'rw', 'TF': 'fr',
    'WF': 'fr', 'YT': 'fr', 'AM': 'hy', 'AZ': 'az', 'GE': 'ka', 'KG': 'ky', 'KZ': 'kk',
    'MN': 'mn', 'TJ': 'tg', 'TM': 'tk', 'UZ': 'uz', 'BI': 'fr', 'ER': 'ti', 'GM': 'en',
    'LS': 'st', 'MG': 'mg', 'MW': 'ny', 'NC': 'fr', 'NU': 'niu',

    'US': 'en', 'GB': 'en', 'CA': 'en', 'AU': 'en', 'IE': 'en', 'NZ': 'en', 'ZA': 'en', 'SG': 'en',
    'PH': 'en', 'KE': 'en', 'GH': 'en', 'ZM': 'en', 'ZW': 'en', 'UG': 'en', 'TT': 'en', 'BS': 'en',
    'JM': 'en', 'BB': 'en', 'LC': 'en', 'VC': 'en', 'DM': 'en', 'GD': 'en', 'AG': 'en', 'KN': 'en',
    'BZ': 'en', 'VI': 'en', 'AW': 'nl', 'BM': 'en', 'KY': 'en', 'TC': 'en', 'VG': 'en', 'AI': 'en',
    'GY': 'en', 'MS': 'en', 'MU': 'en', 'NA': 'en', 'NF': 'en', 'PG': 'en', 'PN': 'en', 'SB': 'en',
    'SC': 'en', 'SH': 'en', 'SL': 'en', 'SZ': 'en', 'TK': 'en', 'UM': 'en', 'BD': 'bn', 'TH': 'th',
    'VN': 'vi', 'MM': 'my', 'NP': 'ne', 'LK': 'si', 'DE': 'de', 'FR': 'fr', 'ES': 'es', 'IT': 'it',
    'PT': 'pt', 'NL': 'nl', 'BE': 'nl', 'CH': 'de', 'FO': 'fo', 'AX': 'sv', 'UA': 'uk', 'IM': 'en',
    'AT': 'de', 'PL': 'pl', 'CZ': 'cs', 'SK': 'sk', 'HU': 'hu', 'RO': 'ro', 'GR': 'el', 'SE': 'sv',
    'NO': 'no', 'DK': 'da', 'FI': 'fi', 'IS': 'is', 'TR': 'tr', 'BG': 'bg', 'HR': 'hr', 'RS': 'sr',
    'SI': 'sl', 'BA': 'bs', 'AL': 'sq', 'MK': 'mk', 'LT': 'lt', 'LV': 'lv', 'EE': 'et', 'CY': 'el',
    'LU': 'fr', 'JE': 'en',

}

NICHE_KEYWORDS_COMBINATIONS = {
    "gambling": [
        ["bonus", "casino", "live"],
        ["free", "spins", "now"],
        ["play", "slots", "online"],
        ["register", "bonus", "win"],
        ["no", "download", "required"],
        ["vip", "offer", "today"],
        ["daily", "spin", "reward"],
        ["classic", "slots", "win"],
        ["slot", "machine", "fun"],
        ["mega", "win", "spin"],
        ["roulette", "spin", "deal"],
        ["install", "slot", "app"],
        ["realistic", "casino", "slots"],
        ["free", "game"],
        ["tournament", "bonus", "prize"],
        ["jackpot", "live", "spin"],
        ["tap", "play", "slots"],
        ["big", "win", "slots"],
        ["exclusive", "slots", "today"],

        ["pwa", "play", "game"],
        ["mobile", "slots", "pwa"],
        ["android", "casino", "app"],
        ["slot", "pwa", "install"],
        ["lite", "casino", "game"],
        ["play", "app", "bonus"],
        ["web", "slots", "app"],
        ["tap", "start", "game"],
        ["browser", "game", "slot"],
        ["instant", "slots", "pwa"],

        ["bonus", "spin", "today"],
        ["claim", "reward", "now"],
        ["play", "get", "reward"],
        ["click", "spin", "start"],
        ["get", "free", "spins"],
        ["bonus", "spin", "code"],
        ["download", "slot", "app"],
        ["exclusive", "claim", "offer"],
        ["instant", "win", "slots"],
        ["fun", "game", "slots"],

        ["slot", "bonus"],
        ["casino"],
        ["free", "spins"],
        ["register", "bonus"],
        ["vip", "offer"],
        ["daily", "spin"],
        ["classic", "slots"],
        ["slot", "machine"],
        ["mega", "spin"],
        ["roulette", "deal"],
        ["install", "app"],
        ["realistic", "slots"],
        ["free", "game"],
        ["tournament", "bonus"],
        ["tap", "slots"],
        ["big", "slots"],
        ["exclusive", "slots"],
        ["pwa", "play"],
        ["mobile", "slots"],
        ["android", "casino"],
        ["slot", "pwa"],
        ["lite", "casino"],
        ["play", "bonus"],
        ["web", "slots"],
        ["tap", "start"],
        ["browser", "game"],
        ["instant", "slots"],
        ["bonus", "today"],
        ["claim", "reward"],
        ["play", "reward"],
        ["click", "start"],
        ["get", "spins"],
        ["bonus", "code"],
        ["download", "app"],
        ["exclusive", "offer"],
        ["instant", "win"],
        ["fun", "slots"]

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
