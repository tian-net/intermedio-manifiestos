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

### 4.1. Instalación de Node Exporters

> **[CAPTURA: Instalación node_exporter en EC2-1]**

> **[CAPTURA: Instalación node_exporter en EC2-2]**

> **[CAPTURA: Instalación node_exporter en EC2-3]**

### 4.2. Instalación de MongoDB Exporter

> **[CAPTURA: Deploy MongoDB Exporter sidecar]**

### 4.3. Configuración de Prometheus

> **[CAPTURA: Prometheus targets up]**

> **[CAPTURA: Prometheus configuración]**

### 4.4. Configuración de Grafana

> **[CAPTURA: Grafana login / datasource]**

> **[CAPTURA: Grafana datasource configurado]**

### 4.5. Configuración de Alertas

> **[CAPTURA: Reglas de alerta en Prometheus]**

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
