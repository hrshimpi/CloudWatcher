variable "project_id" {
  description = "GCP project ID to deploy into."
  type        = string
}

variable "region" {
  description = "GCP region for all resources."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Short environment name, used in resource names (e.g. \"prod\", \"staging\")."
  type        = string
  default     = "prod"
}

# --- Container images -------------------------------------------------
# Full Artifact Registry URIs with tag, e.g.
# "us-central1-docker.pkg.dev/my-project/cloudwatcher/api:abc1234", set by CI
# on every deploy. The defaults point at Google's public placeholder image
# purely so `terraform apply` works on a from-scratch project before any
# image has ever been built -- Cloud Run needs *some* valid image to create
# the service shell first. Real traffic never actually reaches it: CI's
# first deploy overrides both to the real images immediately after.

variable "api_image" {
  description = "Full Artifact Registry image URI (with tag) for the backend API."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "frontend_image" {
  description = "Full Artifact Registry image URI (with tag) for the frontend."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

# --- Cloud SQL ----------------------------------------------------------

variable "cloud_sql_tier" {
  description = "Cloud SQL machine tier. db-f1-micro is fine for a demo; use at least db-g1-small for anything real."
  type        = string
  default     = "db-f1-micro"
}

variable "cloud_sql_deletion_protection" {
  description = "Whether Terraform refuses to delete the Cloud SQL instance. Set true outside of a demo/portfolio project."
  type        = bool
  default     = false
}

# --- Cloud Run scaling ----------------------------------------------------

variable "api_min_instances" {
  description = "Minimum warm instances for the api service. 0 scales to zero (cheaper, adds cold-start latency)."
  type        = number
  default     = 0
}

variable "api_max_instances" {
  description = "Maximum instances for the api service."
  type        = number
  default     = 3
}

variable "frontend_min_instances" {
  type    = number
  default = 0
}

variable "frontend_max_instances" {
  type    = number
  default = 2
}

# --- Scheduler ------------------------------------------------------------

variable "detection_schedule" {
  description = "Cron schedule (Cloud Scheduler / unix-cron syntax) for the nightly anomaly-detection run."
  type        = string
  default     = "0 6 * * *" # 06:00 daily
}

variable "detection_schedule_time_zone" {
  type    = string
  default = "Etc/UTC"
}

# --- Secrets ----------------------------------------------------------
# No defaults on purpose: these are real credentials and must never be
# committed. Supply via `TF_VAR_slack_webhook_url` / `TF_VAR_gemini_api_key`
# environment variables (GitHub Actions populates these from repo secrets --
# see .github/workflows/deploy.yml). Both are optional in the sense that the
# app degrades gracefully without them (no LLM root-cause guess, no Slack
# delivery until configured), so empty strings are accepted.

variable "slack_webhook_url" {
  description = "Slack Incoming Webhook URL used as the deploy-time default alert destination."
  type        = string
  sensitive   = true
  default     = ""
}

variable "gemini_api_key" {
  description = "Gemini API key for LLM-generated anomaly root-cause guesses."
  type        = string
  sensitive   = true
  default     = ""
}

variable "alerts_dry_run" {
  description = "Log Slack alerts instead of sending them. Flip to false once the Slack webhook is verified."
  type        = bool
  default     = true
}

# --- CI/CD identity -----------------------------------------------------

variable "github_repository" {
  description = "GitHub repo allowed to assume the deploy service account via Workload Identity Federation, as \"owner/repo\"."
  type        = string
}

variable "terraform_state_bucket" {
  description = "GCS bucket holding Terraform state (created out-of-band before first `terraform init` -- see README.md). Used only to grant the CI deployer read/write access to it."
  type        = string
}
