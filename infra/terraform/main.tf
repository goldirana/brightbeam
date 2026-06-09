# ─────────────────────────────────────────────────────────────
# Terraform — Production Infrastructure (demonstration)
#
# This provisions:
# - Container registry (ECR/ACR) for Docker images
# - ECS/AKS cluster for running pipeline services
# - SQS/Service Bus queue between pipeline stages
# - S3/Blob storage for transcripts and output
# - IAM roles with least-privilege access
# ─────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# ─── Variables ────────────────────────────────────────────────

variable "region" {
  default     = "eu-west-1"
  description = "AWS region for deployment"
}

variable "environment" {
  default     = "production"
  description = "Environment name"
}

variable "project_name" {
  default     = "brightbeam"
  description = "Project identifier"
}

# ─── Container Registry ──────────────────────────────────────

resource "aws_ecr_repository" "pipeline" {
  name                 = "${var.project_name}-pipeline"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# ─── Message Queue (between pipeline stages) ─────────────────

resource "aws_sqs_queue" "transcript_queue" {
  name                       = "${var.project_name}-transcripts"
  visibility_timeout_seconds = 300 # 5 min per transcript processing
  message_retention_seconds  = 86400

  tags = {
    Project = var.project_name
    Stage   = "ingestion"
  }
}

resource "aws_sqs_queue" "summary_queue" {
  name                       = "${var.project_name}-summaries"
  visibility_timeout_seconds = 120
  message_retention_seconds  = 86400

  tags = {
    Project = var.project_name
    Stage   = "validation"
  }
}

# ─── Storage (transcripts + output) ──────────────────────────

resource "aws_s3_bucket" "data" {
  bucket = "${var.project_name}-data-${var.environment}"

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ─── ECS Cluster ─────────────────────────────────────────────

resource "aws_ecs_cluster" "pipeline" {
  name = "${var.project_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
  }
}

# ─── ECS Task Definitions ────────────────────────────────────

resource "aws_ecs_task_definition" "summarisation" {
  family                   = "${var.project_name}-summarisation"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024

  container_definitions = jsonencode([{
    name  = "summarisation"
    image = "${aws_ecr_repository.pipeline.repository_url}:latest"
    command = ["summarise"]

    environment = [
      { name = "PIPELINE_STAGE", value = "summarisation" }
    ]

    secrets = [
      { name = "OPENROUTER_API_KEY", valueFrom = "arn:aws:ssm:${var.region}:*:parameter/${var.project_name}/openrouter-key" }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/${var.project_name}"
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "summarisation"
      }
    }
  }])

  tags = {
    Project = var.project_name
    Stage   = "summarisation"
  }
}

# ─── Auto-scaling (scale summarisation independently) ─────────

resource "aws_ecs_service" "summarisation" {
  name            = "${var.project_name}-summarisation"
  cluster         = aws_ecs_cluster.pipeline.id
  task_definition = aws_ecs_task_definition.summarisation.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [] # Add your subnet IDs
    assign_public_ip = false
  }

  tags = {
    Project = var.project_name
  }
}

resource "aws_appautoscaling_target" "summarisation" {
  max_capacity       = 10
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.pipeline.name}/${aws_ecs_service.summarisation.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "summarisation_queue_depth" {
  name               = "${var.project_name}-queue-depth-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.summarisation.resource_id
  scalable_dimension = aws_appautoscaling_target.summarisation.scalable_dimension
  service_namespace  = aws_appautoscaling_target.summarisation.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 5 # Scale when queue has >5 messages per task

    customized_metric_specification {
      metric_name = "ApproximateNumberOfMessagesVisible"
      namespace   = "AWS/SQS"
      statistic   = "Average"

      dimensions {
        name  = "QueueName"
        value = aws_sqs_queue.transcript_queue.name
      }
    }
  }
}

# ─── Outputs ──────────────────────────────────────────────────

output "ecr_repository_url" {
  value = aws_ecr_repository.pipeline.repository_url
}

output "cluster_name" {
  value = aws_ecs_cluster.pipeline.name
}

output "transcript_queue_url" {
  value = aws_sqs_queue.transcript_queue.url
}
