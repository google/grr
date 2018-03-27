variable "gce_project" {}

variable "gce_region" {
  default = "europe-west1"
}

variable "windows_client_count" {
  default = "1"
}

variable "linux_client_count" {
  default = "1"
}

provider "google" {
  project = "${var.gce_project}"
  region  = "${var.gce_region}"
}

resource "google_sql_database_instance" "grr-db" {
  name   = "grr-db-instance"
  region = "${var.gce_region}"

  settings {
    tier = "db-n1-standard-1"

    ip_configuration {
      ipv4_enabled = true

      authorized_networks = {
        name  = "grr-server"
        value = "${google_compute_address.grr-address.address}"
      }
    }

    location_preference {
      zone = "${var.gce_region}-b"
    }

    database_flags {
      name  = "max_allowed_packet"
      value = "1073741824"
    }
  }
}

resource "google_sql_user" "users" {
  name     = "grr"
  instance = "${google_sql_database_instance.grr-db.name}"
  host     = "${google_compute_address.grr-address.address}"
  password = "grrpassword"
}

resource "google_sql_database" "grr-db" {
  name     = "grr-db"
  instance = "${google_sql_database_instance.grr-db.name}"
}

resource "google_compute_address" "grr-address" {
  name = "grr-address"
}

data "template_file" "grr-startup" {
  template = "${file("${path.module}/server_startup.sh")}"

  vars {
    server_host = "${google_compute_address.grr-address.address}"
    mysql_host  = "${google_sql_database_instance.grr-db.ip_address.0.ip_address}"
  }
}

data "template_file" "windows_client_install" {
  template = "${file("${path.module}/client_install.ps1")}"

  vars {
    windows_installer_download_url = "${data.google_storage_object_signed_url.windows-installer-get.signed_url}"
  }
}

data "template_file" "linux_client_install" {
  template = "${file("${path.module}/client_install.sh")}"

  vars {
    linux_installer_download_url = "${data.google_storage_object_signed_url.linux-installer-get.signed_url}"
  }
}

resource "google_storage_bucket" "installers-store" {
  name          = "installers-bucket-${google_compute_instance.grr-server.instance_id}"
  location      = "EU"
  force_destroy = true
}

data "google_storage_object_signed_url" "windows-installer-put" {
  bucket      = "${google_storage_bucket.installers-store.name}"
  path        = "dbg_GRR_3.2.1.1_amd64.exe"
  http_method = "PUT"
}

data "google_storage_object_signed_url" "windows-installer-get" {
  bucket      = "${google_storage_bucket.installers-store.name}"
  path        = "dbg_GRR_3.2.1.1_amd64.exe"
  http_method = "GET"
}

data "google_storage_object_signed_url" "linux-installer-put" {
  bucket      = "${google_storage_bucket.installers-store.name}"
  path        = "grr_3.2.1.1_amd64.deb"
  http_method = "PUT"
}

data "google_storage_object_signed_url" "linux-installer-get" {
  bucket      = "${google_storage_bucket.installers-store.name}"
  path        = "grr_3.2.1.1_amd64.deb"
  http_method = "GET"
}

resource "google_compute_firewall" "allow-admin-ui" {
  name    = "allow-admin-ui"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["admin-ui"]
}

resource "google_compute_firewall" "allow-frontend" {
  name    = "allow-frontend"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["8080"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["frontend"]
}

resource "google_compute_project_metadata" "default" {
  metadata {
    windows_installer_upload_url = "${data.google_storage_object_signed_url.windows-installer-put.signed_url}"
    linux_installer_upload_url   = "${data.google_storage_object_signed_url.linux-installer-put.signed_url}"
  }
}

resource "google_compute_instance" "grr-server" {
  depends_on = ["google_sql_database.grr-db"]

  name         = "grr-server"
  machine_type = "n1-standard-1"
  zone         = "${var.gce_region}-b"

  tags = ["admin-ui", "frontend"]

  boot_disk {
    initialize_params {
      image = "https://www.googleapis.com/compute/v1/projects/ubuntu-os-cloud/global/images/ubuntu-1604-xenial-v20180126"
    }
  }

  network_interface {
    network = "default"

    access_config {
      nat_ip = "${google_compute_address.grr-address.address}"
    }
  }

  metadata {}

  metadata_startup_script = "${data.template_file.grr-startup.rendered}"

  service_account {
    scopes = ["userinfo-email", "compute-ro", "storage-ro"]
  }
}

resource "google_compute_instance" "windows-client" {
  count = "${var.windows_client_count}"

  name         = "windows-client-${count.index}"
  machine_type = "g1-small"
  zone         = "${var.gce_region}-b"

  boot_disk {
    initialize_params {
      image = "windows-server-2012-r2-dc-v20180109"
    }
  }

  network_interface {
    network = "default"

    access_config {}
  }

  metadata {
    windows-startup-script-ps1 = "${data.template_file.windows_client_install.rendered}"
  }

  service_account {
    scopes = ["userinfo-email", "compute-ro", "storage-ro"]
  }
}

resource "google_compute_instance" "linux-client" {
  count = "${var.linux_client_count}"

  name         = "linux-client-${count.index}"
  machine_type = "g1-small"
  zone         = "${var.gce_region}-b"

  boot_disk {
    initialize_params {
      image = "https://www.googleapis.com/compute/v1/projects/ubuntu-os-cloud/global/images/ubuntu-1604-xenial-v20180126"
    }
  }

  network_interface {
    network = "default"

    access_config {}
  }

  metadata {}

  metadata_startup_script = "${data.template_file.linux_client_install.rendered}"

  service_account {
    scopes = ["userinfo-email", "compute-ro", "storage-ro"]
  }
}

output "grr_ui_url" {
  value = "https://${google_compute_address.grr-address.address}"
}
