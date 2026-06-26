# INFORME TÉCNICO - Integración de Monitoreo y Observabilidad

**Proyecto:** ELCHINO Restobar
**Curso:** ASE242 - Aplicaciones en Servidores
**Integrantes:** [Nombres]

---

## 1. Arquitectura Actual

### 1.1. Tabla de Servidores

| Servidor | EC2 | Función | Servicios | Puertos |
|----------|-----|---------|-----------|---------|
| MongoDB | EC2-1 | Base de datos | MongoDB 7-jammy (Minikube) | 27017 |
| Backend | EC2-2 | API REST | Spring Boot WebFlux (Minikube) | 30001 → 8087 |
| Frontend | EC2-3 | Interfaz web | React + Vite + Nginx (Minikube) | 30080 → 80 |

### 1.2. Comunicación entre servidores

- **Frontend (EC2-3) → Backend (EC2-2):** vía HTTP, puerto 30001
- **Backend (EC2-2) → MongoDB (EC2-1):** vía MongoDB protocol, puerto 27017
- Cada servidor ejecuta Minikube con Docker driver
- Las instancias EC2 están en la misma VPC (subred 172.31.x.x)

### 1.3. Diagrama de Arquitectura Actual

> **[CAPTURA: Diagrama de arquitectura actual con 3 servidores EC2 y sus conexiones]**

---

## 2. Arquitectura Propuesta (Monitoreo)

### 2.1. Tabla de Servidores con Monitoreo

| Servidor | EC2 | Función | Servicios | Puertos |
|----------|-----|---------|-----------|---------|
| MongoDB | EC2-1 | Base de datos + Exporters | MongoDB 7 + MongoDB Exporter (sidecar) + Node Exporter | 27017, 30092, 9100 |
| Backend | EC2-2 | API REST + Métricas | Spring Boot + Actuator/Micrometer + Node Exporter | 30001, 9100 |
| Frontend | EC2-3 | Frontend + Métricas | React + Nginx + Node Exporter | 30080, 9100 |
| **Monitoreo** | **EC2-4** | **Observabilidad** | **Prometheus + Grafana (Minikube)** | **30090, 30300** |

### 2.2. Flujo de Métricas

1. **Node Exporter** en cada EC2 host expone métricas del SO (CPU, RAM, disco, red) en puerto 9100
2. **MongoDB Exporter** como sidecar en el mismo pod de MongoDB expone métricas de la BD en puerto 9216 → 30092
3. **Actuator** en el Backend expone métricas JVM y HTTP en `/actuator/prometheus` (puerto 30001)
4. **Prometheus** (EC2-4) scrapea todos los targets cada 15 segundos
5. **Grafana** (EC2-4) consulta Prometheus y visualiza los dashboards

### 2.3. Diagrama de Arquitectura Propuesta

> **[CAPTURA: Diagrama de arquitectura con 4 servidores, flechas de scraping de Prometheus hacia los targets]**

---

## 3. Justificación Técnica

### 3.1. ¿Es conveniente instalar Prometheus y Grafana en alguno de los servidores existentes?

No es conveniente. Los servidores actuales (EC2-1, EC2-2, EC2-3) ya ejecutan Minikube con sus respectivas aplicaciones y tienen recursos limitados (t3.medium con 4GB RAM cada uno). Agregar Prometheus y Grafana a cualquiera de ellos implicaría competir por CPU, memoria y disco con los servicios productivos, lo que podría degradar el rendimiento de la aplicación.

### 3.2. ¿Qué ventajas y desventajas tendría esta decisión?

**Ventajas de usar un servidor existente:**
- No se incurre en el costo adicional de una nueva instancia EC2
- La configuración de red es más simple (no hay que abrir puertos adicionales)
- Se aprovecha la infraestructura ya desplegada

**Desventajas de usar un servidor existente:**
- Riesgo de degradación del rendimiento de la aplicación por competencia de recursos
- Si el servidor se cae por saturación, se pierde tanto la aplicación como el monitoreo
- Dificultad para aislar problemas: no se sabe si una alerta es por la aplicación o por Prometheus
- MongoDB (EC2-1) es especialmente crítico: agregar carga podría afectar las operaciones de base de datos

