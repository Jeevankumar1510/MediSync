import {
  User,
  Patient,
  PatientRecord,
  APIIntegration,
  SyncJob,
  SyncStatistics,
  WebhookEvent,
  FieldMappingResponse,
  DataQualityReport,
  Document,
  AuditLogEntry
} from '../types';

export const MOCK_USER: User = {
  id: 'usr-001',
  email: 'admin@medisync.local',
  role: 'ADMIN',
  is_active: true,
  is_superuser: true,
  created_at: '2026-01-15T08:00:00Z',
};

export const MOCK_PATIENTS: Patient[] = [
  {
    id: 'pat-101',
    mrn: 'MRN-100201',
    first_name: 'Jane',
    last_name: 'Doe',
    birth_date: '1985-04-12',
    gender: 'female',
    contact_info: {
      phone: '555-0101',
      email: 'jane.doe@example.com'
    },
    address: {
      city: 'Boston',
      state: 'MA',
      postal_code: '02115',
      country: 'USA'
    },
    is_active: true,
    record_count: 4,
    created_at: '2026-02-10T09:30:00Z'
  },
  {
    id: 'pat-102',
    mrn: 'MRN-100202',
    first_name: 'John',
    last_name: 'Miller',
    birth_date: '1974-11-23',
    gender: 'male',
    contact_info: {
      phone: '555-0102',
      email: 'john.miller@example.com'
    },
    address: {
      city: 'Cambridge',
      state: 'MA',
      postal_code: '02138',
      country: 'USA'
    },
    is_active: true,
    record_count: 6,
    created_at: '2026-02-12T14:15:00Z'
  },
  {
    id: 'pat-103',
    mrn: 'MRN-100203',
    first_name: 'Sofia',
    last_name: 'Rodriguez',
    birth_date: '1992-08-30',
    gender: 'female',
    contact_info: {
      phone: '555-0103',
      email: 'sofia.rodriguez@example.com'
    },
    address: {
      city: 'Somerville',
      state: 'MA',
      postal_code: '02143',
      country: 'USA'
    },
    is_active: true,
    record_count: 3,
    created_at: '2026-03-01T11:00:00Z'
  }
];

export const MOCK_RECORDS: Record<string, PatientRecord[]> = {
  'pat-101': [
    {
      id: 'rec-001',
      patient_id: 'pat-101',
      resource_type: 'Observation',
      fhir_version: 'R4',
      status: 'final',
      checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      raw_payload: {
        vendor: 'Synthea Mock EHR',
        code: '85354-9',
        display: 'Blood Pressure Panel',
        systolic: 128,
        diastolic: 82,
        unit: 'mmHg'
      },
      normalized_payload: {
        resourceType: 'Observation',
        status: 'final',
        category: [{ coding: [{ system: 'http://terminology.hl7.org/CodeSystem/observation-category', code: 'vital-signs' }] }],
        code: { coding: [{ system: 'http://loinc.org', code: '85354-9', display: 'Blood Pressure Panel' }] },
        component: [
          { code: { coding: [{ code: '8480-6', display: 'Systolic' }] }, valueQuantity: { value: 128, unit: 'mmHg' } },
          { code: { coding: [{ code: '8462-4', display: 'Diastolic' }] }, valueQuantity: { value: 82, unit: 'mmHg' } }
        ]
      },
      created_at: '2026-03-10T10:15:00Z'
    },
    {
      id: 'rec-002',
      patient_id: 'pat-101',
      resource_type: 'Condition',
      fhir_version: 'R4',
      status: 'active',
      checksum: 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb',
      raw_payload: {
        diagnosis: 'Essential Primary Hypertension',
        icd_code: 'I10',
        onset: '2025-06-15'
      },
      normalized_payload: {
        resourceType: 'Condition',
        clinicalStatus: { coding: [{ code: 'active' }] },
        code: { coding: [{ system: 'http://hl7.org/fhir/sid/icd-10-cm', code: 'I10', display: 'Essential primary hypertension' }] },
        onsetDateTime: '2025-06-15'
      },
      created_at: '2026-03-10T10:20:00Z'
    }
  ]
};

