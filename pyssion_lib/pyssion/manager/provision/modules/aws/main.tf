# One GPU EC2 instance that joins the Pyssion manager on boot.
terraform {
  required_providers {
    aws = { source = "hashicorp/aws" }
  }
}

variable "name" {}
variable "server_url" {}
variable "join_token" { sensitive = true }
variable "region" { default = "us-east-1" }
variable "instance_type" { default = "g5.xlarge" }
variable "ami" { default = "" } # empty = latest AWS Deep Learning Base GPU AMI (driver preinstalled)
variable "disk_gb" { default = 100 }
variable "spot" { default = false }
variable "subnet_id" { default = null }
variable "security_group_ids" { default = null }
variable "key_name" { default = null }

provider "aws" {
  region = var.region
}

data "aws_ami" "dl" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)*"]
  }
}

resource "aws_instance" "node" {
  ami                                  = var.ami != "" ? var.ami : data.aws_ami.dl.id
  instance_type                        = var.instance_type
  subnet_id                            = var.subnet_id
  vpc_security_group_ids               = var.security_group_ids
  key_name                             = var.key_name
  instance_initiated_shutdown_behavior = "terminate"
  user_data = templatefile("${path.module}/../_shared/agent-init.sh.tftpl", {
    name = var.name, server_url = var.server_url, join_token = var.join_token
  })

  root_block_device {
    volume_size = var.disk_gb
  }

  dynamic "instance_market_options" {
    for_each = var.spot ? [1] : []
    content {
      market_type = "spot"
    }
  }

  tags = { Name = var.name, pyssion = "node" }
}

output "id" {
  value = aws_instance.node.id
}
