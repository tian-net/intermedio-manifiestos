from docx import Document
from docx.shared import Pt, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
import os

doc = Document()

# ── Estilos globales ──
style = doc.styles['Normal']
font = style.font
font.name = 'Arial'
font.size = Pt(11)
paragraph_format = style.paragraph_format
paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
paragraph_format.space_after = Pt(6)

# ── Título ──
title = doc.add_heading('INFORME TÉCNICO', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub = doc.add_paragraph('Integración de Monitoreo y Observabilidad con Prometheus y Grafana')
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub.runs[0].bold = True

info = doc.add_paragraph()
info.alignment = WD_ALIGN_PARAGRAPH.CENTER
info.add_run('Proyecto: ').bold = True
info.add_run('ELCHINO Restobar\n')
info.add_run('Curso: ').bold = True
info.add_run('ASE242 - Aplicaciones en Servidores\n')
info.add_run('Integrantes: ').bold = True
info.add_run('[Nombres de los integrantes]')

doc.add_page_break()

# ── 1. Arquitectura Actual ──
doc.add_heading('1. Arquitectura Actual', level=1)
doc.add_heading('1.1. Tabla de Servidores', level=2)

table = doc.add_table(rows=4, cols=4)
table.style = 'Light Grid Accent 1'
table.alignment = WD_TABLE_ALIGNMENT.CENTER
headers = ['Servidor', 'EC2', 'Función', 'Servicios / Puertos']
for i, h in enumerate(headers):
    cell = table.rows[0].cells[i]
    cell.text = h
    cell.paragraphs[0].runs[0].bold = True

data = [
    ['MongoDB', 'EC2-1', 'Base de datos', 'MongoDB 7 (27017)'],
    ['Backend', 'EC2-2', 'API REST', 'Spring Boot WebFlux (30001 → 8087)'],
    ['Frontend', 'EC2-3', 'Interfaz web', 'React + Vite + Nginx (30080 → 80)'],
]
for r, row_data in enumerate(data):
    for c, val in enumerate(row_data):
        table.rows[r + 1].cells[c].text = val

doc.add_heading('1.2. Comunicación entre servidores', level=2)
p = doc.add_paragraph()
p.add_run('Frontend (EC2-3) → Backend (EC2-2): ').bold = True
p.add_run('vía HTTP, puerto 30001\n')
p.add_run('Backend (EC2-2) → MongoDB (EC2-1): ').bold = True
p.add_run('vía MongoDB protocol, puerto 27017\n')
doc.add_paragraph('Cada servidor ejecuta Minikube con Docker driver. Las instancias EC2 están en la misma VPC (subred 172.31.x.x).')

doc.add_heading('1.3. Diagrama de Arquitectura Actual', level=2)
p = doc.add_paragraph('[CAPTURA: Diagrama de arquitectura actual con 3 servidores EC2 y sus conexiones]')

doc.add_page_break()

# ── 2. Arquitectura Propuesta ──
doc.add_heading('2. Arquitectura Propuesta (Monitoreo)', level=1)
doc.add_heading('2.1. Tabla de Servidores con Monitoreo', level=2)

table = doc.add_table(rows=5, cols=4)
table.style = 'Light Grid Accent 1'
table.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, h in enumerate(headers):
    cell = table.rows[0].cells[i]
    cell.text = h
    cell.paragraphs[0].runs[0].bold = True

data2 = [
    ['MongoDB', 'EC2-1', 'BD + Exporters', 'MongoDB 7 + MongoDB Exporter + Node Exporter\n27017, 30092, 9100'],
    ['Backend', 'EC2-2', 'API + Métricas', 'Spring Boot + Actuator/Micrometer + Node Exporter\n30001, 9100'],
    ['Frontend', 'EC2-3', 'Frontend + Métricas', 'React + Nginx + Node Exporter\n30080, 9100'],
    ['Monitoreo', 'EC2-4', 'Observabilidad', 'Prometheus + Grafana (Minikube)\n30090, 30300'],
]
for r, row_data in enumerate(data2):
    for c, val in enumerate(row_data):
        table.rows[r + 1].cells[c].text = val

doc.add_heading('2.2. Flujo de Métricas', level=2)
items = [
    'Node Exporter en cada EC2 host expone métricas del SO (CPU, RAM, disco, red) en puerto 9100',
    'MongoDB Exporter como sidecar en el mismo pod de MongoDB expone métricas de la BD en puerto 30092',
    'Actuator en el Backend expone métricas JVM y HTTP en /actuator/prometheus (puerto 30001)',
    'Prometheus (EC2-4) scrapea todos los targets cada 15 segundos',
    'Grafana (EC2-4) consulta Prometheus y visualiza los dashboards',
]
for item in items:
    doc.add_paragraph(item, style='List Bullet')

doc.add_heading('2.3. Diagrama de Arquitectura Propuesta', level=2)
p = doc.add_paragraph('[CAPTURA: Diagrama de arquitectura con 4 servidores, flechas de scraping de Prometheus hacia los targets]')

doc.add_page_break()

# ── 3. Justificación Técnica ──
doc.add_heading('3. Justificación Técnica', level=1)

doc.add_heading('3.1. ¿Es conveniente instalar Prometheus y Grafana en alguno de los servidores existentes?', level=2)
doc.add_paragraph(
    'No es conveniente. Los servidores actuales (EC2-1, EC2-2, EC2-3) ya ejecutan Minikube con sus respectivas '
    'aplicaciones y tienen recursos limitados (t3.medium con 4GB RAM cada uno). Agregar Prometheus y Grafana a '
    'cualquiera de ellos implicaría competir por CPU, memoria y disco con los servicios productivos, lo que podría '
    'degradar el rendimiento de la aplicación.'
)

doc.add_heading('3.2. ¿Qué ventajas y desventajas tendría esta decisión?', level=2)
doc.add_paragraph('Ventajas de usar un servidor existente:')
for item in [
    'No se incurre en el costo adicional de una nueva instancia EC2',
    'La configuración de red es más simple (no hay que abrir puertos adicionales)',
    'Se aprovecha la infraestructura ya desplegada',
]:
    doc.add_paragraph(item, style='List Bullet')

doc.add_paragraph('Desventajas de usar un servidor existente:')
for item in [
    'Riesgo de degradación del rendimiento de la aplicación por competencia de recursos',
    'Si el servidor se cae por saturación, se pierde tanto la aplicación como el monitoreo',
    'Dificultad para aislar problemas: no se sabe si una alerta es por la aplicación o por Prometheus',
    'MongoDB (EC2-1) es especialmente crítico: agregar carga podría afectar las operaciones de base de datos',
]:
    doc.add_paragraph(item, style='List Bullet')

doc.add_heading('3.3. ¿Es recomendable implementar un servidor adicional para monitoreo?', level=2)
doc.add_paragraph(
    'Sí, es altamente recomendable. Dedicar una cuarta instancia EC2 exclusivamente para Prometheus y Grafana sigue '
    'el principio de separación de responsabilidades. Esto garantiza que:'
)
for item in [
    'El monitoreo no compite por recursos con la aplicación',
    'Si la aplicación falla, los logs y métricas siguen disponibles para el análisis',
    'Se puede escalar el monitoreo de forma independiente',
    'Se cumple con las mejores prácticas de observabilidad en entornos profesionales',
]:
    doc.add_paragraph(item, style='List Bullet')

doc.add_heading('3.4. ¿Qué recursos mínimos requeriría dicho servidor?', level=2)
table = doc.add_table(rows=6, cols=3)
table.style = 'Light Grid Accent 1'
table.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, h in enumerate(['Recurso', 'Mínimo', 'Justificación']):
    cell = table.rows[0].cells[i]
    cell.text = h
    cell.paragraphs[0].runs[0].bold = True

recursos = [
    ['CPU', '2 vCPUs', 'Prometheus procesa consultas y scrapea datos cada 15s'],
    ['RAM', '2 GB', 'Suficiente para Prometheus + Grafana + Minikube'],
    ['Disco', '20 GB', 'Almacenamiento de métricas (retención default 15 días)'],
    ['SO', 'Ubuntu 24.04', 'Compatibilidad con el resto del proyecto'],
    ['Tipo EC2', 't3.small', 'Cumple con los requisitos mínimos'],
]
for r, row_data in enumerate(recursos):
    for c, val in enumerate(row_data):
        table.rows[r + 1].cells[c].text = val

doc.add_paragraph(
    'En el proyecto se utilizó una instancia t3.small (2GB RAM). Aunque Minikube mostró una advertencia por '
    'memoria justa, el sistema funcionó correctamente.'
)

doc.add_heading('3.5. ¿Cómo se comunicarían Prometheus y Grafana con los demás servidores?', level=2)
doc.add_paragraph(
    'La comunicación se realiza a través de Security Groups de AWS y NodePorts de Kubernetes:'
)
items = [
    'Prometheus (EC2-4) envía peticiones HTTP a los puertos expuestos de cada target (9100 para Node Exporter, 30092 para MongoDB, 30001 para Actuator)',
    'Grafana (EC2-4) se conecta a Prometheus internamente via prometheus-service.monitoreo.svc.cluster.local:9090',
    'Los puertos se exponen mediante kubectl port-forward desde cada pod de Kubernetes hacia 0.0.0.0 en cada host',
    'Security Groups permiten tráfico entrante desde la IP pública de EC2-4 hacia los puertos de monitoreo en EC2-1, EC2-2 y EC2-3',
]
for item in items:
    doc.add_paragraph(item, style='List Bullet')

p = doc.add_paragraph()
p.add_run('Tabla de puertos Security Groups:').bold = True

# Security groups table
table = doc.add_table(rows=5, cols=3)
table.style = 'Light Grid Accent 1'
table.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, h in enumerate(['Servidor', 'Puertos Abiertos', 'Origen']):
    cell = table.rows[0].cells[i]
    cell.text = h
    cell.paragraphs[0].runs[0].bold = True
sg_data = [
    ['EC2-1 (MongoDB)', '27017, 30092, 9100', 'EC2-2, EC2-4'],
    ['EC2-2 (Backend)', '30001, 9100', '0.0.0.0 (30001), EC2-4 (9100)'],
    ['EC2-3 (Frontend)', '30080, 9100', '0.0.0.0 (30080), EC2-4 (9100)'],
    ['EC2-4 (Monitoreo)', '30090, 30300', '0.0.0.0'],
]
for r, row_data in enumerate(sg_data):
    for c, val in enumerate(row_data):
        table.rows[r + 1].cells[c].text = val

doc.add_page_break()

# ── 4. Procedimiento Realizado ──
doc.add_heading('4. Procedimiento Realizado', level=1)

doc.add_heading('4.1. Archivos Modificados / Creados', level=2)
table = doc.add_table(rows=14, cols=3)
table.style = 'Light Grid Accent 1'
table.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, h in enumerate(['Archivo', 'Acción', 'Descripción']):
    cell = table.rows[0].cells[i]
    cell.text = h
    cell.paragraphs[0].runs[0].bold = True
files = [
    ['backend-cluster/backend-deployment.yaml', 'Modificado', 'Image tag monitoring (con Actuator)'],
    ['mongo-cluster/mongo-deployment.yaml', 'Modificado', 'Sidecar MongoDB Exporter --collect-all --compatible-mode'],
    ['mongo-cluster/mongodb-exporter-service.yaml', 'Creado', 'Service NodePort 30092 para MongoDB Exporter'],
    ['monitoreo/namespace-monitoreo.yaml', 'Creado', 'Namespace monitoreo'],
    ['monitoreo/prometheus/prometheus-config.yaml', 'Creado', 'Config de targets + reglas de alerta'],
    ['monitoreo/prometheus/prometheus-deployment.yaml', 'Creado', 'Deployment de Prometheus'],
    ['monitoreo/prometheus/prometheus-service.yaml', 'Creado', 'Service NodePort 30090'],
    ['monitoreo/grafana/grafana-datasource.yaml', 'Creado', 'Datasource automático Prometheus'],
    ['monitoreo/grafana/grafana-dashboard-configmap.yaml', 'Creado', 'Dashboard JSON (6 filas de paneles)'],
    ['monitoreo/grafana/grafana-deployment.yaml', 'Creado', 'Deployment de Grafana'],
    ['monitoreo/grafana/grafana-service.yaml', 'Creado', 'Service NodePort 30300'],
    ['monitoreo/alertas/alert-rules.yaml', 'Creado', '5 reglas de alerta'],
    ['comandos.md', 'Modificado', 'Guía de despliegue organizada cronológicamente'],
]
for r, row_data in enumerate(files):
    for c, val in enumerate(row_data):
        table.rows[r + 1].cells[c].text = val

doc.add_heading('4.2. Instalación de Node Exporters', level=2)
doc.add_paragraph(
    'Se instaló Node Exporter en cada EC2 host (EC2-1, EC2-2, EC2-3) directamente en el sistema operativo, '
    'NO dentro de Minikube. Node Exporter expone métricas del servidor como CPU, memoria, disco y red en el puerto 9100.'
)
p = doc.add_paragraph('[CAPTURA: Instalación de Node Exporter en EC2-1]')
p = doc.add_paragraph('[CAPTURA: Instalación de Node Exporter en EC2-2]')
p = doc.add_paragraph('[CAPTURA: Instalación de Node Exporter en EC2-3]')

doc.add_paragraph('Comandos utilizados:')
code = (
    'wget https://github.com/prometheus/node_exporter/releases/download/v1.11.1/node_exporter-1.11.1.linux-amd64.tar.gz\n'
    'tar xvfz node_exporter-1.11.1.linux-amd64.tar.gz\n'
    'sudo mv node_exporter-1.11.1.linux-amd64/node_exporter /usr/local/bin/\n\n'
    'sudo tee /etc/systemd/system/node_exporter.service > /dev/null << EOF\n'
    '[Unit]\n'
    'Description=Node Exporter\n'
    'After=network.target\n'
    '[Service]\n'
    'Type=simple\n'
    'ExecStart=/usr/local/bin/node_exporter\n'
    'Restart=always\n'
    '[Install]\n'
    'WantedBy=multi-user.target\n'
    'EOF\n\n'
    'sudo systemctl daemon-reload && sudo systemctl enable node_exporter && sudo systemctl start node_exporter'
)
p = doc.add_paragraph()
run = p.add_run(code)
run.font.name = 'Courier New'
run.font.size = Pt(9)

doc.add_heading('4.3. Instalación de MongoDB Exporter (EC2-1)', level=2)
doc.add_paragraph(
    'Se agregó un sidecar container en el mismo pod de MongoDB dentro del archivo mongo-deployment.yaml. '
    'El sidecar usa la imagen bitnami/mongodb-exporter:latest con los flags --collect-all --compatible-mode '
    'para habilitar todas las métricas disponibles. Además, se creó un servicio NodePort en el puerto 30092 '
    'para exponer las métricas.'
)
p = doc.add_paragraph('[CAPTURA: Manifiesto YAML del sidecar de MongoDB Exporter]')
p = doc.add_paragraph('[CAPTURA: Pod funcionando con 2/2 containers (mongo + mongodb-exporter)]')

doc.add_heading('4.4. Configuración del Backend con Actuator', level=2)
doc.add_paragraph(
    'Se modificó el backend Spring Boot para exponer métricas en el formato de Prometheus:'
)
items = [
    'pom.xml: Se agregaron las dependencias spring-boot-starter-actuator y micrometer-registry-prometheus',
    'application.yaml: Se configuró management.endpoints.web.exposure.include: health,info,prometheus',
    'SecurityConfig.java: Se agregó .pathMatchers("/actuator/**").permitAll() para permitir acceso público a las métricas',
    'Se reconstruyó la imagen Docker con el tag tian11qb/sebastian-webflux-nosql:monitoring',
    'Se actualizó el backend-deployment.yaml para usar la nueva imagen',
]
for item in items:
    doc.add_paragraph(item, style='List Bullet')
p = doc.add_paragraph('[CAPTURA: Verificación de métricas del Actuator: curl /actuator/prometheus]')

doc.add_heading('4.5. Configuración de Prometheus (EC2-4)', level=2)
doc.add_paragraph(
    'Se creó un archivo de configuración (prometheus-config.yaml) con 6 jobs de scraping:'
)
for item in [
    'prometheus — Métricas del propio Prometheus',
    'node-mongo — Node Exporter en EC2-1 (puerto 9100)',
    'node-backend — Node Exporter en EC2-2 (puerto 9100)',
    'node-frontend — Node Exporter en EC2-3 (puerto 9100)',
    'mongodb — MongoDB Exporter en EC2-1 (puerto 30092)',
    'backend-actuator — Actuator en EC2-2 (puerto 30001, path /actuator/prometheus)',
]:
    doc.add_paragraph(item, style='List Bullet')

doc.add_paragraph('Pasos de despliegue:')
code = (
    '# 1. Editar las IPs reales en el archivo de configuración\n'
    "kubectl apply -f monitoreo/namespace-monitoreo.yaml\n"
    "kubectl apply -f monitoreo/prometheus/prometheus-config.yaml\n"
    "kubectl apply -f monitoreo/prometheus/prometheus-deployment.yaml\n"
    "kubectl apply -f monitoreo/prometheus/prometheus-service.yaml\n\n"
    "# 2. Exponer Prometheus\n"
    "kubectl port-forward -n monitoreo service/prometheus-service 30090:9090 --address 0.0.0.0"
)
p = doc.add_paragraph()
run = p.add_run(code)
run.font.name = 'Courier New'
run.font.size = Pt(9)

p = doc.add_paragraph('[CAPTURA: Prometheus targets UP - todos los 6 targets en estado UP]')
p = doc.add_paragraph('[CAPTURA: Archivo de configuración de Prometheus]')

doc.add_heading('4.6. Configuración de Grafana (EC2-4)', level=2)
code = (
    "kubectl apply -f monitoreo/grafana/grafana-datasource.yaml\n"
    "kubectl apply -f monitoreo/grafana/grafana-dashboard-configmap.yaml\n"
    "kubectl apply -f monitoreo/grafana/grafana-deployment.yaml\n"
    "kubectl apply -f monitoreo/grafana/grafana-service.yaml\n"
    "kubectl port-forward -n monitoreo service/grafana-service 30300:3000 --address 0.0.0.0"
)
p = doc.add_paragraph()
run = p.add_run(code)
run.font.name = 'Courier New'
run.font.size = Pt(9)

p = doc.add_paragraph('[CAPTURA: Login de Grafana (admin/admin)]')
p = doc.add_paragraph('[CAPTURA: Datasource de Prometheus configurado y con estado verde]')

doc.add_heading('4.7. Configuración de Alertas', level=2)
doc.add_paragraph(
    'Se definieron 5 reglas de alerta en monitoreo/alertas/alert-rules.yaml:'
)
table = doc.add_table(rows=6, cols=3)
table.style = 'Light Grid Accent 1'
table.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, h in enumerate(['Alerta', 'Condición', 'Severidad']):
    cell = table.rows[0].cells[i]
    cell.text = h
    cell.paragraphs[0].runs[0].bold = True
alertas = [
    ['HighCPUUsage', 'CPU > 80% por 5 min', 'Critical'],
    ['HighMemoryUsage', 'Memoria > 80% por 5 min', 'Critical'],
    ['LowDiskSpace', 'Disco libre < 20%', 'Warning'],
    ['BackendDown', 'Backend sin respuesta', 'Critical'],
    ['MongoDBDown', 'MongoDB sin respuesta', 'Critical'],
]
for r, row_data in enumerate(alertas):
    for c, val in enumerate(row_data):
        table.rows[r + 1].cells[c].text = val
p = doc.add_paragraph('[CAPTURA: Reglas de alerta en Prometheus]')

doc.add_heading('4.8. Errores Encontrados y Soluciones', level=2)
table = doc.add_table(rows=10, cols=4)
table.style = 'Light Grid Accent 1'
table.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, h in enumerate(['#', 'Error', 'Causa', 'Solución']):
    cell = table.rows[0].cells[i]
    cell.text = h
    cell.paragraphs[0].runs[0].bold = True
errores = [
    ['1', '404 al descargar Node Exporter', 'URL /latest/download/ sin versión explícita', 'Usar URL con versión v1.11.1 explícita'],
    ['2', 'Prometheus CrashLoopBackOff', 'labels mal indentado en prometheus-config.yaml', 'Eliminar labels de la configuración'],
    ['3', 'Target MongoDB DOWN', 'Falta port-forward para MongoDB Exporter', 'kubectl port-forward service/mongodb-exporter-service 30092:9216'],
    ['4', 'Dashboard MongoDB sin datos', 'Sin collectors habilitados', 'Agregar --collect-all --compatible-mode al sidecar'],
    ['5', 'Error unknown flag en sidecar', 'Flags --collector.database no existen', 'Usar --collect-all en vez de flags individuales'],
    ['6', 'Dashboard JVM sin datos', 'Query jvm_memory_used_bytes con label job incorrecto', 'Usar jvm_memory_committed_bytes con application="Elchino"'],
    ['7', 'P99 sin datos', 'WebFlux no genera histogram buckets', 'Cambiar a promedio: rate(sum)/rate(count)*1000'],
    ['8', 'git push rechazado', 'Cambios remotos no sincronizados', 'git pull origin develop y resolver merge'],
    ['9', 'Minikube warning de memoria', 't3.small 2GB justo para 3072MB default', 'Reducir a --memory=2048mb (opcional)'],
]
for r, row_data in enumerate(errores):
    for c, val in enumerate(row_data):
        table.rows[r + 1].cells[c].text = val

doc.add_page_break()

# ── 5. Dashboard Implementado ──
doc.add_heading('5. Dashboard Implementado', level=1)
doc.add_paragraph(
    'El dashboard "ELCHINO - Monitoreo General" consta de 7 filas de paneles que se importan automáticamente '
    'desde un ConfigMap de Grafana:'
)
table = doc.add_table(rows=8, cols=4)
table.style = 'Light Grid Accent 1'
table.alignment = WD_TABLE_ALIGNMENT.CENTER
for i, h in enumerate(['Fila', 'Panel', 'Métrica Utilizada', 'Tipo']):
    cell = table.rows[0].cells[i]
    cell.text = h
    cell.paragraphs[0].runs[0].bold = True
paneles = [
    ['1', 'Estado General de Servidores', 'up{job="..."}', 'Stat'],
    ['2', 'Consumo de CPU (%)', 'rate(node_cpu_seconds_total{mode="idle"}[5m])', 'Timeseries'],
    ['3', 'Consumo de Memoria (%)', '(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)*100', 'Timeseries'],
    ['4', 'Espacio en Disco', 'node_filesystem_*', 'Timeseries + Stat'],
    ['5', 'Métricas MongoDB', 'mongodb_dbstats_dataSize, mongodb_connections, rate(mongodb_asserts_total)', 'Stat + Timeseries'],
    ['6', 'Métricas Backend JVM', 'jvm_memory_committed_bytes, http_server_requests_seconds_*', 'Timeseries'],
    ['7', 'Alertas Activas', 'ALERTS{alertstate="firing"}', 'Stat'],
]
for r, row_data in enumerate(paneles):
    for c, val in enumerate(row_data):
        table.rows[r + 1].cells[c].text = val

doc.add_heading('5.1. Estado General de Servidores', level=2)
p = doc.add_paragraph('[CAPTURA: Panel de estado general con los 6 servicios monitoreados]')
doc.add_heading('5.2. Consumo de CPU - Comparativa', level=2)
p = doc.add_paragraph('[CAPTURA: Gráfico de CPU con las líneas de los 3 servidores]')
doc.add_heading('5.3. Consumo de Memoria - Comparativa', level=2)
p = doc.add_paragraph('[CAPTURA: Gráfico de memoria con las líneas de los 3 servidores]')
doc.add_heading('5.4. Espacio en Disco', level=2)
p = doc.add_paragraph('[CAPTURA: Gráfico de disco con las líneas de los 3 servidores]')
doc.add_heading('5.5. Métricas de MongoDB', level=2)
p = doc.add_paragraph('[CAPTURA: Panel de MongoDB con tamaño de BD, conexiones activas y operaciones por segundo]')
doc.add_heading('5.6. Métricas del Backend (JVM)', level=2)
p = doc.add_paragraph('[CAPTURA: Panel del Backend con Heap, Non-Heap, HTTP Requests Rate y Tiempo de Respuesta Promedio]')
doc.add_heading('5.7. Alertas Visuales', level=2)
p = doc.add_paragraph('[CAPTURA: Panel de alertas activas en el dashboard]')

doc.add_page_break()

# ── 6. Análisis de Resultados ──
doc.add_heading('6. Análisis de Resultados', level=1)

doc.add_heading('6.1. ¿Cuál es el servidor que consume más recursos?', level=2)
doc.add_paragraph(
    'Según los datos observados en el dashboard, el Backend (EC2-2) es el servidor que consume más recursos, '
    'especialmente en términos de CPU y memoria. Esto se debe a que la aplicación Spring Boot WebFlux con '
    'Reactive MongoDB requiere una cantidad significativa de memoria para el Heap JVM (aproximadamente 150-200 MB) '
    'y la CPU se utiliza intensamente durante las peticiones HTTP y las consultas a la base de datos.\n\n'
    'El Frontend (EC2-3) es el que menos recursos consume, ya que Nginx solo sirve archivos estáticos y la carga '
    'de procesamiento recae principalmente en el navegador del cliente.'
)

doc.add_heading('6.2. ¿Qué componente representa el posible cuello de botella?', level=2)
doc.add_paragraph('El Backend es el principal cuello de botella por las siguientes razones:')
items = [
    'Memoria JVM: El Heap se divide en Eden Space, Old Gen y Survivor Space. GC frecuentes degradan el rendimiento.',
    'HTTP Requests: Cada petición consume procesamiento. Con WebFlux (reactivo) se mitiga, pero hay un límite de concurrencia.',
    'Conexiones a MongoDB: Si el pool de conexiones se agota, las nuevas peticiones deben esperar, aumentando la latencia.',
]
for item in items:
    doc.add_paragraph(item, style='List Bullet')
doc.add_paragraph(
    'El segundo posible cuello de botella es MongoDB (EC2-1) en términos de operaciones de disco y tamaño de la base de datos.'
)

doc.add_heading('6.3. ¿Cuál sería el impacto de aumentar la cantidad de usuarios?', level=2)
items = [
    'Aumento en el CPU del Backend: Más peticiones HTTP = mayor uso de CPU',
    'Aumento en la Memoria del Backend: Más objetos creados = mayor presión en el Garbage Collector',
    'Aumento de conexiones a MongoDB: Más consultas simultáneas = mayor uso del pool de conexiones',
    'Mayor latencia de respuesta: Si el Backend se satura, los tiempos de respuesta aumentan significativamente',
    'Posible degradación del Frontend: No significativa, Nginx maneja bien alta concurrencia para contenido estático',
]
for item in items:
    doc.add_paragraph(item, style='List Bullet')

doc.add_heading('6.4. ¿Qué mejoras podrían implementarse para optimizar el rendimiento?', level=2)
items = [
    'Escalamiento horizontal del Backend: Implementar múltiples réplicas con Load Balancer de Kubernetes',
    'Caché con Redis: Reducir consultas repetitivas a MongoDB',
    'Optimización de consultas MongoDB: Revisar índices y consultas lentas',
    'Límites de recursos en Kubernetes: Configurar resources.requests y resources.limits',
    'Aumentar la memoria JVM: Configurar -Xmx y -Xms en el Backend',
    'Percentiles de latencia: Agregar histogram habilitado para obtener P99, P95 y P50 reales',
    'Auto-scaling: Configurar HPA en Kubernetes para escalar según CPU',
]
for item in items:
    doc.add_paragraph(item, style='List Bullet')

doc.add_page_break()

# ── 7. Conclusiones ──
doc.add_heading('7. Conclusiones', level=1)
doc.add_paragraph(
    'La implementación de monitoreo con Prometheus y Grafana sobre una arquitectura de 4 instancias EC2 con '
    'Minikube ha demostrado ser una solución viable y profesional para la observabilidad del proyecto ELCHINO '
    'Restobar. Los objetivos planteados se cumplieron satisfactoriamente:\n\n'
)
items = [
    'Métricas de infraestructura: Se monitorea CPU, memoria, disco y red de los 3 servidores mediante Node Exporter',
    'Métricas de aplicación: El Backend expone métricas JVM y HTTP mediante Actuator con Micrometer',
    'Métricas de base de datos: MongoDB es monitoreado mediante un sidecar exporter que reporta tamaño, conexiones y operaciones',
    'Dashboard centralizado: Grafana presenta un dashboard completo con 7 filas de paneles',
    'Alertas: Se implementaron 5 reglas de alerta para detectar problemas críticos',
]
for item in items:
    doc.add_paragraph(item, style='List Bullet')
doc.add_paragraph(
    'La decisión de agregar una cuarta instancia EC2 dedicada al monitoreo fue acertada, ya que permite aislar '
    'la carga de observabilidad de los servicios productivos y garantiza que las métricas estén disponibles '
    'incluso si alguno de los servidores falla.'
)

# ── 8. Evidencias Técnicas ──
doc.add_heading('8. Evidencias Técnicas', level=1)
evidencias = [
    'Captura de instalación de Node Exporter en EC2-1',
    'Captura de instalación de Node Exporter en EC2-2',
    'Captura de instalación de Node Exporter en EC2-3',
    'Captura de métricas del Actuator del Backend',
    'Captura de Prometheus targets (todos UP)',
    'Captura de configuración de Prometheus',
    'Captura de login de Grafana',
    'Captura de datasource de Prometheus en Grafana',
    'Captura de dashboard general (vista completa)',
    'Captura de panel de CPU',
    'Captura de panel de Memoria',
    'Captura de panel de Disco',
    'Captura de panel de MongoDB',
    'Captura de panel de Backend JVM',
    'Captura de panel de alertas activas',
    'Captura de reglas de alerta en Prometheus',
    'Captura de diagrama de arquitectura actual',
    'Captura de diagrama de arquitectura propuesta',
]
for item in evidencias:
    p = doc.add_paragraph(style='List Bullet')
    p.add_run('[ ] ').bold = True
    p.add_run(item)

# ── Guardar ──
output_path = os.path.join(os.path.dirname(__file__), '..', 'INFORME_TECNICO_MONITOREO_ELCHINO.docx')
doc.save(output_path)
print(f"Word document created: {output_path}")
