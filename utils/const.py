CONTENT_CHAR_LIMIT = 3000

COMMERCIAL_KEYWORDS = {
    # English
    "download", "install",
    # Ukrainian
    "завантажити", "встановити",
    # Russian
    "скачать", "установить",
    # Spanish
    "descargar", "instalar",
    # French
    "télécharger", "installer",
    # German
    "herunterladen", "installieren",
    # Italian
    "scaricare", "installare",
    # Portuguese
    "baixar", "instalar",
    # Polish
    "pobrać", "zainstalować",
    # Turkish
    "indir", "yükle",
    # Dutch
    "downloaden", "installeren",
    # Swedish
    "ladda ner", "installera",
    # Japanese
    "ダウンロードする", "インストールする",
    # Chinese (Simplified)
    "下载", "安装",
    # Arabic
    "تنزيل", "تثبيت",
    # Hindi
    "डाउनलोड करें", "स्थापित करें",
    # Korean
    "다운로드", "설치하다",
    # Indonesian
    "unduh", "pasang",
    # Malay
    "muat turun", "pasang",
    # Czech
    "stáhnout", "nainstalovat"
}

COUNTRY_TO_LANG_CODE = {
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

}

NICHE_KEYWORDS_COMBINATIONS = {
    "gambling": [
        # 🎰 Ігрові CTA, які часто з’являються в банерах/лендінгах
        ["free", "spins", "casino"],
        ["jackpot", "win", "game"],
        ["slot", "register", "lucky"],
        ["play", "casino", "live"],
        ["tournament", "bonus", "code"],
        ["download", "register", "win"],

        # 🔥 Агресивні, high-CTR, банерні/CPA формати
        ["no", "deposit", "bonus"],
        ["download", "bonus", "play"],
        ["real", "money", "casino"],
        ["cashout", "fast", "payout"],
        ["instant", "withdrawal", "spins"],
        ["no", "verification", "bonus"],
        ["new", "account", "bonus"],
        ["100%", "match", "bonus"],

        # 🎲 Класичні азартні ігри (менш рекламні, більше контентні)
        ["blackjack", "poker", "game"],
        ["roulette", "baccarat", "card"],
        ["slots", "machines", "online"],

        # 📱 Мобільні додатки, Android traffic
        ["mobile", "casino", "app"],
        ["app", "mobile", "android"],
        ["mobile", "slots", "777"],

        # 💸 Виплати, кешбек, фінансові теми
        ["payout", "withdraw", "cashout"],
        ["withdraw", "deposit", "claim"],
        ["fast", "real", "money"],
        ["offer", "deposit", "cash"],

        # 💡 Промо-терміни, бонуси
        ["bonus", "win", "now"],
        ["promo", "spin", "free"],
        ["welcome", "jackpot", "claim"],
        ["exclusive", "offer", "limited"],
        ["big", "prize", "today"],
        ["unlimited", "chance", "today"],

        # 🧠 Менш агресивні — більше схожі на соціальний формат
        ["online", "bonus", "slot"],
        ["bet", "win", "now"],
        ["games", "bet", "money"],
        ["lucky", "exclusive", "big"],
        ["betting", "online", "site"],
        ["new", "player", "bonus"]
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
