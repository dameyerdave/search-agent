<template>
  <div class="xuno-loading-mark" :class="{ 'xuno-loading-mark--sm': small }" role="status" :aria-label="label">
    <svg viewBox="0 0 136 136" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <defs>
        <linearGradient id="xuno-loading-mark-bg" x1="2" y1="-4" x2="118" y2="130" gradientUnits="userSpaceOnUse">
          <stop stop-color="#112117" />
          <stop offset="1" stop-color="#050906" />
        </linearGradient>
        <linearGradient id="xuno-loading-mark-stroke" x1="12" y1="4" x2="110" y2="106" gradientUnits="userSpaceOnUse">
          <stop stop-color="#DFFFF0" />
          <stop offset="1" stop-color="#5DFF99" />
        </linearGradient>
      </defs>

      <rect x="0.75" y="0.75" width="135.5" height="135.5" rx="36" fill="url(#xuno-loading-mark-bg)" />
      <rect
        x="0.75"
        y="0.75"
        width="135.5"
        height="135.5"
        rx="36"
        stroke="#5DFF99"
        stroke-opacity="0.34"
        stroke-width="1.5"
      />
      <path d="M34 34L69 68L104 102" stroke="url(#xuno-loading-mark-stroke)" stroke-width="13" stroke-linecap="round" />
      <path d="M34 102L69 68L104 34" stroke="#9BF7BF" stroke-width="13" stroke-linecap="round" />
      <path d="M69 68H116" stroke="#5DFF99" stroke-width="9" stroke-linecap="round" />
      <circle cx="121" cy="68" r="7" fill="#5DFF99" />
      <circle cx="28" cy="24" r="4.5" fill="#DFFFF0" fill-opacity="0.7" />
      <circle cx="109" cy="112" r="4.5" fill="#DFFFF0" fill-opacity="0.32" />
    </svg>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label?: string; small?: boolean }>()
</script>
