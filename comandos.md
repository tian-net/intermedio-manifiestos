# Despliegue Multi-Cluster y Monitoreo - Examen Intermedio

Arquitectura: 4 instancias EC2 independientes, cada una con Minikube.
Namespaces: `freddy-quispe-12-namespace` (aplicacion), `monitoreo` (monitoreo)

## Despliegue Rapido — Orden de Ejecucion

| Orden | EC2 | Accion | Comandos clave |
|-------|-----|--------|----------------|
| 0 | **Todas** | Security Groups | Configurar puertos segun tabla abajo |
| 1 | **Todas** | Prerequisitos | Docker + Minikube + kubectl |
| 2 | **EC2-1,2,3** | Node Exporter | wget + tar + systemctl start |
| 3 | **EC2-1** | MongoDB + MongoDB Exporter | `kubectl apply -f mongo-cluster/` |
| 4 | **EC2-1** | Seed data | `mongosh < seed_elchino.mongodb` |
| 5 | **EC2-2** | Backend | `sed` IP MongoDB + `kubectl apply -f backend-cluster/` |
| 6 | **PC local** | Frontend rebuild | `cd ASE242S4_T05-fe` → editar constants → `docker build + push` |
| 7 | **EC2-3** | Frontend | `kubectl apply -f frontend-cluster/` |
| 8 | **EC2-4** | Prometheus | `sed` 3 IPs + `kubectl apply -f monitoreo/prometheus/` |
| 9 | **EC2-4** | Grafana | `kubectl apply -f monitoreo/grafana/` |
| 10 | **Todas** | Verificar | `curl` cada servicio + Prometheus targets UP |

---

## Security Groups por EC2 (configurar ANTES de desplegar)

| EC2 | Puerto | Origen | Descripcion |
|-----|--------|--------|-------------|
| **EC2-1 (MongoDB)** | 27017 | IP de EC2-2 | MongoDB desde Backend |
| EC2-1 (MongoDB) | 30092 | IP de EC2-4 | MongoDB Exporter |
| EC2-1 (MongoDB) | 9100 | IP de EC2-4 | Node Exporter |
| **EC2-2 (Backend)** | 30001 | 0.0.0.0/0 | API REST + Swagger + Actuator |
| EC2-2 (Backend) | 9100 | IP de EC2-4 | Node Exporter |
| **EC2-3 (Frontend)** | 30080 | 0.0.0.0/0 | Frontend React |
| EC2-3 (Frontend) | 9100 | IP de EC2-4 | Node Exporter |
| **EC2-4 (Monitoreo)** | 30090 | 0.0.0.0/0 | Prometheus UI |
| EC2-4 (Monitoreo) | 30300 | 0.0.0.0/0 | Grafana UI |

> **Recomendacion:** Usar IPs privadas para trafico entre EC2 (misma VPC) y solo exponer a 0.0.0.0/0 los puertos de acceso publico (30001, 30080, 30090, 30300).

---

## 1. Prerequisitos

### En EC2-1, EC2-2, EC2-3 (con Node Exporter)

```bash
# Docker
sudo apt update && sudo apt install -y docker.io
sudo usermod -aG docker $USER && newgrp docker

# Minikube + kubectl
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
minikube start --driver=docker

# Node Exporter (metricas CPU, memoria, disco, red)
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

sudo systemctl daemon-reload
sudo systemctl enable node_exporter
sudo systemctl start node_exporter
curl http://localhost:9100/metrics | head -5
```

> Node Exporter se instala en el SO host, NO dentro de Minikube.

### En EC2-4 (solo Docker + Minikube, sin Node Exporter)

```bash
# Solo los comandos de Docker, Minikube y kubectl (sin Node Exporter)
sudo apt update && sudo apt install -y docker.io
sudo usermod -aG docker $USER && newgrp docker
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
minikube start --driver=docker
```

---

## 2. Despliegue de Aplicaciones

