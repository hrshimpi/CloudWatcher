resource "google_cloud_run_v2_service" "api" {
  name     = "cloudwatcher-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.api_runtime.email

    scaling {
      min_instance_count = var.api_min_instances
      max_instance_count = var.api_max_instances
    }

    containers {
      image = var.api_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "POSTGRES_USER"
        value = google_sql_user.app.name
      }
      env {
        name  = "POSTGRES_DB"
        value = google_sql_database.app.name
      }
      env {
        name  = "POSTGRES_SOCKET_DIR"
        value = "/cloudsql/${google_sql_database_instance.postgres.connection_name}"
      }
      env {
        name  = "GEMINI_MODEL"
        value = "gemini-2.0-flash"
      }
      env {
        name  = "ALERTS_DRY_RUN"
        value = tostring(var.alerts_dry_run)
      }

      env {
        name = "POSTGRES_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "SLACK_WEBHOOK_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.slack_webhook_url.secret_id
            version = "latest"
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.postgres.connection_name]
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.required]
}

# Public REST API for the dashboard -- consistent with the app's current
# "no auth" reality (see DEVELOPMENT.md). See iam.tf for why the scheduler
# still gets an explicit roles/run.invoker grant on top of this.
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service" "frontend" {
  name     = "cloudwatcher-frontend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.frontend_runtime.email

    scaling {
      min_instance_count = var.frontend_min_instances
      max_instance_count = var.frontend_max_instances
    }

    containers {
      image = var.frontend_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi"
        }
      }

      # nginx proxies /api/* here server-side (see frontend/nginx.conf.template)
      # -- the browser never talks to the api's URL directly, and the api
      # never needs CORS configured.
      env {
        name  = "API_BASE_URL"
        value = google_cloud_run_v2_service.api.uri
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