### 3.3. ¿Es recomendable implementar un servidor adicional para monitoreo?

Sí, es altamente recomendable. Dedicar una cuarta instancia EC2 exclusivamente para Prometheus y Grafana sigue el principio de **separación de responsabilidades**. Esto garantiza que:

- El monitoreo no compite por recursos con la aplicación
- Si la aplicación falla, los logs y métricas siguen disponibles para el análisis
- Se puede escalar el monitoreo de forma independiente
- Se cumple con las mejores prácticas de observabilidad en entornos profesionales

### 3.4. ¿Qué recursos mínimos requeriría dicho servidor?

| Recurso | Mínimo | Justificación |
|---------|--------|---------------|
| CPU | 2 vCPUs | Prometheus procesa consultas y scrapea datos cada 15s |
| RAM | 2 GB | Suficiente para Prometheus + Grafana + Minikube |
| Disco | 20 GB | Almacenamiento de métricas (retención default 15 días) |
| SO | Ubuntu 24.04 | Compatibilidad con el resto del proyecto |
| Tipo EC2 | **t3.small** | Cumple con los requisitos mínimos |

> En el proyecto se utilizó una instancia **t3.small** (2GB RAM). Aunque Minikube mostró una advertencia por memoria justa, el sistema funcionó correctamente.

### 3.5. ¿Cómo se comunicarían Prometheus y Grafana con los demás servidores?

La comunicación se realiza a través de **Security Groups de AWS** y **NodePorts** de Kubernetes:

- **Prometheus** (EC2-4) envía peticiones HTTP a los puertos expuestos de cada target:
  - `http://<EC2-1_IP>:9100/metrics` → Node Exporter (EC2-1)
  - `http://<EC2-1_IP>:30092/metrics` → MongoDB Exporter (EC2-1)
  - `http://<EC2-2_IP>:9100/metrics` → Node Exporter (EC2-2)
  - `http://<EC2-2_IP>:30001/actuator/prometheus` → Backend Actuator (EC2-2)
  - `http://<EC2-3_IP>:9100/metrics` → Node Exporter (EC2-3)
- **Grafana** (EC2-4) se conecta a Prometheus internamente via `prometheus-service.monitoreo.svc.cluster.local:9090`
- Los puertos se exponen mediante `kubectl port-forward` desde cada pod de Kubernetes hacia la IP 0.0.0.0 de cada host EC2
- Los Security Groups permiten el tráfico entrante desde la IP pública de EC2-4 hacia los puertos de monitoreo en EC2-1, EC2-2 y EC2-3

---

## 4. Procedimiento Realizado

### 4.1. Archivos Modificados / Creados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `backend-cluster/backend-deployment.yaml` | Modificado | Image tag `lastest` → `monitoring` (con Actuator) |
| `mongo-cluster/mongo-deployment.yaml` | Modificado | Agregado sidecar MongoDB Exporter con `--collect-all --compatible-mode` |
| `mongo-cluster/mongodb-exporter-service.yaml` | Creado | Service NodePort 30092 para MongoDB Exporter |
| `monitoreo/namespace-monitoreo.yaml` | Creado | Namespace `monitoreo` |
| `monitoreo/prometheus/prometheus-config.yaml` | Creado | Config de targets + reglas de alerta |
| `monitoreo/prometheus/prometheus-deployment.yaml` | Creado | Deployment de Prometheus |
| `monitoreo/prometheus/prometheus-service.yaml` | Creado | Service NodePort 30090 |
| `monitoreo/grafana/grafana-datasource.yaml` | Creado | Datasource automático Prometheus |
| `monitoreo/grafana/grafana-dashboard-configmap.yaml` | Creado | Dashboard JSON (6 filas de paneles) |
| `monitoreo/grafana/grafana-deployment.yaml` | Creado | Deployment de Grafana |
| `monitoreo/grafana/grafana-service.yaml` | Creado | Service NodePort 30300 |
| `monitoreo/alertas/alert-rules.yaml` | Creado | 5 reglas de alerta |
| `comandos.md` | Modificado | Guía de despliegue organizada cronológicamente |
| `seed_elchino.mongodb` | Creado | Seed data para MongoDB |
| Backend `pom.xml` | Modificado | Agregadas dependencias Actuator + Micrometer Prometheus |
| Backend `application.yaml` | Modificado | Exposición endpoint `/actuator/prometheus` |
| Backend `SecurityConfig.java` | Modificado | PermitAll para `/actuator/**` |

