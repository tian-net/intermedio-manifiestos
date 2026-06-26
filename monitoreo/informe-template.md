# INFORME TÉCNICO - Integración de Monitoreo y Observabilidad

**Proyecto:** ELCHINO Restobar
**Curso:** ASE242 - Aplicaciones en Servidores
**Integrantes:** [Nombres]

---

## 1. Arquitectura Actual

| Servidor | EC2 | Función | Servicios | Puertos |
|----------|-----|---------|-----------|---------|
| MongoDB | EC2-1 | Base de datos | MongoDB 7-jammy (Minikube) | 27017 |
| Backend | EC2-2 | API REST | Spring Boot WebFlux (Minikube) | 30001 → 8087 |
| Frontend | EC2-3 | Interfaz web | React + Vite + Nginx (Minikube) | 30080 → 80 |

### Diagrama de Arquitectura Actual

> **[ESPACIO PARA DIAGRAMA]**

### Comunicación entre servidores

- Frontend (EC2-3) → Backend (EC2-2) vía HTTP (puerto 30001)
- Backend (EC2-2) → MongoDB (EC2-1) vía MongoDB protocol (puerto 27017)
- Cada servidor ejecuta Minikube con Docker driver

---

## 2. Arquitectura Propuesta (Monitoreo)

| Servidor | EC2 | Función | Servicios | Puertos |
|----------|-----|---------|-----------|---------|
| MongoDB | EC2-1 | Base de datos + Exporters | MongoDB 7 + MongoDB Exporter + Node Exporter | 27017, 30092, 9100 |
| Backend | EC2-2 | API REST + Métricas | Spring Boot + Actuator + Node Exporter | 30001, 9100 |
| Frontend | EC2-3 | Frontend + Métricas | React + Nginx + Node Exporter | 30080, 9100 |
| Monitoreo | **EC2-4** | Observabilidad | Prometheus + Grafana (Minikube) | 30090, 30300 |

### Diagrama de Arquitectura Propuesta

> **[ESPACIO PARA DIAGRAMA]**

---

## 3. Justificación Técnica

### 3.1. ¿Es conveniente instalar Prometheus y Grafana en alguno de los servidores existentes?

[Responder aquí]

### 3.2. ¿Qué ventajas y desventajas tendría esta decisión?

**Ventajas:**
- [Listar]

**Desventajas:**
- [Listar]

### 3.3. ¿Es recomendable implementar un servidor adicional para monitoreo?

[Responder aquí]

### 3.4. ¿Qué recursos mínimos requeriría dicho servidor?

| Recurso | Mínimo |
|---------|--------|
| CPU | 2 vCPUs |
| RAM | 2 GB |
| Disco | 20 GB |
| SO | Ubuntu 24.04 |

### 3.5. ¿Cómo se comunicarían Prometheus y Grafana con los demás servidores?

[Responder aquí]

---

## 4. Procedimiento Realizado

### 4.1. Archivos Modificados / Creados

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `backend-cluster/backend-deployment.yaml` | Modificado | Image tag `lastest` → `monitoring` (con Actuator) |
| `mongo-cluster/mongo-deployment.yaml` | Modificado | Agregado sidecar MongoDB Exporter con collectors |
| `mongo-cluster/mongodb-exporter-service.yaml` | Creado | Service NodePort 30092 para MongoDB Exporter |
| `monitoreo/namespace-monitoreo.yaml` | Creado | Namespace `monitoreo` |
| `monitoreo/prometheus/prometheus-config.yaml` | Creado | Config de targets + reglas de alerta |
| `monitoreo/prometheus/prometheus-deployment.yaml` | Creado | Deployment de Prometheus |
| `monitoreo/prometheus/prometheus-service.yaml` | Creado | Service NodePort 30090 |
| `monitoreo/grafana/grafana-datasource.yaml` | Creado | Datasource automático Prometheus |
| `monitoreo/grafana/grafana-dashboard-configmap.yaml` | Creado | Dashboard JSON (6 filas de paneles) |
| `monitoreo/grafana/grafana-deployment.yaml` | Creado | Deployment de Grafana |
| `monitoreo/grafana/grafana-service.yaml` | Creado | Service NodePort 30300 |
| `monitoreo/alertas/alert-rules.yaml` | Creado | 5 reglas de alerta (CPU, Mem, Disco, Backend, MongoDB) |
| `comandos.md` | Modificado | Guía organizada cronológicamente con Node Exporter en prerequisitos |
| `seed_elchino.mongodb` | Creado | Seed data para MongoDB |
| `ASE242S4_T05-be/pom.xml` | Modificado | Agregadas dependencias Actuator + Micrometer |
| `ASE242S4_T05-be/src/main/resources/application.yaml` | Modificado | Exposición endpoint `/actuator/prometheus` |
| `ASE242S4_T05-be/src/main/java/.../SecurityConfig.java` | Modificado | `.pathMatchers("/actuator/**").permitAll()` |

