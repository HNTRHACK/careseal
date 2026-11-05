-- CARESEAL AI — DATABASE SCHEMA (Hackathon planning draft, 2026-11-05)
-- PostgreSQL / Supabase. USE SYNTHETIC MEDICAL DATA ONLY.
-- IMPORTANT: This migration is DENY-BY-DEFAULT. RLS is enabled but policies are
-- deliberately NOT added; access through a client will be denied until separate
-- reviewed membership/tenant policies are implemented and tested.
-- Server/service secret bypasses RLS: never expose one to a browser.
-- It is NOT a complete production-ready schema or compliance implementation.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE public.organizations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    kind text NOT NULL CHECK (kind IN ('hospital','ngo','reviewer','platform')),
    registration_reference text,
    verification_status text NOT NULL DEFAULT 'pending'
        CHECK (verification_status IN ('pending','verified','rejected','suspended')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.profiles (
    id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.org_memberships (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES public.organizations(id),
    user_id uuid NOT NULL REFERENCES public.profiles(id),
    role text NOT NULL CHECK (role IN ('admin','issuer','medical_reviewer','financial_reviewer','funder','auditor')),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, user_id, role)
);

CREATE TABLE public.organization_wallets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES public.organizations(id),
    wallet_address text NOT NULL CHECK (wallet_address ~ '^0x[0-9a-f]{40}$'),
    chain_id bigint NOT NULL,
    purpose text NOT NULL CHECK (purpose IN ('hospital_payee','hospital_signer','reviewer','funder','guardian')),
    verified_at timestamptz,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (chain_id, wallet_address, purpose)
);

CREATE TABLE public.medical_claims (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id uuid NOT NULL REFERENCES public.organizations(id),
    patient_ref_token uuid NOT NULL DEFAULT gen_random_uuid(), -- opaque; never on-chain
    hospital_invoice_fingerprint text NOT NULL,
    claim_commitment text UNIQUE CHECK (claim_commitment IS NULL OR claim_commitment ~ '^0x[0-9a-f]{64}$'),
    procedure_code text NOT NULL,
    procedure_description text NOT NULL DEFAULT '',
    region_code text NOT NULL DEFAULT '',
    clinical_complexity text NOT NULL DEFAULT 'standard',
    estimate_inr_paise bigint NOT NULL CHECK (estimate_inr_paise > 0),
    approved_cap_token_units bigint CHECK (approved_cap_token_units > 0),
    token_chain_id bigint,
    approved_token_address text,
    hospital_payee_address text,
    status text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','submitted','screened','needs_review','approved','registered','funding','funded','milestone_approved','settled','rejected','cancelled','expired')),
    signed_payload_digest text,
    signed_at timestamptz,
    created_by uuid REFERENCES public.profiles(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (hospital_id, hospital_invoice_fingerprint),
    CHECK (hospital_payee_address IS NULL OR hospital_payee_address ~ '^0x[0-9a-f]{40}$')
);

CREATE TABLE public.claim_line_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id uuid NOT NULL REFERENCES public.medical_claims(id) ON DELETE CASCADE,
    category text NOT NULL,
    item_description text NOT NULL,
    quantity numeric(12,2) NOT NULL CHECK (quantity > 0),
    unit_price_inr_paise bigint NOT NULL CHECK (unit_price_inr_paise >= 0),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.claim_documents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id uuid NOT NULL REFERENCES public.medical_claims(id) ON DELETE CASCADE,
    storage_path text NOT NULL UNIQUE,
    mime_type text NOT NULL CHECK (mime_type IN ('application/pdf','image/png','image/jpeg')),
    sha256_digest text NOT NULL,
    uploaded_by uuid REFERENCES public.profiles(id),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.price_comparisons (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id uuid NOT NULL REFERENCES public.medical_claims(id) ON DELETE CASCADE,
    source_name text NOT NULL,
    source_url text,
    source_date date,
    procedure_code text NOT NULL,
    reference_region text,
    price_min_inr_paise bigint NOT NULL CHECK (price_min_inr_paise >= 0),
    price_max_inr_paise bigint NOT NULL CHECK (price_max_inr_paise >= price_min_inr_paise),
    is_synthetic boolean NOT NULL DEFAULT true,
    reviewer_notes text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.ml_assessments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id uuid NOT NULL REFERENCES public.medical_claims(id) ON DELETE CASCADE,
    model_name text NOT NULL,
    model_version text NOT NULL,
    anomaly_score numeric,
    risk_flags jsonb NOT NULL DEFAULT '[]'::jsonb,
    is_synthetic_training_data boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.claim_reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id uuid NOT NULL REFERENCES public.medical_claims(id),
    reviewer_org_id uuid NOT NULL REFERENCES public.organizations(id),
    reviewer_user_id uuid NOT NULL REFERENCES public.profiles(id),
    discipline text NOT NULL CHECK (discipline IN ('medical','financial','milestone')),
    decision text NOT NULL CHECK (decision IN ('approved','rejected','needs_evidence')),
    conflict_declared boolean NOT NULL DEFAULT false,
    reviewer_notes text,
    evidence_document_id uuid REFERENCES public.claim_documents(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (claim_id, reviewer_org_id, discipline)
);

CREATE TABLE public.funding_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id uuid NOT NULL REFERENCES public.medical_claims(id),
    funder_org_id uuid REFERENCES public.organizations(id),
    donor_wallet_address text NOT NULL CHECK (donor_wallet_address ~ '^0x[0-9a-f]{40}$'),
    token_amount_units bigint NOT NULL CHECK (token_amount_units > 0),
    event_kind text NOT NULL CHECK (event_kind IN ('contributed','refunded')),
    chain_id bigint NOT NULL,
    tx_hash text NOT NULL,
    log_index integer NOT NULL CHECK (log_index >= 0),
    block_number bigint,
    observed_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (chain_id, tx_hash, log_index)
);

CREATE TABLE public.settlement_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id uuid NOT NULL REFERENCES public.medical_claims(id),
    recipient_wallet_address text NOT NULL,
    token_amount_units bigint NOT NULL CHECK (token_amount_units > 0),
    chain_id bigint NOT NULL,
    tx_hash text NOT NULL,
    log_index integer NOT NULL CHECK (log_index >= 0),
    observed_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (chain_id, tx_hash, log_index)
);

CREATE TABLE public.audit_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id uuid REFERENCES public.medical_claims(id),
    actor_user_id uuid REFERENCES public.profiles(id),
    actor_org_id uuid REFERENCES public.organizations(id),
    event_type text NOT NULL,
    safe_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    chain_tx_hash text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX ON public.org_memberships (user_id, organization_id);
CREATE INDEX ON public.medical_claims (hospital_id, status, created_at DESC);
CREATE INDEX ON public.claim_reviews (claim_id, discipline, decision);
CREATE INDEX ON public.funding_events (claim_id, observed_at DESC);
CREATE INDEX ON public.audit_events (claim_id, created_at DESC);

-- SECURITY GATE: No authenticated browser access until policies are written.
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.org_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organization_wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.medical_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.claim_line_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.claim_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.price_comparisons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ml_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.claim_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.funding_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.settlement_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;

-- Before use:
-- 1. Implement and verify org membership RLS policies with cross-tenant denial.
-- 2. Configure Storage bucket RLS separately (these tables do NOT secure Storage).
-- 3. Add application-enforced workflow state transitions, reviewer independence,
--    financial-event sync from trusted chain receipts and claim signature verification.
-- 4. Use trigger or row versioning so signed claims cannot silently mutate.
-- 5. No real medical / financial data in this MVP.
