output "api_url" {
  description = "Public URL of the backend API Cloud Run service."
  value       = google_cloud_run_v2_service.api.uri
}

output "frontend_url" {
  description = "Public URL of the frontend Cloud Run service -- this is the dashboard."
  value       = google_cloud_run_v2_service.frontend.uri
}

output "artifact_registry_repository" {
  description = "Full path of the Artifact Registry repo images get pushed to."
  value       = google_artifact_registry_repository.cloudwatcher.name
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL instance connection name, for connecting via the Cloud SQL Auth Proxy locally (e.g. for running Alembic migrations from CI)."
  value       = google_sql_database_instance.postgres.connection_name
}

output "github_actions_service_account" {
  description = "Service account GitHub Actions impersonates via Workload Identity Federation."
  value       = google_service_account.github_actions.email
}

output "workload_identity_provider" {
  description = "Full resource name to pass as workload_identity_provider in google-github-actions/auth."
  value       = google_iam_workload_identity_pool_provider.github.name
}
