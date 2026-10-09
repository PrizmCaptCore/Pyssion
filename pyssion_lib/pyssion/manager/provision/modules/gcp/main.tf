# One GPU Compute Engine VM that joins the Pyssion manager on boot.
terraform {
  required_providers {
    google = { source = "hashicorp/google" }
  }
}

variable "name" {}
variable "server_url" {}
variable "join_token" { sensitive = true }
variable "project" {}
variable "zone" { default = "us-central1-a" }
variable "machine_type" { default = "g2-standard-4" } # G2/A2/A3 types come with their GPUs attached
variable "gpu_type" { default = "" }                  # only for N1 types, e.g. "nvidia-tesla-t4"
variable "gpu_count" { default = 0 }
# Deep Learning VM image family with the NVIDIA driver; check `gcloud compute images list --project deeplearning-platform-release`.
variable "image" { default = "projects/deeplearning-platform-release/global/images/family/common-cu124-debian-11-py310" }
variable "disk_gb" { default = 100 }
variable "spot" { default = false }
variable "network" { default = "default" }

provider "google" {
  project = var.project
  zone    = var.zone
}

resource "google_compute_instance" "node" {
  name         = var.name
  machine_type = var.machine_type

  boot_disk {
    initialize_params {
      image = var.image
      size  = var.disk_gb
    }
  }

  dynamic "guest_accelerator" {
    for_each = var.gpu_count > 0 ? [1] : []
    content {
      type  = var.gpu_type
      count = var.gpu_count
    }
  }

  scheduling {
    on_host_maintenance = "TERMINATE"
    automatic_restart   = !var.spot
    preemptible         = var.spot
    provisioning_model  = var.spot ? "SPOT" : "STANDARD"
  }

  network_interface {
    network = var.network
    access_config {}
  }

  metadata = {
    install-nvidia-driver = "True"
    startup-script = templatefile("${path.module}/../_shared/agent-init.sh.tftpl", {
      name = var.name, server_url = var.server_url, join_token = var.join_token
    })
  }

  labels = { pyssion = "node" }
}

output "id" {
  value = google_compute_instance.node.id
}
