import { getErrorMessage } from 'errors'

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)))
}

export const usePushNotificationsStore = defineStore('pushNotificationsStore', () => {
  const api = useSearchAgentApi()
  const config = useRuntimeConfig()
  const { t } = useI18n()
  const toast = useToast()

  const vapidPublicKey = config.public.vapidPublicKey as string
  const isSupported = ref(false)
  const permission = ref<NotificationPermission>('default')
  const isSubscribed = ref(false)
  const isRequesting = ref(false)

  const canEnable = computed(() => isSupported.value && permission.value !== 'denied')
  const isDenied = computed(() => permission.value === 'denied')

  const syncState = () => {
    if (!import.meta.client) return
    isSupported.value = 'Notification' in window && 'serviceWorker' in navigator && 'PushManager' in window && !!vapidPublicKey
    if (isSupported.value) {
      permission.value = Notification.permission
    }
  }

  const checkSubscription = async () => {
    if (!isSupported.value) return
    try {
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.getSubscription()
      isSubscribed.value = !!sub
    } catch {
      isSubscribed.value = false
    }
  }

  const subscribe = async () => {
    if (!isSupported.value || !vapidPublicKey) return
    try {
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
      })
      const json = sub.toJSON()
      await api.post('/api/v1/push-subscriptions/', {
        endpoint: json.endpoint,
        p256dh: json.keys?.p256dh,
        auth: json.keys?.auth,
      })
      isSubscribed.value = true
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('push.subscribe_failed'), color: 'error' })
    }
  }

  const unsubscribe = async () => {
    try {
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.getSubscription()
      if (sub) {
        await api.delete(`/api/v1/push-subscriptions/${encodeURIComponent(sub.endpoint)}/`).catch(() => {})
        await sub.unsubscribe()
      }
      isSubscribed.value = false
    } catch (error: unknown) {
      toast.add({ title: getErrorMessage(error) || t('push.unsubscribe_failed'), color: 'error' })
    }
  }

  const requestAndSubscribe = async () => {
    if (!isSupported.value || isRequesting.value) return
    isRequesting.value = true
    try {
      const result = await Notification.requestPermission()
      permission.value = result
      if (result === 'granted') {
        await subscribe()
      }
    } finally {
      isRequesting.value = false
    }
  }

  const initForUser = async () => {
    syncState()
    if (!isSupported.value) return
    await checkSubscription()
    if (permission.value === 'granted' && !isSubscribed.value) {
      await subscribe()
    }
  }

  const resetState = () => {
    isSubscribed.value = false
  }

  return {
    isSupported,
    permission,
    isSubscribed,
    isRequesting,
    canEnable,
    isDenied,
    syncState,
    checkSubscription,
    subscribe,
    unsubscribe,
    requestAndSubscribe,
    initForUser,
    resetState,
  }
})