### 4.2. Instalación de Node Exporters

En cada **EC2 host** (EC2-1, EC2-2, EC2-3), directamente en el SO:

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

> **[CAPTURA: Instalación node_exporter en EC2-1]**
> **[CAPTURA: Instalación node_exporter en EC2-2]**
> **[CAPTURA: Instalación node_exporter en EC2-3]**

### 4.3. Instalación de MongoDB Exporter

Sidecar container en el mismo pod de MongoDB (`mongo-cluster/mongo-deployment.yaml`):

```yaml
- name: mongodb-exporter
  image: bitnami/mongodb-exporter:latest
  args:
    - "--collector.database"
    - "--collector.topmetrics"
    - "--collector.connections"
    - "--collector.opcounters"
    - "--collector.collstats"
    - "--compatible-mode"
  ports:
    - containerPort: 9216
  env:
    - name: MONGODB_URI
      value: "mongodb://localhost:27017"
```

Además, el service NodePort (`mongo-cluster/mongodb-exporter-service.yaml`):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mongodb-exporter-service
  namespace: freddy-quispe-12-namespace
spec:
  type: NodePort
  ports:
    - port: 9216
      targetPort: 9216
      nodePort: 30092
  selector:
    app: mongo
```

> **[CAPTURA: Deploy MongoDB Exporter sidecar]**

### 4.4. Configuración de Prometheus

Archivo de configuración (`monitoreo/prometheus/prometheus-config.yaml`):

```yaml
scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  - job_name: 'node-mongo'
    static_configs:
      - targets: ['<EC2-1_IP>:9100']
  - job_name: 'node-backend'
    static_configs:
      - targets: ['<EC2-2_IP>:9100']
  - job_name: 'node-frontend'
    static_configs:
      - targets: ['<EC2-3_IP>:9100']
  - job_name: 'mongodb'
    static_configs:
      - targets: ['<EC2-1_IP>:30092']
  - job_name: 'backend-actuator'
    metrics_path: '/actuator/prometheus'
    static_configs:
      - targets: ['<EC2-2_IP>:30001']
