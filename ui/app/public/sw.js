const CACHE_NAME = 'xuno-pwa-v1'
const APP_SHELL = [
  '/',
  '/manifest.webmanifest',
  '/favicon/xuno-mark.svg',
  '/pwa/icon-192.png',
  '/pwa/icon-512.png',
  '/pwa/apple-touch-icon.png',
]

self.addEventListener('install', (event) => {
  self.skipWaiting()
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  )
})

const networkFirst = async (request) => {
  const cache = await caches.open(CACHE_NAME)

  try {
    const response = await fetch(request)
    cache.put(request, response.clone())
    return response
  } catch {
    return (await cache.match(request)) || cache.match('/')
  }
}

const staleWhileRevalidate = async (request) => {
  const cache = await caches.open(CACHE_NAME)
  const cached = await cache.match(request)

  const networkResponse = fetch(request)
    .then((response) => {
      cache.put(request, response.clone())
      return response
    })
    .catch(() => cached)

  return cached || networkResponse
}

self.addEventListener('push', (event) => {
  if (!event.data) return
  let data = {}
  try {
    data = event.data.json()
  } catch {
    data = { title: 'xuno', body: event.data.text() }
  }
  const title = data.title || 'xuno'
  const options = {
    body: data.body || '',
    icon: '/pwa/icon-192.png',
    badge: '/pwa/icon-192.png',
    tag: 'xuno-new-results',
    renotify: true,
    data: { url: '/' },
  }
  event.waitUntil(
    Promise.all([
      self.registration.showNotification(title, options),
      data.badge && 'setAppBadge' in self.navigator
        ? self.navigator.setAppBadge(data.badge)
        : Promise.resolve(),
    ]),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = event.notification.data?.url || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ('focus' in client) return client.focus()
      }
      return self.clients.openWindow(target)
    }),
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return
  if (url.pathname.startsWith('/api/')) return
  if (url.pathname.startsWith('/admin')) return
  if (url.pathname.startsWith('/swagger')) return

  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request))
    return
  }

  event.respondWith(staleWhileRevalidate(request))
})