### 4.2. Instalación de Node Exporters

Se instaló **Node Exporter** en cada EC2 host (EC2-1, EC2-2, EC2-3) directamente en el sistema operativo, NO dentro de Minikube. Node Exporter expone métricas del servidor como CPU, memoria, disco y red en el puerto 9100.

> **[CAPTURA: Instalación de Node Exporter en EC2-1]**
> **[CAPTURA: Instalación de Node Exporter en EC2-2]**
> **[CAPTURA: Instalación de Node Exporter en EC2-3]**

**Comandos utilizados:**

```bash
wget https://github.com/prometheus/node_exporter/releases/download/v1.11.1/node_exporter-1.11.1.linux-amd64.tar.gz
tar xvfz node_exporter-1.11.1.linux-amd64.tar.gz
sudo mv node_exporter-1.11.1.linux-amd64/node_exporter /usr/local/bin/

sudo tee /etc/systemd/system/node_exporter.service > /dev/null << EOF
[Unit]
Description=Node Exporter
After=network.target
[Service]
Type=simple
ExecStart=/usr/local/bin/node_exporter
Restart=always
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload && sudo systemctl enable node_exporter && sudo systemctl start node_exporter
```

### 4.3. Instalación de MongoDB Exporter (EC2-1)

Se agregó un **sidecar container** en el mismo pod de MongoDB dentro del archivo `mongo-deployment.yaml`. El sidecar usa la imagen `bitnami/mongodb-exporter:latest` con los flags `--collect-all --compatible-mode` para habilitar todas las métricas disponibles. Además, se creó un servicio NodePort en el puerto 30092 para exponer las métricas.

> **[CAPTURA: Manifiesto YAML del sidecar de MongoDB Exporter]**
> **[CAPTURA: Pod funcionando con 2/2 containers (mongo + mongodb-exporter)]**

### 4.4. Configuración del Backend con Actuator

Se modificó el backend Spring Boot para exponer métricas en el formato de Prometheus:

1. **pom.xml:** Se agregaron las dependencias `spring-boot-starter-actuator` y `micrometer-registry-prometheus`
2. **application.yaml:** Se configuró `management.endpoints.web.exposure.include: health,info,prometheus`
3. **SecurityConfig.java:** Se agregó `.pathMatchers("/actuator/**").permitAll()` para permitir acceso público a las métricas
4. Se reconstruyó la imagen Docker con el tag `tian11qb/sebastian-webflux-nosql:monitoring`
5. Se actualizó el `backend-deployment.yaml` para usar la nueva imagen

> **[CAPTURA: Verificación de métricas del Actuator: curl /actuator/prometheus]**

### 4.5. Configuración de Prometheus (EC2-4)

Se creó un archivo de configuración (`prometheus-config.yaml`) con 6 jobs de scraping:

```yaml
scrape_configs:
  - job_name: 'prometheus'        # Métricas del propio Prometheus
  - job_name: 'node-mongo'        # Node Exporter en EC2-1 (puerto 9100)
  - job_name: 'node-backend'      # Node Exporter en EC2-2 (puerto 9100)
  - job_name: 'node-frontend'     # Node Exporter en EC2-3 (puerto 9100)
  - job_name: 'mongodb'           # MongoDB Exporter en EC2-1 (puerto 30092)
  - job_name: 'backend-actuator'  # Actuator en EC2-2 (puerto 30001, path /actuator/prometheus)
```

**Pasos de despliegue:**

