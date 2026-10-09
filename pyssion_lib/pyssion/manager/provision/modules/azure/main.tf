# One GPU Azure VM (own resource group, so destroy removes everything) that joins the Pyssion manager on boot.
terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
  }
}

variable "name" {}
variable "server_url" {}
variable "join_token" { sensitive = true }
variable "location" { default = "eastus" }
variable "size" { default = "Standard_NC4as_T4_v3" }
variable "disk_gb" { default = 128 }
variable "ssh_public_key" {} # Azure requires one for Linux VMs; Pyssion itself never uses SSH

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "rg" {
  name     = "${var.name}-rg"
  location = var.location
}

resource "azurerm_virtual_network" "net" {
  name                = "${var.name}-net"
  address_space       = ["10.42.0.0/16"]
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "sub" {
  name                 = "nodes"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.net.name
  address_prefixes     = ["10.42.1.0/24"]
}

resource "azurerm_public_ip" "ip" { # outbound path; new VNets have no default outbound access
  name                = "${var.name}-ip"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_interface" "nic" {
  name                = "${var.name}-nic"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  ip_configuration {
    name                          = "main"
    subnet_id                     = azurerm_subnet.sub.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.ip.id
  }
}

resource "azurerm_linux_virtual_machine" "node" {
  name                  = var.name
  location              = var.location
  resource_group_name   = azurerm_resource_group.rg.name
  size                  = var.size
  admin_username        = "pyssion"
  network_interface_ids = [azurerm_network_interface.nic.id]
  custom_data = base64encode(templatefile("${path.module}/../_shared/agent-init.sh.tftpl", {
    name = var.name, server_url = var.server_url, join_token = var.join_token
  }))

  admin_ssh_key {
    username   = "pyssion"
    public_key = var.ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = var.disk_gb
  }

  source_image_reference { # Ubuntu + NVIDIA driver via the extension below
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }
}

resource "azurerm_virtual_machine_extension" "gpu" {
  name                 = "nvidia-driver"
  virtual_machine_id   = azurerm_linux_virtual_machine.node.id
  publisher            = "Microsoft.HpcCompute"
  type                 = "NvidiaGpuDriverLinux"
  type_handler_version = "1.9"
}

output "id" {
  value = azurerm_linux_virtual_machine.node.id
}
