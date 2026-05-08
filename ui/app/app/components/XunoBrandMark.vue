<template>
  <div class="inline-flex w-full items-center">
    <svg
      viewBox="0 0 720 180"
      xmlns="http://www.w3.org/2000/svg"
      class="h-auto w-full overflow-visible drop-shadow-[0_0_28px_rgba(93,255,153,0.16)]"
      role="img"
      aria-labelledby="xuno-brand-title"
    >
      <title id="xuno-brand-title">xuno</title>
      <defs>
        <linearGradient id="xuno-mark-bg" x1="18" y1="14" x2="134" y2="148" gradientUnits="userSpaceOnUse">
          <stop stop-color="#112117" />
          <stop offset="1" stop-color="#050906" />
        </linearGradient>
        <linearGradient id="xuno-mark-stroke" x1="28" y1="24" x2="126" y2="126" gradientUnits="userSpaceOnUse">
          <stop stop-color="#DFFFF0" />
          <stop offset="1" stop-color="#5DFF99" />
        </linearGradient>
        <linearGradient id="xuno-scan-line" x1="178" y1="130" x2="460" y2="130" gradientUnits="userSpaceOnUse">
          <stop stop-color="#5DFF99" stop-opacity="0.9" />
          <stop offset="1" stop-color="#5DFF99" stop-opacity="0.1" />
        </linearGradient>
      </defs>

      <ellipse cx="120" cy="82" rx="118" ry="78" fill="#5DFF99" fill-opacity="0.07" />

      <g transform="translate(16 20)">
        <rect x="0.75" y="0.75" width="135.5" height="135.5" rx="36" fill="url(#xuno-mark-bg)" />
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
        <path d="M34 34L69 68L104 102" stroke="url(#xuno-mark-stroke)" stroke-width="13" stroke-linecap="round" />
        <path d="M34 102L69 68L104 34" stroke="#9BF7BF" stroke-width="13" stroke-linecap="round" />
        <path d="M69 68H116" stroke="#5DFF99" stroke-width="9" stroke-linecap="round" />
        <circle cx="121" cy="68" r="7" fill="#5DFF99" />
        <circle cx="28" cy="24" r="4.5" fill="#DFFFF0" fill-opacity="0.7" />
        <circle cx="109" cy="112" r="4.5" fill="#DFFFF0" fill-opacity="0.32" />
      </g>

      <g transform="translate(178 0)">
        <text
          x="0"
          y="88"
          fill="#F3FFF8"
          font-size="76"
          font-family="'Share Tech Mono', monospace"
          letter-spacing="6"
          v-text="'xuno'"
        />
        <text
          x="2"
          y="120"
          fill="#92B49B"
          font-size="14"
          font-family="'Space Mono', monospace"
          letter-spacing="5"
          v-text="'RESEARCH SEARCH AGENT'"
        />
        <path d="M2 136H288" stroke="url(#xuno-scan-line)" stroke-width="2.5" stroke-linecap="round" />
        <circle cx="296" cy="136" r="4.5" fill="#5DFF99" />
      </g>
    </svg>
  </div>
</template>
