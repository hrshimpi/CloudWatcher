from pydantic import BaseModel


class DetectionRunResponse(BaseModel):
    anomalies_processed: int
    alerts_sent: int
    dry_run: bool
