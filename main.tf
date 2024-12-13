terraform {
  required_providers {
    linode = {
      source = "linode/linode"
      version = "2.5.0"
    }
  }
}

provider "linode" {
    token = var.token
}

resource "linode_instance_config" "my-config" {
  linode_id = linode_instance.betexchange.id
  label = "my-config"

  devices {
    sda {
      disk_id = linode_instance_disk.boot.id
    }

    sdb {
      disk_id = linode_instance_disk.swap.id
    }

    sdc {
      volume_id = "1559881"
    }
  }

  booted = true

  // Run a remote-exec provisioner
  connection {
    type        = "ssh"
    host        = linode_instance.betexchange.ip_address
    user        = "root"
    password    = var.root_pass
  }

  provisioner "remote-exec" {
    inline = [
      "mkdir /opt/app"
    ]
  }

  # Copy bash script to Linode instance

  provisioner "file" {
    source      = "scripts"
    destination = "/opt/app" 
  }

  provisioner "file" {
    source      = ".env"
    destination = "/opt/app/.env"
  }

  provisioner "file" {
    source      = "docker-compose.yml"
    destination = "/opt/app/docker-compose.yml"
  }

  provisioner "file" {
    source      = "Dockerfile"
    destination = "/opt/app/Dockerfile"
  }

  provisioner "file" {
    source      = "Pipfile"
    destination = "/opt/app/Pipfile"
  }

  provisioner "file" {
      source      = "Pipfile.lock"
      destination = "/opt/app/Pipfile.lock"
  }

  provisioner "remote-exec" {
    inline = [
      "echo 'Hello World!'",
      "export dynu_hostname=${var.dynu_hostname}",
      "export dynu_user=${var.dynu_user}",
      "export dynu_pwd=${var.dynu_pwd}",
      "export linode_ip=${linode_instance.danalytics.ip_address}",
      "bash /opt/app/scripts/linode_init.sh",
    ]
  }
}

# Create a boot disk
resource "linode_instance_disk" "boot" {
  label = "boot"
  linode_id = linode_instance.betexchange.id
  size = linode_instance.betexchange.specs.0.disk - 512

  image = "linode/ubuntu22.04"
  root_pass = var.root_pass
}

# Create a swap disk
resource "linode_instance_disk" "swap" {
  label = "swap"
  linode_id = linode_instance.betexchange.id
  size = 512
  filesystem = "swap"
}

resource "linode_instance" "betexchange" {
  label = "betexchange"
  type = "g6-nanode-1"
  region = "eu-west"
}

resource "linode_firewall" "betexchange_firewall" {
  label = "betexchange_firewall"

  inbound {
    label    = "allow-ssh"
    action   = "ACCEPT"
    protocol = "TCP"
    ports    = "22"
    ipv4     = ["0.0.0.0/0"]
    ipv6     = ["::/0"]
  }

  inbound_policy = "DROP"

  outbound_policy = "DROP"

  linodes = [linode_instance.betexchange.id]
}

# variables
variable "token" {}
variable "root_pass" {}
variable "ssh_key" {}
variable "dynu_pwd" {}
variable "dynu_hostname" {}
variable "dynu_user" {}