```bash
# 1. Editar las IPs reales en el archivo de configuración
sed -i 's/<EC2-1_IP>/IP_REAL/g' monitoreo/prometheus/prometheus-config.yaml

# 2. Aplicar los manifiestos
kubectl apply -f monitoreo/namespace-monitoreo.yaml
kubectl apply -f monitoreo/prometheus/prometheus-config.yaml
kubectl apply -f monitoreo/prometheus/prometheus-deployment.yaml
kubectl apply -f monitoreo/prometheus/prometheus-service.yaml

# 3. Exponer Prometheus
kubectl port-forward -n monitoreo service/prometheus-service 30090:9090 --address 0.0.0.0
```

> **[CAPTURA: Prometheus targets UP - todos los 6 targets en estado UP]**
> **[CAPTURA: Archivo de configuración de Prometheus]**

### 4.6. Configuración de Grafana (EC2-4)

```bash
kubectl apply -f monitoreo/grafana/grafana-datasource.yaml
kubectl apply -f monitoreo/grafana/grafana-dashboard-configmap.yaml
kubectl apply -f monitoreo/grafana/grafana-deployment.yaml
kubectl apply -f monitoreo/grafana/grafana-service.yaml
kubectl port-forward -n monitoreo service/grafana-service 30300:3000 --address 0.0.0.0
```

> **[CAPTURA: Login de Grafana (admin/admin)]**
> **[CAPTURA: Datasource de Prometheus configurado y con estado verde]**

### 4.7. Configuración de Alertas

Se definieron 5 reglas de alerta en `monitoreo/alertas/alert-rules.yaml`:

| Alerta | Condición | Severidad |
|--------|-----------|-----------|
| HighCPUUsage | CPU > 80% por 5 min | Critical |
| HighMemoryUsage | Memoria > 80% por 5 min | Critical |
| LowDiskSpace | Disco libre < 20% | Warning |
| BackendDown | Backend sin respuesta | Critical |
| MongoDBDown | MongoDB sin respuesta | Critical |

> **[CAPTURA: Reglas de alerta en Prometheus]**

### 4.8. Errores Encontrados y Soluciones

| # | Error | Causa | Solución | Archivos afectados |
|---|-------|-------|----------|-------------------|
| 1 | `404` al descargar Node Exporter | URL `/latest/download/` redirige a asset sin versión | Usar URL con versión explícita: `v1.11.1/node_exporter-1.11.1.linux-amd64.tar.gz` | `comandos.md` |
| 2 | Pod Prometheus `CrashLoopBackOff` | `labels` mal indentado en `prometheus-config.yml` (fuera de `static_configs`) | Eliminar `labels` de la configuración | `monitoreo/prometheus/prometheus-config.yaml` |
| 3 | Target MongoDB `DOWN: connection refused` | Falta `kubectl port-forward` para MongoDB Exporter en EC2-1 | Agregar port-forward: `service/mongodb-exporter-service 30092:9216` | — |
| 4 | Dashboard MongoDB "No data" | MongoDB Exporter sin collectors habilitados (solo métrica `mongodb_up`) | Agregar `args: ["--collect-all", "--compatible-mode"]` al sidecar | `mongo-cluster/mongo-deployment.yaml` |
| 5 | Sidecar `Error: unknown flag` | Nombres de collectors incorrectos (`--collector.database`, `--collector.connections` no existen) | Usar `--collect-all` en vez de flags individuales | `mongo-cluster/mongo-deployment.yaml` |
| 6 | Dashboard JVM "No data" | Queries con `jvm_memory_used_bytes` y `job="backend-actuator"` | Usar `jvm_memory_committed_bytes` con `application="Elchino"` | `monitoreo/grafana/grafana-dashboard-configmap.yaml` |
| 7 | P99 "No data" | WebFlux no genera histogram buckets por defecto | Cambiar a promedio: `rate(sum)/rate(count) * 1000` | `monitoreo/grafana/grafana-dashboard-configmap.yaml` |
| 8 | `git push` rechazado | Cambios remotos no sincronizados | `git pull origin develop` y resolver merge conflict | `comandos.md` |
| 9 | Minikube warning de memoria | t3.small (2GB RAM) muy justo para 3072MB default | Reducir: `minikube start --memory=2048mb` (opcional) | — |

