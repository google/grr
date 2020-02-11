variable "gce_project" {
}

variable "gce_region" {
  default = "europe-west1"
}

variable "grr_version" {
  // Should match an existing GRR release (i.e. "3.2.1.1") or
  // have a value of "latest".
  // "latest" means that the latest successfully built DEB (matching
  // the HEAD version on GitHub) will be used.
  default = "latest"
}

variable "windows_client_count" {
  default = "1"
}

variable "linux_client_count" {
  default = "1"
}

variable "linux_poolclient_count" {
  default = "0"
}

provider "google" {
  project = var.gce_project
  region  = var.gce_region
}

provider "google-beta" {
  project = var.gce_project
  region  = var.gce_region
}

resource "google_compute_network" "private_network" {
  provider = google-beta

  name = "private-network"
}

resource "google_compute_global_address" "private_ip_address" {
  provider = google-beta

  name          = "private-ip-address"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.private_network.self_link
}

resource "google_service_networking_connection" "private_vpc_connection" {
  provider = google-beta

  network                 = google_compute_network.private_network.self_link
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

resource "random_id" "db_name_suffix" {
  byte_length = 4
}

resource "google_sql_database_instance" "grr-db" {
  name   = "grr-db-instance-${random_id.db_name_suffix.hex}"
  region = var.gce_region

  depends_on = [google_service_networking_connection.private_vpc_connection]

  settings {
    tier = "db-n1-standard-1"

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.private_network.self_link
    }

    location_preference {
      zone = "${var.gce_region}-b"
    }

    database_flags {
      name  = "max_allowed_packet"
      value = "1073741824"
    }

    database_flags {
      name  = "log_output"
      value = "FILE"
    }

    database_flags {
      name  = "slow_query_log"
      value = "on"
    }
  }
}

resource "google_sql_user" "users" {
  name     = "grr"
  instance = google_sql_database_instance.grr-db.name
  password = "grrpassword"
}

resource "google_sql_database" "grr-db" {
  name      = "grr"
  instance  = google_sql_database_instance.grr-db.name
  charset   = "utf8mb4"
  collation = "utf8mb4_unicode_ci"
}

resource "google_compute_address" "grr-address" {
  name = "grr-address"
}

resource "random_id" "admin_password" {
  byte_length = 12
}

data "template_file" "grr-startup" {
  template = file("${path.module}/server_startup.sh")

  vars = {
    grr_admin_password = random_id.admin_password.hex
    grr_version = var.grr_version
    server_host = google_compute_address.grr-address.address
    mysql_host  = google_sql_database_instance.grr-db.ip_address[0].ip_address
  }
}

data "template_file" "windows_client_install" {
  template = file("${path.module}/client_install.ps1")

  vars = {
    windows_installer_download_url = data.google_storage_object_signed_url.windows-installer-get.signed_url
  }
}

data "template_file" "linux_client_install" {
  template = file("${path.module}/client_install.sh")

  vars = {
    linux_installer_download_url = data.google_storage_object_signed_url.linux-installer-get.signed_url
  }
}

data "template_file" "linux_poolclient_install" {
  template = file("${path.module}/poolclient_install.sh")

  vars = {
    num_clients                  = 100
    linux_installer_download_url = data.google_storage_object_signed_url.linux-installer-get.signed_url
  }
}

resource "google_storage_bucket" "installers-store" {
  name          = "installers-bucket-${google_compute_instance.grr-server.instance_id}"
  location      = "EU"
  force_destroy = true
}

data "google_storage_object_signed_url" "windows-installer-put" {
  bucket      = google_storage_bucket.installers-store.name
  path        = "dbg_GRR_${var.grr_version}_amd64.exe"
  http_method = "PUT"
}

data "google_storage_object_signed_url" "windows-installer-get" {
  bucket      = google_storage_bucket.installers-store.name
  path        = "dbg_GRR_${var.grr_version}_amd64.exe"
  http_method = "GET"
}

data "google_storage_object_signed_url" "linux-installer-put" {
  bucket      = google_storage_bucket.installers-store.name
  path        = "grr_${var.grr_version}_amd64.deb"
  http_method = "PUT"
}

data "google_storage_object_signed_url" "linux-installer-get" {
  bucket      = google_storage_bucket.installers-store.name
  path        = "grr_${var.grr_version}_amd64.deb"
  http_method = "GET"
}

resource "google_compute_firewall" "allow-ssh" {
  name    = "allow-ssh"
  network = google_compute_network.private_network.self_link

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["ssh"]
}

resource "google_compute_firewall" "allow-admin-ui" {
  name    = "allow-admin-ui"
  network = google_compute_network.private_network.self_link

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["admin-ui"]
}

resource "google_compute_firewall" "allow-frontend" {
  name    = "allow-frontend"
  network = google_compute_network.private_network.self_link

  allow {
    protocol = "tcp"
    ports    = ["8080"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["frontend"]
}

resource "google_compute_project_metadata" "default" {
  metadata = {
    windows_installer_upload_url = data.google_storage_object_signed_url.windows-installer-put.signed_url
    linux_installer_upload_url   = data.google_storage_object_signed_url.linux-installer-put.signed_url
  }
}

resource "google_compute_instance" "grr-server" {
  depends_on = [google_sql_database.grr-db]

  name         = "grr-server"
  machine_type = "n1-standard-8"
  zone         = "${var.gce_region}-b"

  tags = ["admin-ui", "frontend", "ssh"]

  boot_disk {
    initialize_params {
      image = "ubuntu-1804-lts"
    }
  }

  network_interface {
    network = google_compute_network.private_network.self_link

    access_config {
      nat_ip = google_compute_address.grr-address.address
    }
  }

  metadata = {}

  metadata_startup_script = data.template_file.grr-startup.rendered

  service_account {
    scopes = ["userinfo-email", "compute-ro", "storage-ro"]
  }
}

resource "google_compute_instance" "windows-client" {
  count = var.windows_client_count

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

    access_config {
    }
  }

  metadata = {
    windows-startup-script-ps1 = data.template_file.windows_client_install.rendered
  }

  service_account {
    scopes = ["userinfo-email", "compute-ro", "storage-ro"]
  }
}

resource "google_compute_instance" "linux-client" {
  count = var.linux_client_count

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

    access_config {
    }
  }

  metadata = {}

  metadata_startup_script = data.template_file.linux_client_install.rendered

  service_account {
    scopes = ["userinfo-email", "compute-ro", "storage-ro"]
  }
}

resource "google_compute_instance" "linux-poolclient" {
  count = var.linux_poolclient_count

  name         = "linux-poolclient-${count.index}"
  machine_type = "n1-standard-8"
  zone         = "${var.gce_region}-b"

  boot_disk {
    initialize_params {
      image = "https://www.googleapis.com/compute/v1/projects/ubuntu-os-cloud/global/images/ubuntu-1604-xenial-v20180126"
    }
  }

  network_interface {
    network = "default"

    access_config {
    }
  }

  metadata = {}

  metadata_startup_script = data.template_file.linux_poolclient_install.rendered

  service_account {
    scopes = ["userinfo-email", "compute-ro", "storage-ro"]
  }
}

output "grr_ui_url" {
  value = "https://${google_compute_address.grr-address.address}"
}
output "grr_ui_admin_password" {
  value = random_id.admin_password.hex
}