### 2.1. MongoDB + MongoDB Exporter (EC2-1)

```bash
git clone https://github.com/tian-net/intermedio-manifiestos.git
cd intermedio-manifiestos
git checkout develop

kubectl apply -f mongo-cluster/freddy-quispe-12-namespace.yaml
kubectl apply -f mongo-cluster/mongo-deployment.yaml
kubectl apply -f mongo-cluster/mongo-service.yaml
kubectl apply -f mongo-cluster/mongodb-exporter-service.yaml

kubectl wait --for=condition=ready pod -l app=mongo -n freddy-quispe-12-namespace --timeout=60s

# Port-forward MongoDB (dejar terminal abierta)
kubectl port-forward -n freddy-quispe-12-namespace service/mongo-service 27017:27017 --address 0.0.0.0
```

> El `port-forward` debe quedar ejecutandose. Usa otra terminal o agrega `&` al final.

### 2.2. Seed Data (EC2-1)

```bash
# Desde tu maquina local:
scp -i <tu-key.pem> seed_elchino.mongodb ubuntu@<EC2-1_IP>:~/

# En EC2-1:
mongosh < seed_elchino.mongodb
```

### 2.3. Backend (EC2-2)

Antes de desplegar, editar `<MONGO_EC2_IP>` con la IP de EC2-1:

```bash
git clone https://github.com/tian-net/intermedio-manifiestos.git
cd intermedio-manifiestos
git checkout develop

# Reemplazar con IP real de EC2-1 (publica o privada)
sed -i 's/<MONGO_EC2_IP>/100.30.143.138/g' backend-cluster/backend-deployment.yaml

cat backend-cluster/backend-deployment.yaml | grep DATABASE_URI
# Debe mostrar: mongodb://<IP>:27017/elchino

kubectl apply -f backend-cluster/freddy-quispe-12-namespace.yaml
kubectl apply -f backend-cluster/backend-deployment.yaml
kubectl apply -f backend-cluster/backend-service.yaml

kubectl wait --for=condition=ready pod -l app=freddy-quispe-12-deployment -n freddy-quispe-12-namespace --timeout=120s

# Port-forward Backend (dejar terminal abierta)
kubectl port-forward -n freddy-quispe-12-namespace service/freddy-quispe-12-service 30001:30001 --address 0.0.0.0
```

### 2.4. Frontend (EC2-3)

Primero, en tu **PC local** reconstruir la imagen con la IP del backend:

```bash
cd ASE242S4_T05-fe

# Editar src/lib/constants.ts:
# API_BASE = 'http://<EC2-2_IP>:30001/api'

docker build -t tian11qb/sebastian-front-react-vite-tailwind:lastest .
docker push tian11qb/sebastian-front-react-vite-tailwind:lastest
```

Luego en EC2-3:

```bash
git clone https://github.com/tian-net/intermedio-manifiestos.git
cd intermedio-manifiestos
git checkout develop

kubectl apply -f frontend-cluster/freddy-quispe-12-namespace.yaml
kubectl apply -f frontend-cluster/frontend-deployment.yaml
kubectl apply -f frontend-cluster/frontend-service.yaml

kubectl wait --for=condition=ready pod -l app=frontend -n freddy-quispe-12-namespace --timeout=120s

# Si la imagen cambio, forzar reinicio
kubectl rollout restart deployment/frontend-deployment -n freddy-quispe-12-namespace

# Port-forward Frontend (dejar terminal abierta)
kubectl port-forward -n freddy-quispe-12-namespace service/frontend-service 30080:80 --address 0.0.0.0
```

---

## 3. Port-Forwards Necesarios (6 terminales)

Para que todo funcione, deben estar activos estos port-forwards:

