# intermedio-manifiestos

Manifiestos Kubernetes para despliegue multi-cluster y monitoreo del proyecto ELCHINO Restobar en AWS.

## Estructura

```
├── comandos.md                     ← Manual completo de despliegue + monitoreo
├── seed_elchino.mongodb            ← Seed data para MongoDB
├── backend-cluster/                ← Manifiestos del Backend Spring Boot
├── frontend-cluster/               ← Manifiestos del Frontend React
├── mongo-cluster/                  ← Manifiestos de MongoDB
└── monitoreo/                      ← Configuracion de Prometheus + Grafana
    ├── namespace-monitoreo.yaml
    ├── informe-template.md         ← Template del informe tecnico (Google Doc)
    ├── prometheus/                 ← Config, deployment y service de Prometheus
    ├── grafana/                    ← Datasource, dashboard y deployment de Grafana
    └── alertas/                    ← Reglas de alerta
```

## Arquitectura

| EC2 | Servicio | Stack |
|-----|----------|-------|
| EC2-1 | MongoDB + MongoDB Exporter | Minikube + Mongo 7 |
| EC2-2 | Backend + Actuator | Minikube + Spring Boot WebFlux |
| EC2-3 | Frontend | Minikube + React/Vite/Nginx |
| EC2-4 | Prometheus + Grafana | Minikube |

Ver `comandos.md` para instrucciones detalladas de despliegue.
