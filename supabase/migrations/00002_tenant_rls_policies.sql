-- CARESEAL — TENANT ISOLATION RLS POLICIES
-- References: docs/CARESEAL_MASTER_BLUEPRINT.md, docs/CARESEAL_SCHEMA_DRAFT.sql
-- Invariant: An authorized member of Hospital A can access Hospital A data,
-- CANNOT read or change Hospital B data, and unauthorized users are DENIED.

-- Ensure auth.uid() function exists for both native Supabase and standalone Postgres test harnesses
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_proc JOIN pg_namespace ON pg_proc.pronamespace = pg_namespace.oid WHERE nspname = 'auth' AND proname = 'uid') THEN
        CREATE SCHEMA IF NOT EXISTS auth;
        CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $fn$
            SELECT NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid;
        $fn$;
    END IF;
END $$;

-- 1. Helper function: Check if current authenticated user is an active member of the target organization
CREATE OR REPLACE FUNCTION public.is_active_org_member(target_org_id uuid, allowed_roles text[] DEFAULT NULL)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.org_memberships
    WHERE user_id = auth.uid()
      AND organization_id = target_org_id
      AND status = 'active'
      AND (allowed_roles IS NULL OR role = ANY(allowed_roles))
  );
$$;

-- 2. Grants: Explicitly grant minimal required DML to authenticated role (RLS filters rows)
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON public.organizations TO authenticated;
GRANT SELECT ON public.org_memberships TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.medical_claims TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.claim_line_items TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.claim_documents TO authenticated;

-- anon role receives ZERO table grants (fail-closed deny-by-default)
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;

-- 3. RLS Policies: Organizations
DROP POLICY IF EXISTS "org_members_view_own_organization" ON public.organizations;
CREATE POLICY "org_members_view_own_organization"
ON public.organizations
FOR SELECT
TO authenticated
USING (
  public.is_active_org_member(id) OR kind = 'platform'
);

-- 4. RLS Policies: Org Memberships
DROP POLICY IF EXISTS "users_view_own_memberships" ON public.org_memberships;
CREATE POLICY "users_view_own_memberships"
ON public.org_memberships
FOR SELECT
TO authenticated
USING (
  user_id = auth.uid()
);

-- 5. RLS Policies: Medical Claims
-- Read: Hospital members can view ONLY their own hospital's claims
DROP POLICY IF EXISTS "hospital_members_view_own_claims" ON public.medical_claims;
CREATE POLICY "hospital_members_view_own_claims"
ON public.medical_claims
FOR SELECT
TO authenticated
USING (
  public.is_active_org_member(hospital_id)
);

-- Insert: Only authorized issuers or admins of the hospital can submit claims for that hospital
DROP POLICY IF EXISTS "hospital_issuers_create_claims" ON public.medical_claims;
CREATE POLICY "hospital_issuers_create_claims"
ON public.medical_claims
FOR INSERT
TO authenticated
WITH CHECK (
  public.is_active_org_member(hospital_id, ARRAY['admin', 'issuer'])
);

-- Update: Only authorized issuers or admins can modify claims for their hospital
DROP POLICY IF EXISTS "hospital_issuers_update_own_claims" ON public.medical_claims;
CREATE POLICY "hospital_issuers_update_own_claims"
ON public.medical_claims
FOR UPDATE
TO authenticated
USING (
  public.is_active_org_member(hospital_id, ARRAY['admin', 'issuer'])
)
WITH CHECK (
  public.is_active_org_member(hospital_id, ARRAY['admin', 'issuer'])
);

-- Delete: HARD DENY — medical claims cannot be deleted by client roles
-- (No DELETE policy defined; deny-by-default applies)

