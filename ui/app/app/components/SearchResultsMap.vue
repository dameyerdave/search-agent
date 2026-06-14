<script setup lang="ts">
import type { SearchResultMapMarker } from 'types/search-agent'

const { t } = useI18n()

const props = defineProps<{
  markers: SearchResultMapMarker[]
  selectedMarkerId: string | null
  emptyLabel?: string
}>()

const emit = defineEmits<{
  select: [markerId: string]
}>()

const mapElement = ref<HTMLElement | null>(null)
const { width, height } = useElementSize(mapElement)

const TILE_SIZE = 256
const MIN_ZOOM = 2
const MAX_ZOOM = 7
const WHEEL_ZOOM_THRESHOLD = 80
const WHEEL_ZOOM_COOLDOWN_MS = 180

const center = reactive({
  lat: 20,
  lon: 0,
})
const zoom = ref(2)
let dragState: {
  x: number
  y: number
  centerX: number
  centerY: number
} | null = null
let wheelDelta = 0
let lastWheelZoomAt = 0
let wheelResetTimer: ReturnType<typeof setTimeout> | null = null

const project = (lat: number, lon: number, currentZoom: number) => {
  const worldSize = TILE_SIZE * 2 ** currentZoom
  const sinLat = Math.sin((Math.max(Math.min(lat, 85.05112878), -85.05112878) * Math.PI) / 180)
  return {
    x: ((lon + 180) / 360) * worldSize,
    y: (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * worldSize,
  }
}

const unproject = (x: number, y: number, currentZoom: number) => {
  const worldSize = TILE_SIZE * 2 ** currentZoom
  const lon = (x / worldSize) * 360 - 180
  const mercator = Math.PI - (2 * Math.PI * y) / worldSize
  const lat = (180 / Math.PI) * Math.atan(Math.sinh(mercator))
  return { lat, lon }
}

const fitToMarkers = () => {
  if (!props.markers.length || !width.value || !height.value) {
    return
  }

  if (props.markers.length === 1) {
    center.lat = props.markers[0].latitude
    center.lon = props.markers[0].longitude
    zoom.value = 5
    return
  }

  const latitudes = props.markers.map((marker) => marker.latitude)
  const longitudes = props.markers.map((marker) => marker.longitude)
  const minLat = Math.min(...latitudes)
  const maxLat = Math.max(...latitudes)
  const minLon = Math.min(...longitudes)
  const maxLon = Math.max(...longitudes)

  center.lat = (minLat + maxLat) / 2
  center.lon = (minLon + maxLon) / 2

  const safeWidth = Math.max(width.value - 96, 120)
  const safeHeight = Math.max(height.value - 96, 120)

  for (let nextZoom = MAX_ZOOM; nextZoom >= MIN_ZOOM; nextZoom -= 1) {
    const topLeft = project(maxLat, minLon, nextZoom)
    const bottomRight = project(minLat, maxLon, nextZoom)
    if (Math.abs(bottomRight.x - topLeft.x) <= safeWidth && Math.abs(bottomRight.y - topLeft.y) <= safeHeight) {
      zoom.value = nextZoom
      return
    }
  }

  zoom.value = MIN_ZOOM
}

watch(
  () => [props.markers, width.value, height.value],
  () => {
    fitToMarkers()
  },
  { deep: true, immediate: true },
)

const centerPoint = computed(() => project(center.lat, center.lon, zoom.value))

const tiles = computed(() => {
  if (!width.value || !height.value) {
    return []
  }

  const scale = 2 ** zoom.value
  const viewportLeft = centerPoint.value.x - width.value / 2
  const viewportTop = centerPoint.value.y - height.value / 2
  const startX = Math.floor(viewportLeft / TILE_SIZE)
  const endX = Math.floor((centerPoint.value.x + width.value / 2) / TILE_SIZE)
  const startY = Math.floor(viewportTop / TILE_SIZE)
  const endY = Math.floor((centerPoint.value.y + height.value / 2) / TILE_SIZE)

  const visibleTiles = []
  for (let tileX = startX; tileX <= endX; tileX += 1) {
    for (let tileY = startY; tileY <= endY; tileY += 1) {
      if (tileY < 0 || tileY >= scale) {
        continue
      }

      const wrappedX = ((tileX % scale) + scale) % scale
      visibleTiles.push({
        key: `${zoom.value}:${tileX}:${tileY}`,
        src: `https://tile.openstreetmap.org/${zoom.value}/${wrappedX}/${tileY}.png`,
        left: tileX * TILE_SIZE - viewportLeft,
        top: tileY * TILE_SIZE - viewportTop,
      })
    }
  }

  return visibleTiles
})

const positionedMarkers = computed(() => {
  return props.markers
    .map((marker) => {
      const point = project(marker.latitude, marker.longitude, zoom.value)
      const left = point.x - (centerPoint.value.x - width.value / 2)
      const top = point.y - (centerPoint.value.y - height.value / 2)
      const size = Math.min(64, 18 + Math.sqrt(marker.related_result_count) * 10)
      return {
        ...marker,
        left,
        top,
        size,
      }
    })
    .filter(
      (marker) =>
        marker.left >= -80 && marker.left <= width.value + 80 && marker.top >= -80 && marker.top <= height.value + 80,
    )
})

const zoomIn = (step = 1) => {
  zoom.value = Math.min(MAX_ZOOM, zoom.value + step)
}

const zoomOut = (step = 1) => {
  zoom.value = Math.max(MIN_ZOOM, zoom.value - step)
}

const normalizeWheelDelta = (event: WheelEvent) => {
  if (event.deltaMode === 1) {
    return event.deltaY * 16
  }
  if (event.deltaMode === 2) {
    return event.deltaY * Math.max(height.value, 600)
  }
  return event.deltaY
}

const resetWheelDeltaSoon = () => {
  if (wheelResetTimer) {
    clearTimeout(wheelResetTimer)
  }
  wheelResetTimer = setTimeout(() => {
    wheelDelta = 0
    wheelResetTimer = null
  }, 220)
}

const onWheel = (event: WheelEvent) => {
  const nextDelta = normalizeWheelDelta(event)
  if ((wheelDelta > 0 && nextDelta < 0) || (wheelDelta < 0 && nextDelta > 0)) {
    wheelDelta = 0
  }

  wheelDelta += nextDelta
  resetWheelDeltaSoon()

  if (Math.abs(wheelDelta) < WHEEL_ZOOM_THRESHOLD || Date.now() - lastWheelZoomAt < WHEEL_ZOOM_COOLDOWN_MS) {
    return
  }

  if (wheelDelta < 0) {
    zoomIn()
  } else {
    zoomOut()
  }

  lastWheelZoomAt = Date.now()
  wheelDelta = 0
}

const focusMarker = (marker: SearchResultMapMarker) => {
  emit('select', marker.id)
  center.lat = marker.latitude
  center.lon = marker.longitude
  zoomIn(2)
}

const startDrag = (event: PointerEvent) => {
  if (!mapElement.value) {
    return
  }

  mapElement.value.setPointerCapture(event.pointerId)
  dragState = {
    x: event.clientX,
    y: event.clientY,
    centerX: centerPoint.value.x,
    centerY: centerPoint.value.y,
  }
}

const moveDrag = (event: PointerEvent) => {
  if (!dragState) {
    return
  }

  const deltaX = event.clientX - dragState.x
  const deltaY = event.clientY - dragState.y
  const nextCenter = unproject(dragState.centerX - deltaX, dragState.centerY - deltaY, zoom.value)
  center.lat = nextCenter.lat
  center.lon = nextCenter.lon
}

const stopDrag = (event: PointerEvent) => {
  if (mapElement.value?.hasPointerCapture(event.pointerId)) {
    mapElement.value.releasePointerCapture(event.pointerId)
  }
  dragState = null
}

onUnmounted(() => {
  if (wheelResetTimer) {
    clearTimeout(wheelResetTimer)
  }
})
</script>

<template>
  <div
    ref="mapElement"
    class="relative h-[420px] touch-none overflow-hidden rounded-[1.5rem] border border-[var(--line)] bg-[#08100a]"
    @pointerdown="startDrag"
    @pointermove="moveDrag"
    @pointerup="stopDrag"
    @pointercancel="stopDrag"
    @pointerleave="stopDrag"
    @wheel.prevent="onWheel"
  >
    <div
      class="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(93,255,153,0.16),transparent_28%),linear-gradient(180deg,rgba(255,255,255,0.04),transparent_45%)]"
    />

    <img
      v-for="tile in tiles"
      :key="tile.key"
      :src="tile.src"
      :alt="t('map.tiles.alt')"
      class="pointer-events-none absolute h-64 w-64 max-w-none select-none"
      :style="{ left: `${tile.left}px`, top: `${tile.top}px` }"
      loading="lazy"
      draggable="false"
    />

    <button
      v-for="marker in positionedMarkers"
      :key="marker.id"
      type="button"
      class="absolute flex items-center justify-center rounded-full border border-white/30 bg-[rgba(93,255,153,0.25)] font-semibold text-white shadow-[0_0_28px_rgba(93,255,153,0.18)] backdrop-blur-sm transition-transform hover:scale-105"
      :class="selectedMarkerId === marker.id ? 'ring-2 ring-white/70' : ''"
      :style="{
        left: `${marker.left}px`,
        top: `${marker.top}px`,
        width: `${marker.size}px`,
        height: `${marker.size}px`,
        transform: 'translate(-50%, -50%)',
        fontSize: marker.related_result_count > 99 ? '0.72rem' : '0.85rem',
      }"
      :title="`${marker.name}: ${marker.related_result_count}`"
      @pointerdown.stop
      @click.stop="emit('select', marker.id)"
      @dblclick.stop.prevent="focusMarker(marker)"
    >
      {{ marker.related_result_count }}
    </button>

    <div class="absolute top-3 right-3 flex flex-col gap-2" @pointerdown.stop @wheel.stop>
      <button
        type="button"
        class="terminal-button terminal-button-secondary h-10 w-10 p-0 text-lg"
        @click.stop="zoomIn()"
      >
        +
      </button>
      <button
        type="button"
        class="terminal-button terminal-button-secondary h-10 w-10 p-0 text-lg"
        @click.stop="zoomOut()"
      >
        -
      </button>
      <button
        type="button"
        class="terminal-button terminal-button-secondary px-4 py-2 text-[11px]"
        @click.stop="fitToMarkers"
      >
        {{ t('map.controls.fit') }}
      </button>
    </div>

    <div
      class="absolute bottom-3 left-3 rounded-full border border-[var(--line)] bg-black/55 px-3 py-1 text-[11px] text-[var(--muted)]"
    >
      {{ t('map.tiles.attribution') }}
    </div>

    <div
      v-if="!markers.length"
      class="absolute inset-0 flex items-center justify-center px-6 text-center text-sm text-[var(--muted)]"
    >
      {{ props.emptyLabel || t('map.empty_map') }}
    </div>
  </div>
</template>
