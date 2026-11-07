"""Conversation language is the language of the citizen's current message.

It is separate from the interface language. A Hindi question is answered in
Hindi even when menus are in English, unless the citizen explicitly asks for
another language.
"""

from __future__ import annotations

import re

SUPPORTED = {"bn", "en", "gu", "hi", "kn", "ml", "mr", "pa", "ta", "te"}

LANGUAGE_NAMES = {
    "bn": "Bengali",
    "en": "English",
    "gu": "Gujarati",
    "hi": "Hindi",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "pa": "Punjabi",
    "ta": "Tamil",
    "te": "Telugu",
}

_SCRIPT_RANGES = (
    ("pa", 0x0A00, 0x0A7F),
    ("gu", 0x0A80, 0x0AFF),
    ("bn", 0x0980, 0x09FF),
    ("ta", 0x0B80, 0x0BFF),
    ("te", 0x0C00, 0x0C7F),
    ("kn", 0x0C80, 0x0CFF),
    ("ml", 0x0D00, 0x0D7F),
    ("deva", 0x0900, 0x097F),
)

_EXPLICIT = (
    (re.compile(r"\b(?:reply|respond|answer|explain|write|speak|say)\s+(?:that\s+)?in\s+english\b", re.I), "en"),
    (re.compile(r"\b(?:reply|respond|answer|explain|write|speak|say)\s+(?:that\s+)?in\s+hindi\b", re.I), "hi"),
    (re.compile(r"\b(?:reply|respond|answer|explain|write|speak|say)\s+(?:that\s+)?in\s+kannada\b", re.I), "kn"),
    (re.compile(r"\b(?:reply|respond|answer|explain|write|speak|say)\s+(?:that\s+)?in\s+tamil\b", re.I), "ta"),
    (re.compile(r"\b(?:reply|respond|answer|explain|write|speak|say)\s+(?:that\s+)?in\s+telugu\b", re.I), "te"),
    (re.compile(r"\b(?:reply|respond|answer|explain|write|speak|say)\s+(?:that\s+)?in\s+malayalam\b", re.I), "ml"),
    (re.compile(r"\b(?:reply|respond|answer|explain|write|speak|say)\s+(?:that\s+)?in\s+marathi\b", re.I), "mr"),
    (re.compile(r"\b(?:reply|respond|answer|explain|write|speak|say)\s+(?:that\s+)?in\s+bengali\b", re.I), "bn"),
    (re.compile(r"\b(?:reply|respond|answer|explain|write|speak|say)\s+(?:that\s+)?in\s+gujarati\b", re.I), "gu"),
    (re.compile(r"\b(?:reply|respond|answer|explain|write|speak|say)\s+(?:that\s+)?in\s+punjabi\b", re.I), "pa"),
    (re.compile(r"(?:हिंदी|हिन्दी)\s*में"), "hi"),
    (re.compile(r"ಕನ್ನಡ(?:ದಲ್ಲಿ|ದಲ್ಲಿ)"), "kn"),
    (re.compile(r"தமிழில்"), "ta"),
    (re.compile(r"తెలుగులో"), "te"),
    (re.compile(r"മലയാളത്തിൽ"), "ml"),
    (re.compile(r"मराठी(?:त|मध्ये)"), "mr"),
    (re.compile(r"বাংলা(?:য়|তে)"), "bn"),
    (re.compile(r"ગુજરાતીમાં"), "gu"),
    (re.compile(r"ਪੰਜਾਬੀ\s*ਵਿੱਚ"), "pa"),
)

