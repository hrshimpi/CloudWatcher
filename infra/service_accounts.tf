# Runtime identity for the api Cloud Run service: needs Cloud SQL + the
# three secrets, nothing else (see iam.tf).
resource "google_service_account" "api_runtime" {
  account_id   = "cloudwatcher-api"
  display_name = "CloudWatcher api Cloud Run runtime"
}

# Runtime identity for the frontend Cloud Run service. It only serves static
# files and reverse-proxies to the api's public URL, so it needs no GCP
# permissions beyond the ones Cloud Run grants by default -- kept as its own
# service account anyway so it's never accidentally broadened later just
# because it happens to share the api's identity.
resource "google_service_account" "frontend_runtime" {
  account_id   = "cloudwatcher-frontend"
  display_name = "CloudWatcher frontend Cloud Run runtime"
}

# Identity Cloud Scheduler uses to mint the OIDC token it presents when
# calling POST /anomalies/detect.
resource "google_service_account" "scheduler_invoker" {
  account_id   = "cloudwatcher-scheduler"
  display_name = "CloudWatcher Cloud Scheduler invoker"
}

# --- GitHub Actions CI/CD identity, via Workload Identity Federation ------
# No downloadable JSON key: GitHub's OIDC token is exchanged for short-lived
# GCP credentials at workflow run time (google-github-actions/auth), scoped
# to this one repo via the attribute condition below.

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions"
  description               = "Trusts GitHub Actions OIDC tokens for CI/CD deploys."

  depends_on = [google_project_service.required]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions-provider"
  display_name                       = "GitHub Actions OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # Scopes the trust to exactly this repo -- without this, any GitHub Actions
  # workflow anywhere could attempt to impersonate the deploy service account.
  attribute_condition = "assertion.repository == \"${var.github_repository}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "github_actions" {
  account_id   = "cloudwatcher-gha-deployer"
  display_name = "CloudWatcher GitHub Actions deployer"
}

resource "google_service_account_iam_member" "github_actions_wif_binding" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}
