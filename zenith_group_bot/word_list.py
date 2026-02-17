BANNED_WORDS = [
    # --- [EN] Stage 1 & 2 English ---
    "ass", "asshole", "bastard", "bitch", "bloody", "bollocks", "bullshit",
    "cock", "cocksucker", "crap", "cunt", "dick", "dickhead", "fag", "faggot",
    "fuck", "fucked", "fucker", "fucking", "fuckoff", "jerk", "motherfucker",
    "moron", "piss", "pissed", "prick", "pussy", "shit", "shitty", "slut",
    "sonofabitch", "whore", "wanker", "wtf", "arse", "arsehole", "arsewipe", 
    "arseface", "bugger", "buggeroff", "knob", "knobhead", "bellend", "balls", 
    "ballsack", "ballbag", "scumbag", "scum", "shithead", "shitface", "shitbag", 
    "shitstain", "dipshit", "jackass", "jackhole", "jerkoff", "wankstain", "twat", 
    "twatface", "twathead", "douche", "douchebag", "slag", "skank", "hoe", "hoebag", 
    "tramp", "pisshead", "retard", "retarded", "numpty", "wazzock", "sex", "sexy", "porn",

    # --- [HI] Stage 1 & 2 Hindi / Hinglish (Romanized) ---
    "chutiya", "chutia", "chutiye", "chut", "chutmarika", "gand", "gandu",
    "gaandfat", "gaandmasti", "haraami", "harami", "haramkhor", "bhosdiwale",
    "bhosdike", "bhosdiwala", "bhenchod", "behenchod", "bahenchod", "madarchod",
    "maadarchod", "maa-ki-chut", "maa-ki-aankh", "betichod", "bhaichod", 
    "lauda", "laode", "lund", "land", "randi", "raand", "randwa", "randibaz",
    "suar", "sooar", "kutte", "kutta", "kutti", "kuttiya", "ullu", "ulluka-patha",
    "chudai", "chudne", "chodna", "chodenge", "chodu", "chichora", "kamina", 
    "kamini", "kamine", "kaminey", "haramzadah", "haramzaadah", "haramzaadi", 
    "haramzadi", "haram ki aulaad", "harami ke bacche", "suar ki aulaad", 
    "kutte ki aulaad", "suar ka bachcha", "kutte ka bachcha", "bhand", "bhandwa", 
    "bhadwa", "bhadwaa", "rakhail", "hijrah", "hijdah", "hijda", "saala", "chhakkah", 
    "chakka", "meetha", "katua", "mulla", "mulle", "khotta", "tatte", "tatti", 
    "tattee", "tatty", "saala", "salasali", "sali", "nalayak", "nikamma", "nalayak kutta",
    "bokachoda", "suar ka bacha", "tera maa ka boor", "randi ka jana", "boor ka baal",

    # --- [HI] Stage 1 & 2 Devanagari ---
    "चुतिया", "চুতিয়া", "गांडू", "हरामी", "हरामखोर", "भोसड़ीके", "बहनचोद",
    "मাদারচোদ", "रांडी", "सुअर", "कुत्ता", "कुत्ती", "उल्लू", "चुदाई", "कमीना", 
    "कमीनी", "कमीने", "हरामज़ादा", "हरामज़ादी", "हराम की औलाद", "हरामी के बच्चे", 
    "सुअर की औलाद", "कुत्ते की औलाद", "भंड", "भड़वा", "रखैल", "हिजड़ा", "छक्का", 
    "मीठा", "कटुआ", "मुल्ला", "टट्टी", "साला", "साली", "नालायक",

    # --- [BN] Stage 1 & 2 Bengali (Bangla Script) ---
    "চোদা", "চোদাচুদি", "চোদচুদি", "চোদান", "চোদানোর", "চুদাচুদি", "চুদানি",
    "চুদি", "চুদিরবাজ", "চুতমারানি", "চুতিয়া", "চুতমারানিরবাচ্চা", "চুতমারানিরপোলা",
    "চুদবাজ", "চুদখোর", "হারামজাদা", "হারামজাদী", "হারামি", "হারামী", "রান্ডি",
    "বাজে", "বোকাচোদা", "বোকাচুদি", "বোকাচোদ", "বেঙ্গাচুদা", "কুত্তা", "কুত্তি", 
    "মাদারচোদ", "শালা", "শালারবাচ্চা", "শালারপোলা", "শালারছেলে", "খানকি", 
    "খানকিরমেয়ে", "খানকিরছেলে", "খানকিরবাচ্চা", "বেশ্যা", "বেশ্যাকন্যা", 
    "বেশ্যারবাচ্চা", "মাগী", "মাগীরবাচ্চা", "মাগীরছেলে", "ডাইনী", "ডাইনি", 
    "হারামজাদারবাচ্চা", "হারামখোর", "কুত্তারবাচ্চা"
]

# Common spam/phishing patterns 
SPAM_DOMAINS = [
    "t.me/joinchat", "bit.ly", "goo.gl", "t.co", "whatsapp.com/join"
]
#@academictelebotbyroshhellwett