# High-precision aliases so Indic questions can still retrieve English records.
_ALIASES = (
    ("पीएम किसान", "PM-KISAN kisan farmer"),
    ("पीएम-किसान", "PM-KISAN kisan farmer"),
    ("किसान", "kisan farmer PM-KISAN"),
    ("छात्रवृत्ति", "scholarship"),
    ("स्कॉलर", "scholarship"),
    ("आयुष्मान", "ayushman"),
    ("उद्यम", "udyam"),
    ("पेंशन", "pension"),
    ("दस्तावे", "documents"),
    ("पात्र", "eligibility"),
    ("आवेदन", "apply application"),
    ("ಪಿಎಂ", "PM-KISAN"),
    ("ರೈತ", "farmer kisan PM-KISAN"),
    ("ವಿದ್ಯಾರ್ಥಿವೇತನ", "scholarship"),
    ("ದಾಖಲ", "documents"),
    ("ಅರ್ಹ", "eligibility"),
    ("ஆவண", "documents"),
    ("தகுதி", "eligibility"),
    ("உதவித்தொகை", "scholarship"),
    ("విద్యార్థి", "scholarship student"),
    ("పత్ర", "documents"),
    ("అర్హత", "eligibility"),
    ("రైతు", "farmer kisan PM-KISAN"),
    ("രേഖ", "documents"),
    ("യോഗ്യത", "eligibility"),
    ("സ്കോളർഷിപ്പ്", "scholarship"),
    ("कागद", "documents"),
    ("शिष्यवृत्ती", "scholarship"),
    ("নথি", "documents"),
    ("বৃত্তি", "scholarship"),
    ("દસ્તાવેજ", "documents"),
    ("ਦਸਤਾਵੇਜ਼", "documents"),
    ("ਕਿਸਾਨ", "farmer kisan PM-KISAN"),
    ("ਵਜ਼ੀਫ", "scholarship"),
)

