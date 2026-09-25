resource "google_artifact_registry_repository" "cloudwatcher" {
  location      = var.region
  repository_id = "cloudwatcher"
  format        = "DOCKER"
  description   = "Container images for CloudWatcher (api, frontend)."

  cleanup_policies {
    id     = "keep-last-10"
    action = "KEEP"
    most_recent_versions {
      keep_count = 10
    }
  }

  cleanup_policies {
    id     = "delete-untagged"
    action = "DELETE"
    condition {
      tag_state = "UNTAGGED"
    }
  }

  depends_on = [google_project_service.required]
}
