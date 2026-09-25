# --- api runtime service account ------------------------------------------

# Cloud SQL client is a project-level role in GCP's IAM model -- it can't be
# scoped to one instance.
resource "google_project_iam_member" "api_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api_runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "api_reads_slack_webhook" {
  secret_id = google_secret_manager_secret.slack_webhook_url.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "api_reads_gemini_key" {
  secret_id = google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "api_reads_db_password" {
  secret_id = google_secret_manager_secret.db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_runtime.email}"
}

# --- Cloud Scheduler -> api Cloud Run ---------------------------------

# The api service allows unauthenticated access overall (it's a public
# dashboard API -- see cloud_run.tf), so this grant isn't strictly required
# for the scheduler's calls to succeed today. It's kept anyway for two
# reasons: it's what actually authenticates the request if the service is
# ever locked down to `--no-allow-unauthenticated` later (no Terraform
# change needed at that point), and it documents, in code, exactly who is
# expected to call the detection endpoint on a schedule.
resource "google_cloud_run_v2_service_iam_member" "scheduler_can_invoke_api" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler_invoker.email}"
}

# --- GitHub Actions deploy identity -----------------------------------
# Broad-but-documented: this one identity runs `terraform apply` for the
# whole stack (Cloud Run, Cloud SQL, Secret Manager, Scheduler, Artifact
# Registry) plus pushes images, so it needs admin-level access to each of
# those services at the project level. A stricter setup would split "build
# and push images" (needs only artifactregistry.writer) from "apply
# Terraform" (needs the rest) into separate identities -- reasonable next
# step if this ever became more than a demo pipeline.

resource "google_project_iam_member" "gha_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "gha_artifact_registry_admin" {
  project = var.project_id
  role    = "roles/artifactregistry.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "gha_cloudsql_admin" {
  project = var.project_id
  role    = "roles/cloudsql.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "gha_secretmanager_admin" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "gha_scheduler_admin" {
  project = var.project_id
  role    = "roles/cloudscheduler.admin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_project_iam_member" "gha_service_account_admin" {
  project = var.project_id
  role    = "roles/iam.serviceAccountAdmin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# Lets the CI deployer assign the runtime service accounts to Cloud Run
# revisions (`gcloud run deploy --service-account=...` / this Terraform
# config both need `iam.serviceAccounts.actAs` on the target SA).
resource "google_service_account_iam_member" "gha_can_act_as_api_runtime" {
  service_account_id = google_service_account.api_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_service_account_iam_member" "gha_can_act_as_frontend_runtime" {
  service_account_id = google_service_account.frontend_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github_actions.email}"
}

# Needed because iam.tf itself grants project-level IAM bindings (the ones
# on this page) -- Terraform is managing its own deployer's permissions.
resource "google_project_iam_member" "gha_project_iam_admin" {
  project = var.project_id
  role    = "roles/resourcemanager.projectIamAdmin"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

resource "google_storage_bucket_iam_member" "gha_state_bucket_access" {
  bucket = var.terraform_state_bucket
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_actions.email}"
}
