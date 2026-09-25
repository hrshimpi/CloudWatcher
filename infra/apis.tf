locals {
  required_apis = [
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com", # workload identity federation token exchange
    "sts.googleapis.com",            # ditto
    "cloudresourcemanager.googleapis.com",
  ]
}

resource "google_project_service" "required" {
  for_each = toset(local.required_apis)

  project = var.project_id
  service = each.value

  # Don't disable a project-wide API just because this config stops managing
  # it (or gets destroyed) -- another workload in the same project might
  # depend on it.
  disable_on_destroy         = false
  disable_dependent_services = false
}
