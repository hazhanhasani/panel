import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import HttpApi from 'i18next-http-backend'
import { initReactI18next } from 'react-i18next'
import { joinURL } from 'ufo'

const applyBluePanelBranding = () => {
  const branding: Record<string, Record<string, string>> = {
    en: {
      pasarguard: 'BluePanel',
      'donation.title': 'Support BluePanel',
      'donation.message': 'Your support helps us improve BluePanel and build better features for everyone!',
    },
    fa: {
      pasarguard: 'BluePanel',
      'donation.title': 'حمایت از BluePanel',
      'donation.message': 'حمایت شما به توسعه و بهبود BluePanel کمک می‌کند.',
    },
    ru: {
      pasarguard: 'BluePanel',
      'donation.title': 'Поддержать BluePanel',
      'donation.message': 'Ваша поддержка помогает развивать и улучшать BluePanel.',
    },
    zh: {
      pasarguard: 'BluePanel',
      'donation.title': '支持 BluePanel',
      'donation.message': '您的支持有助于持续改进 BluePanel。',
    },
  }

  for (const [lang, values] of Object.entries(branding)) {
    for (const [key, value] of Object.entries(values)) {
      i18n.addResource(lang, 'translation', key, value)
    }
  }
}

i18n.on('loaded', applyBluePanelBranding)

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .use(HttpApi)
  .init(
    {
      debug: import.meta.env.NODE_ENV === 'development',
      returnNull: false,
      fallbackLng: 'en',
      interpolation: {
        escapeValue: false,
      },
      react: {
        useSuspense: true,
      },
      load: 'languageOnly',
      detection: {
        caches: ['localStorage'],
      },
      backend: {
        loadPath: joinURL(import.meta.env.BASE_URL, `statics/locales/{{lng}}.json`),
      },
    },
    function (err) {
      if (err) {
        console.error('i18next initialization error:', err)
      }
      applyBluePanelBranding()
      const lang = i18n.language
      document.documentElement.lang = lang
      document.documentElement.setAttribute('dir', i18n.dir())
    },
  )

export default i18n
