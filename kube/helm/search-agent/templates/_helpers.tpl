{{/*
Common labels shared by every resource in the chart.
*/}}
{{- define "search-agent.labels" -}}
app.kubernetes.io/part-of: search-agent
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels for a given component.
Usage: {{ include "search-agent.selectorLabels" (dict "component" "api") }}
*/}}
{{- define "search-agent.selectorLabels" -}}
app.kubernetes.io/name: {{ .component }}
{{- end -}}

{{/*
Full labels (common + selector) for a given component.
Usage: {{ include "search-agent.componentLabels" (dict "root" $ "component" "api") }}
*/}}
{{- define "search-agent.componentLabels" -}}
{{ include "search-agent.labels" .root }}
{{ include "search-agent.selectorLabels" (dict "component" .component) }}
{{- end -}}

{{/*
Standard tolerations for all workloads.
Pods are evicted 30 s after their node becomes not-ready or unreachable,
instead of the default 5 min, so they reschedule quickly on a healthy node.
*/}}
{{- define "search-agent.podTolerations" -}}
tolerations:
  - key: node.kubernetes.io/not-ready
    operator: Exists
    effect: NoExecute
    tolerationSeconds: 30
  - key: node.kubernetes.io/unreachable
    operator: Exists
    effect: NoExecute
    tolerationSeconds: 30
{{- end -}}

{{/*
Full image reference for the api image.
*/}}
{{- define "search-agent.apiImage" -}}
{{ .Values.image.registry }}/{{ .Values.image.repository }}/{{ .Values.image.api.name }}:{{ .Values.image.api.tag }}
{{- end -}}

{{/*
Full image reference for the ui image.
*/}}
{{- define "search-agent.uiImage" -}}
{{ .Values.image.registry }}/{{ .Values.image.repository }}/{{ .Values.image.ui.name }}:{{ .Values.image.ui.tag }}
{{- end -}}