export const MOCK_INTEGRATIONS: APIIntegration[] = [
  {
    id: 'int-001',
    name: 'Metropolitan Hospital Epic FHIR',
    integration_type: 'FHIR_R4',
    base_url: 'https://fhir.metrohospital.org/r4',
    auth_type: 'OAUTH2',
    is_active: true,
    sync_frequency_minutes: 15,
    last_synced_at: '2026-11-17T11:45:00Z',
    created_at: '2026-01-20T10:00:00Z'
  },
  {
    id: 'int-002',
    name: 'Community Care Cerner Millennium',
    integration_type: 'FHIR_R4',
    base_url: 'https://api.cerner.communitycare.org/v1',
    auth_type: 'BEARER_TOKEN',
    is_active: true,
    sync_frequency_minutes: 30,
    last_synced_at: '2026-11-17T11:30:00Z',
    created_at: '2026-02-05T08:30:00Z'
  },
  {
    id: 'int-003',
    name: 'Quest Diagnostics Vendor REST',
    integration_type: 'VENDOR_REST',
    base_url: 'https://api.quest-lab-integration.net/clinical',
    auth_type: 'API_KEY',
    is_active: true,
    sync_frequency_minutes: 60,
    last_synced_at: '2026-11-17T11:00:00Z',
    created_at: '2026-02-18T13:00:00Z'
  }
];

export const MOCK_SYNC_JOBS: SyncJob[] = [
  {
    id: 'job-901',
    integration_id: 'int-001',
    integration_name: 'Metropolitan Hospital Epic FHIR',
    status: 'COMPLETED',
    records_extracted: 142,
    records_transformed: 142,
    records_loaded: 140,
    records_failed: 2,
    execution_duration_ms: 1240,
    created_at: '2026-11-17T11:45:00Z',
    completed_at: '2026-11-17T11:45:01Z'
  },
  {
    id: 'job-902',
    integration_id: 'int-002',
    integration_name: 'Community Care Cerner Millennium',
    status: 'COMPLETED',
    records_extracted: 88,
    records_transformed: 88,
    records_loaded: 88,
    records_failed: 0,
    execution_duration_ms: 920,
    created_at: '2026-11-17T11:30:00Z',
    completed_at: '2026-11-17T11:30:01Z'
  },
  {
    id: 'job-903',
    integration_id: 'int-003',
    integration_name: 'Quest Diagnostics Vendor REST',
    status: 'COMPLETED',
    records_extracted: 210,
    records_transformed: 208,
    records_loaded: 205,
    records_failed: 3,
    execution_duration_ms: 2150,
    created_at: '2026-11-17T11:00:00Z',
    completed_at: '2026-11-17T11:00:02Z'
  }
];

export const MOCK_SYNC_STATS: SyncStatistics = {
  total_sync_jobs: 148,
  completed_jobs: 144,
  failed_jobs: 4,
  total_records_ingested: 12450,
  success_rate_percentage: 97.3,
  average_latency_ms: 1180
};

export const MOCK_WEBHOOKS: WebhookEvent[] = [
  {
    id: 'wh-001',
    source: 'Metropolitan_EHR_Gateway',
    event_type: 'ADT_A01_ADMISSION',
    event_id: 'EVT-77881',
    status: 'PROCESSED',
    signature_verified: true,
    retry_count: 0,
    payload: {
      patient_mrn: 'MRN-100201',
      admission_time: '2026-11-17T11:20:00Z',
      department: 'Cardiology',
      bed: 'C-302'
    },
    created_at: '2026-11-17T11:20:02Z'
  },
  {
    id: 'wh-002',
    source: 'Cerner_Ambulatory_Feed',
    event_type: 'OBSERVATION_CREATE',
    event_id: 'EVT-77882',
    status: 'PROCESSED',
    signature_verified: true,
    retry_count: 0,
    payload: {
      patient_mrn: 'MRN-100202',
      vital_type: 'Pulse',
      value: 76,
      unit: 'bpm'
    },
    created_at: '2026-11-17T11:15:10Z'
  },
  {
    id: 'wh-003',
    source: 'External_Lab_Partner',
    event_type: 'LAB_RESULT_UPDATE',
    event_id: 'EVT-77883',
    status: 'FAILED',
    signature_verified: false,
    retry_count: 2,
    error_message: 'Invalid HMAC signature in X-MediSync-Signature header',
    payload: {
      sample_id: 'SMP-99120',
      status: 'pending'
    },
    created_at: '2026-11-17T10:45:00Z'
  }
];

