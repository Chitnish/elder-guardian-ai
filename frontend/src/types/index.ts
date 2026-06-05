export interface RiskScore {
  id: string
  score: number
  narrative: string
  scored_at: string
}

export interface Alert {
  id: string
  contact_name: string
  sms_status: string
  email_status: string
  sent_at: string
}

export interface AlertDetail {
  id: string
  contact_name: string
  contact_email: string
  contact_phone: string
  sms_status: string
  email_status: string
  sent_at: string
}

export interface DashboardData {
  risk_scores: RiskScore[]
  alerts: Alert[]
  latest_upload_status: string | null
}

export interface UploadResponse {
  upload_id: string
  risk_score: number
  anomalous_count: number
  narrative: string
  alert_sent: boolean
}

export interface EmergencyContact {
  full_name: string
  phone: string
  email: string
}
