# Despliegue Multi-Cluster y Monitoreo - Examen Intermedio

Arquitectura: 4 instancias EC2 independientes, cada una con Minikube.
Namespaces: `freddy-quispe-12-namespace` (aplicacion), `monitoreo` (monitoreo)

Security Groups por EC2 (configurar **antes de desplegar**):

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

## 1. Prerequisitos (en cada EC2)

```bash
# Ubuntu 24.04 - t3.medium - 20GB EBS
sudo apt update && sudo apt install -y docker.io
sudo usermod -aG docker $USER && newgrp docker

# Minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Iniciar Minikube
minikube start --driver=docker
```

Ademas, en EC2-1, EC2-2 y EC2-3 instalar **Node Exporter** para metricas de CPU, memoria, disco y red (EC2-4 no necesita Node Exporter):

```bash
# Descargar e instalar Node Exporter
wget https://github.com/prometheus/node_exporter/releases/download/v1.11.1/node_exporter-1.11.1.linux-amd64.tar.gz
tar xvfz node_exporter-1.11.1.linux-amd64.tar.gz
sudo mv node_exporter-1.11.1.linux-amd64/node_exporter /usr/local/bin/

    # Crear servicio systemd
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

# Iniciar servicio
sudo systemctl daemon-reload
sudo systemctl enable node_exporter
sudo systemctl start node_exporter

# Verificar
curl http://localhost:9100/metrics | head -5
```

> **Nota:** Node Exporter se instala directamente en el SO host, NO dentro de Minikube.

---

## 2. Despliegue de Aplicaciones

### 2.1. Cluster MongoDB (EC2-1)

```bash
git clone https://github.com/tian-net/intermedio-manifiestos.git
cd intermedio-manifiestos
git checkout develop

kubectl apply -f mongo-cluster/freddy-quispe-12-namespace.yaml
kubectl apply -f mongo-cluster/mongo-deployment.yaml
kubectl apply -f mongo-cluster/mongo-service.yaml
kubectl apply -f mongo-cluster/mongodb-exporter-service.yaml

# Verificar que el pod este listo
kubectl wait --for=condition=ready pod -l app=mongo -n freddy-quispe-12-namespace --timeout=60s

# Exponer MongoDB fuera del cluster (dejar terminal abierta)
kubectl port-forward -n freddy-quispe-12-namespace service/mongo-service 27017:27017 --address 0.0.0.0
```

> **Nota:** El comando `port-forward` debe quedar ejecutandose. Abre una terminal separada o usa `&` al final para background.

### 2.2. Seed Data

Copiar el archivo `seed_elchino.mongodb` a EC2-1 y ejecutar:

```bash
# Desde tu maquina local a EC2-1
scp -i <tu-key.pem> seed_elchino.mongodb ubuntu@<EC2-1_IP>:~/

# En EC2-1, ejecutar el seed
mongosh < seed_elchino.mongodb
```

### 2.3. Cluster Backend (EC2-2)

Antes de desplegar, editar `backend-cluster/backend-deployment.yaml`:
- Reemplazar `<MONGO_EC2_IP>` con la **IP privada** de EC2-1 (si estan en la misma VPC) o **IP publica** (si no).
- Verificar que la imagen use el tag `monitoring` (con Actuator):

```bash
git clone https://github.com/tian-net/intermedio-manifiestos.git
cd intermedio-manifiestos
git checkout develop

# Editar la IP en backend-deployment.yaml
sed -i 's/<MONGO_EC2_IP>/IP_REAL_EC2_1/g' backend-cluster/backend-deployment.yaml

# Verificar que quedo correcto
cat backend-cluster/backend-deployment.yaml | grep DATABASE_URI
# Debe mostrar: mongodb://<IP>:27017/elchino

kubectl apply -f backend-cluster/freddy-quispe-12-namespace.yaml
kubectl apply -f backend-cluster/backend-deployment.yaml
kubectl apply -f backend-cluster/backend-service.yaml

# Verificar que el pod este listo
kubectl wait --for=condition=ready pod -l app=freddy-quispe-12-deployment -n freddy-quispe-12-namespace --timeout=120s

# Exponer Backend (dejar terminal abierta)
kubectl port-forward -n freddy-quispe-12-namespace service/freddy-quispe-12-service 30001:30001 --address 0.0.0.0
```

