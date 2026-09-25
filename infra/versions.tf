terraform {
  required_version = ">= 1.7"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Bucket is intentionally omitted here -- pass it at `terraform init` time
  # with `-backend-config="bucket=<your-state-bucket>"` (see README.md).
  # Keeping it out of version control means the same config works across
  # multiple environments/state buckets without editing this file.
  backend "gcs" {
    prefix = "cloudwatcher/terraform/state"
  }
}
