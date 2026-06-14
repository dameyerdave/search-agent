import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'node:url'

const appDir = fileURLToPath(new URL('./app', import.meta.url))

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  ssr: false,
  app: {
    head: {
      title: 'xuno | Search Agent',
      meta: [
        { name: 'theme-color', content: '#040604' },
        { name: 'application-name', content: 'xuno' },
        { name: 'mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-status-bar-style', content: 'black-translucent' },
        { name: 'apple-mobile-web-app-title', content: 'xuno' },
      ],
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon/xuno-mark.svg' },
        { rel: 'manifest', href: '/manifest.webmanifest' },
        { rel: 'apple-touch-icon', href: '/pwa/apple-touch-icon.png' },
      ],
    },
  },
  css: ['./app/assets/css/main.css'],
  nitro: {
    devProxy: {
      '/api/v1': `http://api:${process.env.DJANGO_PORT || '5000'}/api/v1`,
      // drf-spectacular swagger UI
      '/swagger': `http://api:${process.env.DJANGO_PORT || '5000'}/api/v1/schema/swagger-ui`,
      '/admin': `http://api:${process.env.DJANGO_PORT || '5000'}/admin`,
      '/media': `http://api:${process.env.DJANGO_PORT || '5000'}/media`,
      '/static': `http://api:${process.env.DJANGO_PORT || '5000'}/static`,
    },
  },
  runtimeConfig: {
    public: {
      baseURL: process.env.NUXT_PUBLIC_API_URL || '',
    },
  },
  vite: {
    plugins: [tailwindcss()],
  },
  devtools: { enabled: true },
  modules: ['@nuxt/ui', '@nuxt/eslint', '@pinia/nuxt', '@vueuse/nuxt', '@nuxtjs/i18n'],
  i18n: {
    restructureDir: '',
    strategy: 'prefix_except_default',
    defaultLocale: 'en',
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'i18n_redirected',
      redirectOn: 'root',
    },
    locales: [
      {
        code: 'en',
        name: 'English',
        file: 'en.json',
      },
    ],
    langDir: 'app/locales',
  },
  devServer: {
    host: '0.0.0.0',
    port: parseInt(process.env.UI_PORT || '8077', 10),
  },
  alias: {
    components: `${appDir}/components`,
    stores: `${appDir}/stores`,
    types: `${appDir}/types`,
    utils: `${appDir}/utils`,
    errors: `${appDir}/utils/errors`,
  },
})