---

## 5. Dashboard Implementado

El dashboard "ELCHINO - Monitoreo General" consta de 7 filas de paneles que se importan automáticamente desde un ConfigMap de Grafana:

| Fila | Panel | Métrica Utilizada | Tipo |
|------|-------|-------------------|------|
| 1 | Estado General de Servidores | `up{job="..."}` | Stat |
| 2 | Consumo de CPU (%) | `rate(node_cpu_seconds_total{mode="idle"}[5m])` | Timeseries |
| 3 | Consumo de Memoria (%) | `(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100` | Timeseries |
| 4 | Espacio en Disco (% usado y GB libres) | `node_filesystem_*` | Timeseries + Stat |
| 5 | Métricas de MongoDB (tamaño BD, conexiones, operaciones) | `mongodb_dbstats_dataSize`, `mongodb_connections`, `rate(mongodb_asserts_total)` | Stat + Timeseries |
| 6 | Métricas del Backend JVM (Heap, Non-Heap, requests, tiempo promedio) | `jvm_memory_committed_bytes`, `http_server_requests_seconds_*` | Timeseries |
| 7 | Alertas Activas | `ALERTS{alertstate="firing"}` | Stat |

### 5.1. Estado General de Servidores

> **[CAPTURA: Panel de estado general con los 6 servicios monitoreados]**

### 5.2. Consumo de CPU - Comparativa

> **[CAPTURA: Gráfico de CPU con las líneas de los 3 servidores]**

### 5.3. Consumo de Memoria - Comparativa

> **[CAPTURA: Gráfico de memoria con las líneas de los 3 servidores]**

### 5.4. Espacio en Disco

> **[CAPTURA: Gráfico de disco con las líneas de los 3 servidores]**

### 5.5. Métricas de MongoDB

> **[CAPTURA: Panel de MongoDB con tamaño de BD, conexiones activas y operaciones por segundo]**

### 5.6. Métricas del Backend (JVM)

> **[CAPTURA: Panel del Backend con Heap, Non-Heap, HTTP Requests Rate y Tiempo de Respuesta Promedio]**

### 5.7. Alertas Visuales

> **[CAPTURA: Panel de alertas activas en el dashboard]**

---

## 6. Análisis de Resultados

### 6.1. ¿Cuál es el servidor que consume más recursos?

Según los datos observados en el dashboard, el **Backend (EC2-2)** es el servidor que consume más recursos, especialmente en términos de CPU y memoria. Esto se debe a que la aplicación Spring Boot WebFlux con Reactive MongoDB requiere una cantidad significativa de memoria para el Heap JVM (aproximadamente 150-200 MB) y la CPU se utiliza intensamente durante las peticiones HTTP y las consultas a la base de datos.

El **Frontend (EC2-3)** es el que menos recursos consume, ya que Nginx solo sirve archivos estáticos y la carga de procesamiento recae principalmente en el navegador del cliente.

### 6.2. ¿Qué componente representa el posible cuello de botella?

El **Backend** es el principal cuello de botella por las siguientes razones:

- **Memoria JVM:** El Heap se divide en Eden Space, Old Gen y Survivor Space. Si la memoria asignada es insuficiente, se producen GC (Garbage Collection) frecuentes que degradan el rendimiento.
- **HTTP Requests:** Cada petición consume un hilo de procesamiento. Con WebFlux (reactivo) esto se mitiga, pero aun así hay un límite en la cantidad de requests concurrentes que puede manejar.
- **Conexiones a MongoDB:** Si el pool de conexiones se agota, las nuevas peticiones deben esperar, aumentando la latencia.

El segundo posible cuello de botella es **MongoDB (EC2-1)** en términos de operaciones de disco y tamaño de la base de datos.

### 6.3. ¿Cuál sería el impacto de aumentar la cantidad de usuarios?