| EC2 | Terminal | Puerto Host | Puerto Pod | Comando |
|-----|----------|-------------|------------|---------|
| **EC2-1** | T1 | `27017` | 27017 | `kubectl port-forward -n freddy-quispe-12-namespace service/mongo-service 27017:27017 --address 0.0.0.0` |
| **EC2-1** | T2 | `30092` | 9216 | `kubectl port-forward -n freddy-quispe-12-namespace service/mongodb-exporter-service 30092:9216 --address 0.0.0.0` |
| **EC2-2** | T1 | `30001` | 30001 | `kubectl port-forward -n freddy-quispe-12-namespace service/freddy-quispe-12-service 30001:30001 --address 0.0.0.0` |
| **EC2-3** | T1 | `30080` | 80 | `kubectl port-forward -n freddy-quispe-12-namespace service/frontend-service 30080:80 --address 0.0.0.0` |
| **EC2-4** | T1 | `30090` | 9090 | `kubectl port-forward -n monitoreo service/prometheus-service 30090:9090 --address 0.0.0.0` |
| **EC2-4** | T2 | `30300` | 3000 | `kubectl port-forward -n monitoreo service/grafana-service 30300:3000 --address 0.0.0.0` |

> Cada terminal ocupada = 1 port-forward. Si se cierra una terminal, el servicio deja de ser accesible.

---

## 4. Verificacion

```bash
# EC2-1: MongoDB
kubectl logs -n freddy-quispe-12-namespace deployment/mongo-deployment

# EC2-2: Backend
curl http://localhost:30001/swagger-ui.html
curl http://localhost:30001/api/events
curl http://localhost:30001/actuator/health
curl http://localhost:30001/actuator/prometheus | head -20

# EC2-3: Frontend
curl http://localhost:30080

# Estado general
kubectl get all -n freddy-quispe-12-namespace
```

---

## 5. Monitoreo con Prometheus + Grafana

### 5.1. Despliegue de Prometheus (EC2-4)

Editar las 3 IPs de los targets y desplegar:

```bash
cd ~/intermedio-manifiestos
git checkout develop

# Reemplazar con las IPs reales (publicas o privadas segun Security Groups)
sed -i 's/<EC2-1_IP>/100.30.143.138/g' monitoreo/prometheus/prometheus-config.yaml
sed -i 's/<EC2-2_IP>/35.172.21.255/g' monitoreo/prometheus/prometheus-config.yaml
sed -i 's/<EC2-3_IP>/100.57.54.206/g' monitoreo/prometheus/prometheus-config.yaml

kubectl apply -f monitoreo/namespace-monitoreo.yaml
kubectl apply -f monitoreo/prometheus/prometheus-config.yaml
kubectl apply -f monitoreo/prometheus/prometheus-deployment.yaml
kubectl apply -f monitoreo/prometheus/prometheus-service.yaml

kubectl wait --for=condition=ready pod -l app=prometheus -n monitoreo --timeout=60s

# Exponer Prometheus (dejar terminal abierta)
kubectl port-forward -n monitoreo service/prometheus-service 30090:9090 --address 0.0.0.0
```

### 5.2. Despliegue de Grafana (EC2-4)

```bash
kubectl apply -f monitoreo/grafana/grafana-datasource.yaml
kubectl apply -f monitoreo/grafana/grafana-dashboard-configmap.yaml
kubectl apply -f monitoreo/grafana/grafana-deployment.yaml
kubectl apply -f monitoreo/grafana/grafana-service.yaml

kubectl wait --for=condition=ready pod -l app=grafana -n monitoreo --timeout=60s

# Exponer Grafana (dejar terminal abierta)
kubectl port-forward -n monitoreo service/grafana-service 30300:3000 --address 0.0.0.0
```

> **Acceso:** `http://<EC2-4_IP>:30300` | Usuario: `admin` | Password: `admin`

### 5.3. Verificacion de Monitoreo

```bash
curl http://localhost:30090/targets
kubectl get all -n monitoreo
```

