terraform {
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

resource "aws_s3_bucket" "uploads" {
  bucket = "cnapp-demo-uploads"
  acl    = "public-read"
}

resource "aws_security_group" "app" {
  name        = "cnapp-demo-app"
  description = "cnapp-demo app nodes"

  ingress {
    description = "ssh"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "http"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Planted finding: a wildcard IAM policy (Action "*" on Resource "*").
# Expressed as a standalone aws_iam_policy because the Qualys IaC backend's
# Terraform parser currently fails on aws_iam_role / aws_iam_role_policy blocks.
resource "aws_iam_policy" "app_admin" {
  name = "cnapp-demo-app-admin"
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "*", Resource = "*" }]
  })
}

resource "aws_security_group_rule" "rdp" {
  type              = "ingress"
  from_port         = 3389
  to_port           = 3389
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.app.id
}