> **Importante:** Si el pod no arranca, revisa logs: `kubectl logs -n freddy-quispe-12-namespace deployment/freddy-quispe-12-deployment`

### 2.4. Cluster Frontend (EC2-3)

El frontend requiere la URL del backend **compilada en la imagen**. Pasos:

```bash
# En tu MAQUINA LOCAL (donde tienes el codigo frontend):
cd ASE242S4_T05-fe

# 1. Editar src/lib/constants.ts
#    Cambiar: 'http://localhost:8087/api'
#    Por:     'http://<EC2-2_IP>:30001/api'

# 2. Reconstruir imagen
docker build -t tian11qb/sebastian-front-react-vite-tailwind:lastest .

# 3. Pushear a Docker Hub
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

# Verificar que el pod este listo
kubectl wait --for=condition=ready pod -l app=frontend -n freddy-quispe-12-namespace --timeout=120s

# Si la imagen se actualizo, forzar reinicio
kubectl rollout restart deployment/frontend-deployment -n freddy-quispe-12-namespace

# Exponer Frontend (dejar terminal abierta)
kubectl port-forward -n freddy-quispe-12-namespace service/frontend-service 30080:80 --address 0.0.0.0
```

---

## 3. Verificacion

```bash
# Estado general
kubectl get all -n freddy-quispe-12-namespace

# EC2-1: MongoDB
kubectl logs -n freddy-quispe-12-namespace deployment/mongo-deployment

# EC2-2: Backend (Swagger)
curl http://localhost:30001/swagger-ui.html
curl http://localhost:30001/api/events

# EC2-2: Backend Actuator (Health + Metrics)
curl http://localhost:30001/actuator/health
curl http://localhost:30001/actuator/prometheus | head -20

# EC2-3: Frontend
curl http://localhost:30080
```

---

## 4. Monitoreo con Prometheus + Grafana

### 4.1. Despliegue de Prometheus (EC2-4)

```bash
# En EC2-4: instalar prerequisitos (Docker + Minikube + kubectl)
sudo apt update && sudo apt install -y docker.io
sudo usermod -aG docker $USER && newgrp docker
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
minikube start

# Clonar repositorio
git clone https://github.com/tian-net/intermedio-manifiestos.git
cd intermedio-manifiestos
git checkout develop

# IMPORTANTE: Editar monitoreo/prometheus/prometheus-config.yaml
# Reemplazar <EC2-1_IP>, <EC2-2_IP>, <EC2-3_IP> con IPs publicas reales
# (Node Exporter y demas targets ya deben estar accesibles en esas IPs)
sed -i 's/<EC2-1_IP>/IP_REAL_EC2_1/g' monitoreo/prometheus/prometheus-config.yaml
sed -i 's/<EC2-2_IP>/IP_REAL_EC2_2/g' monitoreo/prometheus/prometheus-config.yaml
sed -i 's/<EC2-3_IP>/IP_REAL_EC2_3/g' monitoreo/prometheus/prometheus-config.yaml

# Desplegar Prometheus
kubectl apply -f monitoreo/namespace-monitoreo.yaml
kubectl apply -f monitoreo/prometheus/prometheus-config.yaml
kubectl apply -f monitoreo/prometheus/prometheus-deployment.yaml
kubectl apply -f monitoreo/prometheus/prometheus-service.yaml

# Verificar pod
kubectl wait --for=condition=ready pod -l app=prometheus -n monitoreo --timeout=60s

# Exponer Prometheus (dejar terminal abierta)
kubectl port-forward -n monitoreo service/prometheus-service 30090:9090 --address 0.0.0.0
```