export const MOCK_FIELD_MAPPING: FieldMappingResponse = {
  resource_type: 'Patient',
  overall_confidence: 0.94,
  requires_human_approval: false,
  suggestions: [
    {
      source_field: 'mrn',
      suggested_target_field: 'identifier[0].value',
      confidence_score: 0.99,
      requires_human_approval: false,
      notes: 'Matches canonical hospital patient identifier'
    },
    {
      source_field: 'first_name',
      suggested_target_field: 'name[0].given[0]',
      confidence_score: 0.98,
      requires_human_approval: false,
      notes: 'Demographic given name'
    },
    {
      source_field: 'last_name',
      suggested_target_field: 'name[0].family',
      confidence_score: 0.98,
      requires_human_approval: false,
      notes: 'Demographic surname'
    },
    {
      source_field: 'dob',
      suggested_target_field: 'birthDate',
      confidence_score: 0.96,
      requires_human_approval: false,
      notes: 'Standard ISO-8601 birthDate representation'
    },
    {
      source_field: 'patient_phone',
      suggested_target_field: 'telecom[0].value',
      confidence_score: 0.92,
      requires_human_approval: false,
      notes: 'Telecom telephone contact endpoint'
    },
    {
      source_field: 'custom_vendor_clinic_code',
      suggested_target_field: 'meta.tag[0].code',
      confidence_score: 0.72,
      requires_human_approval: true,
      notes: 'Fuzzy match to metadata tag, review suggested'
    }
  ]
};

export const MOCK_QUALITY_REPORT: DataQualityReport = {
  record_id: 'rec-001',
  resource_type: 'Observation',
  total_fields: 8,
  missing_fields: ['performer', 'effectiveDateTime'],
  anomalies_detected: [
    {
      field: 'systolic',
      observed_value: 188,
      expected_range: '90 - 140 mmHg',
      anomaly_score: -0.74,
      clinical_risk: 'HIGH',
      description: 'Severe systolic blood pressure outlier exceeding physiological threshold (> 180 mmHg stage 3 hypertensive crisis).'
    }
  ],
  quality_score: 0.78,
  passes_threshold: true
};

export const MOCK_DOCUMENTS: Document[] = [
  {
    id: 'doc-001',
    title: 'Cardiovascular Clinical Practice Guidelines 2026',
    filename: 'cardiovascular_guidelines_2026.md',
    file_type: 'md',
    file_size_bytes: 4096,
    chunk_count: 4,
    status: 'INDEXED',
    is_public: true,
    created_at: '2026-02-15T10:00:00Z'
  },
  {
    id: 'doc-002',
    title: 'HL7 FHIR R4 Clinical Integration Specification',
    filename: 'fhir_r4_integration_spec.md',
    file_type: 'md',
    file_size_bytes: 8192,
    chunk_count: 6,
    status: 'INDEXED',
    is_public: true,
    created_at: '2026-02-20T14:30:00Z'
  },
  {
    id: 'doc-003',
    title: 'MediSync AI Data Governance & HIPAA Audit Policy',
    filename: 'data_governance_policy.txt',
    file_type: 'txt',
    file_size_bytes: 3200,
    chunk_count: 3,
    status: 'INDEXED',
    is_public: true,
    created_at: '2026-03-01T09:15:00Z'
  }
];

export const MOCK_AUDIT_LOGS: AuditLogEntry[] = [
  {
    id: 'log-001',
    user_email: 'admin@medisync.local',
    action: 'RAG_QUERY',
    resource_type: 'Document',
    details: { query: 'First-line medication for stage 1 hypertension', sources_matched: 2 },
    created_at: '2026-11-17T11:40:12Z'
  },
  {
    id: 'log-002',
    user_email: 'engineer@medisync.local',
    action: 'SYNC_DISPATCH',
    resource_type: 'APIIntegration',
    resource_id: 'int-001',
    details: { integration: 'Metropolitan Hospital Epic FHIR', mode: 'celery_async' },
    created_at: '2026-11-17T11:35:00Z'
  },
  {
    id: 'log-003',
    user_email: 'analyst@medisync.local',
    action: 'PATIENT_READ',
    resource_type: 'Patient',
    resource_id: 'pat-101',
    details: { mrn: 'MRN-100201', accessed_records: 4 },
    created_at: '2026-11-17T11:22:45Z'
  },
  {
    id: 'log-004',
    user_email: 'system@medisync.local',
    action: 'WEBHOOK_INGEST',
    resource_type: 'WebhookEvent',
    resource_id: 'wh-001',
    details: { source: 'Metropolitan_EHR_Gateway', signature_valid: true },
    created_at: '2026-11-17T11:20:02Z'
  }
];
