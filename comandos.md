# Despliegue Multi-Cluster y Monitoreo — Examen Intermedio

**Arquitectura:** 4 instancias EC2 independientes, cada una con Minikube.
**Namespaces:** `freddy-quispe-12-namespace` (aplicacion), `monitoreo` (monitoreo)

---

## Puertos por Servidor (configurar Security Groups ANTES de empezar)

| EC2 | Puertos abiertos | Origen |
|-----|------------------|--------|
| **EC2-1** (MongoDB) | 27017, 30092, 9100 | IPs EC2-2, EC2-4 |
| **EC2-2** (Backend) | 30001, 9100 | 0.0.0.0 (30001), EC2-4 (9100) |
| **EC2-3** (Frontend) | 30080, 9100 | 0.0.0.0 (30080), EC2-4 (9100) |
| **EC2-4** (Monitoreo) | 30090, 30300 | 0.0.0.0 |

> Usar IPs privadas (172.31.x.x) para trafico entre EC2 (misma VPC). Exponer a 0.0.0.0 solo los puertos de acceso publico.

---

## BLOQUE 1 — Docker + Minikube + kubectl (correr en EC2-1, EC2-2, EC2-3, EC2-4)

```bash
sudo apt update && sudo apt install -y docker.io
sudo usermod -aG docker $USER
newgrp docker
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
minikube start --driver=docker
```

---

## BLOQUE 2 — Node Exporter (correr solo en EC2-1, EC2-2, EC2-3)

```bash
wget https://github.com/prometheus/node_exporter/releases/download/v1.11.1/node_exporter-1.11.1.linux-amd64.tar.gz
tar xvfz node_exporter-1.11.1.linux-amd64.tar.gz
sudo mv node_exporter-1.11.1.linux-amd64/node_exporter /usr/local/bin/
sudo tee /etc/systemd/system/node_exporter.service > /dev/null << 'EOF'
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
sudo systemctl enable --now node_exporter
curl -s http://localhost:9100/metrics | head -3
```

---

## BLOQUE 3 — MongoDB + MongoDB Exporter + Seed Data (correr en EC2-1)

Antes de empezar: anota la IP **privada** de EC2-1 (la usarás en el Backend).

```bash
# 1. Clonar repo
git clone https://github.com/tian-net/intermedio-manifiestos.git
cd intermedio-manifiestos
git checkout develop

# 2. Desplegar MongoDB
kubectl apply -f mongo-cluster/freddy-quispe-12-namespace.yaml
kubectl apply -f mongo-cluster/mongo-deployment.yaml
kubectl apply -f mongo-cluster/mongo-service.yaml
kubectl apply -f mongo-cluster/mongodb-exporter-service.yaml
kubectl wait --for=condition=ready pod -l app=mongo -n freddy-quispe-12-namespace --timeout=90s

# 3. Port-forwards (dejar corriendo en background)
nohup kubectl port-forward -n freddy-quispe-12-namespace service/mongo-service 27017:27017 --address 0.0.0.0 > /dev/null 2>&1 &
nohup kubectl port-forward -n freddy-quispe-12-namespace service/mongodb-exporter-service 30092:9216 --address 0.0.0.0 > /dev/null 2>&1 &

# 4. Seed data (desde tu PC local, copiar el archivo)
# scp -i <tu-key.pem> seed_elchino.mongodb ubuntu@<EC2-1_IP>:~/
# Luego en EC2-1:
mongosh < seed_elchino.mongodb

# 5. Verificar
kubectl get pods -n freddy-quispe-12-namespace
curl -s http://localhost:30092/metrics | head -3
```

---

## BLOQUE 4 — Backend (correr en EC2-2)

Reemplaza `IP_PRIVADA_EC2-1` con la IP privada de EC2-1 (172.31.x.x).

```bash
git clone https://github.com/tian-net/intermedio-manifiestos.git
cd intermedio-manifiestos
git checkout develop

# Reemplazar con IP privada de EC2-1
sed -i "s/<MONGO_EC2_IP>/IP_PRIVADA_EC2-1/g" backend-cluster/backend-deployment.yaml

kubectl apply -f backend-cluster/freddy-quispe-12-namespace.yaml
kubectl apply -f backend-cluster/backend-deployment.yaml
kubectl apply -f backend-cluster/backend-service.yaml
kubectl wait --for=condition=ready pod -l app=freddy-quispe-12-deployment -n freddy-quispe-12-namespace --timeout=120s

nohup kubectl port-forward -n freddy-quispe-12-namespace service/freddy-quispe-12-service 30001:30001 --address 0.0.0.0 > /dev/null 2>&1 &

# Verificar
curl -s http://localhost:30001/actuator/health | head -5
curl -s http://localhost:30001/actuator/prometheus | head -10
```

---

## BLOQUE 5 — Frontend (correr en EC2-3)

```bash
git clone https://github.com/tian-net/intermedio-manifiestos.git
cd intermedio-manifiestos
git checkout develop

kubectl apply -f frontend-cluster/freddy-quispe-12-namespace.yaml
kubectl apply -f frontend-cluster/frontend-deployment.yaml
kubectl apply -f frontend-cluster/frontend-service.yaml
kubectl wait --for=condition=ready pod -l app=frontend -n freddy-quispe-12-namespace --timeout=120s

nohup kubectl port-forward -n freddy-quispe-12-namespace service/frontend-service 30080:80 --address 0.0.0.0 > /dev/null 2>&1 &

# Verificar
curl -s http://localhost:30080 | head -5
```

