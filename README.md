# pet-behavior-platform

An AI-powered, cloud-native platform for analyzing pet behavior from images and videos using Computer Vision, Large Language Models (LLMs), and distributed GPU inference.

The platform enables pet owners to upload media and receive behavior analysis, natural-language explanations, and potential behavioral insights through a scalable Kubernetes-based architecture.

---

## Features

* Image and video upload
* AI-powered pet detection
* Pose estimation and behavior recognition
* Temporal behavior analysis for videos
* LLM-generated behavior summaries
* Asynchronous inference pipeline
* Distributed GPU inference workers
* Kubernetes-native deployment
* Prometheus and Grafana observability
* CI/CD with GitHub Actions
* Secure object storage integration

---

## Architecture

```text
                Mobile / Web Client
                        │
                        ▼
             API Gateway / Load Balancer
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
 Upload Service                  Authentication
        │
        ▼
 Object Storage
        │
        ▼
 Message Queue
        │
        ▼
 Image / Video Preprocessing
        │
        ▼
 Computer Vision Models
        │
        ▼
 Behavior Analysis
        │
        ▼
 Large Language Model
        │
        ▼
 PostgreSQL / Redis
        │
        ▼
 Result API
```

---

## Technology Stack

### Backend

* Python
* FastAPI
* PostgreSQL
* Redis
* Kafka / RabbitMQ

### AI

* PyTorch
* OpenCV
* YOLO
* Vision Transformers
* Large Language Models

### Infrastructure

* Kubernetes
* Docker
* Helm
* Terraform

### Observability

* Prometheus
* Grafana
* OpenTelemetry

### Cloud

* OCI
* AWS
* Object Storage

---

## Repository Structure

```text
pet-behavior-platform/
├── services/
├── workers/
├── models/
├── shared/
├── infrastructure/
├── database/
├── configs/
├── tests/
├── docs/
├── scripts/
└── .github/
```

---

## Getting Started

### Prerequisites

* Docker
* Kubernetes
* Python 3.11+
* PostgreSQL
* Redis
* Object Storage
* NVIDIA GPU (optional for inference)

### Clone

```bash
git clone https://github.com/bing-intelligence/pet-behavior-platform.git

cd pet-behavior-platform
```

### Local Development

```bash
docker compose up
```

or

```bash
make dev
```

---

## Deployment

Deploy using Helm:

```bash
helm install pet-platform ./infrastructure/helm
```

Or deploy using Kubernetes manifests:

```bash
kubectl apply -f infrastructure/kubernetes/
```

---

## Monitoring

The platform exposes Prometheus metrics for:

* API latency
* Request throughput
* Error rate
* Queue depth
* GPU utilization
* Inference latency
* Model accuracy
* System health

Grafana dashboards are provided under:

```text
infrastructure/monitoring/grafana/
```

---

## Documentation

Additional documentation is available under:

```text
docs/
```

including:

* System Architecture
* AI Inference Pipeline
* Kubernetes Deployment
* API Specification
* Operations Runbook
* Disaster Recovery

---

## Roadmap

* Image behavior analysis
* Video behavior analysis
* Multi-pet tracking
* Audio analysis
* Personalized pet profiles
* Real-time streaming inference
* Multi-region deployment

---

## Contributing

Contributions are welcome.

Please submit pull requests with appropriate tests and documentation updates.

---

## License

This project is licensed under the Apache License 2.0.
See the LICENSE file for details.
