/* Interface language for GovNexus.
 * Official scheme sentences are not machine-translated.
 * A missing interface translation stays in English and is marked as such.
 */
(() => {
  const STORAGE_KEY = "schemesathi_language_v1";
  const LANGUAGES = [
    ["en", "English"],
    ["kn", "ಕನ್ನಡ"],
    ["hi", "हिन्दी"],
    ["ta", "தமிழ்"],
    ["te", "తెలుగు"],
    ["ml", "മലയാളം"],
    ["mr", "मराठी"],
    ["bn", "বাংলা"],
    ["gu", "ગુજરાતી"],
    ["pa", "ਪੰਜਾਬੀ"]
  ];
  const NOTE = "Official scheme text stays in the source language when a verified translation is not available.";
  const PHRASES = {
    "Home": { kn: "ಮುಖಪುಟ", hi: "होम", ta: "முகப்பு", te: "హోమ్", ml: "ഹോം", mr: "मुखपृष्ठ", bn: "হোম", gu: "હોમ", pa: "ਹੋਮ" },
    "Explore services": { kn: "ಸೇವೆಗಳನ್ನು ನೋಡಿ", hi: "सेवाएँ देखें", ta: "சேவைகளை காண்க", te: "సేవలను చూడండి", ml: "സേവനങ്ങൾ കാണുക", mr: "सेवा पहा", bn: "পরিষেবা দেখুন", gu: "સેવાઓ જુઓ", pa: "ਸੇਵਾਵਾਂ ਵੇਖੋ" },
    "How it works": { kn: "ಇದು ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ", hi: "यह कैसे काम करता है", ta: "இது எப்படி செயல்படுகிறது", te: "ఇది ఎలా పని చేస్తుంది", ml: "ഇത് എങ്ങനെ പ്രവർത്തിക്കുന്നു", mr: "हे कसे काम करते", bn: "এটি কীভাবে কাজ করে", gu: "આ કેવી રીતે કામ કરે છે", pa: "ਇਹ ਕਿਵੇਂ ਕੰਮ ਕਰਦਾ ਹੈ" },
    "AI assistant": { kn: "ಎಐ ಸಹಾಯಕ", hi: "एआई सहायक", ta: "ஏஐ உதவியாளர்", te: "ఏఐ సహాయకుడు", ml: "എഐ സഹായി", mr: "एआय सहाय्यक", bn: "এআই সহায়ক", gu: "એઆઈ સહાયક", pa: "ਏਆਈ ਸਹਾਇਕ" },
    "Sign in": { kn: "ಸೈನ್ ಇನ್", hi: "साइन इन", ta: "உள்நுழைக", te: "సైన్ ఇన్", ml: "സൈൻ ഇൻ", mr: "साइन इन", bn: "সাইন ইন", gu: "સાઇન ઇન", pa: "ਸਾਈਨ ਇਨ" },
    "Sign out": { kn: "ಸೈನ್ ಔಟ್", hi: "साइन आउट", ta: "வெளியேறு", te: "సైన్ అవుట్", ml: "സൈൻ ഔട്ട്", mr: "साइन आउट", bn: "সাইন আউট", gu: "સાઇન આઉટ", pa: "ਸਾਈਨ ਆਉਟ" },
    "My dashboard": { kn: "ನನ್ನ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", hi: "मेरा डैशबोर्ड", ta: "என் டாஷ்போர்டு", te: "నా డాష్‌బోర్డ్", ml: "എന്റെ ഡാഷ്‌ബോർഡ്", mr: "माझा डॅशबोर्ड", bn: "আমার ড্যাশবোর্ড", gu: "મારું ડેશબોર્ડ", pa: "ਮੇਰਾ ਡੈਸ਼ਬੋਰਡ" },
    "My profile": { kn: "ನನ್ನ ಪ್ರೊಫೈಲ್", hi: "मेरी प्रोफ़ाइल", ta: "என் சுயவிவரம்", te: "నా ప్రొఫైల్", ml: "എന്റെ പ്രൊഫൈൽ", mr: "माझे प्रोफाइल", bn: "আমার প্রোফাইল", gu: "મારી પ્રોફાઇલ", pa: "ਮੇਰੀ ਪ੍ਰੋਫ਼ਾਈਲ" },
    "Preferences": { kn: "ಆದ್ಯತೆಗಳು", hi: "प्राथमिकताएँ", ta: "விருப்பங்கள்", te: "ప్రాధాన్యతలు", ml: "മുൻഗണനകൾ", mr: "प्राधान्ये", bn: "পছন্দসমূহ", gu: "પસંદગીઓ", pa: "ਤਰਜੀਹਾਂ" },
    "Search": { kn: "ಹುಡುಕಿ", hi: "खोजें", ta: "தேடு", te: "వెతకండి", ml: "തിരയുക", mr: "शोधा", bn: "খুঁজুন", gu: "શોધો", pa: "ਖੋਜੋ" },
    "Filters": { kn: "ಫಿಲ್ಟರ್‌ಗಳು", hi: "फ़िल्टर", ta: "வடிகட்டிகள்", te: "ఫిల్టర్లు", ml: "ഫിൽട്ടറുകൾ", mr: "फिल्टर", bn: "ফিল্টার", gu: "ફિલ્ટર", pa: "ਫਿਲਟਰ" },
    "Reset": { kn: "ಮರುಹೊಂದಿಸಿ", hi: "रीसेट", ta: "மீட்டமை", te: "రీసెట్", ml: "പുനഃക്രമീകരിക്കുക", mr: "रीसेट", bn: "রিসেট", gu: "રીસેટ", pa: "ਰੀਸੈੱਟ" },
    "Overview": { kn: "ಅವಲೋಕನ", hi: "सारांश", ta: "மேலோட்டம்", te: "అవలోకనం", ml: "അവലോകനം", mr: "आढावा", bn: "সারাংশ", gu: "ઝાંખી", pa: "ਸਾਰ" },
    "Eligibility": { kn: "ಅರ್ಹತೆ", hi: "पात्रता", ta: "தகுதி", te: "అర్హత", ml: "യോഗ്യത", mr: "पात्रता", bn: "যোগ্যতা", gu: "પાત્રતા", pa: "ਯੋਗਤਾ" },
    "Documents": { kn: "ದಾಖಲೆಗಳು", hi: "दस्तावेज़", ta: "ஆவணங்கள்", te: "పత్రాలు", ml: "രേഖകൾ", mr: "कागदपत्रे", bn: "নথি", gu: "દસ્તાવેજો", pa: "ਦਸਤਾਵੇਜ਼" },
    "How to apply": { kn: "ಅರ್ಜಿ ಹೇಗೆ ಸಲ್ಲಿಸುವುದು", hi: "आवेदन कैसे करें", ta: "விண்ணப்பிப்பது எப்படி", te: "దరఖాస్తు ఎలా చేయాలి", ml: "എങ്ങനെ അപേക്ഷിക്കാം", mr: "अर्ज कसा करावा", bn: "আবেদন কীভাবে করবেন", gu: "અરજી કેવી રીતે કરવી", pa: "ਅਰਜ਼ੀ ਕਿਵੇਂ ਦੇਣੀ ਹੈ" },
    "Sources": { kn: "ಮೂಲಗಳು", hi: "स्रोत", ta: "மூலங்கள்", te: "మూలాలు", ml: "സ്രോതസ്സുകൾ", mr: "स्रोत", bn: "উৎস", gu: "સ્રોત", pa: "ਸਰੋਤ" },
    "Save changes": { kn: "ಬದಲಾವಣೆಗಳನ್ನು ಉಳಿಸಿ", hi: "बदलाव सहेजें", ta: "மாற்றங்களை சேமி", te: "మార్పులను సేవ్ చేయండి", ml: "മാറ്റങ്ങൾ സംരക്ഷിക്കുക", mr: "बदल जतन करा", bn: "পরিবর্তন সংরক্ষণ করুন", gu: "ફેરફારો સાચવો", pa: "ਬਦਲਾਅ ਸੰਭਾਲੋ" },
    "Language": { kn: "ಭಾಷೆ", hi: "भाषा", ta: "மொழி", te: "భాష", ml: "ഭാഷ", mr: "भाषा", bn: "ভাষা", gu: "ભાષા", pa: "ਭਾਸ਼ਾ" },
    "All states and Union Territories": { kn: "ಎಲ್ಲಾ ರಾಜ್ಯಗಳು ಮತ್ತು ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶಗಳು", hi: "सभी राज्य और केंद्र शासित प्रदेश", ta: "அனைத்து மாநிலங்களும் யூனியன் பிரதேசங்களும்", te: "అన్ని రాష్ట్రాలు మరియు కేంద్రపాలిత ప్రాంతాలు", ml: "എല്ലാ സംസ്ഥാനങ്ങളും കേന്ദ്രഭരണ പ്രദേശങ്ങളും", mr: "सर्व राज्ये आणि केंद्रशासित प्रदेश", bn: "সব রাজ্য ও কেন্দ্রশাসিত অঞ্চল", gu: "બધાં રાજ્યો અને કેન્દ્રશાસિત પ્રદેશો", pa: "ਸਾਰੇ ਰਾਜ ਅਤੇ ਕੇਂਦਰ ਸ਼ਾਸਿਤ ਪ੍ਰਦੇਸ਼" },
    "Central and matching state or UT": { kn: "ಕೇಂದ್ರ ಮತ್ತು ಆಯ್ದ ರಾಜ್ಯ ಅಥವಾ ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶ", hi: "केंद्र और चुना हुआ राज्य या केंद्र शासित प्रदेश", ta: "மத்திய அரசும் தேர்ந்த மாநிலம் அல்லது யூனியன் பிரதேசமும்", te: "కేంద్రం మరియు ఎంచుకున్న రాష్ట్రం లేదా కేంద్రపాలిత ప్రాంతం", ml: "കേന്ദ്രവും തിരഞ്ഞെടുത്ത സംസ്ഥാനമോ കേന്ദ്രഭരണ പ്രദേശമോ", mr: "केंद्र आणि निवडलेले राज्य किंवा केंद्रशासित प्रदेश", bn: "কেন্দ্র এবং নির্বাচিত রাজ্য বা কেন্দ্রশাসিত অঞ্চল", gu: "કેન્દ્ર અને પસંદ કરેલું રાજ્ય અથવા કેન્દ્રશાસિત પ્રદેશ", pa: "ਕੇਂਦਰ ਅਤੇ ਚੁਣਿਆ ਰਾਜ ਜਾਂ ਕੇਂਦਰ ਸ਼ਾਸਿਤ ਪ੍ਰਦੇਸ਼" },
    "Central only": { kn: "ಕೇವಲ ಕೇಂದ್ರ", hi: "केवल केंद्र", ta: "மத்திய அரசு மட்டும்", te: "కేంద్రం మాత్రమే", ml: "കേന്ദ്രം മാത്രം", mr: "फक्त केंद्र", bn: "শুধু কেন্দ্র", gu: "ફક્ત કેન્દ્ર", pa: "ਸਿਰਫ਼ ਕੇਂਦਰ" },
    "Selected state or UT only": { kn: "ಆಯ್ದ ರಾಜ್ಯ ಅಥವಾ ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶ ಮಾತ್ರ", hi: "केवल चुना हुआ राज्य या केंद्र शासित प्रदेश", ta: "தேர்ந்த மாநிலம் அல்லது யூனியன் பிரதேசம் மட்டும்", te: "ఎంచుకున్న రాష్ట్రం లేదా కేంద్రపాలిత ప్రాంతం మాత్రమే", ml: "തിരഞ്ഞെടുത്ത സംസ്ഥാനം അല്ലെങ്കിൽ കേന്ദ്രഭരണ പ്രദേശം മാത്രം", mr: "फक्त निवडलेले राज्य किंवा केंद्रशासित प्रदेश", bn: "শুধু নির্বাচিত রাজ্য বা কেন্দ্রশাসিত অঞ্চল", gu: "ફક્ત પસંદ કરેલું રાજ્ય અથવા કેન્દ્રશાસિત પ્રદેશ", pa: "ਸਿਰਫ਼ ਚੁਣਿਆ ਰਾਜ ਜਾਂ ਕੇਂਦਰ ਸ਼ਾਸਿਤ ਪ੍ਰਦੇਸ਼" },
    "State or Union Territory": { kn: "ರಾಜ್ಯ ಅಥವಾ ಕೇಂದ್ರಾಡಳಿತ ಪ್ರದೇಶ", hi: "राज्य या केंद्र शासित प्रदेश", ta: "மாநிலம் அல்லது யூனியன் பிரதேசம்", te: "రాష్ట్రం లేదా కేంద్రపాలిత ప్రాంతం", ml: "സംസ്ഥാനം അല്ലെങ്കിൽ കേന്ദ്രഭരണ പ്രദേശം", mr: "राज्य किंवा केंद्रशासित प्रदेश", bn: "রাজ্য বা কেন্দ্রশাসিত অঞ্চল", gu: "રાજ્ય અથવા કેન્દ્રશાસિત પ્રદેશ", pa: "ਰਾਜ ਜਾਂ ਕੇਂਦਰ ਸ਼ਾਸਿਤ ਪ੍ਰਦੇਸ਼" },
    "Government level": { kn: "ಸರ್ಕಾರದ ಮಟ್ಟ", hi: "सरकार का स्तर", ta: "அரசு நிலை", te: "ప్రభుత్వ స్థాయి", ml: "സർക്കാർ തലം", mr: "शासन स्तर", bn: "সরকারের স্তর", gu: "સરકારનું સ્તર", pa: "ਸਰਕਾਰ ਦਾ ਪੱਧਰ" },
    "Categories": { kn: "ವರ್ಗಗಳು", hi: "श्रेणियाँ", ta: "வகைகள்", te: "వర్గాలు", ml: "വിഭാഗങ്ങൾ", mr: "श्रेणी", bn: "বিভাগ", gu: "શ્રેણીઓ", pa: "ਸ਼੍ਰੇਣੀਆਂ" },
    "Check these conditions": { kn: "ಈ ಷರತ್ತುಗಳನ್ನು ಪರಿಶೀಲಿಸಿ", hi: "इन शर्तों की जाँच करें", ta: "இந்த நிபந்தனைகளை சரிபார்க்கவும்", te: "ఈ షరతులను తనిఖీ చేయండి", ml: "ഈ വ്യവസ്ഥകൾ പരിശോധിക്കുക", mr: "या अटी तपासा", bn: "এই শর্তগুলো যাচাই করুন", gu: "આ શરતો તપાસો", pa: "ਇਹ ਸ਼ਰਤਾਂ ਜਾਂਚੋ" },
    "Listen with Prism": { kn: "ಪ್ರಿಸಂನಲ್ಲಿ ಕೇಳಿ", hi: "प्रिज़्म से सुनें", ta: "பிரிஸம் மூலம் கேளுங்கள்", te: "ప్రిజమ్‌తో వినండి", ml: "പ്രിസം വഴി കേൾക്കുക", mr: "प्रिझमने ऐका", bn: "প্রিজম দিয়ে শুনুন", gu: "પ્રિઝમથી સાંભળો", pa: "ਪ੍ਰਿਜ਼ਮ ਨਾਲ ਸੁਣੋ" },
    "Copy response": { kn: "ಉತ್ತರವನ್ನು ನಕಲಿಸಿ", hi: "उत्तर कॉपी करें", ta: "பதிலை நகலெடு", te: "సమాధానాన్ని కాపీ చేయండి", ml: "മറുപടി പകർത്തുക", mr: "उत्तर कॉपी करा", bn: "উত্তর কপি করুন", gu: "જવાબ કૉપિ કરો", pa: "ਜਵਾਬ ਕਾਪੀ ਕਰੋ" },
    "Replay": { kn: "ಮತ್ತೆ ಕೇಳಿ", hi: "फिर चलाएँ", ta: "மீண்டும் இயக்கு", te: "మళ్లీ వినండి", ml: "വീണ്ടും കേൾക്കുക", mr: "पुन्हा ऐका", bn: "আবার চালান", gu: "ફરી વગાડો", pa: "ਦੁਬਾਰਾ ਚਲਾਓ" },
    "Stop": { kn: "ನಿಲ್ಲಿಸಿ", hi: "रोकें", ta: "நிறுத்து", te: "ఆపండి", ml: "നിർത്തുക", mr: "थांबवा", bn: "থামান", gu: "બંધ કરો", pa: "ਰੋਕੋ" },
    "Pending": { kn: "ಬಾಕಿ", hi: "लंबित", ta: "நிலுவையில்", te: "పెండింగ్", ml: "ശേഷിക്കുന്നു", mr: "प्रलंबित", bn: "অপেক্ষমাণ", gu: "બાકી", pa: "ਬਕਾਇਆ" },
    "Available": { kn: "ಲಭ್ಯ", hi: "उपलब्ध", ta: "உள்ளது", te: "అందుబాటులో ఉంది", ml: "ലഭ്യം", mr: "उपलब्ध", bn: "আছে", gu: "ઉપલબ્ધ", pa: "ਉਪਲਬਧ" },
    "Yes": { kn: "ಹೌದು", hi: "हाँ", ta: "ஆம்", te: "అవును", ml: "അതെ", mr: "होय", bn: "হ্যাঁ", gu: "હા", pa: "ਹਾਂ" },
    "No": { kn: "ಇಲ್ಲ", hi: "नहीं", ta: "இல்லை", te: "కాదు", ml: "അല്ല", mr: "नाही", bn: "না", gu: "ના", pa: "ਨਹੀਂ" },
    "I don't know": { kn: "ನನಗೆ ಗೊತ್ತಿಲ್ಲ", hi: "मुझे नहीं पता", ta: "எனக்கு தெரியவில்லை", te: "నాకు తెలియదు", ml: "എനിക്കറിയില്ല", mr: "मला माहीत नाही", bn: "আমি জানি না", gu: "મને ખબર નથી", pa: "ਮੈਨੂੰ ਨਹੀਂ ਪਤਾ" },
    "Some interface text is still shown in English.": {
      kn: "ಕೆಲವು ಇಂಟರ್ಫೇಸ್ ಪಠ್ಯ ಇನ್ನೂ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿದೆ.",
      hi: "कुछ इंटरफ़ेस पाठ अभी भी अंग्रेज़ी में है।",
      ta: "சில இடைமுக உரை இன்னும் ஆங்கிலத்தில் உள்ளது.",
      te: "కొంత ఇంటర్‌ఫేస్ పాఠ్యం ఇంకా ఆంగ్లంలోనే ఉంది.",
      ml: "ചില ഇന്റർഫേസ് വാചകം ഇപ്പോഴും ഇംഗ്ലീഷിലാണ്.",
      mr: "काही इंटरफेस मजकूर अजून इंग्रजीत आहे.",
      bn: "কিছু ইন্টারফেস লেখা এখনও ইংরেজিতে আছে।",
      gu: "કેટલુંક ઇન્ટરફેસ લખાણ હજુ અંગ્રેજીમાં છે.",
      pa: "ਕੁਝ ਇੰਟਰਫੇਸ ਲਿਖਤ ਅਜੇ ਵੀ ਅੰਗਰੇਜ਼ੀ ਵਿੱਚ ਹੈ।"
    },
    "Government schemes and services, connected to you.": {
      kn: "ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ಮತ್ತು ಸೇವೆಗಳು, ನಿಮಗೆ ಜೋಡಿಸಲಾಗಿದೆ.",
      hi: "सरकारी योजनाएँ और सेवाएँ, आपसे जुड़ी हुईं।",
      ta: "அரசு திட்டங்களும் சேவைகளும், உங்களுடன் இணைக்கப்பட்டுள்ளன.",
      te: "ప్రభుత్వ పథకాలు మరియు సేవలు, మీకు అనుసంధానించబడ్డాయి.",
      ml: "സർക്കാർ പദ്ധതികളും സേവനങ്ങളും, നിങ്ങളുമായി ബന്ധിപ്പിച്ചിരിക്കുന്നു.",
      mr: "सरकारी योजना आणि सेवा, तुमच्याशी जोडलेल्या.",
      bn: "সরকারি প্রকল্প ও পরিষেবা, আপনার সঙ্গে যুক্ত।",
      gu: "સરકારી યોજનાઓ અને સેવાઓ, તમારી સાથે જોડાયેલી.",
      pa: "ਸਰਕਾਰੀ ਯੋਜਨਾਵਾਂ ਅਤੇ ਸੇਵਾਵਾਂ, ਤੁਹਾਡੇ ਨਾਲ ਜੁੜੀਆਂ।"
    },
    [NOTE]: {
      kn: "ಪರಿಶೀಲಿತ ಅನುವಾದ ಇಲ್ಲದಿದ್ದಾಗ ಅಧಿಕೃತ ಯೋಜನೆ ಪಠ್ಯವು ಮೂಲ ಭಾಷೆಯಲ್ಲಿಯೇ ಇರುತ್ತದೆ.",
      hi: "सत्यापित अनुवाद न होने पर आधिकारिक योजना पाठ स्रोत भाषा में रहता है।",
      ta: "சரிபார்க்கப்பட்ட மொழிபெயர்ப்பு இல்லையென்றால் அதிகாரப்பூர்வ திட்ட உரை மூல மொழியிலேயே இருக்கும்.",
      te: "ధృవీకరించిన అనువాదం లేకపోతే అధికారిక పథక పాఠ్యం మూల భాషలోనే ఉంటుంది.",
      ml: "പരിശോധിച്ച വിവർത്തനം ഇല്ലെങ്കിൽ ഔദ്യോഗിക പദ്ധതി വാചകം മൂലഭാഷയിൽ തന്നെ തുടരും.",
      mr: "पडताळलेला अनुवाद नसेल तर अधिकृत योजना मजकूर मूळ भाषेत राहतो.",
      bn: "যাচাই করা অনুবাদ না থাকলে সরকারি প্রকল্পের পাঠ মূল ভাষাতেই থাকে।",
      gu: "ચકાસાયેલ અનુવાદ ન હોય ત્યારે અધિકૃત યોજનાનું લખાણ મૂળ ભાષામાં રહે છે.",
      pa: "ਜਦੋਂ ਪ੍ਰਮਾਣਿਤ ਅਨੁਵਾਦ ਨਾ ਹੋਵੇ ਤਾਂ ਅਧਿਕਾਰਤ ਯੋਜਨਾ ਲਿਖਤ ਸਰੋਤ ਭਾਸ਼ਾ ਵਿੱਚ ਰਹਿੰਦੀ ਹੈ।"
    }
  };

  let untranslated = 0;

  function currentLanguage() {
    const fromApi = window.SchemeSathiAPI?.getCachedPreferredLanguage?.();
    const stored = fromApi || localStorage.getItem(STORAGE_KEY) || "en";
    const code = String(stored).toLowerCase().split("-")[0];
    return LANGUAGES.some(([value]) => value === code) ? code : "en";
  }

  function phraseTable() {
    return Object.assign({}, PHRASES, window.GOVNEXUS_PHRASES || {});
  }

  function translate(text, language) {
    if (!text || language === "en") return text;
    const table = phraseTable();
    return table[text]?.[language] || null;
  }

  function t(text, language = currentLanguage()) {
    if (!text) return text;
    return translate(String(text), language) || text;
  }

  let applying = false;

  function apply(language = currentLanguage()) {
    if (applying) return language;
    applying = true;
    try {
    untranslated = 0;
    document.documentElement.lang = language;
    const skip = node => node.parentElement?.closest("[data-i18n-skip], script, style");
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => {
      if (!node.nodeValue || skip(node)) return;
      if (!node.govnexusSource) node.govnexusSource = node.nodeValue;
      const source = node.govnexusSource;
      const trimmed = source.trim();
      if (!trimmed) return;
      const translated = translate(trimmed, language);
      if (language !== "en" && !translated && /[A-Za-z]{3,}/.test(trimmed) && trimmed.length < 180) {
        untranslated += 1;
      }
      const padStart = source.match(/^\s*/)?.[0] || "";
      const padEnd = source.match(/\s*$/)?.[0] || "";
      const nextValue = translated ? `${padStart}${translated}${padEnd}` : source;
      if (node.nodeValue !== nextValue) node.nodeValue = nextValue;
    });
    document.querySelectorAll("input[placeholder], textarea[placeholder]").forEach(field => {
      if (!field.dataset.i18nPlaceholder) field.dataset.i18nPlaceholder = field.placeholder;
      const translated = translate(field.dataset.i18nPlaceholder, language);
      field.placeholder = translated || field.dataset.i18nPlaceholder;
    });
    document.querySelectorAll("[aria-label], [title]").forEach(field => {
      [["aria-label", "i18nAria"], ["title", "i18nTitle"]].forEach(([attribute, key]) => {
        const current = field.getAttribute(attribute);
        if (!current) return;
        if (!field.dataset[key]) field.dataset[key] = current;
        const translated = translate(field.dataset[key], language);
        const next = translated || field.dataset[key];
        if (field.getAttribute(attribute) !== next) field.setAttribute(attribute, next);
      });
    });
    document.querySelectorAll("option").forEach(option => {
      if (!option.dataset.i18nLabel) option.dataset.i18nLabel = option.textContent;
      const translated = translate(option.dataset.i18nLabel.trim(), language);
      if (translated) option.textContent = translated;
      else option.textContent = option.dataset.i18nLabel;
    });
    let note = document.getElementById("govnexus-language-note");
    if (!note) {
      note = document.createElement("p");
      note.id = "govnexus-language-note";
      note.setAttribute("role", "status");
      note.style.cssText = "margin:0;padding:8px 16px;background:#f4f7f8;color:#3d4c5c;font:13px/1.5 'DM Sans',sans-serif;border-bottom:1px solid #e4ebf0";
      document.body.prepend(note);
    }
    note.setAttribute("data-i18n-skip", "");
    note.hidden = language === "en";
    const interfaceNote = language === "en"
      ? ""
      : `${translate(NOTE, language) || NOTE} ${untranslated ? t("Some interface text is still shown in English.") : ""}`.trim();
    note.textContent = interfaceNote;
    const button = document.getElementById("languageButton");
    if (button && !button.querySelector("select")) {
      const label = LANGUAGES.find(([code]) => code === language)?.[1] || "English";
      const text = [...button.childNodes].find(node => node.nodeType === 3 && node.nodeValue.trim());
      if (text) text.nodeValue = ` ${label} `;
    }
    const voice = document.getElementById("voiceLanguage");
    if (voice) {
      const match = `${language}-IN`;
      if ([...voice.options].some(option => option.value === match)) voice.value = match;
    }
    document.dispatchEvent(new CustomEvent("govnexus:language", { detail: { language } }));
    return language;
    } finally {
      applying = false;
    }
  }

  function persist(language) {
    const api = window.SchemeSathiAPI;
    if (api?.cachePreferredLanguage) api.cachePreferredLanguage(language);
    else {
      localStorage.setItem(STORAGE_KEY, language);
      document.documentElement.lang = language;
    }
    apply(language);
  }

  function ensureMenu() {
    let menu = document.getElementById("govnexus-language-menu");
    if (menu) return menu;
    menu = document.createElement("div");
    menu.id = "govnexus-language-menu";
    menu.setAttribute("data-i18n-skip", "");
    menu.hidden = true;
    menu.setAttribute("role", "listbox");
    menu.setAttribute("aria-label", "Language");
    menu.style.cssText = "position:absolute;z-index:40;min-width:180px;padding:8px;background:#fff;border:1px solid #d5e0e8;border-radius:12px;box-shadow:0 12px 30px #0e4d6c22;display:grid;gap:4px";
    LANGUAGES.forEach(([code, label]) => {
      const item = document.createElement("button");
      item.type = "button";
      item.textContent = label;
      item.setAttribute("role", "option");
      item.style.cssText = "text-align:left;border:0;background:transparent;padding:8px 10px;border-radius:8px;font:600 14px 'DM Sans',sans-serif;color:#142033";
      item.addEventListener("click", () => {
        persist(code);
        menu.hidden = true;
      });
      menu.appendChild(item);
    });
    document.body.appendChild(menu);
    document.addEventListener("click", event => {
      if (!menu.hidden && !menu.contains(event.target) && event.target.id !== "languageButton") {
        menu.hidden = true;
      }
    });
    return menu;
  }

  function open(anchor) {
    const menu = ensureMenu();
    const rect = anchor.getBoundingClientRect();
    menu.style.top = `${rect.bottom + window.scrollY + 8}px`;
    menu.style.left = `${Math.max(8, rect.right + window.scrollX - 180)}px`;
    menu.hidden = !menu.hidden;
  }

  function mountButton() {
    if (document.getElementById("languageButton")) return;
    const host = document.querySelector(".header-actions, .top-right, .topbar");
    if (!host) return;
    const button = document.createElement("button");
    button.id = "languageButton";
    button.type = "button";
    button.className = "language-button";
    button.textContent = "English";
    button.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      open(button);
    });
    host.prepend(button);
  }

  const script = document.currentScript;
  if (script?.src && !document.querySelector("link[rel='icon']")) {
    const icon = document.createElement("link");
    icon.rel = "icon";
    icon.type = "image/svg+xml";
    icon.href = script.src.replace(/js\/localization\.js.*$/, "favicon.svg");
    document.head.appendChild(icon);
  }

  window.GovNexusI18n = {
    apply,
    open,
    persist,
    t,
    language: currentLanguage,
    languages: LANGUAGES
  };
  document.addEventListener("DOMContentLoaded", () => {
    mountButton();
    const existing = document.getElementById("languageButton");
    if (existing && !existing.dataset.bound) {
      existing.dataset.bound = "1";
      existing.addEventListener("click", event => {
        event.preventDefault();
        event.stopPropagation();
        open(existing);
      });
    }
    apply();
    const observer = new MutationObserver(() => {
      if (applying) return;
      window.clearTimeout(observer.timer);
      observer.timer = window.setTimeout(() => apply(currentLanguage()), 60);
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  });
})();
