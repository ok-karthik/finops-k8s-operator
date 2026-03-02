{{/* Generate chart name */}}
{{- define "finops-k8s-operator.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Generate full resource name - just use release name to avoid duplication */}}
{{- define "finops-k8s-operator.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