En el navegador: `http://<EC2-4_IP>:30090/targets` deben aparecer 6 targets UP:

- `prometheus` (UP)
- `node-mongo` (UP)
- `node-backend` (UP)
- `node-frontend` (UP)
- `mongodb` (UP)
- `backend-actuator` (UP)

### 5.4. Dashboard en Grafana

En `http://<EC2-4_IP>:30300`:

1. **Dashboards → Browse → "ELCHINO - Monitoreo General"** (se importa automaticamente)
2. Si no aparece, importar manualmente desde el JSON en `monitoreo/grafana/grafana-dashboard-configmap.yaml`

Paneles del dashboard:

| Fila | Panel | Metrica |
|------|-------|---------|
| 1 | Estado general | UP de cada servicio |
| 2 | CPU | % uso por servidor |
| 3 | Memoria | % uso por servidor |
| 4 | Disco | % usado y GB libres |
| 5 | MongoDB | Tamaño BD, conexiones, ops/s |
| 6 | Backend JVM | Heap, Non-Heap, requests, tiempo promedio |
| 7 | Alertas activas | Lista de alertas disparadas |

### 5.5. Alertas

| Alerta | Condicion | Severidad |
|--------|-----------|-----------|
| HighCPUUsage | CPU > 80% por 5 min | Critical |
| HighMemoryUsage | Memoria > 80% por 5 min | Critical |
| LowDiskSpace | Disco libre < 20% | Warning |
| BackendDown | Backend sin respuesta | Critical |
| MongoDBDown | MongoDB sin respuesta | Critical |

Configurar notificaciones en Grafana: **Alerting → Contact points → New contact point** (Email, Slack, Webhook)

---

## 6. Errores Comunes y Soluciones

| # | Error | Causa | Solucion |
|---|-------|-------|----------|
| 1 | `404 Not Found` al descargar Node Exporter | URL `/latest/download/` redirige a asset sin version | Usar URL con version explicita: `v1.11.1/node_exporter-1.11.1.linux-amd64.tar.gz` |
| 2 | Pod Prometheus `CrashLoopBackOff` | `labels` mal indentado en `prometheus-config.yml` | Eliminar `labels` o moverlos dentro de `static_configs` |
| 3 | Target MongoDB `DOWN`: `connection refused :30092` | Falta port-forward de MongoDB Exporter en EC2-1 | `kubectl port-forward -n freddy-quispe-12-namespace service/mongodb-exporter-service 30092:9216 --address 0.0.0.0` |
| 4 | Dashboard MongoDB muestra "No data" | MongoDB Exporter sin collectors habilitados | Usar `--collect-all --compatible-mode` en args del sidecar |
| 5 | Pod MongoDB sidecar `Error: unknown flag` | Nombres de collectors incorrectos | Usar `--collect-all --compatible-mode` en vez de collectors sueltos |
| 6 | Dashboard muestra "No data" en JVM | Nombres de metricas incorrectos en queries | Usar `jvm_memory_committed_bytes{application="Elchino"}` en vez de `jvm_memory_used_bytes{job="backend-actuator"}` |
| 7 | Tiempo de respuesta P99 sin datos | WebFlux no genera histogram buckets por defecto | Usar promedio: `rate(sum)/rate(count) * 1000` |
| 8 | `git push` rechazado | Cambios remotos no sincronizados | `git pull origin develop` y resolver conflictos |
| 9 | Minikube warning: "memory allocation" | t3.small (2GB RAM) justo para 3072MB default | `minikube start --memory=2048mb` (warning no bloqueante) |

---

## 7. Limpieza

```bash
# Eliminar namespaces completos
kubectl delete namespace freddy-quispe-12-namespace
kubectl delete namespace monitoreo

# Matar procesos de port-forward
sudo fuser -k 30080/tcp 30001/tcp 27017/tcp 30090/tcp 30300/tcp

# Eliminar Minikube
minikube delete --all
```