Al aumentar la cantidad de usuarios, se esperaría:

1. **Aumento en el CPU del Backend:** Más peticiones HTTP = mayor procesamiento = mayor uso de CPU
2. **Aumento en la Memoria del Backend:** Más objetos creados = mayor presión en el Garbage Collector
3. **Aumento de conexiones a MongoDB:** Más consultas simultáneas = mayor uso de conexiones en el pool
4. **Mayor latencia de respuesta:** Si el Backend se satura, los tiempos de respuesta P99 (percentil 99) aumentarán significativamente
5. **Posible degradación del Frontend:** No significativa, ya que Nginx maneja bien alta concurrencia para contenido estático

### 6.4. ¿Qué mejoras podrían implementarse para optimizar el rendimiento?

1. **Escalamiento horizontal del Backend:** Implementar múltiples réplicas del Backend usando un Load Balancer de Kubernetes para distribuir la carga
2. **Caché con Redis:** Implementar una capa de caché para reducir consultas repetitivas a MongoDB y mejorar los tiempos de respuesta
3. **Optimización de consultas MongoDB:** Revisar índices y consultas lentas usando el MongoDB Exporter para identificar cuellos de botella
4. **Límites de recursos en Kubernetes:** Configurar `resources.requests` y `resources.limits` en los deployments para garantizar una distribución justa de recursos
5. **Aumentar la memoria JVM:** Configurar `-Xmx` y `-Xms` en el Backend para dar más memoria Heap si es necesario
6. **Percentiles de latencia:** Agregar `management.metrics.distribution.percentiles-histogram.http.server.requests=true` en el backend para obtener métricas de P99, P95 y P50 reales (actualmente se usa promedio)
7. **Auto-scaling:** Configurar Horizontal Pod Autoscaler (HPA) en Kubernetes para escalar automáticamente según el uso de CPU

---

## 7. Conclusiones

La implementación de monitoreo con Prometheus y Grafana sobre una arquitectura de 4 instancias EC2 con Minikube ha demostrado ser una solución viable y profesional para la observabilidad del proyecto ELCHINO Restobar. Los objetivos planteados se cumplieron satisfactoriamente:

1. **Métricas de infraestructura:** Se monitorea CPU, memoria, disco y red de los 3 servidores mediante Node Exporter
2. **Métricas de aplicación:** El Backend expone métricas JVM y HTTP mediante Actuator con Micrometer
3. **Métricas de base de datos:** MongoDB es monitoreado mediante un sidecar exporter que reporta tamaño, conexiones y operaciones
4. **Dashboard centralizado:** Grafana presenta un dashboard completo con 7 filas de paneles que permiten visualizar el estado de toda la arquitectura
5. **Alertas:** Se implementaron 5 reglas de alerta para detectar problemas críticos como CPU alto, memoria alta, disco bajo o servicios caídos

La decisión de agregar una cuarta instancia EC2 dedicada al monitoreo fue acertada, ya que permite aislar la carga de observabilidad de los servicios productivos y garantiza que las métricas estén disponibles incluso si alguno de los servidores falla.

---

## 8. Evidencias Técnicas

- [ ] Captura de instalación de Node Exporter en EC2-1
- [ ] Captura de instalación de Node Exporter en EC2-2
- [ ] Captura de instalación de Node Exporter en EC2-3
- [ ] Captura de métricas del Actuator del Backend
- [ ] Captura de Prometheus targets (todos UP)
- [ ] Captura de configuración de Prometheus
- [ ] Captura de login de Grafana
- [ ] Captura de datasource de Prometheus en Grafana
- [ ] Captura de dashboard general (vista completa)
- [ ] Captura de panel de CPU
- [ ] Captura de panel de Memoria
- [ ] Captura de panel de Disco
- [ ] Captura de panel de MongoDB
- [ ] Captura de panel de Backend JVM
- [ ] Captura de panel de alertas activas
- [ ] Captura de reglas de alerta en Prometheus
- [ ] Captura de diagrama de arquitectura actual
- [ ] Captura de diagrama de arquitectura propuesta
