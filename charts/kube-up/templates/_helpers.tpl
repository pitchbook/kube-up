{{/*
Expand the name of the chart.
*/}}
{{- define "kubeUp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create Manager name.
*/}}
{{- define "kubeUp.managerName" -}}
{{- print "kube-up-manager" -}}
{{- end -}}

{{/*
Create API name.
*/}}
{{- define "kubeUp.apiName" -}}
{{- print "kube-up-api" -}}
{{- end -}}

{{/*
Set default container port name.
*/}}
{{- define "portNames.container" -}}
{{- print "traffic" -}}
{{- end -}}

{{/*
Set default service port name.
*/}}
{{- define "portNames.service" -}}
{{- print "traffic" -}}
{{- end -}}

{{/*
Set default Manager service metrics port name.
*/}}
{{- define "portNames.metrics" -}}
{{- print "metrics" -}}
{{- end -}}

{{/*
Set default Manager service healthcheck port name.
*/}}
{{- define "portNames.health" -}}
{{- print "health" -}}
{{- end -}}

{{/*
Set default Manager healthcheck path.
*/}}
{{- define "probes.endpoint" -}}
{{- print "/readyz" -}}
{{- end -}}

{{/*
API selector labels
*/}}
{{- define "kubeUp.apiSelectorLabels" -}}
app.kubernetes.io/name: {{ include "kubeUp.name" . }}-api
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Manager selector labels
*/}}
{{- define "kubeUp.managerSelectorLabels" -}}
app.kubernetes.io/name: {{ include "kubeUp.name" . }}-manager
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "kubeUp.labels" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}
{{- end -}}

{{/*
Common API labels
*/}}
{{- define "kubeUp.apiLabels" -}}
{{ include "kubeUp.apiSelectorLabels" . }}
{{ include "kubeUp.labels" . }}
{{- end -}}

{{/*
Common Manager labels
*/}}
{{- define "kubeUp.managerLabels" -}}
{{ include "kubeUp.managerSelectorLabels" . }}
{{ include "kubeUp.labels" . }}
{{- end -}}

{{/*
Image
*/}}
{{- define "kubeUp.image" -}}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) -}}
{{- end -}}