_MESSAGES = {
    "insufficient": {
        "en": "I couldn't confirm this information from a reliable government source. I don't want to give you incorrect government-service guidance. Please consult the relevant official government department.",
        "hi": "मुझे किसी विश्वसनीय सरकारी स्रोत से यह जानकारी पक्की नहीं हुई। मैं गलत सरकारी जानकारी नहीं देना चाहता। कृपया संबंधित सरकारी विभाग से जाँच करें।",
        "kn": "ವಿಶ್ವಾಸಾರ್ಹ ಸರ್ಕಾರಿ ಮೂಲದಿಂದ ಈ ಮಾಹಿತಿಯನ್ನು ಖಚಿತಪಡಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ತಪ್ಪು ಸರ್ಕಾರಿ ಮಾರ್ಗದರ್ಶನ ನೀಡಲು ನಾನು ಇಷ್ಟಪಡುವುದಿಲ್ಲ. ದಯವಿಟ್ಟು ಸಂಬಂಧಿತ ಸರ್ಕಾರಿ ಇಲಾಖೆಯನ್ನು ಸಂಪರ್ಕಿಸಿ.",
        "ta": "நம்பகமான அரசு மூலத்திலிருந்து இந்தத் தகவலை உறுதிப்படுத்த முடியவில்லை. தவறான அரசு வழிகாட்டுதலைத் தர விரும்பவில்லை. தொடர்புடைய அரசுத் துறையை அணுகுங்கள்.",
        "te": "నమ్మదగిన ప్రభుత్వ మూలం నుంచి ఈ సమాచారాన్ని నిర్ధారించలేకపోయాను. తప్పు ప్రభుత్వ సమాచారం ఇవ్వదలచుకోలేదు. సంబంధిత ప్రభుత్వ శాఖను సంప్రదించండి.",
        "ml": "വിശ്വസനീയമായ സർക്കാർ ഉറവിടത്തിൽ നിന്ന് ഈ വിവരം ഉറപ്പിക്കാനായില്ല. തെറ്റായ സർക്കാർ മാർഗനിർദേശം നൽകാൻ ഞാൻ ആഗ്രഹിക്കുന്നില്ല. ബന്ധപ്പെട്ട സർക്കാർ വകുപ്പിനെ സമീപിക്കുക.",
        "mr": "विश्वासार्ह शासकीय स्रोतातून ही माहिती निश्चित करता आली नाही. चुकीचे शासकीय मार्गदर्शन द्यायचे नाही. कृपया संबंधित शासकीय विभागाकडे तपासा.",
        "bn": "নির্ভরযোগ্য সরকারি উৎস থেকে এই তথ্য নিশ্চিত করা যায়নি। ভুল সরকারি তথ্য দিতে চাই না। অনুগ্রহ করে সংশ্লিষ্ট সরকারি দপ্তরে যাচাই করুন।",
        "gu": "વિશ્વસનીય સરકારી સ્રોતમાંથી આ માહિતી પુષ્ટિ થઈ નથી. ખોટું સરકારી માર્ગદર્શન આપવા માંગતો નથી. કૃપા કરીને સંબંધિત સરકારી વિભાગ ચકાસો.",
        "pa": "ਕਿਸੇ ਭਰੋਸੇਯੋਗ ਸਰਕਾਰੀ ਸਰੋਤ ਤੋਂ ਇਹ ਜਾਣਕਾਰੀ ਪੱਕੀ ਨਹੀਂ ਹੋਈ। ਮੈਂ ਗਲਤ ਸਰਕਾਰੀ ਜਾਣਕਾਰੀ ਨਹੀਂ ਦੇਣਾ ਚਾਹੁੰਦਾ। ਕਿਰਪਾ ਕਰਕੇ ਸੰਬੰਧਿਤ ਸਰਕਾਰੀ ਵਿਭਾਗ ਨਾਲ ਜਾਂਚ ਕਰੋ।",
    },
    "safe_intro": {
        "en": "I found the following source information. It may not answer every part of your question.",
        "hi": "मुझे यह स्रोत जानकारी मिली। यह आपके प्रश्न के हर हिस्से का उत्तर नहीं भी हो सकती है।",
        "kn": "ಈ ಮೂಲ ಮಾಹಿತಿ ಸಿಕ್ಕಿದೆ. ಇದು ನಿಮ್ಮ ಪ್ರಶ್ನೆಯ ಪ್ರತಿ ಭಾಗಕ್ಕೂ ಉತ್ತರವಾಗದಿರಬಹುದು.",
        "ta": "பின்வரும் மூலத் தகவல் கிடைத்தது. இது உங்கள் கேள்வியின் ஒவ்வொரு பகுதிக்கும் பதிலாக இல்லாமல் இருக்கலாம்.",
        "te": "ఈ మూల సమాచారం దొరికింది. ఇది మీ ప్రశ్నలోని ప్రతి భాగానికీ సమాధానం కాకపోవచ్చు.",
        "ml": "ഈ ഉറവിട വിവരം കണ്ടെത്തി. ഇത് നിങ്ങളുടെ ചോദ്യത്തിന്റെ എല്ലാ ഭാഗത്തിനും മറുപടിയാകണമെന്നില്ല.",
        "mr": "खालील स्रोत माहिती सापडली. ती तुमच्या प्रश्नाच्या प्रत्येक भागाचे उत्तर देईलच असे नाही.",
        "bn": "নিচের উৎস-তথ্য পাওয়া গেছে। এটি আপনার প্রশ্নের প্রতিটি অংশের উত্তর না-ও হতে পারে।",
        "gu": "નીચેની સ્રોત માહિતી મળી. તે તમારા પ્રશ્નના દરેક ભાગનો જવાબ ન પણ હોય.",
        "pa": "ਇਹ ਸਰੋਤ ਜਾਣਕਾਰੀ ਮਿਲੀ। ਇਹ ਤੁਹਾਡੇ ਸਵਾਲ ਦੇ ਹਰ ਹਿੱਸੇ ਦਾ ਜਵਾਬ ਨਾ ਵੀ ਹੋਵੇ।",
    },
    "pending_intro": {
        "en": "I found the following source information. It is pending human verification and may not answer every part of your question.",
        "hi": "मुझे यह स्रोत जानकारी मिली। यह मानव सत्यापन के लिए लंबित है और आपके प्रश्न के हर हिस्से का उत्तर नहीं भी हो सकती है।",
        "kn": "ಈ ಮೂಲ ಮಾಹಿತಿ ಸಿಕ್ಕಿದೆ. ಇದು ಮಾನವ ಪರಿಶೀಲನೆಗೆ ಬಾಕಿ ಇದೆ ಮತ್ತು ನಿಮ್ಮ ಪ್ರಶ್ನೆಯ ಪ್ರತಿ ಭಾಗಕ್ಕೂ ಉತ್ತರವಾಗದಿರಬಹುದು.",
        "ta": "பின்வரும் மூலத் தகவல் கிடைத்தது. இது மனித சரிபார்ப்புக்காக நிலுவையில் உள்ளது.",
        "te": "ఈ మూల సమాచారం దొరికింది. ఇది మానవ ధృవీకరణ కోసం పెండింగ్‌లో ఉంది.",
        "ml": "ഈ ഉറവിട വിവരം കണ്ടെത്തി. ഇത് മനുഷ്യ പരിശോധനയ്ക്കായി ശേഷിക്കുന്നു.",
        "mr": "खालील स्रोत माहिती सापडली. ती मानवी पडताळणीसाठी प्रलंबित आहे.",
        "bn": "নিচের উৎস-তথ্য পাওয়া গেছে। এটি মানুষের যাচাইয়ের অপেক্ষায় আছে।",
        "gu": "નીચેની સ્રોત માહિતી મળી. તે માનવ ચકાસણી માટે બાકી છે.",
        "pa": "ਇਹ ਸਰੋਤ ਜਾਣਕਾਰੀ ਮਿਲੀ। ਇਹ ਮਨੁੱਖੀ ਜਾਂਚ ਲਈ ਬਕਾਇਆ ਹੈ।",
    },
    "source_original": {
        "en": "The source wording below is kept in its original language. This is not an official government translation.",
        "hi": "नीचे का स्रोत पाठ मूल भाषा में रखा गया है। यह सरकारी आधिकारिक अनुवाद नहीं है।",
        "kn": "ಕೆಳಗಿನ ಮೂಲ ಪಠ್ಯವನ್ನು ಮೂಲ ಭಾಷೆಯಲ್ಲಿಯೇ ಇಡಲಾಗಿದೆ. ಇದು ಅಧಿಕೃತ ಸರ್ಕಾರಿ ಅನುವಾದವಲ್ಲ.",
        "ta": "கீழுள்ள மூல உரை அதன் மூல மொழியிலேயே வைக்கப்பட்டுள்ளது. இது அதிகாரப்பூர்வ அரசு மொழிபெயர்ப்பு அல்ல.",
        "te": "కింది మూల పాఠ్యం దాని అసలు భాషలోనే ఉంచబడింది. ఇది అధికారిక ప్రభుత్వ అనువాదం కాదు.",
        "ml": "താഴെയുള്ള ഉറവിട വാചകം മൂലഭാഷയിൽ തന്നെ സൂക്ഷിച്ചിരിക്കുന്നു. ഇത് ഔദ്യോഗിക സർക്കാർ വിവർത്തനമല്ല.",
        "mr": "खालील स्रोत मजकूर मूळ भाषेत ठेवला आहे. हा अधिकृत शासकीय अनुवाद नाही.",
        "bn": "নিচের উৎস পাঠ মূল ভাষাতেই রাখা হয়েছে। এটি সরকারের আনুষ্ঠানিক অনুবাদ নয়।",
        "gu": "નીચેનું સ્રોત લખાણ મૂળ ભાષામાં રાખ્યું છે. આ અધિકૃત સરકારી અનુવાદ નથી.",
        "pa": "ਹੇਠਾਂ ਦੀ ਸਰੋਤ ਲਿਖਤ ਮੂਲ ਭਾਸ਼ਾ ਵਿੱਚ ਰੱਖੀ ਗਈ ਹੈ। ਇਹ ਸਰਕਾਰੀ ਅਧਿਕਾਰਤ ਅਨੁਵਾਦ ਨਹੀਂ ਹੈ।",
    },
}


