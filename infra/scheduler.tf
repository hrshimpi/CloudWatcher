resource "google_cloud_scheduler_job" "nightly_detection" {
  name      = "cloudwatcher-nightly-detection"
  region    = var.region
  schedule  = var.detection_schedule
  time_zone = var.detection_schedule_time_zone
  # Generous: detection runs STL per service, then one Gemini + one Slack
  # call per newly flagged anomaly, sequentially.
  attempt_deadline = "600s"

  retry_config {
    retry_count = 2
  }

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.api.uri}/anomalies/detect"

    oidc_token {
      service_account_email = google_service_account.scheduler_invoker.email
      audience              = google_cloud_run_v2_service.api.uri
    }
  }

  depends_on = [google_project_service.required]
}
