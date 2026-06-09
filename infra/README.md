# Infrastructure

This folder contains deployment configurations for production.

## Structure

```
infra/
├── docker/
│   ├── Dockerfile           # Container image for the pipeline
│   └── docker-compose.yml   # Local multi-service simulation
└── terraform/
    └── main.tf              # AWS infrastructure (ECS, SQS, S3, ECR)
```

## Local Docker

```bash
# Build and run locally
cd infra/docker
docker-compose up --build
```

## Production (Terraform)

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

## Architecture (Production)

```
                    ┌─────────────┐
                    │  S3 Bucket  │
Transcripts ──────►│  (input)    │
                    └──────┬──────┘
                           │ S3 event
                           ▼
                    ┌─────────────┐
                    │  SQS Queue  │
                    │ (transcripts)│
                    └──────┬──────┘
                           │ poll
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     ┌────────────┐ ┌────────────┐ ┌────────────┐
     │  ECS Task  │ │  ECS Task  │ │  ECS Task  │  ← auto-scales
     │(summarise) │ │(summarise) │ │(summarise) │     based on
     └─────┬──────┘ └─────┬──────┘ └─────┬──────┘     queue depth
           │               │               │
           └───────────────┼───────────────┘
                           ▼
                    ┌─────────────┐
                    │  SQS Queue  │
                    │ (summaries) │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  S3 Bucket  │
                    │  (output)   │
                    └─────────────┘
```