def language_base(value: str | None) -> str:
    if not value:
        return "en"
    base = str(value).strip().lower().split("-", 1)[0]
    return base if base in SUPPORTED else "en"


def language_name(value: str | None) -> str:
    return LANGUAGE_NAMES[language_base(value)]


def citizen_text(key: str, language_code: str | None) -> str:
    table = _MESSAGES[key]
    return table.get(language_base(language_code), table["en"])


def explicit_language(message: str) -> str | None:
    for pattern, code in _EXPLICIT:
        if pattern.search(message or ""):
            return code
    return None


def _counts(message: str) -> dict[str, int]:
    counts = {code: 0 for code, _, _ in _SCRIPT_RANGES}
    counts["latin"] = 0
    for char in message or "":
        code_point = ord(char)
        if ("A" <= char <= "Z") or ("a" <= char <= "z"):
            counts["latin"] += 1
            continue
        for code, start, end in _SCRIPT_RANGES:
            if start <= code_point <= end:
                counts[code] += 1
                break
    return counts


def dominant_indic_script(message: str) -> str | None:
    counts = _counts(message)
    best_code = None
    best_count = 0
    for code, _, _ in _SCRIPT_RANGES:
        if counts[code] > best_count:
            best_code = code
            best_count = counts[code]
    if best_count == 0 or best_count < counts["latin"]:
        return None
    return best_code


