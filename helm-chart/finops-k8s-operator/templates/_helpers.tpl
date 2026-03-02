{{/* Generate chart name */}}
{{- define "finops-operator.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Generate full resource name (with release) */}}
{{- define "finops-operator.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "finops-operator.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
