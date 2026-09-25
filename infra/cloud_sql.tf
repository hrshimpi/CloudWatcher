resource "random_password" "db" {
  length  = 32
  special = false # simplest to pass safely through env vars / connection strings
}

resource "google_sql_database_instance" "postgres" {
  name             = "cloudwatcher-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = var.cloud_sql_tier

    ip_configuration {
      # No VPC connector in this setup -- Cloud Run reaches Cloud SQL via the
      # Cloud SQL Auth Proxy integration (see cloud_run.tf's `cloud_sql_instance`
      # volume), which tunnels over IAM-authenticated TLS regardless of the
      # instance having a public IP. Cloud SQL's default authorized-networks
      # list is empty, so nothing can reach it directly over that public IP
      # without also holding `roles/cloudsql.client` and going through the
      # proxy.
      ipv4_enabled = true
    }

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }
  }

  # A demo/portfolio project shouldn't need `terraform destroy` blocked.
  # Flip cloud_sql_deletion_protection to true for anything real.
  deletion_protection = var.cloud_sql_deletion_protection

  depends_on = [google_project_service.required]
}

resource "google_sql_database" "app" {
  name     = "cloudwatcher"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app" {
  name     = "cloudwatcher"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db.result
}