def _devanagari_language(message: str, requested: str, detected: str | None) -> str:
    if detected in {"hi", "mr"}:
        return detected
    marathi = sum(message.count(word) for word in ("आहे", "नाही", "मला", "काय", "आणि", "होते"))
    hindi = sum(message.count(word) for word in ("है", "हैं", "क्या", "मुझे", "नहीं", "चाहिए"))
    if marathi > hindi and marathi > 0:
        return "mr"
    if requested in {"hi", "mr"} and marathi == 0 and hindi == 0:
        return requested
    return "hi"


def resolve_conversation_language(
    message: str,
    requested: str | None = "en",
    detected: str | None = None,
) -> str:
    """Choose the language for this answer from the utterance itself."""
    requested_base = language_base(requested)
    detected_base = language_base(detected) if detected else None
    if detected and language_base(detected) == "en" and str(detected).strip().lower().split("-", 1)[0] != "en":
        detected_base = None
    explicit = explicit_language(message)
    if explicit:
        return explicit
    script = dominant_indic_script(message)
    if script == "deva":
        return _devanagari_language(message or "", requested_base, detected_base)
    if script:
        return script
    if _counts(message).get("latin", 0) >= 3:
        return "en"
    if detected_base in SUPPORTED and detected_base != "en":
        return detected_base
    return requested_base


def response_language_instruction(language_code: str) -> str:
    name = language_name(language_code)
    code = language_base(language_code)
    return (
        f"The citizen's conversation language for this message is {name} ({code}). "
        f"Write the entire answer in {name}. "
        "Do not translate the citizen's question into English unless they asked for a translation. "
        "Do not switch to English merely because the retrieved government documents are in English. "
        f"Explain English government wording in {name}. "
        "Keep official scheme names, document names, department names, and portal names in their official form when a translation could cause confusion, and explain the meaning beside them. "
        "Use simple, citizen-friendly language. "
        "If a source is available only in English, say that the explanation is not an official government translation. "
        "Headings must also be in the conversation language."
    )


def append_retrieval_aliases(text: str) -> str:
    """Add English scheme words so Indic questions can match English records."""
    if not text or not re.search(r"[\u0900-\u0D7F]", text):
        return text
    extras: list[str] = []
    for needle, alias in _ALIASES:
        if needle in text and alias not in extras:
            extras.append(alias)
    if not extras:
        return text
    return f"{text} {' '.join(extras)}"