```

Comandos de despliegue:
```bash
kubectl apply -f monitoreo/namespace-monitoreo.yaml
kubectl apply -f monitoreo/prometheus/prometheus-config.yaml
kubectl apply -f monitoreo/prometheus/prometheus-deployment.yaml
kubectl apply -f monitoreo/prometheus/prometheus-service.yaml
kubectl wait --for=condition=ready pod -l app=prometheus -n monitoreo --timeout=60s
kubectl port-forward -n monitoreo service/prometheus-service 30090:9090 --address 0.0.0.0
```

> **[CAPTURA: Prometheus targets up]**
> **[CAPTURA: Prometheus configuración]**

### 4.5. Configuración de Grafana

```bash
kubectl apply -f monitoreo/grafana/grafana-datasource.yaml
kubectl apply -f monitoreo/grafana/grafana-dashboard-configmap.yaml
kubectl apply -f monitoreo/grafana/grafana-deployment.yaml
kubectl apply -f monitoreo/grafana/grafana-service.yaml
kubectl wait --for=condition=ready pod -l app=grafana -n monitoreo --timeout=60s
kubectl port-forward -n monitoreo service/grafana-service 30300:3000 --address 0.0.0.0
```

> **[CAPTURA: Grafana login / datasource]**
> **[CAPTURA: Grafana datasource configurado]**

### 4.6. Configuración de Alertas

5 reglas definidas en `monitoreo/alertas/alert-rules.yaml`:

| Alerta | Condición | Severidad |
|--------|-----------|-----------|
| HighCPUUsage | CPU > 80% por 5 min | Critical |
| HighMemoryUsage | Memoria > 80% por 5 min | Critical |
| LowDiskSpace | Disco libre < 20% | Warning |
| BackendDown | Backend sin respuesta | Critical |
| MongoDBDown | MongoDB sin respuesta | Critical |

> **[CAPTURA: Reglas de alerta en Prometheus]**

### 4.7. Errores Encontrados y Soluciones

| # | Error | Causa | Solución | Archivos afectados |
|---|-------|-------|----------|-------------------|
| 1 | `404 Not Found` al descargar Node Exporter | URL `/latest/download/` redirige a asset sin versión en el nombre | Usar URL con versión explícita: `v1.11.1/node_exporter-1.11.1.linux-amd64.tar.gz` | `comandos.md` |
| 2 | Pod Prometheus en `CrashLoopBackOff` | `labels` mal indentado en `prometheus-config.yml` (fuera de `static_configs`) | Mover `labels` dentro de `static_configs` o eliminarlas | `monitoreo/prometheus/prometheus-config.yaml` |
| 3 | Target MongoDB en `DOWN`: `connection refused :30092` | Falta `kubectl port-forward` para MongoDB Exporter en EC2-1 | Agregar port-forward: `kubectl port-forward -n freddy-quispe-12-namespace service/mongodb-exporter-service 30092:9216 --address 0.0.0.0` | — |
| 4 | Dashboard MongoDB muestra "No data" | MongoDB Exporter sin collectors habilitados (solo `general`) | Agregar `args` al sidecar: `--collector.database`, `--collector.connections`, `--collector.opcounters`, etc. | `mongo-cluster/mongo-deployment.yaml` |
| 5 | `git push` rechazado (`fetch first`) | Cambios remotos no sincronizados | `git pull origin develop` y resolver merge conflict en `comandos.md` | `comandos.md` |
| 6 | Merge conflict en `comandos.md` | Versión local vs remota divergentes en sección Frontend | Resolver manteniendo ambas versiones (MAQUINA LOCAL + EC2-3) | `comandos.md` |
| 7 | Minikube warning: "memory allocation leaves no room for system overhead" | t3.small (2GB RAM) muy justo para 3072MB default de Minikube | Reducir memoria: `minikube start --memory=2048mb` (opcional, warning no bloqueante) | — |

---

## 5. Dashboard Implementado

### 5.1. Estado General de Servidores

> **[CAPTURA: Panel de estado general]**

### 5.2. Consumo de CPU - Comparativa

> **[CAPTURA: Gráfico CPU]**

### 5.3. Consumo de Memoria - Comparativa

> **[CAPTURA: Gráfico Memoria]**

### 5.4. Espacio en Disco

> **[CAPTURA: Gráfico Disco]**

### 5.5. Métricas de MongoDB

> **[CAPTURA: Panel MongoDB]**

### 5.6. Métricas del Backend (JVM)

> **[CAPTURA: Panel Backend JVM]**

### 5.7. Alertas Visuales

> **[CAPTURA: Panel de alertas activas]**

---

## 6. Análisis de Resultados

### 6.1. ¿Cuál es el servidor que consume más recursos?

[Responder aquí - basado en datos observados]

### 6.2. ¿Qué componente representa el posible cuello de botella?

[Responder aquí]

### 6.3. ¿Cuál sería el impacto de aumentar la cantidad de usuarios?

[Responder aquí]

### 6.4. ¿Qué mejoras podrían implementarse para optimizar el rendimiento?

[Responder aquí]

---

## 7. Conclusiones

[Escribir conclusiones aquí]

---

## 8. Evidencias Técnicas

- [ ] Capturas de instalación
- [ ] Capturas de Prometheus
- [ ] Capturas de Grafana
- [ ] Capturas de dashboards implementados
