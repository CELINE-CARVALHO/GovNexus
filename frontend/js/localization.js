/* Small interface-only localization layer.
 * Government guidance and service facts are never machine-translated here.
 * Missing strings intentionally remain in English.
 */
(() => {
  const translations = {
    kn: {
      "Preferred language": "ಆದ್ಯತೆಯ ಭಾಷೆ",
      "District / City": "ಜಿಲ್ಲೆ / ನಗರ",
      "Save changes": "ಬದಲಾವಣೆಗಳನ್ನು ಉಳಿಸಿ",
      "Change password": "ಪಾಸ್‌ವರ್ಡ್ ಬದಲಾಯಿಸಿ",
      "AI assistant": "AI ಸಹಾಯಕ"
    },
    hi: {
      "Preferred language": "पसंदीदा भाषा",
      "District / City": "जिला / शहर",
      "Save changes": "बदलाव सहेजें",
      "Change password": "पासवर्ड बदलें",
      "AI assistant": "AI सहायक"
    }
  };

  function apply() {
    const language = document.documentElement.lang || "en";
    const dictionary = translations[language] || {};
    document.querySelectorAll("[data-i18n]").forEach(element => {
      const source = element.dataset.i18n;
      const translated = dictionary[source];
      if (translated) element.textContent = translated;
    });
  }

  window.SchemeSathiLocalization = { apply };
  document.addEventListener("DOMContentLoaded", apply);
})();
