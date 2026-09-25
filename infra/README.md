# Infrastructure

Terraform for CloudWatcher's GCP deployment: two Cloud Run services (`api`,
`frontend`), a Cloud SQL Postgres instance, Secret Manager entries, a nightly
Cloud Scheduler job, an Artifact Registry repo, and the IAM wiring it all
together — including a Workload Identity Federation setup so GitHub Actions
never needs a downloadable service account key.

## Bootstrap (one-time, run manually — not from CI)

CI can't create the identity it needs to authenticate as before that
identity exists. The first `terraform apply` has to run with your own
`gcloud` credentials; every apply after that can run from GitHub Actions.

1. **Create a GCS bucket for Terraform state** (Terraform can't provision the
   backend it's also using in the same config):

   ```bash
   gcloud storage buckets create gs://<your-project-id>-cloudwatcher-tfstate \
     --project=<your-project-id> --location=<region> --uniform-bucket-level-access
   ```

2. **Authenticate locally** and set your project:

   ```bash
   gcloud auth application-default login
   gcloud config set project <your-project-id>
   ```

3. **Copy the example vars** and fill in your project ID, region, GitHub repo,
   and the state bucket name from step 1:

   ```bash
   cp terraform.tfvars.example terraform.tfvars
   $EDITOR terraform.tfvars
   ```

4. **Init and apply**, using the state bucket from step 1 (kept out of
   `versions.tf` so the same config works for multiple environments):

   ```bash
   terraform init -backend-config="bucket=<your-project-id>-cloudwatcher-tfstate"
   terraform apply
   ```

   This first apply deploys both Cloud Run services running Google's public
   placeholder image (`api_image`/`frontend_image` default to it) — that's
   expected; it exists only so Cloud Run has something valid to create the
   service with. CI's first real deploy replaces it immediately.

5. **Wire up GitHub Actions**: add these as repository secrets (Settings →
   Secrets and variables → Actions), reading the first two from this apply's
   outputs:

   | Secret | Value |
   | --- | --- |
   | `GCP_WORKLOAD_IDENTITY_PROVIDER` | `terraform output -raw workload_identity_provider` |
   | `GCP_SERVICE_ACCOUNT` | `terraform output -raw github_actions_service_account` |
   | `GCP_PROJECT_ID` | your project ID |
   | `GCP_TERRAFORM_STATE_BUCKET` | the bucket from step 1 |
   | `SLACK_WEBHOOK_URL` | your Slack Incoming Webhook (optional — leave empty to skip Slack delivery for now) |
   | `GEMINI_API_KEY` | your Gemini API key (optional — LLM root-cause guesses just fall back to templated text without it) |

   From here on, pushes to `main` run `terraform apply` through
   `.github/workflows/deploy.yml` using that identity.

## What's not automated

- **First-time secret values**: `slack_webhook_url` and `gemini_api_key`
  default to empty strings so `apply` never fails on a fresh project — the
  app runs fine without them (see `DEVELOPMENT.md` in the repo root for how
  it degrades). Set the GitHub secrets above once you have real values;
  Terraform updates the Secret Manager versions on the next apply.
- **Database schema**: this config provisions the Cloud SQL *instance*, not
  the schema inside it. `.github/workflows/deploy.yml` runs
  `alembic upgrade head` against it (via the Cloud SQL Auth Proxy) as a
  deploy step, after `terraform apply` and before Cloud Run starts serving
  the new image.
- **Alerting config**: `alert_config` rows (Slack webhook + Z-score
  threshold per service, or the global default) are application data, not
  infrastructure — set them via the Settings page or `PUT /config/thresholds`
  after deploying. `SLACK_WEBHOOK_URL` from Secret Manager is only a
  fallback default until the global row exists in the DB.

## Design notes

- **`api` is public** (`allUsers` + `roles/run.invoker`), matching the app's
  current no-auth reality — the frontend's nginx proxies `/api/*` to it
  server-side, and the browser only ever talks to the frontend's own origin
  (see `frontend/nginx.conf.template`). Cloud Scheduler still gets its own
  `roles/run.invoker` grant on top of the public one; see the comment in
  `iam.tf` for why that's not redundant.
- **Cloud SQL Auth Proxy**: `google_cloud_run_v2_service.api` mounts a
  `cloud_sql_instance` volume, which is Cloud Run's built-in Auth Proxy
  integration — no proxy sidecar or VPC connector to manage by hand. The app
  connects via the resulting Unix socket at `/cloudsql/<connection_name>`
  (see `POSTGRES_SOCKET_DIR` in `backend/app/core/config.py`).
- **The GitHub Actions service account is broad** (project-level admin roles
  across Cloud Run, Cloud SQL, Secret Manager, Scheduler, Artifact Registry)
  because one identity runs `terraform apply` for the whole stack. See the
  comment above the relevant block in `iam.tf` for the narrower alternative.
- **Cloud SQL has a public IP** (`ipv4_enabled = true`) but no authorized
  networks are configured, so nothing reaches it directly — only the Auth
  Proxy path (IAM + TLS) works. This avoids needing a VPC connector for a
  single-instance demo; a real production setup would likely use a private
  IP instead.
