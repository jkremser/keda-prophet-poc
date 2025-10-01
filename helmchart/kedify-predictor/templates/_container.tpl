{{- define "prophet.container" -}}
- name: keda-prophet
  image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
  imagePullPolicy: {{ .Values.image.pullPolicy }}
  {{- if .Values.kedaPredictionController.enabled }}
  restartPolicy: Always
  {{- end }}
  ports:
    - name: http
      containerPort: {{ .Values.service.port }}
      protocol: TCP
  env:
    - name: DB_FILE
      value: {{ .Values.settings.storage.dbFile }}
    - name: MODELS_PATH
      value: {{ .Values.settings.storage.modelsPath }}
  {{- with .Values.livenessProbe }}
  livenessProbe:
    {{- toYaml . | nindent 12 }}
  {{- end }}
  {{- with .Values.readinessProbe }}
  readinessProbe:
    {{- toYaml . | nindent 12 }}
  {{- end }}
  {{- with .Values.resources }}
  resources:
    {{- toYaml . | nindent 12 }}
  {{- end }}
  {{- with .Values.securityContext }}
  securityContext:
    {{- toYaml . | nindent 12 }}
  {{- end }}
  {{- with .Values.volumeMounts }}
  volumeMounts:
    {{- toYaml . | nindent 12 }}
  {{- end }}
{{- end }}