> Si cambiaste la IP del backend, reconstruir la imagen frontend desde tu PC local:
> ```bash
> cd ASE242S4_T05-fe
> # 1. Editar .env con la IP publica de EC2-2
> echo "VITE_API_BASE=http://<EC2-2_PUBLIC_IP>:30001/api" > .env
> # 2. Build + push
> npm run build
> docker build -t tian11qb/sebastian-front-react-vite-tailwind:lastest .
> docker push tian11qb/sebastian-front-react-vite-tailwind:lastest
> # 3. En EC2-3: rollout restart
> kubectl rollout restart deployment/frontend-deployment -n freddy-quispe-12-namespace
> ```

---

## BLOQUE 6 — Prometheus (correr en EC2-4)

Reemplaza las 3 IPs con las IPs **publicas** de EC2-1, EC2-2, EC2-3.

```bash
cd ~/intermedio-manifiestos
git checkout develop

sed -i "s/<EC2-1_IP>/IP_PUBLICA_EC2-1/g" monitoreo/prometheus/prometheus-config.yaml
sed -i "s/<EC2-2_IP>/IP_PUBLICA_EC2-2/g" monitoreo/prometheus/prometheus-config.yaml  # para Actuator
sed -i "s/<EC2-3_IP>/IP_PUBLICA_EC2-3/g" monitoreo/prometheus/prometheus-config.yaml

kubectl apply -f monitoreo/namespace-monitoreo.yaml
kubectl apply -f monitoreo/prometheus/prometheus-config.yaml
kubectl apply -f monitoreo/prometheus/prometheus-deployment.yaml
kubectl apply -f monitoreo/prometheus/prometheus-service.yaml
kubectl wait --for=condition=ready pod -l app=prometheus -n monitoreo --timeout=60s

nohup kubectl port-forward -n monitoreo service/prometheus-service 30090:9090 --address 0.0.0.0 > /dev/null 2>&1 &

# Verificar targets (deben aparecer 6 targets UP)
curl -s http://localhost:30090/api/v1/targets | python3 -m json.tool | grep -E "job|health"
```

---

## BLOQUE 7 — Grafana (correr en EC2-4)

```bash
kubectl apply -f monitoreo/grafana/grafana-datasource.yaml
kubectl apply -f monitoreo/grafana/grafana-dashboard-configmap.yaml
kubectl apply -f monitoreo/grafana/grafana-deployment.yaml
kubectl apply -f monitoreo/grafana/grafana-service.yaml
kubectl wait --for=condition=ready pod -l app=grafana -n monitoreo --timeout=60s

nohup kubectl port-forward -n monitoreo service/grafana-service 30300:3000 --address 0.0.0.0 > /dev/null 2>&1 &

echo "Accede a: http://$(curl -s ifconfig.me):30300  |  admin / admin"
```

---

## BLOQUE 8 — Verificacion General

```bash
# Backend API
curl -s http://<EC2-2_IP>:30001/api/events | head -5
curl -s http://<EC2-2_IP>:30001/actuator/health

# Frontend
curl -s http://<EC2-3_IP>:30080 | head -5

# Prometheus targets
curl -s http://<EC2-4_IP>:30090/targets | python3 -m json.tool | grep -E '"job"|"health"'

# Dashboard
echo "http://<EC2-4_IP>:30300/d/elchino"
```

---

## Errores Comunes

| # | Error | Causa | Solucion |
|---|-------|-------|----------|
| 1 | `404` al descargar Node Exporter | URL `/latest/download/` sin version | Usar `v1.11.1/node_exporter-1.11.1.linux-amd64.tar.gz` |
| 2 | Prometheus `CrashLoopBackOff` | `labels` mal indentado en YAML | Eliminar `labels` de la config |
| 3 | Target MongoDB `DOWN` | Falta port-forward exporter | `kubectl port-forward -n freddy-quispe-12-namespace service/mongodb-exporter-service 30092:9216 --address 0.0.0.0` |
| 4 | Dashboard MongoDB "No data" | Sidecar sin collectors | Usar `--collect-all --compatible-mode` |
| 5 | Sidecar `unknown flag` | Flags sueltos no existen | Usar solo `--collect-all --compatible-mode` |
| 6 | Dashboard JVM "No data" | Query con label `job` incorrecto | Usar `application="Elchino"` en vez de `job="backend-actuator"` |
| 7 | P99 sin datos | WebFlux no genera histogram | Usar promedio: `rate(sum)/rate(count)*1000` |
| 8 | `git push` rechazado | Cambios remotos no sincronizados | `git pull origin develop` y resolver conflictos |
| 9 | Minikube warning memoria | t3.small justo para 3072MB | `minikube start --memory=2048mb` (opcional) |

---

## Limpieza

```bash
kubectl delete namespace freddy-quispe-12-namespace
kubectl delete namespace monitoreo
sudo fuser -k 30080/tcp 30001/tcp 27017/tcp 30090/tcp 30300/tcp 30092/tcp 9100/tcp 2>/dev/null
minikube delete --all
```
