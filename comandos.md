# Despliegue Multi-Cluster - Examen Intermedio

Arquitectura: 3 instancias EC2 independientes, cada una con Minikube.

| Cluster | EC2 | Servicio | Puerto Expuesto |
|---------|-----|----------|----------------|
| MongoDB | EC2-1 | MongoDB 7-jammy | 27017 |
| Backend | EC2-2 | Spring Boot (WebFlux) | 30001 |
| Frontend | EC2-3 | React + Vite + Nginx | 30080 |

Namespace comun: `freddy-quispe-12-namespace`

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

minikube start --driver=docker
```

## 2. Orden de Despliegue

### Paso 1: Cluster MongoDB (EC2-1)

```bash
git clone https://github.com/tian-net/intermedio-manifiestos.git
cd intermedio-manifiestos
git checkout develop

kubectl apply -f mongo-cluster/freddy-quispe-12-namespace.yaml
kubectl apply -f mongo-cluster/mongo-deployment.yaml
kubectl apply -f mongo-cluster/mongo-service.yaml

# Exponer MongoDB (Minikube no expone NodePort en localhost)
kubectl port-forward -n freddy-quispe-12-namespace service/mongo-service 27017:27017 --address 0.0.0.0 &

# Anotar IP publica de EC2-1
curl ifconfig.me  # Anotar esta IP como <MONGO_EC2_IP>
```

### Paso 2: Cluster Backend (EC2-2)

Antes de desplegar, editar `backend-cluster/backend-deployment.yaml`:
- Reemplazar `<MONGO_EC2_IP>` con la IP publica de EC2-1

```bash
git clone https://github.com/tian-net/intermedio-manifiestos.git
cd intermedio-manifiestos
git checkout develop

# Editar la IP en backend-deployment.yaml
sed -i 's/<MONGO_EC2_IP>/REEMPLAZAR_CON_IP_EC2_MONGO/g' backend-cluster/backend-deployment.yaml

kubectl apply -f backend-cluster/freddy-quispe-12-namespace.yaml
kubectl apply -f backend-cluster/backend-deployment.yaml
kubectl apply -f backend-cluster/backend-service.yaml

# Exponer Backend
kubectl port-forward -n freddy-quispe-12-namespace service/freddy-quispe-12-service 30001:30001 --address 0.0.0.0 &

# Verificar
curl http://localhost:30001/api/events
```

### Paso 3: Cluster Frontend (EC2-3)

El frontend tiene la URL del backend hardcodeada en el build.
Pasos:
1. Clonar `https://github.com/tian-net/ASE242S4_T05-fe.git`
2. Editar `src/lib/constants.ts` -> `API_BASE = 'http://<EC2_BACKEND_IP>:30001/api'`
3. Reconstruir imagen: `docker build -t tian11qb/sebastian-front-react-vite-tailwind:lastest .`
4. Pushear: `docker push tian11qb/sebastian-front-react-vite-tailwind:lastest`

```bash
git clone https://github.com/tian-net/intermedio-manifiestos.git
cd intermedio-manifiestos
git checkout develop

kubectl apply -f frontend-cluster/freddy-quispe-12-namespace.yaml
kubectl apply -f frontend-cluster/frontend-deployment.yaml
kubectl apply -f frontend-cluster/frontend-service.yaml

# Exponer Frontend
kubectl port-forward -n freddy-quispe-12-namespace service/frontend-service 30080:80 --address 0.0.0.0 &
```

## 3. Verificacion

```bash
# Estado general
kubectl get all -n freddy-quispe-12-namespace

# EC2-1: MongoDB
kubectl logs -n freddy-quispe-12-namespace deployment/mongo-deployment

# EC2-2: Backend (Swagger)
curl http://localhost:30001/swagger-ui.html

# EC2-3: Frontend
curl http://localhost:30080
```

## 4. Security Groups (AWS)

| EC2 | Puerto | Origen | Descripcion |
|-----|--------|--------|-------------|
| EC2-1 (Mongo) | 27017 | IP de EC2-2 | MongoDB desde Backend |
| EC2-2 (Backend) | 30001 | 0.0.0.0/0 | API REST + Swagger |
| EC2-3 (Frontend) | 30080 | 0.0.0.0/0 | Frontend React |

## 5. Limpieza

```bash
minikube delete --all
```
