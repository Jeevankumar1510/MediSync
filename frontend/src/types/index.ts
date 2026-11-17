export type UserRole = 'ADMIN' | 'INTEGRATION_ENGINEER' | 'CLINICAL_ANALYST' | 'VIEWER';

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Patient {
  id: string;
  mrn: string;
  first_name: string;
  last_name: string;
  birth_date: string;
  gender: string;
  contact_info: {
    phone?: string;
    email?: string;
  };
  address: {
    city?: string;
    state?: string;
    postal_code?: string;
    country?: string;
  };
  is_active: boolean;
  created_at: string;
  record_count?: number;
}

export interface PatientRecord {
  id: string;
  patient_id: string;
  resource_type: string;
  fhir_version: string;
  status: string;
  checksum: string;
  raw_payload: any;
  normalized_payload: any;
  created_at: string;
}

export interface APIIntegration {
  id: string;
  name: string;
  integration_type: 'FHIR_R4' | 'VENDOR_REST' | 'HL7_V2';
  base_url: string;
  auth_type: 'BEARER_TOKEN' | 'BASIC_AUTH' | 'API_KEY' | 'OAUTH2';
  is_active: boolean;
  sync_frequency_minutes: number;
  last_synced_at?: string;
  created_at: string;
}

export interface SyncJob {
  id: string;
  integration_id: string;
  integration_name?: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'RETRYING';
  records_extracted: number;
  records_transformed: number;
  records_loaded: number;
  records_failed: number;
  error_message?: string;
  execution_duration_ms?: number;
  created_at: string;
  completed_at?: string;
}

export interface SyncStatistics {
  total_sync_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  total_records_ingested: number;
  success_rate_percentage: number;
  average_latency_ms: number;
}

export interface WebhookEvent {
  id: string;
  source: string;
  event_type: string;
  event_id: string;
  status: 'RECEIVED' | 'PROCESSING' | 'PROCESSED' | 'FAILED' | 'IGNORED';
  signature_verified: boolean;
  retry_count: number;
  error_message?: string;
  payload: any;
  created_at: string;
}

export interface FieldMappingSuggestion {
  source_field: string;
  suggested_target_field: string;
  confidence_score: number;
  requires_human_approval: boolean;
  notes?: string;
}

export interface FieldMappingResponse {
  resource_type: string;
  overall_confidence: number;
  requires_human_approval: boolean;
  suggestions: FieldMappingSuggestion[];
}

export interface ClinicalAnomaly {
  field: string;
  observed_value: any;
  expected_range: string;
  anomaly_score: number;
  clinical_risk: 'LOW' | 'MEDIUM' | 'HIGH';
  description: string;
}

export interface DataQualityReport {
  record_id?: string;
  resource_type: string;
  total_fields: number;
  missing_fields: string[];
  anomalies_detected: ClinicalAnomaly[];
  quality_score: number;
  passes_threshold: boolean;
}

export interface Document {
  id: string;
  title: string;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  chunk_count: number;
  status: 'PENDING' | 'PROCESSING' | 'INDEXED' | 'FAILED';
  is_public: boolean;
  created_at: string;
}

export interface SourceReference {
  document_id: string;
  document_title: string;
  chunk_index: number;
  similarity_score: number;
  snippet: string;
}

export interface RAGQueryResponse {
  answer: string;
  sources: SourceReference[];
  evidence_found: boolean;
  conversation_id?: string;
}

export interface AuditLogEntry {
  id: string;
  user_id?: string;
  user_email?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details: any;
  created_at: string;
}