### 4.2. Despliegue de Grafana (EC2-4)

```bash
# Desplegar Grafana (datasource + dashboard se auto-configuran)
kubectl apply -f monitoreo/grafana/grafana-datasource.yaml
kubectl apply -f monitoreo/grafana/grafana-dashboard-configmap.yaml
kubectl apply -f monitoreo/grafana/grafana-deployment.yaml
kubectl apply -f monitoreo/grafana/grafana-service.yaml

# Verificar pod
kubectl wait --for=condition=ready pod -l app=grafana -n monitoreo --timeout=60s

# Exponer Grafana (dejar terminal abierta)
kubectl port-forward -n monitoreo service/grafana-service 30300:3000 --address 0.0.0.0
```

> **Acceso:** http://<EC2-4_IP>:30300 | Usuario: `admin` | Password: `admin`

### 4.3. Verificacion de Monitoreo

```bash
# Prometheus targets
curl http://localhost:30090/targets

# Pods en namespace monitoreo
kubectl get all -n monitoreo

# Verificar targets UP en browser:
# http://<EC2-4_IP>:30090/targets
# Deben aparecer:
#   - prometheus (UP)
#   - node-mongo (UP)
#   - node-backend (UP)
#   - node-frontend (UP)
#   - mongodb (UP)
#   - backend-actuator (UP)
```

### 4.4. Dashboard en Grafana

Una vez en Grafana (http://<EC2-4_IP>:30300):

1. Ir a **Dashboards → Browse**
2. Seleccionar **"ELCHINO - Monitoreo General"**
3. El dashboard se importo automaticamente desde el ConfigMap

> Si no aparece, importar manualmente:
> 1. Dashboards → New → Import
> 2. Pegar el contenido de `monitoreo/grafana/grafana-dashboard-configmap.yaml` (seccion JSON)
> 3. Seleccionar datasource Prometheus
> 4. Import

Paneles del dashboard:

| Fila | Panel | Metrica |
|------|-------|---------|
| 1 | Estado general | UP de cada servicio |
| 2 | CPU | % uso por servidor |
| 3 | Memoria | % uso por servidor |
| 4 | Disco | % usado y GB libres |
| 5 | MongoDB | Tamaño BD, conexiones, ops/s |
| 6 | Backend JVM | Heap, Non-Heap, requests, latencia P99 |
| 7 | Alertas activas | Lista de alertas disparadas |

### 4.5. Alertas

Las alertas estan definidas en `monitoreo/alertas/alert-rules.yaml` e incluidas en Prometheus:

| Alerta | Condicion | Severidad |
|--------|-----------|-----------|
| HighCPUUsage | CPU > 80% por 5 min | Critical |
| HighMemoryUsage | Memoria > 80% por 5 min | Critical |
| LowDiskSpace | Disco libre < 20% | Warning |
| BackendDown | Backend sin respuesta | Critical |
| MongoDBDown | MongoDB sin respuesta | Critical |

Para configurar notificaciones en Grafana:

1. Ir a **Alerting → Contact points → New contact point**
2. Elegir tipo (Email, Slack, Webhook, etc.)
3. Configurar destinatario
4. Ir a **Alerting → Notification policies** y asignar la politica

---

## 5. Limpieza

```bash
# Eliminar namespaces completos
kubectl delete namespace freddy-quispe-12-namespace
kubectl delete namespace monitoreo

# Matar procesos de port-forward
sudo fuser -k 30080/tcp 30001/tcp 27017/tcp 30090/tcp 30300/tcp

# Eliminar Minikube
minikube delete --all

# Ver logs de pods antes de eliminar (opcional)
kubectl logs -n freddy-quispe-12-namespace deployment/freddy-quispe-12-deployment
kubectl describe pod -l app=frontend -n freddy-quispe-12-namespace
```
