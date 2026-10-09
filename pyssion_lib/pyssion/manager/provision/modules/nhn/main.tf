# One GPU instance on NHN Cloud (OpenStack API) that joins the Pyssion manager on boot.
# Auth comes from the manager's OS_* env vars (OS_AUTH_URL, OS_TENANT_ID, OS_USERNAME, OS_PASSWORD, OS_REGION_NAME).
terraform {
  required_providers {
    nhncloud = { source = "nhn-cloud/nhncloud" }
  }
}

variable "name" {}
variable "server_url" {}
variable "join_token" { sensitive = true }
variable "flavor_name" { default = "g2.t4.c8m64" }
variable "image_id" {}   # a GPU image with the NVIDIA driver, from the NHN Cloud console
variable "network_id" {} # a VPC subnet with an internet gateway
variable "key_pair" {}   # NHN Cloud requires one; Pyssion itself never uses SSH
variable "disk_gb" { default = 100 }

provider "nhncloud" {}

resource "nhncloud_compute_instance_v2" "node" {
  name        = var.name
  flavor_name = var.flavor_name
  key_pair    = var.key_pair
  user_data = templatefile("${path.module}/../_shared/agent-init.sh.tftpl", {
    name = var.name, server_url = var.server_url, join_token = var.join_token
  })

  network {
    uuid = var.network_id
  }

  block_device {
    uuid                  = var.image_id
    source_type           = "image"
    destination_type      = "volume"
    boot_index            = 0
    volume_size           = var.disk_gb
    delete_on_termination = true
  }
}

output "id" {
  value = nhncloud_compute_instance_v2.node.id
}
