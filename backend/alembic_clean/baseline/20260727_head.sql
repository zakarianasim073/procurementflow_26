CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

--
-- PostgreSQL database dump
--


-- Dumped from database version 17.10
-- Dumped by pg_dump version 17.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: canonical; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA canonical;


--
-- Name: commercial; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA commercial;


--
-- Name: intelligence; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA intelligence;


--
-- Name: knowledge; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA knowledge;


--
-- Name: raw; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA raw;


--
-- Name: staging; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA staging;


--
-- Name: tender; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA tender;


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: documenttype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.documenttype AS ENUM (
    'NOTICE',
    'TDS',
    'TDS_2',
    'BOQ',
    'SOR',
    'TEMPLATE_DOCX',
    'TEMPLATE_XLSX',
    'OTHER'
);


--
-- Name: soragency; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.soragency AS ENUM (
    'BWDB',
    'PWD',
    'LGED',
    'RHD',
    'CUSTOM'
);


--
-- Name: teamrole; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.teamrole AS ENUM (
    'OWNER',
    'ADMIN',
    'MEMBER',
    'VIEWER'
);


--
-- Name: tenderstatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.tenderstatus AS ENUM (
    'DRAFT',
    'ACTIVE',
    'COMPLETED',
    'ARCHIVED'
);


--
-- Name: userplan; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.userplan AS ENUM (
    'FREE',
    'PRO',
    'ENTERPRISE'
);


--
-- Name: app_records_agency_trigger(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.app_records_agency_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_result RECORD;
BEGIN
    IF NEW.agency_code IS NULL OR NEW.agency_code = '' OR NEW.agency_code = 'UNKNOWN' THEN
        SELECT * INTO v_result FROM apply_agency_extraction(NEW.procuring_entity, NEW.title, NEW.pe_office, NEW.district);
        NEW.agency_code := v_result.agency_code;
        NEW.agency_name := v_result.agency_name;
        NEW.ministry := v_result.ministry;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: apply_agency_extraction(text, text, text, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.apply_agency_extraction(p_procuring_entity text, p_title text, p_pe_office text DEFAULT NULL::text, p_district text DEFAULT NULL::text) RETURNS TABLE(agency_code character varying, agency_name character varying, ministry character varying, extraction_source character varying, confidence character varying)
    LANGUAGE plpgsql STABLE
    AS $$
DECLARE
    v_result RECORD;
BEGIN
    -- Try procuring_entity first (highest confidence)
    SELECT * INTO v_result FROM extract_agency_from_text(p_procuring_entity, 'procuring_entity');
    IF FOUND THEN
        RETURN QUERY SELECT v_result.canonical_agency_code, v_result.canonical_agency, v_result.canonical_ministry, 'procuring_entity'::VARCHAR(50), v_result.confidence;
        RETURN;
    END IF;

    -- Try pe_office if provided
    IF p_pe_office IS NOT NULL THEN
        SELECT * INTO v_result FROM extract_agency_from_text(p_pe_office, 'pe_office');
        IF FOUND THEN
            RETURN QUERY SELECT v_result.canonical_agency_code, v_result.canonical_agency, v_result.canonical_ministry, 'pe_office'::VARCHAR(50), v_result.confidence;
            RETURN;
        END IF;
    END IF;

    -- Try district (for road division codes like JRD, DRD)
    IF p_district IS NOT NULL THEN
        SELECT * INTO v_result FROM extract_agency_from_text(p_district, 'district');
        IF FOUND THEN
            RETURN QUERY SELECT v_result.canonical_agency_code, v_result.canonical_agency, v_result.canonical_ministry, 'district'::VARCHAR(50), v_result.confidence;
            RETURN;
        END IF;
    END IF;

    -- Fall back to title (lowest confidence but broadest coverage)
    SELECT * INTO v_result FROM extract_agency_from_text(p_title, 'title');
    IF FOUND THEN
        RETURN QUERY SELECT v_result.canonical_agency_code, v_result.canonical_agency, v_result.canonical_ministry, 'title'::VARCHAR(50), v_result.confidence;
        RETURN;
    END IF;

    -- Nothing found
    RETURN QUERY SELECT 'UNMAPPED'::VARCHAR(20), 'UNMAPPED'::VARCHAR(100), 'UNMAPPED'::VARCHAR(100), 'none'::VARCHAR(50), 'none'::VARCHAR(20);
END;
$$;


--
-- Name: award_records_agency_trigger(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.award_records_agency_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_result RECORD;
BEGIN
    IF NEW.agency_code IS NULL OR NEW.agency_code = '' OR NEW.agency_code = 'UNKNOWN' THEN
        SELECT * INTO v_result FROM extract_agency_from_text(NEW.procuring_entity, 'procuring_entity');
        IF NOT FOUND THEN
            SELECT * INTO v_result FROM extract_agency_from_text(NEW.title, 'title');
        END IF;
        IF FOUND THEN
            NEW.agency_code := v_result.canonical_agency_code;
        ELSE
            NEW.agency_code := 'UNMAPPED';
        END IF;
    END IF;

    -- Auto-extract procurement_method from procuring_entity
    IF NEW.procurement_method IS NULL OR NEW.procurement_method = '' THEN
        NEW.procurement_method := CASE 
            WHEN NEW.procuring_entity ILIKE '%OTM' THEN 'OTM'
            WHEN NEW.procuring_entity ILIKE '%RFQ' THEN 'RFQ'
            WHEN NEW.procuring_entity ILIKE '%LTM' THEN 'LTM'
            WHEN NEW.procuring_entity ILIKE '%DPM' THEN 'DPM'
            WHEN NEW.procuring_entity ILIKE '%NCB' THEN 'NCB'
            WHEN NEW.procuring_entity ILIKE '%ICB' THEN 'ICB'
            WHEN NEW.procuring_entity ILIKE '%e-GP' THEN 'e-GP'
            WHEN NEW.procuring_entity ILIKE '%eGP' THEN 'e-GP'
            ELSE 'UNMAPPED'
        END;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: canonical_clean_text(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.canonical_clean_text(value text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT nullif(trim(regexp_replace(upper(coalesce(value, '')), '\s+', ' ', 'g')), '')
$$;


--
-- Name: canonical_contractor_key(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.canonical_contractor_key(value text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT md5(coalesce(canonical_normalize_contractor(value), 'UNKNOWN'))
$$;


--
-- Name: canonical_is_jv(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.canonical_is_jv(value text) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT upper(coalesce(value, '')) ~ '(\mJV\M|\mJ V\M|JOINT\s+VENTURE|JVCA|\mCONSORTIUM\M)'
$$;


--
-- Name: canonical_normalize_contractor(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.canonical_normalize_contractor(value text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT nullif(
        trim(
            regexp_replace(
                regexp_replace(
                    regexp_replace(
                        regexp_replace(upper(coalesce(value, '')), '(^|\s)(M/S\.?|MS\.?|M/S|MESSRS\.?|MD\.?)(\s|\.|:)+', ' ', 'gi'),
                        '[^A-Z0-9& ]+', ' ', 'g'
                    ),
                    '\s+', ' ', 'g'
                ),
                '(^THE\s+)', '', 'i'
            )
        ),
        ''
    )
$$;


--
-- Name: canonical_normalize_package(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.canonical_normalize_package(value text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT nullif(trim(regexp_replace(upper(coalesce(value, '')), '[^A-Z0-9/._-]+', ' ', 'g')), '')
$$;


--
-- Name: canonical_package_key(text, text, text, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.canonical_package_key(pkg text, tender text, title text, agency text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT md5(
        coalesce(canonical_normalize_package(pkg), '') || '|' ||
        coalesce(nullif(trim(tender), ''), '') || '|' ||
        left(coalesce(canonical_clean_text(title), ''), 160) || '|' ||
        coalesce(canonical_clean_text(agency), '')
    )
$$;


--
-- Name: canonical_safe_date(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.canonical_safe_date(value text) RETURNS date
    LANGUAGE plpgsql IMMUTABLE
    AS $$
BEGIN
    IF value IS NULL OR trim(value) = '' THEN
        RETURN NULL;
    END IF;
    BEGIN
        RETURN value::date;
    EXCEPTION WHEN others THEN
        RETURN NULL;
    END;
END;
$$;


--
-- Name: extract_agency_from_text(text, character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.extract_agency_from_text(p_text text, p_match_field character varying DEFAULT 'title'::character varying) RETURNS TABLE(canonical_agency character varying, canonical_agency_code character varying, canonical_ministry character varying, matched_pattern character varying, confidence character varying)
    LANGUAGE plpgsql STABLE
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        aer.canonical_agency,
        aer.canonical_agency_code,
        aer.canonical_ministry,
        aer.pattern as matched_pattern,
        aer.confidence
    FROM agency_extraction_rules aer
    WHERE aer.match_field = p_match_field
      AND aer.category != 'procurement_method'
      AND p_text ILIKE '%' || aer.pattern || '%'
    ORDER BY aer.priority ASC, LENGTH(aer.pattern) DESC
    LIMIT 1;
END;
$$;


--
-- Name: extract_ref_no_from_title(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.extract_ref_no_from_title(p_title text) RETURNS text
    LANGUAGE plpgsql IMMUTABLE
    AS $$
DECLARE
    v_ref TEXT;
BEGIN
    -- Pattern 1: Numbers with dots and dashes at start (e.g., "58.04.5900.088.04.001.26-1169")
    v_ref := (regexp_match(p_title, '^([0-9\.\-]+)'))[1];
    IF v_ref IS NOT NULL AND LENGTH(v_ref) > 5 THEN
        RETURN v_ref;
    END IF;

    -- Pattern 2: "Ref: " or "Reference: " followed by alphanumeric
    v_ref := (regexp_match(p_title, '(?i)(?:ref|reference)[\s:]*([A-Z0-9\-\/\.]+)'))[1];
    IF v_ref IS NOT NULL AND LENGTH(v_ref) > 3 THEN
        RETURN v_ref;
    END IF;

    -- Pattern 3: "No. " or "Number: " followed by alphanumeric
    v_ref := (regexp_match(p_title, '(?i)(?:no\.?|number)[\s:]*([A-Z0-9\-\/\.]+)'))[1];
    IF v_ref IS NOT NULL AND LENGTH(v_ref) > 3 THEN
        RETURN v_ref;
    END IF;

    RETURN NULL;
END;
$$;


--
-- Name: normalize_contractor_name(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.normalize_contractor_name(raw_name text) RETURNS text
    LANGUAGE plpgsql IMMUTABLE
    AS $_$
DECLARE
    cleaned TEXT;
BEGIN
    cleaned := raw_name;

    -- Remove common prefixes (case-insensitive)
    cleaned := regexp_replace(cleaned, '^(M/S|M/s|M/S\.|M/s\.|M/S|M/s|MS|MESSRS|Messrs|M/s\s|M/S\s)\s*[\.\-]?\s*', '', 'i');
    cleaned := regexp_replace(cleaned, '^(M/s\.?|M/S\.?|MS\.?|MESSRS\.?)\s*', '', 'i');
    cleaned := regexp_replace(cleaned, '^(M\.S\.|M\.S|M\/S)\s*', '', 'i');

    -- Remove suffixes that vary
    cleaned := regexp_replace(cleaned, '\s*(Ltd\.?|Limited|Pvt\.?|Private|JV|Joint\s*Venture|J\.V\.|J/V|\(JV\)|\(J/V\)|\(J\.V\.\))\s*$', '', 'i');
    cleaned := regexp_replace(cleaned, '\s*(Co\.?|Company|Corp\.?|Corporation|Inc\.?)\s*$', '', 'i');
    cleaned := regexp_replace(cleaned, '\s*(\&\s*Co\.?|And\s*Co\.?)\s*$', '', 'i');
    cleaned := regexp_replace(cleaned, '\s*(Group|Enterprise|Enterprises|Associates|Construction|Builders|Engineering|Contractors)\s*$', '', 'i');

    -- Standardize whitespace
    cleaned := regexp_replace(cleaned, '\s+', ' ', 'g');
    cleaned := TRIM(cleaned);

    -- Uppercase for matching (store original separately for display)
    RETURN UPPER(cleaned);
END;
$_$;


--
-- Name: refresh_contractor_dna(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.refresh_contractor_dna() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- Update contractor aggregate stats from award_records
    WITH contractor_stats AS (
        SELECT
            ar.contractor_name,
            COUNT(*) AS total_contracts,
            SUM(ar.amount_bdt) AS total_amount,
            AVG(pl.npp_ratio) AS avg_npp,
            STDDEV(pl.npp_ratio) AS npp_volatility,
            COUNT(DISTINCT ar.agency_code) AS agencies_worked,
            COUNT(DISTINCT ar.zone_id) AS districts_worked,
            MODE() WITHIN GROUP (ORDER BY ar.agency_code) AS preferred_agency,
            MIN(ar.award_date) AS first_award,
            MAX(ar.award_date) AS last_award
        FROM award_records ar
        LEFT JOIN procurement_lifecycle pl ON ar.tender_id = pl.tender_id
        WHERE ar.contractor_name = NEW.contractor_name
        GROUP BY ar.contractor_name
    )
    INSERT INTO contractor_dna (
        contractor_id, total_contracts, total_amount_bdt, avg_award_bdt,
        agencies_worked, districts_worked, preferred_agency, avg_npp,
        npp_volatility, avg_discount_pct, first_award_date, last_award_date
    )
    SELECT
        c.contractor_id,
        cs.total_contracts,
        cs.total_amount,
        CASE WHEN cs.total_contracts > 0 THEN cs.total_amount / cs.total_contracts ELSE 0 END,
        cs.agencies_worked,
        cs.districts_worked,
        cs.preferred_agency,
        cs.avg_npp,
        COALESCE(cs.npp_volatility, 0),
        COALESCE((1 - cs.avg_npp) * 100, 0),
        cs.first_award,
        cs.last_award
    FROM contractors c
    JOIN contractor_stats cs ON c.contractor_name = cs.contractor_name
    ON CONFLICT (contractor_id)
    DO UPDATE SET
        total_contracts      = EXCLUDED.total_contracts,
        total_amount_bdt     = EXCLUDED.total_amount_bdt,
        avg_award_bdt        = EXCLUDED.avg_award_bdt,
        agencies_worked      = EXCLUDED.agencies_worked,
        districts_worked     = EXCLUDED.districts_worked,
        preferred_agency     = EXCLUDED.preferred_agency,
        avg_npp              = EXCLUDED.avg_npp,
        npp_volatility       = EXCLUDED.npp_volatility,
        avg_discount_pct     = EXCLUDED.avg_discount_pct,
        first_award_date     = EXCLUDED.first_award_date,
        last_award_date      = EXCLUDED.last_award_date,
        updated_at           = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: reject_audit_mutate(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.reject_audit_mutate() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only; updates and deletes are forbidden'
                USING ERRCODE = '42501';
        END;
        $$;


--
-- Name: run_data_quality_checks(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.run_data_quality_checks() RETURNS TABLE(check_name character varying, violation_count integer, threshold integer, severity character varying, status character varying, last_run timestamp without time zone)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_check RECORD;
    v_count INT;
    v_status VARCHAR(20);
BEGIN
    FOR v_check IN SELECT * FROM data_quality_checks WHERE is_active = TRUE LOOP
        EXECUTE v_check.check_query INTO v_count;

        v_status := CASE 
            WHEN v_count > v_check.threshold_violation THEN 'FAILED'
            WHEN v_count > v_check.threshold_violation * 0.8 THEN 'WARNING'
            ELSE 'PASS'
        END;

        UPDATE data_quality_checks 
        SET last_run = NOW(), violation_count = v_count
        WHERE id = v_check.id;

        check_name := v_check.check_name;
        violation_count := v_count;
        threshold := v_check.threshold_violation;
        severity := v_check.severity;
        status := v_status;
        last_run := NOW();
        RETURN NEXT;
    END LOOP;
END;
$$;


--
-- Name: trg_pf_relationships_updated(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_pf_relationships_updated() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$;


--
-- Name: update_app_records_agencies(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_app_records_agencies() RETURNS TABLE(updated_count bigint, unmapped_count bigint, agency_breakdown text)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_updated BIGINT;
    v_unmapped BIGINT;
BEGIN
    UPDATE app_records ar
    SET 
        agency_code = COALESCE(NULLIF(TRIM(ar.agency_code), ''), 
            (SELECT agency_code FROM apply_agency_extraction(ar.procuring_entity, ar.title, ar.pe_office, ar.district)),
            'UNMAPPED'
        ),
        agency_name = COALESCE(NULLIF(TRIM(ar.agency_name), ''), 
            (SELECT agency_name FROM apply_agency_extraction(ar.procuring_entity, ar.title, ar.pe_office, ar.district)),
            'UNMAPPED'
        ),
        ministry = COALESCE(NULLIF(TRIM(ar.ministry), ''), 
            (SELECT ministry FROM apply_agency_extraction(ar.procuring_entity, ar.title, ar.pe_office, ar.district)),
            'UNMAPPED'
        )
    WHERE ar.agency_code IS NULL OR ar.agency_code = '' OR ar.agency_code = 'UNKNOWN';

    GET DIAGNOSTICS v_updated = ROW_COUNT;
    SELECT COUNT(*) INTO v_unmapped FROM app_records WHERE agency_code = 'UNMAPPED' OR agency_code = '' OR agency_code IS NULL;

    RETURN QUERY
    SELECT 
        v_updated,
        v_unmapped,
        (SELECT STRING_AGG(agency_code || ':' || cnt::TEXT, ', ' ORDER BY cnt DESC)
         FROM (SELECT agency_code, COUNT(*) as cnt FROM app_records GROUP BY agency_code ORDER BY cnt DESC LIMIT 20) t);
END;
$$;


--
-- Name: update_award_records_agencies(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_award_records_agencies() RETURNS TABLE(updated_count bigint, unmapped_count bigint, agency_breakdown text)
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_updated BIGINT;
    v_unmapped BIGINT;
BEGIN
    UPDATE award_records_v2 arv
    SET 
        agency_code = COALESCE(NULLIF(TRIM(arv.agency_code), ''), 
            (SELECT canonical_agency_code FROM extract_agency_from_text(arv.procuring_entity, 'procuring_entity')),
            (SELECT canonical_agency_code FROM extract_agency_from_text(arv.title, 'title')),
            'UNMAPPED'
        ),
        procurement_method = COALESCE(NULLIF(TRIM(arv.procurement_method), ''), 
            CASE 
                WHEN arv.procuring_entity ILIKE '%OTM' THEN 'OTM'
                WHEN arv.procuring_entity ILIKE '%RFQ' THEN 'RFQ'
                WHEN arv.procuring_entity ILIKE '%LTM' THEN 'LTM'
                WHEN arv.procuring_entity ILIKE '%DPM' THEN 'DPM'
                WHEN arv.procuring_entity ILIKE '%NCB' THEN 'NCB'
                WHEN arv.procuring_entity ILIKE '%ICB' THEN 'ICB'
                WHEN arv.procuring_entity ILIKE '%e-GP' THEN 'e-GP'
                WHEN arv.procuring_entity ILIKE '%eGP' THEN 'e-GP'
                ELSE 'UNMAPPED'
            END
        )
    WHERE arv.agency_code IS NULL OR arv.agency_code = '' OR arv.agency_code = 'UNKNOWN';

    GET DIAGNOSTICS v_updated = ROW_COUNT;

    SELECT COUNT(*) INTO v_unmapped FROM award_records_v2 WHERE agency_code = 'UNMAPPED' OR agency_code = '' OR agency_code IS NULL;

    RETURN QUERY
    SELECT 
        v_updated,
        v_unmapped,
        (SELECT STRING_AGG(agency_code || ':' || cnt::TEXT, ', ' ORDER BY cnt DESC)
         FROM (SELECT agency_code, COUNT(*) as cnt FROM award_records_v2 GROUP BY agency_code ORDER BY cnt DESC LIMIT 20) t);
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: amendments; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.amendments (
    id character varying(36) NOT NULL,
    document_id character varying(36) NOT NULL,
    clause_id character varying(36),
    amendment_type character varying(50) NOT NULL,
    previous_text text,
    new_text text,
    effective_date date NOT NULL,
    authority_circular_id character varying(128),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: bid_security_requirements; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.bid_security_requirements (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    bid_security_amount double precision,
    bid_security_pct double precision,
    bid_security_type character varying(100),
    validity_days integer,
    exposure_amount double precision,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: budget_lines; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.budget_lines (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36),
    budget_code character varying(100) NOT NULL,
    description character varying(500) NOT NULL,
    allocated_amount double precision NOT NULL,
    spent_amount double precision DEFAULT '0'::double precision,
    committed_amount double precision DEFAULT '0'::double precision,
    variance double precision,
    variance_pct double precision,
    fiscal_year character varying(10),
    status character varying(20) DEFAULT 'active'::character varying,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: circulars; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.circulars (
    id character varying(36) NOT NULL,
    circular_number character varying(128) NOT NULL,
    title character varying(500) NOT NULL,
    issuing_authority character varying(255) NOT NULL,
    issue_date date NOT NULL,
    effective_date date,
    affected_document_ids json,
    affected_clause_ids json,
    override_instructions text,
    status character varying(20) DEFAULT 'ACTIVE'::character varying,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: clauses; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.clauses (
    id character varying(36) NOT NULL,
    version_id character varying(36) NOT NULL,
    clause_number character varying(64) NOT NULL,
    title character varying(500) NOT NULL,
    text text NOT NULL,
    summary character varying(2000),
    parent_clause_id character varying(36),
    order_index integer DEFAULT 0,
    effective_date date,
    amendment_date date,
    status character varying(20) DEFAULT 'ACTIVE'::character varying,
    metadata json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: competitor_patterns; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.competitor_patterns (
    id character varying(36) NOT NULL,
    contractor_id character varying(36) NOT NULL,
    contractor_name character varying(300) NOT NULL,
    avg_discount_pct double precision,
    avg_markup_pct double precision,
    bid_range_low double precision,
    bid_range_high double precision,
    win_rate double precision,
    agency_specific json,
    recent_bids json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: cost_estimates; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.cost_estimates (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    workspace_id character varying(36),
    total_direct_cost double precision,
    total_indirect_cost double precision,
    total_cost double precision,
    contingency_pct double precision,
    contingency_amount double precision,
    escalation_pct double precision,
    escalation_amount double precision,
    grand_total double precision,
    items json,
    summary text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: decisions; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.decisions (
    id character varying(36) NOT NULL,
    tender_id character varying(36),
    evaluation_type character varying(50) NOT NULL,
    decision character varying(50) NOT NULL,
    evidence json,
    legal_citations json,
    rule_execution_id character varying(36),
    made_by character varying(64),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: escalation_indices; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.escalation_indices (
    id character varying(36) NOT NULL,
    index_code character varying(50) NOT NULL,
    name character varying(200) NOT NULL,
    base_year integer,
    current_value double precision,
    annual_change_pct double precision,
    source character varying(200),
    effective_date character varying(20),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: estimate_sessions; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.estimate_sessions (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    workspace_id character varying(36),
    items json,
    total_estimate double precision,
    methodology character varying(50) DEFAULT 'rate_analysis'::character varying,
    status character varying(20) DEFAULT 'draft'::character varying,
    notes text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: financial_kpis; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.financial_kpis (
    id character varying(36) NOT NULL,
    avg_margin double precision,
    avg_bid_value double precision,
    win_rate double precision,
    total_pipeline_value double precision DEFAULT '0'::double precision,
    cash_conversion_cycle integer,
    avg_payment_delay integer,
    bid_security_exposure double precision DEFAULT '0'::double precision,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: financial_pipeline_summaries; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.financial_pipeline_summaries (
    id character varying(36) NOT NULL,
    total_bid_value double precision DEFAULT '0'::double precision,
    weighted_value double precision DEFAULT '0'::double precision,
    expected_margin double precision,
    win_adjusted_revenue double precision,
    portfolio_exposure double precision DEFAULT '0'::double precision,
    cashflow_forecast json,
    top_risks json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: financial_risks; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.financial_risks (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    risk_type character varying(100) NOT NULL,
    description character varying(2000) NOT NULL,
    probability double precision,
    impact_amount double precision,
    risk_score double precision,
    mitigation text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: financial_workflows; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.financial_workflows (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    workspace_id character varying(36),
    workflow_type character varying(100) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    steps json,
    results json,
    errors json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: formula_definitions; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.formula_definitions (
    id character varying(36) NOT NULL,
    formula_name character varying(128) NOT NULL,
    expression text NOT NULL,
    description text,
    parameters json,
    version character varying(16) DEFAULT '1.0'::character varying,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: formula_parameters; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.formula_parameters (
    id character varying(36) NOT NULL,
    rule_id character varying(100) NOT NULL,
    name character varying(128) NOT NULL,
    value double precision NOT NULL,
    parameter_type character varying(32) DEFAULT 'constant'::character varying,
    description text,
    source text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: historical_prices; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.historical_prices (
    id character varying(36) NOT NULL,
    item_code character varying(100) NOT NULL,
    description character varying(500) NOT NULL,
    unit character varying(50),
    price double precision NOT NULL,
    region character varying(100),
    source_tender_id character varying(36),
    source_date character varying(20),
    contract_value double precision,
    escalation_rate double precision,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: legal_citations; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.legal_citations (
    id character varying(36) NOT NULL,
    regulation_version_id character varying(36),
    clause_id character varying(36),
    clause_number character varying(64) NOT NULL,
    sub_clause character varying(64),
    page_number integer,
    circular_id character varying(36),
    document_version character varying(32),
    citation_text text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: margin_simulations; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.margin_simulations (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    workspace_id character varying(36),
    estimated_cost double precision NOT NULL,
    target_margin_pct double precision,
    target_price double precision,
    overhead_pct double precision,
    profit_at_target double precision,
    break_even_price double precision,
    scenarios json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: market_rates; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.market_rates (
    id character varying(36) NOT NULL,
    item_code character varying(100) NOT NULL,
    description character varying(500) NOT NULL,
    unit character varying(50),
    current_rate double precision NOT NULL,
    rate_low double precision,
    rate_high double precision,
    source character varying(200),
    effective_date character varying(20),
    region character varying(100),
    currency character varying(3),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: nppi_datasets; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.nppi_datasets (
    id character varying(36) NOT NULL,
    rule_id character varying(100),
    procurement_type character varying(50),
    agency character varying(100),
    zone character varying(10),
    tender_value double precision,
    official_estimate double precision,
    award_amount double precision,
    award_date date,
    nppi_calculated double precision,
    data_source character varying(100),
    exclusion_reason text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: nppi_projects; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.nppi_projects (
    id character varying(36) NOT NULL,
    project_code character varying(100) NOT NULL,
    project_name character varying(500) NOT NULL,
    ministry character varying(200),
    agency character varying(200),
    approved_cost double precision,
    revised_cost double precision,
    expenditure_to_date double precision,
    budget_allocation double precision,
    fiscal_year character varying(10),
    status character varying(50),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: payment_schedules; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.payment_schedules (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    workspace_id character varying(36),
    contract_value double precision NOT NULL,
    advance_payment_pct double precision,
    advance_amount double precision,
    retention_pct double precision,
    retention_amount double precision,
    milestones json,
    total_receivables double precision,
    payment_terms_days integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: performance_guarantees; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.performance_guarantees (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    guarantee_pct double precision,
    guarantee_amount double precision,
    validity_period_months integer,
    guarantee_type character varying(100),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: procurement_type_defs; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.procurement_type_defs (
    id character varying(36) NOT NULL,
    code character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    applicable_rule_ids json,
    parent_code character varying(50),
    is_active boolean DEFAULT true,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: rate_analyses; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.rate_analyses (
    id character varying(36) NOT NULL,
    item_code character varying(100) NOT NULL,
    description character varying(500) NOT NULL,
    unit character varying(50),
    material_cost double precision,
    labor_cost double precision,
    equipment_cost double precision,
    overhead_cost double precision,
    profit_pct double precision,
    total_rate double precision,
    notes text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: regulation_documents; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.regulation_documents (
    id character varying(36) NOT NULL,
    title character varying(500) NOT NULL,
    document_type character varying(50) NOT NULL,
    issuing_authority character varying(255) NOT NULL,
    publication_date date NOT NULL,
    effective_date date NOT NULL,
    superseded_date date,
    status character varying(20) DEFAULT 'ACTIVE'::character varying,
    pdf_reference character varying(512),
    metadata json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: regulation_versions; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.regulation_versions (
    id character varying(36) NOT NULL,
    document_id character varying(36) NOT NULL,
    version character varying(32) NOT NULL,
    version_label character varying(255),
    effective_date date NOT NULL,
    superseded_date date,
    change_summary text,
    previous_version_id character varying(36),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: rule_definitions; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.rule_definitions (
    id character varying(36) NOT NULL,
    rule_id character varying(100) NOT NULL,
    title character varying(500) NOT NULL,
    authority_version_id character varying(36) NOT NULL,
    procurement_types json,
    inputs json,
    outputs json,
    formula_reference character varying(255),
    threshold_definitions json,
    effective_from date NOT NULL,
    effective_to date,
    rule_version integer DEFAULT 1,
    status character varying(20) DEFAULT 'ACTIVE'::character varying,
    yaml_definition text,
    metadata json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: rule_execution_logs; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.rule_execution_logs (
    id character varying(36) NOT NULL,
    rule_id character varying(100) NOT NULL,
    tender_id character varying(36),
    evaluation_id character varying(36),
    inputs json NOT NULL,
    outputs json NOT NULL,
    intermediate_values json,
    decision character varying(50),
    legal_citations json,
    rule_version integer NOT NULL,
    executed_by character varying(64),
    correlation_id character varying(64),
    execution_time_ms double precision DEFAULT '0'::double precision,
    metadata json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: scenario_results; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.scenario_results (
    id character varying(36) NOT NULL,
    scenario_name character varying(200) NOT NULL,
    assumptions json,
    estimated_margin double precision,
    estimated_price double precision,
    confidence double precision,
    risk_level character varying(20) DEFAULT 'medium'::character varying,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: sensitivity_analyses; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.sensitivity_analyses (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    cost_drivers json,
    scenarios json,
    most_sensitive_factor character varying(200),
    summary text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: slt_assessments; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.slt_assessments (
    id character varying(36) NOT NULL,
    calculation_id character varying(36),
    quoted_price double precision,
    deviation_pct double precision,
    slt_status character varying(50) NOT NULL,
    legal_citation_id character varying(36),
    notes text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: weighted_average_calculations; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.weighted_average_calculations (
    id character varying(36) NOT NULL,
    rule_id character varying(100),
    tender_id character varying(36),
    official_estimate double precision,
    nppi_applied double precision,
    responsive_bids json,
    weighted_average double precision,
    weighted_std_dev double precision,
    lower_limit double precision,
    upper_limit double precision,
    calculation_parameters json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: working_capital; Type: TABLE; Schema: commercial; Owner: -
--

CREATE TABLE commercial.working_capital (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    estimated_monthly_cost double precision,
    mobilization_period_months integer,
    payment_delay_days integer,
    required_capital double precision,
    available_capital double precision,
    shortfall double precision,
    recommendation text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: clauses; Type: TABLE; Schema: knowledge; Owner: -
--

CREATE TABLE knowledge.clauses (
    id character varying(36) NOT NULL,
    source character varying(32) NOT NULL,
    source_version character varying(32) DEFAULT '1.0'::character varying NOT NULL,
    clause_number character varying(64) NOT NULL,
    title character varying(500) NOT NULL,
    text text NOT NULL,
    summary character varying(2000) DEFAULT ''::character varying NOT NULL,
    keywords json DEFAULT '[]'::json NOT NULL,
    effective_date date,
    amendment_date date,
    supersedes json DEFAULT '[]'::json NOT NULL,
    superseded_by character varying(64),
    parent_clause_id character varying(36),
    order_index integer DEFAULT 0 NOT NULL,
    categories json DEFAULT '[]'::json NOT NULL,
    tenant_id character varying(64),
    is_active boolean DEFAULT true NOT NULL,
    tags json DEFAULT '[]'::json NOT NULL,
    metadata json DEFAULT '{}'::json NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: dictionary_terms; Type: TABLE; Schema: knowledge; Owner: -
--

CREATE TABLE knowledge.dictionary_terms (
    id character varying(36) NOT NULL,
    term character varying(255) NOT NULL,
    language character varying(2) NOT NULL,
    category character varying(32) NOT NULL,
    subcategory character varying(64),
    domain character varying(32) NOT NULL,
    definition character varying(2000) NOT NULL,
    translation character varying(255),
    synonyms json DEFAULT '[]'::json NOT NULL,
    ai_synonyms json DEFAULT '[]'::json NOT NULL,
    abbreviation_of character varying(255),
    parent_term_id character varying(36),
    version integer DEFAULT 1 NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    metadata json DEFAULT '{}'::json NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: document_nodes; Type: TABLE; Schema: knowledge; Owner: -
--

CREATE TABLE knowledge.document_nodes (
    id character varying(36) NOT NULL,
    document_type character varying(32) NOT NULL,
    title character varying(500) NOT NULL,
    reference_number character varying(128),
    version character varying(32) DEFAULT '1.0'::character varying NOT NULL,
    date date,
    issuing_entity character varying(255),
    receiving_entity character varying(255),
    project_id character varying(36),
    contract_id character varying(36),
    file_reference character varying(512),
    extracted_terms json DEFAULT '[]'::json NOT NULL,
    summary character varying(2000),
    tenant_id character varying(64),
    is_active boolean DEFAULT true NOT NULL,
    tags json DEFAULT '[]'::json NOT NULL,
    metadata json DEFAULT '{}'::json NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: document_relationships; Type: TABLE; Schema: knowledge; Owner: -
--

CREATE TABLE knowledge.document_relationships (
    id character varying(36) NOT NULL,
    source_document_id character varying(36) NOT NULL,
    target_document_id character varying(36) NOT NULL,
    relationship_type character varying(32) NOT NULL,
    description character varying(500),
    metadata json DEFAULT '{}'::json NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: _bench; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public._bench (
    id text,
    title text,
    payload jsonb
);


--
-- Name: agencies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agencies (
    agency_code character varying(20) NOT NULL,
    agency_name character varying(300) NOT NULL,
    ministry character varying(300) NOT NULL,
    keyword character varying(100),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL,
    total_awards integer DEFAULT 0,
    total_value_bdt double precision DEFAULT 0,
    org_count integer DEFAULT 0,
    pe_offices json DEFAULT '[]'::json
);


--
-- Name: agency_extraction_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agency_extraction_rules (
    id integer NOT NULL,
    pattern character varying(100) NOT NULL,
    canonical_agency character varying(100) NOT NULL,
    canonical_agency_code character varying(20) NOT NULL,
    canonical_ministry character varying(100) NOT NULL,
    match_field character varying(50) DEFAULT 'procuring_entity'::character varying NOT NULL,
    confidence character varying(20) DEFAULT 'medium'::character varying NOT NULL,
    category character varying(50) DEFAULT 'general'::character varying NOT NULL,
    priority integer DEFAULT 100 NOT NULL
);


--
-- Name: agency_extraction_rules_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agency_extraction_rules_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agency_extraction_rules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agency_extraction_rules_id_seq OWNED BY public.agency_extraction_rules.id;


--
-- Name: agency_extraction_summary; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.agency_extraction_summary AS
 SELECT category,
    count(*) AS rule_count,
    count(DISTINCT canonical_agency) AS unique_agencies,
    count(DISTINCT canonical_ministry) AS unique_ministries,
    string_agg(DISTINCT (confidence)::text, ', '::text ORDER BY (confidence)::text) AS confidence_levels
   FROM public.agency_extraction_rules
  WHERE ((category)::text <> 'procurement_method'::text)
  GROUP BY category
  ORDER BY (count(*)) DESC;


--
-- Name: agency_intelligence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agency_intelligence (
    agency_code character varying(20) NOT NULL,
    total_contracts integer NOT NULL,
    total_amount_bdt double precision NOT NULL,
    avg_npp double precision,
    npp_trend character varying(20),
    preferred_method character varying(100),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: agency_performance_summary; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agency_performance_summary (
    agency_code text,
    unique_contractors bigint,
    total_projects bigint,
    completed_projects bigint,
    ongoing_projects bigint,
    avg_delay_days numeric,
    avg_project_value_bdt numeric,
    largest_project_value_bdt double precision,
    total_value_bdt double precision,
    completed_value_bdt double precision,
    delayed_projects_pct numeric,
    on_time_rate_pct numeric,
    completion_rate_pct numeric
);


--
-- Name: agent_brain_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_brain_messages (
    id character varying(36) NOT NULL,
    sender_id character varying(50) NOT NULL,
    recipient_id character varying(50),
    message_type character varying(50),
    subject character varying(255),
    body json,
    thread_id character varying(36),
    status character varying(20),
    response_to character varying(36),
    created_at timestamp with time zone
);


--
-- Name: agent_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_jobs (
    id character varying(36) NOT NULL,
    tenant_id character varying(36),
    agent_id character varying(50) NOT NULL,
    request_id character varying(36),
    tender_id character varying(100),
    state character varying(20),
    priority integer,
    attempts integer,
    max_attempts integer,
    last_error text,
    input_data json,
    result_id character varying(36),
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: agent_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_logs (
    id integer NOT NULL,
    result_id character varying(36),
    agent_id character varying(50),
    tender_id character varying(100),
    level character varying(10),
    message text,
    meta json,
    created_at timestamp with time zone
);


--
-- Name: agent_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.agent_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: agent_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.agent_logs_id_seq OWNED BY public.agent_logs.id;


--
-- Name: agent_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_results (
    id character varying(36) NOT NULL,
    tenant_id character varying(36),
    agent_id character varying(50) NOT NULL,
    agent_name character varying(255),
    agent_version character varying(20),
    request_id character varying(36),
    tender_id character varying(100),
    status character varying(20),
    output json,
    error text,
    execution_time_ms integer,
    model_used character varying(100),
    trace_id character varying(36),
    source_ids json,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: agent_thoughts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.agent_thoughts (
    id character varying(36) NOT NULL,
    agent_id character varying(100) NOT NULL,
    agent_name character varying(255),
    tender_id character varying(100),
    thought_type character varying(50),
    title character varying(500),
    description text,
    evidence json,
    impact character varying(50),
    confidence double precision,
    status character varying(20),
    reviewer_comment text,
    approved_at timestamp with time zone,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: alembic_version_commercial; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version_commercial (
    version_num character varying(32) NOT NULL
);


--
-- Name: alembic_version_knowledge; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version_knowledge (
    version_num character varying(32) NOT NULL
);


--
-- Name: alembic_version_tender; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version_tender (
    version_num character varying(32) NOT NULL
);


--
-- Name: amendments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.amendments (
    id character varying(36) NOT NULL,
    regulation_version_id character varying(36) NOT NULL,
    clause_id character varying(36),
    amendment_ref character varying(100) NOT NULL,
    effective_date date NOT NULL,
    description text,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: amount_normalization_audit; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.amount_normalization_audit (
    id bigint NOT NULL,
    source_table text NOT NULL,
    source_id text NOT NULL,
    package_no text,
    amount_original double precision DEFAULT 0 NOT NULL,
    amount_normalized_bdt double precision DEFAULT 0 NOT NULL,
    amount_unit text DEFAULT 'bdt'::text NOT NULL,
    confidence double precision DEFAULT 0 NOT NULL,
    warning text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: amount_normalization_audit_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.amount_normalization_audit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: amount_normalization_audit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.amount_normalization_audit_id_seq OWNED BY public.amount_normalization_audit.id;


--
-- Name: app_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.app_records (
    procurement_tender_id character varying(36) NOT NULL,
    source_tender_id character varying(500),
    title text,
    estimated_cost_bdt double precision NOT NULL,
    status character varying(50),
    published_date character varying(20),
    deadline character varying(20),
    financial_year character varying(20),
    app_code character varying(200),
    category character varying(100),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL,
    package_no character varying(300),
    pe_office character varying(300),
    agency_code character varying(50),
    agency_name character varying(300),
    ministry character varying(300),
    district character varying(100),
    procurement_method character varying(50),
    procuring_entity character varying(500),
    location character varying(150),
    normalized_package_no character varying(300)
);


--
-- Name: award_records_v2; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.award_records_v2 (
    procurement_tender_id character varying(36) NOT NULL,
    source_tender_id character varying(500),
    package_no character varying(300),
    title text,
    contractor_name character varying(300),
    amount_bdt double precision NOT NULL,
    procurement_method character varying(100),
    award_date character varying(20),
    detail_url text,
    agency_code character varying(20),
    district character varying(100),
    pe_office character varying(300),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL,
    tender_id character varying(100),
    estimated_amount_bdt double precision DEFAULT 0,
    agency_confidence double precision DEFAULT 0,
    procuring_entity character varying(500),
    office character varying(300),
    location character varying(150),
    source character varying(50) DEFAULT 'egp'::character varying,
    raw_data json,
    discount_pct double precision,
    npp_ratio double precision,
    normalized_package_no character varying(300),
    date_contract_start date,
    date_contract_completion date,
    date_notification_award date,
    date_contract_signing date,
    contract_duration_days integer,
    canonical_contractor_id uuid
);


--
-- Name: contractors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractors (
    contractor_name character varying(300) NOT NULL,
    total_contracts integer NOT NULL,
    total_amount_bdt double precision NOT NULL,
    agencies_worked json,
    districts_worked json,
    avg_npp double precision NOT NULL,
    first_award_date character varying(20),
    last_award_date character varying(20),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: procurement_lifecycle; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.procurement_lifecycle (
    package_no character varying(300) NOT NULL,
    agency_code character varying(20),
    zone_name character varying(100),
    title text,
    estimated_cost_bdt double precision NOT NULL,
    award_amount_bdt double precision NOT NULL,
    npp_ratio double precision NOT NULL,
    winner character varying(300),
    award_date character varying(20),
    procurement_method character varying(100),
    pe_office character varying(300),
    match_type character varying(20) NOT NULL,
    data_source character varying(10) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL,
    tender_id character varying(100)
);


--
-- Name: procurement_tenders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.procurement_tenders (
    package_no character varying(300) NOT NULL,
    title text,
    agency_code character varying(20),
    zone_id character varying(36),
    pe_office character varying(300),
    procurement_method character varying(100),
    match_type character varying(20) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL,
    normalized_package_no character varying(300)
);


--
-- Name: tenders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenders (
    owner_id character varying(36) NOT NULL,
    tender_id character varying(100) NOT NULL,
    title character varying(500) NOT NULL,
    procuring_entity character varying(255),
    district character varying(100),
    division character varying(100),
    estimated_cost double precision,
    tender_security double precision,
    closing_date timestamp without time zone,
    opening_date timestamp without time zone,
    status public.tenderstatus NOT NULL,
    sor_agency character varying(20) NOT NULL,
    zone character varying(50),
    extracted_data json NOT NULL,
    comparison_results json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL,
    package_no character varying(100),
    invitation_ref character varying(100),
    work_name text,
    description text,
    procuring_entity_district character varying(100),
    ministry character varying(255),
    organization character varying(255),
    department_id character varying(50),
    agency_target character varying(100),
    procurement_method character varying(255),
    regime character varying(20) DEFAULT 'PPR2008'::character varying NOT NULL,
    publication_date timestamp with time zone,
    last_selling_date timestamp with time zone,
    work_period_start timestamp with time zone,
    work_period_end timestamp with time zone,
    estimated_amount_bdt double precision,
    completion_period_days integer,
    is_archived boolean DEFAULT false NOT NULL,
    raw_data json,
    source_file character varying(255),
    _stored_at character varying(50),
    _domain character varying(50),
    app_id character varying(100),
    source character varying(50) DEFAULT 'egp'::character varying NOT NULL,
    tenant_id character varying(36),
    procurement_type character varying(255)
);


--
-- Name: award_full_map; Type: MATERIALIZED VIEW; Schema: public; Owner: -
--

CREATE MATERIALIZED VIEW public.award_full_map AS
 SELECT DISTINCT ON (ar.id) ar.id AS award_id,
    ar.tender_id,
    ar.package_no,
    ar.contractor_name,
    ar.amount_bdt,
    ar.estimated_amount_bdt,
    ar.discount_pct,
    ar.npp_ratio,
    ar.award_date,
    ar.agency_code,
    ar.district,
    ar.pe_office,
    ar.procurement_method,
    ar.source,
    pt.id AS tender_uuid,
    pt.zone_id,
    pt.match_type AS tender_match_type,
    ap.financial_year,
    ap.estimated_cost_bdt AS app_estimate,
    ap.status AS app_status,
    ap.app_code,
    ap.category AS app_category,
    ap.ministry,
    ap.agency_name,
    c.total_contracts,
    c.total_amount_bdt AS contractor_total_bdt,
    c.avg_npp AS contractor_avg_npp,
    c.agencies_worked,
    c.districts_worked,
    pl.estimated_cost_bdt AS life_estimate,
    pl.award_amount_bdt AS life_award,
    pl.npp_ratio AS life_npp,
    pl.winner AS life_winner,
    pl.data_source,
    t.title AS tender_title,
    t.status AS tender_status,
    t.estimated_cost AS tender_estimate,
    t.sor_agency,
    t.zone
   FROM (((((public.award_records_v2 ar
     LEFT JOIN public.procurement_tenders pt ON (((ar.procurement_tender_id)::text = (pt.id)::text)))
     LEFT JOIN public.app_records ap ON (((ap.procurement_tender_id)::text = (ar.procurement_tender_id)::text)))
     LEFT JOIN public.contractors c ON (((ar.contractor_name)::text = (c.contractor_name)::text)))
     LEFT JOIN public.procurement_lifecycle pl ON (((pl.package_no)::text = (ar.package_no)::text)))
     LEFT JOIN public.tenders t ON (((t.tender_id)::text = (ar.tender_id)::text)))
  ORDER BY ar.id, ar.award_date DESC NULLS LAST
  WITH NO DATA;


--
-- Name: ecms_ongoing; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ecms_ongoing (
    id character varying(36) NOT NULL,
    tender_id character varying(50),
    package_no character varying(300) NOT NULL,
    title text,
    pe_office character varying(300),
    agency_code character varying(20),
    procurement_method character varying(100),
    contractor_name character varying(300),
    company_unique_id character varying(50),
    experience_certificate_no character varying(200),
    contract_value_bdt double precision DEFAULT 0,
    completed_value_bdt double precision DEFAULT 0,
    contract_start_date character varying(20),
    contract_end_date character varying(20),
    planned_completion_date character varying(20),
    actual_completion_date character varying(20),
    published_date character varying(20),
    award_date character varying(20),
    completion_status character varying(50),
    work_status character varying(100),
    status character varying(50),
    progress_pct double precision DEFAULT 0,
    completed_on_time boolean,
    district character varying(100),
    source_url text,
    procurement_tender_id character varying(36),
    data_source character varying(50) DEFAULT 'ECMS_ONGOING'::character varying,
    raw_payload jsonb,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    tender_ref_no character varying(300),
    package_name text,
    name_of_work text,
    ministry_division character varying(300),
    organization_name character varying(300),
    pe_name character varying(300),
    procurement_nature character varying(100),
    work_category character varying(200),
    contract_no character varying(200),
    physical_progress_pct double precision DEFAULT 0,
    financial_progress_pct double precision DEFAULT 0,
    physical_progress_date character varying(20),
    financial_progress_date character varying(20),
    is_jvca boolean,
    remarks text,
    comments_by_pe text
);


--
-- Name: staging_app_packages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staging_app_packages (
    staging_id text NOT NULL,
    raw_id text,
    source_family text NOT NULL,
    source_path text,
    package_no text,
    normalized_package_no text,
    tender_id text,
    title text,
    agency_code text,
    district text,
    pe_office text,
    contractor_name text,
    amount_raw text,
    amount_normalized_bdt double precision DEFAULT 0 NOT NULL,
    amount_confidence double precision DEFAULT 0 NOT NULL,
    source_date date,
    confidence_score double precision DEFAULT 0 NOT NULL,
    raw_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    parsed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: app_ecms_award_map; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.app_ecms_award_map AS
 SELECT ap.staging_id AS app_staging_id,
    ap.tender_id AS app_tender_id,
    ap.package_no AS app_package_no,
    "left"(ap.title, 200) AS app_title,
    ap.amount_normalized_bdt AS app_estimate,
    (ap.raw_payload ->> 'ministry'::text) AS app_ministry,
    (ap.raw_payload ->> 'status'::text) AS app_status,
    (ap.raw_payload ->> 'source'::text) AS app_source,
    afm.award_id,
    afm.tender_id AS award_tender_id,
    afm.package_no AS award_package_no,
    afm.contractor_name,
    afm.amount_bdt AS award_amount,
    afm.estimated_amount_bdt AS award_estimate,
    afm.discount_pct,
    afm.npp_ratio,
    afm.award_date,
    afm.agency_code,
    afm.district AS award_district,
    afm.pe_office AS award_pe_office,
    afm.tender_title,
    afm.tender_status,
    afm.financial_year AS award_financial_year,
    afm.app_category,
    afm.ministry AS award_ministry,
    afm.agency_name,
    afm.procurement_method,
    afm.sor_agency,
    afm.zone,
    e.id AS ecms_id,
    e.tender_id AS ecms_tender_id,
    e.package_no AS ecms_package_no,
    "left"(e.title, 200) AS ecms_title,
    e.contractor_name AS ecms_contractor,
    e.contract_value_bdt AS ecms_contract_value,
    e.award_date AS ecms_award_date,
    e.work_status,
    e.completion_status,
    e.progress_pct,
    e.contract_start_date,
    e.contract_end_date,
    e.completed_on_time
   FROM ((public.staging_app_packages ap
     LEFT JOIN public.award_full_map afm ON ((ap.tender_id = (afm.tender_id)::text)))
     LEFT JOIN public.ecms_ongoing e ON ((ap.tender_id = (e.tender_id)::text)));


--
-- Name: app_ecms_award_map_mv; Type: MATERIALIZED VIEW; Schema: public; Owner: -
--

CREATE MATERIALIZED VIEW public.app_ecms_award_map_mv AS
 SELECT app_staging_id,
    app_tender_id,
    app_package_no,
    app_title,
    app_estimate,
    app_ministry,
    app_status,
    app_source,
    award_id,
    award_tender_id,
    award_package_no,
    contractor_name,
    award_amount,
    award_estimate,
    discount_pct,
    npp_ratio,
    award_date,
    agency_code,
    award_district,
    award_pe_office,
    tender_title,
    tender_status,
    award_financial_year,
    app_category,
    award_ministry,
    agency_name,
    procurement_method,
    sor_agency,
    zone,
    ecms_id,
    ecms_tender_id,
    ecms_package_no,
    ecms_title,
    ecms_contractor,
    ecms_contract_value,
    ecms_award_date,
    work_status,
    completion_status,
    progress_pct,
    contract_start_date,
    contract_end_date,
    completed_on_time
   FROM public.app_ecms_award_map
  WITH NO DATA;


--
-- Name: app_tender_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.app_tender_link (
    id integer NOT NULL,
    app_id text NOT NULL,
    pkg_id text NOT NULL,
    app_package_no text,
    tender_id text,
    tender_reference_no text,
    match_confidence numeric,
    match_method text,
    matched_at timestamp without time zone DEFAULT now()
);


--
-- Name: app_tender_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.app_tender_link_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: app_tender_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.app_tender_link_id_seq OWNED BY public.app_tender_link.id;


--
-- Name: app_unmatched_tmp; Type: TABLE; Schema: public; Owner: -
--

CREATE UNLOGGED TABLE public.app_unmatched_tmp (
    canonical_app_id text,
    package_no text,
    norm_pkg text
);


--
-- Name: archived_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.archived_records (
    id character varying(36) NOT NULL,
    tenant_id character varying(36),
    source_table character varying(120) NOT NULL,
    source_id character varying(120) NOT NULL,
    resource_type character varying(100) NOT NULL,
    record_data json NOT NULL,
    archived_at timestamp with time zone NOT NULL,
    delete_after timestamp with time zone
);


--
-- Name: atl_fanout_tmp; Type: TABLE; Schema: public; Owner: -
--

CREATE UNLOGGED TABLE public.atl_fanout_tmp (
    tender_id text,
    n bigint
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id character varying(36) NOT NULL,
    tenant_id character varying(36),
    actor_id character varying(36),
    actor_type character varying(50) NOT NULL,
    action character varying(120) NOT NULL,
    resource_type character varying(100),
    resource_id character varying(120),
    status character varying(30) NOT NULL,
    ip_address character varying(64),
    user_agent text,
    request_id character varying(64),
    trace_id character varying(64),
    metadata_json json NOT NULL,
    created_at timestamp with time zone NOT NULL,
    previous_hash character varying(64),
    entry_hash character varying(64)
);


--
-- Name: award_intelligence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.award_intelligence (
    agency_code character varying(20),
    fiscal_year character varying(20),
    quarter integer NOT NULL,
    total_contracts integer NOT NULL,
    total_amount_bdt double precision NOT NULL,
    avg_npp double precision,
    avg_contract_amount double precision NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: award_pkg_map; Type: TABLE; Schema: public; Owner: -
--

CREATE UNLOGGED TABLE public.award_pkg_map (
    tender_id text,
    package_no text
);


--
-- Name: award_pkg_src; Type: TABLE; Schema: public; Owner: -
--

CREATE UNLOGGED TABLE public.award_pkg_src (
    award_key text,
    tender_id text,
    package_no text
);


--
-- Name: award_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.award_records (
    source character varying(50) NOT NULL,
    source_id character varying(100) NOT NULL,
    tender_id character varying(100),
    award_date timestamp without time zone,
    award_notice_no character varying(100),
    procuring_entity character varying(255) NOT NULL,
    entity_type character varying(50),
    ministry character varying(255),
    work_name character varying(500) NOT NULL,
    work_type character varying(100),
    district character varying(100),
    division character varying(100),
    estimated_cost double precision,
    awarded_amount double precision NOT NULL,
    currency character varying(10) NOT NULL,
    contractor_name character varying(255) NOT NULL,
    contractor_license character varying(100),
    contractor_address character varying(500),
    contract_period_days integer,
    work_start_date timestamp without time zone,
    work_completion_date timestamp without time zone,
    raw_data json NOT NULL,
    boq_items json NOT NULL,
    discount_pct double precision,
    unit_rates json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: awards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.awards (
    id character varying(36) NOT NULL,
    tenant_id character varying(36),
    tender_id character varying(100),
    award_amount numeric(16,2),
    amount_bdt numeric(16,2),
    award_date date,
    contract_start_date date,
    contract_end_date date,
    work_status character varying(50),
    contractor_name character varying(255),
    contractor_id character varying(100),
    winner character varying(255),
    company_id character varying(100),
    experience_cert_no character varying(100),
    procurement_nature character varying(100),
    procurement_type character varying(255),
    agency character varying(255),
    raw_data json,
    source_file character varying(255),
    created_at timestamp with time zone
);


--
-- Name: bid_price_models; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bid_price_models (
    id character varying(36) NOT NULL,
    model_version character varying(50) NOT NULL,
    model_blob bytea,
    feature_importance_json json,
    validation_rmse double precision,
    validation_r2 double precision,
    training_rmse double precision,
    training_r2 double precision,
    training_samples integer,
    is_active boolean DEFAULT false NOT NULL,
    trained_at timestamp with time zone,
    deployed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: boq_comparisons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.boq_comparisons (
    user_id character varying(36) NOT NULL,
    tender_id character varying(36),
    boq_file_id character varying(100) NOT NULL,
    sor_agency character varying(20) NOT NULL,
    zone character varying(50),
    total_items integer NOT NULL,
    matches integer NOT NULL,
    variances integer NOT NULL,
    mismatches integer NOT NULL,
    below_sor integer NOT NULL,
    total_sor_amount double precision,
    total_quoted_amount double precision,
    discount_pct double precision,
    summary_by_work_type json NOT NULL,
    excel_path character varying(500),
    docx_path character varying(500),
    tenderai_dir character varying(500),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL,
    upload_object_key character varying(500),
    excel_object_key character varying(500),
    docx_object_key character varying(500)
);


--
-- Name: boq_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.boq_items (
    tender_id character varying(36) NOT NULL,
    item_no character varying(50),
    code character varying(100),
    description character varying(1000) NOT NULL,
    unit character varying(50),
    quantity double precision,
    quoted_rate double precision,
    sor_rate double precision,
    sor_code character varying(100),
    diff double precision,
    pct_diff double precision,
    flag character varying(50),
    work_type character varying(100),
    section character varying(100),
    agency character varying(20),
    attributes json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: boq_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.boq_jobs (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    kind character varying(20) NOT NULL,
    status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    progress integer DEFAULT 0 NOT NULL,
    params json NOT NULL,
    comparison_id character varying(36),
    result_meta json,
    error character varying(2000),
    celery_task_id character varying(155),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: bwdb_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bwdb_alerts (
    tender_id character varying(300) NOT NULL,
    title text,
    value double precision NOT NULL,
    entity character varying(500),
    deadline character varying(100),
    sent_at character varying(50) NOT NULL,
    recipient character varying(300) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: canonical_app_packages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.canonical_app_packages (
    canonical_app_id text NOT NULL,
    canonical_package_key text NOT NULL,
    package_no text,
    tender_id text,
    title text,
    agency_code text,
    district text,
    pe_office text,
    financial_year text,
    estimated_cost_bdt double precision DEFAULT 0 NOT NULL,
    confidence_score double precision DEFAULT 0 NOT NULL,
    source_ref jsonb DEFAULT '{}'::jsonb NOT NULL,
    rebuilt_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: canonical_awards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.canonical_awards (
    canonical_award_id text NOT NULL,
    canonical_contract_id text,
    canonical_package_key text NOT NULL,
    canonical_contractor_id text,
    package_no text,
    tender_id text,
    title text,
    agency_code text,
    district text,
    contractor_name text,
    award_date date,
    award_amount_bdt double precision DEFAULT 0 NOT NULL,
    confidence_score double precision DEFAULT 0 NOT NULL,
    source_ref jsonb DEFAULT '{}'::jsonb NOT NULL,
    rebuilt_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: canonical_contractor_aliases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.canonical_contractor_aliases (
    alias_key text NOT NULL,
    canonical_contractor_id text NOT NULL,
    alias_name text NOT NULL,
    normalized_alias text NOT NULL,
    source text DEFAULT 'derived'::text NOT NULL,
    confidence double precision DEFAULT 0.8 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: canonical_contractor_dna; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.canonical_contractor_dna (
    canonical_contractor_id text NOT NULL,
    contractor_name text,
    normalized_name text,
    aliases jsonb DEFAULT '[]'::jsonb NOT NULL,
    jv_members jsonb DEFAULT '[]'::jsonb NOT NULL,
    total_awarded_5yr_bdt double precision DEFAULT 0 NOT NULL,
    annual_turnover_estimate_bdt double precision DEFAULT 0 NOT NULL,
    work_in_hand_bdt double precision DEFAULT 0 NOT NULL,
    available_capacity_bdt double precision DEFAULT 0 NOT NULL,
    tender_capacity_bdt double precision DEFAULT 0 NOT NULL,
    total_bids integer DEFAULT 0 NOT NULL,
    total_wins integer DEFAULT 0 NOT NULL,
    win_rate double precision DEFAULT 0 NOT NULL,
    late_delivery_rate double precision DEFAULT 0 NOT NULL,
    on_time_rate double precision DEFAULT 0 NOT NULL,
    top_agencies jsonb DEFAULT '[]'::jsonb NOT NULL,
    top_districts jsonb DEFAULT '[]'::jsonb NOT NULL,
    work_type_mix jsonb DEFAULT '{}'::jsonb NOT NULL,
    reliability_score double precision DEFAULT 0 NOT NULL,
    financial_strength_score double precision DEFAULT 0 NOT NULL,
    capacity_score double precision DEFAULT 0 NOT NULL,
    competition_score double precision DEFAULT 0 NOT NULL,
    overall_dna_score double precision DEFAULT 0 NOT NULL,
    data_confidence_score double precision DEFAULT 0 NOT NULL,
    rebuilt_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: canonical_contractor_jv_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.canonical_contractor_jv_members (
    jv_canonical_contractor_id text NOT NULL,
    member_canonical_contractor_id text NOT NULL,
    member_name text NOT NULL,
    normalized_member_name text NOT NULL,
    share_pct double precision,
    confidence double precision DEFAULT 0.5 NOT NULL
);


--
-- Name: canonical_contractors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.canonical_contractors (
    canonical_contractor_id text NOT NULL,
    canonical_name text NOT NULL,
    display_name text,
    is_joint_venture boolean DEFAULT false NOT NULL,
    jv_member_count integer DEFAULT 0 NOT NULL,
    total_award_amount_bdt double precision DEFAULT 0 NOT NULL,
    last_5yr_awarded_amount_bdt double precision DEFAULT 0 NOT NULL,
    work_in_hand_bdt double precision DEFAULT 0 NOT NULL,
    estimated_turnover_bdt double precision DEFAULT 0 NOT NULL,
    tender_capacity_bdt double precision DEFAULT 0 NOT NULL,
    total_bids integer DEFAULT 0 NOT NULL,
    total_wins integer DEFAULT 0 NOT NULL,
    win_rate double precision DEFAULT 0 NOT NULL,
    agencies jsonb DEFAULT '{}'::jsonb NOT NULL,
    districts jsonb DEFAULT '{}'::jsonb NOT NULL,
    work_type_mix jsonb DEFAULT '{}'::jsonb NOT NULL,
    reliability_score double precision DEFAULT 0 NOT NULL,
    data_confidence_score double precision DEFAULT 0 NOT NULL,
    source_counts jsonb DEFAULT '{}'::jsonb NOT NULL,
    rebuilt_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: canonical_contracts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.canonical_contracts (
    canonical_contract_id text NOT NULL,
    canonical_package_key text NOT NULL,
    canonical_contractor_id text,
    source_table text NOT NULL,
    source_id text NOT NULL,
    tender_id text,
    package_no text,
    title text,
    agency_code text,
    district text,
    contractor_name text,
    contract_date date,
    amount_original double precision DEFAULT 0 NOT NULL,
    amount_normalized_bdt double precision DEFAULT 0 NOT NULL,
    amount_unit text DEFAULT 'bdt'::text NOT NULL,
    amount_confidence double precision DEFAULT 0 NOT NULL,
    amount_warning text,
    status text,
    is_ongoing boolean DEFAULT false NOT NULL,
    progress_pct double precision DEFAULT 0 NOT NULL,
    raw_ref jsonb DEFAULT '{}'::jsonb NOT NULL,
    rebuilt_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: canonical_identity_repair_queue; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.canonical_identity_repair_queue (
    repair_id text NOT NULL,
    entity_type text NOT NULL,
    entity_key text NOT NULL,
    source_table text NOT NULL,
    source_id text NOT NULL,
    issue_type text NOT NULL,
    confidence double precision DEFAULT 0 NOT NULL,
    severity text DEFAULT 'medium'::text NOT NULL,
    status text DEFAULT 'open'::text NOT NULL,
    suggested_action text,
    evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    resolved_at timestamp with time zone
);


--
-- Name: canonical_tenders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.canonical_tenders (
    canonical_package_key text NOT NULL,
    package_no text,
    normalized_package_no text,
    tender_id text,
    title text,
    agency_code text,
    district text,
    pe_office text,
    estimated_cost_bdt double precision DEFAULT 0 NOT NULL,
    source_counts jsonb DEFAULT '{}'::jsonb NOT NULL,
    identity_confidence double precision DEFAULT 0 NOT NULL,
    rebuilt_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: circulars; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.circulars (
    id character varying(36) NOT NULL,
    circular_no character varying(100) NOT NULL,
    issuing_authority character varying(255),
    issue_date date NOT NULL,
    title character varying(255) NOT NULL,
    summary text,
    affects_rule_ids json NOT NULL,
    source_url text,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: clauses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clauses (
    id character varying(36) NOT NULL,
    regulation_version_id character varying(36) NOT NULL,
    clause_ref character varying(50) NOT NULL,
    title character varying(255),
    full_text text,
    page_ref character varying(50),
    created_at timestamp with time zone NOT NULL
);


--
-- Name: clean_intel_agency_award_pattern; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_agency_award_pattern (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_agency_award_pattern_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_agency_award_pattern_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_agency_award_pattern_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_agency_award_pattern_id_seq OWNED BY public.clean_intel_agency_award_pattern.id;


--
-- Name: clean_intel_agency_bidder_statistics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_agency_bidder_statistics (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_agency_bidder_statistics_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_agency_bidder_statistics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_agency_bidder_statistics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_agency_bidder_statistics_id_seq OWNED BY public.clean_intel_agency_bidder_statistics.id;


--
-- Name: clean_intel_agency_budget; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_agency_budget (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_agency_budget_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_agency_budget_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_agency_budget_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_agency_budget_id_seq OWNED BY public.clean_intel_agency_budget.id;


--
-- Name: clean_intel_agency_contractor_network; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_agency_contractor_network (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_agency_contractor_network_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_agency_contractor_network_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_agency_contractor_network_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_agency_contractor_network_id_seq OWNED BY public.clean_intel_agency_contractor_network.id;


--
-- Name: clean_intel_agency_delay_index; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_agency_delay_index (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_agency_delay_index_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_agency_delay_index_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_agency_delay_index_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_agency_delay_index_id_seq OWNED BY public.clean_intel_agency_delay_index.id;


--
-- Name: clean_intel_agency_office_map; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_agency_office_map (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_agency_office_map_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_agency_office_map_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_agency_office_map_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_agency_office_map_id_seq OWNED BY public.clean_intel_agency_office_map.id;


--
-- Name: clean_intel_agency_profile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_agency_profile (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_agency_profile_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_agency_profile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_agency_profile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_agency_profile_id_seq OWNED BY public.clean_intel_agency_profile.id;


--
-- Name: clean_intel_app_structure_summary; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_app_structure_summary (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_app_structure_summary_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_app_structure_summary_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_app_structure_summary_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_app_structure_summary_id_seq OWNED BY public.clean_intel_app_structure_summary.id;


--
-- Name: clean_intel_award_by_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_award_by_category (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_award_by_category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_award_by_category_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_award_by_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_award_by_category_id_seq OWNED BY public.clean_intel_award_by_category.id;


--
-- Name: clean_intel_award_by_region; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_award_by_region (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_award_by_region_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_award_by_region_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_award_by_region_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_award_by_region_id_seq OWNED BY public.clean_intel_award_by_region.id;


--
-- Name: clean_intel_award_competitiveness; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_award_competitiveness (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_award_competitiveness_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_award_competitiveness_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_award_competitiveness_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_award_competitiveness_id_seq OWNED BY public.clean_intel_award_competitiveness.id;


--
-- Name: clean_intel_award_delay; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_award_delay (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_award_delay_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_award_delay_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_award_delay_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_award_delay_id_seq OWNED BY public.clean_intel_award_delay.id;


--
-- Name: clean_intel_award_summary; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_award_summary (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_award_summary_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_award_summary_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_award_summary_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_award_summary_id_seq OWNED BY public.clean_intel_award_summary.id;


--
-- Name: clean_intel_bid_discount_analysis; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_bid_discount_analysis (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_bid_discount_analysis_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_bid_discount_analysis_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_bid_discount_analysis_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_bid_discount_analysis_id_seq OWNED BY public.clean_intel_bid_discount_analysis.id;


--
-- Name: clean_intel_competitor_bid_aggressiveness; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_competitor_bid_aggressiveness (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_competitor_bid_aggressiveness_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_competitor_bid_aggressiveness_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_competitor_bid_aggressiveness_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_competitor_bid_aggressiveness_id_seq OWNED BY public.clean_intel_competitor_bid_aggressiveness.id;


--
-- Name: clean_intel_competitor_discount_pattern; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_competitor_discount_pattern (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_competitor_discount_pattern_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_competitor_discount_pattern_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_competitor_discount_pattern_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_competitor_discount_pattern_id_seq OWNED BY public.clean_intel_competitor_discount_pattern.id;


--
-- Name: clean_intel_competitor_market_share; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_competitor_market_share (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_competitor_market_share_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_competitor_market_share_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_competitor_market_share_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_competitor_market_share_id_seq OWNED BY public.clean_intel_competitor_market_share.id;


--
-- Name: clean_intel_competitor_profile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_competitor_profile (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_competitor_profile_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_competitor_profile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_competitor_profile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_competitor_profile_id_seq OWNED BY public.clean_intel_competitor_profile.id;


--
-- Name: clean_intel_competitor_win_pattern; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_competitor_win_pattern (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_competitor_win_pattern_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_competitor_win_pattern_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_competitor_win_pattern_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_competitor_win_pattern_id_seq OWNED BY public.clean_intel_competitor_win_pattern.id;


--
-- Name: clean_intel_contractor_competitiveness; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_contractor_competitiveness (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_contractor_competitiveness_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_contractor_competitiveness_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_contractor_competitiveness_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_contractor_competitiveness_id_seq OWNED BY public.clean_intel_contractor_competitiveness.id;


--
-- Name: clean_intel_contractor_competitor_network; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_contractor_competitor_network (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_contractor_competitor_network_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_contractor_competitor_network_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_contractor_competitor_network_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_contractor_competitor_network_id_seq OWNED BY public.clean_intel_contractor_competitor_network.id;


--
-- Name: clean_intel_contractor_dna; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_contractor_dna (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_contractor_dna_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_contractor_dna_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_contractor_dna_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_contractor_dna_id_seq OWNED BY public.clean_intel_contractor_dna.id;


--
-- Name: clean_intel_contractor_experience_enriched; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_contractor_experience_enriched (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_contractor_experience_enriched_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_contractor_experience_enriched_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_contractor_experience_enriched_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_contractor_experience_enriched_id_seq OWNED BY public.clean_intel_contractor_experience_enriched.id;


--
-- Name: clean_intel_contractor_geographic_preference; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_contractor_geographic_preference (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_contractor_geographic_preference_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_contractor_geographic_preference_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_contractor_geographic_preference_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_contractor_geographic_preference_id_seq OWNED BY public.clean_intel_contractor_geographic_preference.id;


--
-- Name: clean_intel_contractor_growth_trend; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_contractor_growth_trend (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_contractor_growth_trend_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_contractor_growth_trend_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_contractor_growth_trend_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_contractor_growth_trend_id_seq OWNED BY public.clean_intel_contractor_growth_trend.id;


--
-- Name: clean_intel_contractor_heatmap; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_contractor_heatmap (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_contractor_heatmap_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_contractor_heatmap_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_contractor_heatmap_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_contractor_heatmap_id_seq OWNED BY public.clean_intel_contractor_heatmap.id;


--
-- Name: clean_intel_contractor_profile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_contractor_profile (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_contractor_profile_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_contractor_profile_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_contractor_profile_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_contractor_profile_id_seq OWNED BY public.clean_intel_contractor_profile.id;


--
-- Name: clean_intel_contractor_recommendation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_contractor_recommendation (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_contractor_recommendation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_contractor_recommendation_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_contractor_recommendation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_contractor_recommendation_id_seq OWNED BY public.clean_intel_contractor_recommendation.id;


--
-- Name: clean_intel_contractor_risk; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_contractor_risk (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_contractor_risk_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_contractor_risk_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_contractor_risk_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_contractor_risk_id_seq OWNED BY public.clean_intel_contractor_risk.id;


--
-- Name: clean_intel_contractor_sector_preference; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_contractor_sector_preference (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_contractor_sector_preference_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_contractor_sector_preference_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_contractor_sector_preference_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_contractor_sector_preference_id_seq OWNED BY public.clean_intel_contractor_sector_preference.id;


--
-- Name: clean_intel_contractor_success_rate; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_contractor_success_rate (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_contractor_success_rate_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_contractor_success_rate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_contractor_success_rate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_contractor_success_rate_id_seq OWNED BY public.clean_intel_contractor_success_rate.id;


--
-- Name: clean_intel_district_market; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_district_market (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_district_market_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_district_market_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_district_market_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_district_market_id_seq OWNED BY public.clean_intel_district_market.id;


--
-- Name: clean_intel_division_market; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_division_market (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_division_market_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_division_market_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_division_market_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_division_market_id_seq OWNED BY public.clean_intel_division_market.id;


--
-- Name: clean_intel_estimated_margin; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_estimated_margin (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_estimated_margin_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_estimated_margin_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_estimated_margin_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_estimated_margin_id_seq OWNED BY public.clean_intel_estimated_margin.id;


--
-- Name: clean_intel_expected_discount; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_expected_discount (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_expected_discount_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_expected_discount_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_expected_discount_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_expected_discount_id_seq OWNED BY public.clean_intel_expected_discount.id;


--
-- Name: clean_intel_feature_award; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_feature_award (
    data jsonb
);


--
-- Name: clean_intel_feature_contractor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_feature_contractor (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_feature_contractor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_feature_contractor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_feature_contractor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_feature_contractor_id_seq OWNED BY public.clean_intel_feature_contractor.id;


--
-- Name: clean_intel_feature_market; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_feature_market (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_feature_market_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_feature_market_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_feature_market_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_feature_market_id_seq OWNED BY public.clean_intel_feature_market.id;


--
-- Name: clean_intel_feature_tender; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_feature_tender (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_feature_tender_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_feature_tender_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_feature_tender_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_feature_tender_id_seq OWNED BY public.clean_intel_feature_tender.id;


--
-- Name: clean_intel_likely_bidders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_likely_bidders (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_likely_bidders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_likely_bidders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_likely_bidders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_likely_bidders_id_seq OWNED BY public.clean_intel_likely_bidders.id;


--
-- Name: clean_intel_likely_winner; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_likely_winner (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_likely_winner_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_likely_winner_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_likely_winner_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_likely_winner_id_seq OWNED BY public.clean_intel_likely_winner.id;


--
-- Name: clean_intel_market_price_index; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_market_price_index (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_market_price_index_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_market_price_index_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_market_price_index_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_market_price_index_id_seq OWNED BY public.clean_intel_market_price_index.id;


--
-- Name: clean_intel_market_snapshot; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_market_snapshot (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_market_snapshot_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_market_snapshot_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_market_snapshot_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_market_snapshot_id_seq OWNED BY public.clean_intel_market_snapshot.id;


--
-- Name: clean_intel_operational_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_operational_metrics (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_operational_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_operational_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_operational_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_operational_metrics_id_seq OWNED BY public.clean_intel_operational_metrics.id;


--
-- Name: clean_intel_regional_discount; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_regional_discount (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_regional_discount_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_regional_discount_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_regional_discount_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_regional_discount_id_seq OWNED BY public.clean_intel_regional_discount.id;


--
-- Name: clean_intel_regional_price_index; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_regional_price_index (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_regional_price_index_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_regional_price_index_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_regional_price_index_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_regional_price_index_id_seq OWNED BY public.clean_intel_regional_price_index.id;


--
-- Name: clean_intel_repeat_winner_analysis; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_repeat_winner_analysis (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_repeat_winner_analysis_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_repeat_winner_analysis_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_repeat_winner_analysis_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_repeat_winner_analysis_id_seq OWNED BY public.clean_intel_repeat_winner_analysis.id;


--
-- Name: clean_intel_tender_anomaly_detection; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_tender_anomaly_detection (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_tender_anomaly_detection_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_tender_anomaly_detection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_tender_anomaly_detection_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_tender_anomaly_detection_id_seq OWNED BY public.clean_intel_tender_anomaly_detection.id;


--
-- Name: clean_intel_tender_complexity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_tender_complexity (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_tender_complexity_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_tender_complexity_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_tender_complexity_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_tender_complexity_id_seq OWNED BY public.clean_intel_tender_complexity.id;


--
-- Name: clean_intel_tender_risk_score; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_tender_risk_score (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_tender_risk_score_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_tender_risk_score_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_tender_risk_score_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_tender_risk_score_id_seq OWNED BY public.clean_intel_tender_risk_score.id;


--
-- Name: clean_intel_tender_seasonality; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_tender_seasonality (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_tender_seasonality_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_tender_seasonality_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_tender_seasonality_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_tender_seasonality_id_seq OWNED BY public.clean_intel_tender_seasonality.id;


--
-- Name: clean_intel_tender_summary; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_tender_summary (
    id bigint NOT NULL,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_tender_summary_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.clean_intel_tender_summary_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: clean_intel_tender_summary_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.clean_intel_tender_summary_id_seq OWNED BY public.clean_intel_tender_summary.id;


--
-- Name: clean_intel_works_agencies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_works_agencies (
    id bigint,
    key_id character varying(20),
    data jsonb
);


--
-- Name: clean_intel_works_award_trends; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_works_award_trends (
    id bigint,
    key_id text,
    data jsonb
);


--
-- Name: clean_intel_works_contractors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_works_contractors (
    id bigint,
    key_id character varying(300),
    data jsonb
);


--
-- Name: clean_intel_works_lifecycle; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_works_lifecycle (
    id bigint,
    key_id character varying(300),
    data jsonb
);


--
-- Name: clean_intel_works_zones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.clean_intel_works_zones (
    id bigint,
    key_id character varying(100),
    data jsonb
);


--
-- Name: client_priority_states; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.client_priority_states (
    id character varying(36) NOT NULL,
    tenant_id character varying(36) NOT NULL,
    tender_id character varying(100) NOT NULL,
    priority_score integer,
    priority_tier character varying(20),
    workload_score integer,
    need_for_work_score integer,
    financial_headroom numeric(16,2),
    recommendation character varying(50),
    advice_summary text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: client_subscriptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.client_subscriptions (
    id character varying(36) NOT NULL,
    tenant_id character varying(36) NOT NULL,
    plan_id character varying(36) NOT NULL,
    status character varying(20),
    tender_quota_used integer,
    tender_quota_limit integer,
    quota_reset_date timestamp with time zone,
    billing_cycle_start timestamp with time zone,
    billing_cycle_end timestamp with time zone,
    auto_renew boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: competitor_awards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.competitor_awards (
    competitor_id character varying(36) NOT NULL,
    award_id character varying(36) NOT NULL,
    role character varying(50) NOT NULL,
    is_jv boolean NOT NULL,
    jv_partners json NOT NULL,
    bid_amount double precision,
    share_pct double precision,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: competitor_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.competitor_profiles (
    name character varying(255) NOT NULL,
    normalized_name character varying(255) NOT NULL,
    license_number character varying(100),
    address character varying(500),
    district character varying(100),
    division character varying(100),
    contact_person character varying(255),
    phone character varying(50),
    email character varying(255),
    website character varying(255),
    entity_type character varying(50),
    category character varying(50),
    specializations json NOT NULL,
    total_awards integer NOT NULL,
    total_awarded_amount double precision NOT NULL,
    avg_discount_pct double precision,
    avg_project_size double precision,
    first_award_date timestamp without time zone,
    last_award_date timestamp without time zone,
    active_districts json NOT NULL,
    work_types json NOT NULL,
    predicted_win_probability double precision,
    predicted_price_range json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: compliance_checks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.compliance_checks (
    id character varying(36) NOT NULL,
    agent_result_id character varying(36),
    tender_id character varying(100),
    check_name character varying(255) NOT NULL,
    check_type character varying(50),
    passed boolean,
    score double precision,
    max_score double precision,
    details text,
    recommendation text,
    created_at timestamp with time zone
);


--
-- Name: contractor_agency_experience; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractor_agency_experience (
    id character varying(36) NOT NULL,
    contractor_name character varying(300) NOT NULL,
    agency_code character varying(100) NOT NULL,
    total_projects integer DEFAULT 0,
    completed_projects integer DEFAULT 0,
    ongoing_projects integer DEFAULT 0,
    total_value_bdt double precision DEFAULT 0,
    avg_contract_value double precision DEFAULT 0,
    avg_delay_days double precision DEFAULT 0,
    on_time_rate double precision DEFAULT 0,
    first_project_date character varying(20),
    last_project_date character varying(20)
);


--
-- Name: contractor_capacity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractor_capacity (
    id character varying(36) NOT NULL,
    contractor_name character varying(300) NOT NULL,
    total_contracts integer DEFAULT 0 NOT NULL,
    total_award_value_bdt double precision DEFAULT 0,
    max_single_contract_bdt double precision DEFAULT 0,
    avg_contract_size_bdt double precision DEFAULT 0,
    active_districts json DEFAULT '[]'::json,
    active_agencies json DEFAULT '[]'::json,
    work_types json DEFAULT '[]'::json,
    project_capacity_score double precision DEFAULT 0,
    geographic_reach_score double precision DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    concurrent_projects integer DEFAULT 0,
    current_workload_bdt double precision DEFAULT 0,
    available_capacity_score double precision DEFAULT 0
);


--
-- Name: contractor_district_experience; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractor_district_experience (
    id character varying(36) NOT NULL,
    contractor_name character varying(300) NOT NULL,
    district character varying(100) NOT NULL,
    total_projects integer DEFAULT 0,
    completed_projects integer DEFAULT 0,
    total_value_bdt double precision DEFAULT 0,
    avg_contract_value double precision DEFAULT 0
);


--
-- Name: contractor_dna; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractor_dna (
    contractor_id character varying(36) NOT NULL,
    total_contracts integer NOT NULL,
    total_amount_bdt double precision NOT NULL,
    avg_award_bdt double precision NOT NULL,
    agencies_worked integer NOT NULL,
    districts_worked integer NOT NULL,
    preferred_agency character varying(20),
    preferred_zone character varying(100),
    avg_npp double precision NOT NULL,
    npp_volatility double precision NOT NULL,
    win_rate double precision NOT NULL,
    avg_discount_pct double precision NOT NULL,
    first_award_date character varying(20),
    last_award_date character varying(20),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL,
    completion_rate double precision DEFAULT 0,
    on_time_rate double precision DEFAULT 0,
    avg_delay_days double precision DEFAULT 0,
    total_experience_contracts integer DEFAULT 0,
    total_experience_value_bdt double precision DEFAULT 0,
    health_score double precision,
    max_contract_value double precision DEFAULT 0,
    ongoing_projects integer DEFAULT 0,
    delayed_projects integer DEFAULT 0,
    execution_score double precision DEFAULT 0,
    reliability_score double precision DEFAULT 0,
    contractor_name character varying(512),
    slug character varying(512),
    years_active json,
    procurement_type_breakdown json,
    agencies_json json,
    win_probability_json json,
    top_agency_wins integer
);


--
-- Name: contractor_dna_v2; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractor_dna_v2 (
    id character varying(36) NOT NULL,
    contractor_id character varying(36) NOT NULL,
    contractor_name character varying(300) NOT NULL,
    total_bids integer DEFAULT 0,
    total_wins integer DEFAULT 0,
    win_rate double precision DEFAULT 0.0,
    avg_discount double precision DEFAULT 0.0,
    discount_stddev double precision DEFAULT 0.0,
    avg_rank double precision DEFAULT 0.0,
    responsive_rate double precision DEFAULT 0.0,
    slt_rate double precision DEFAULT 0.0,
    non_responsive_rate double precision DEFAULT 0.0,
    agency_affinity jsonb DEFAULT '{}'::jsonb,
    zone_affinity jsonb DEFAULT '{}'::jsonb,
    project_type_affinity jsonb DEFAULT '{}'::jsonb,
    total_award_amount_bdt double precision DEFAULT 0.0,
    avg_award_amount_bdt double precision DEFAULT 0.0,
    nppi_score double precision DEFAULT 0.0,
    aggression_index double precision DEFAULT 0.0,
    reliability_index double precision DEFAULT 0.0,
    adaptation_score double precision DEFAULT 0.0,
    health_score double precision DEFAULT 0.0,
    last_rebuilt_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: contractor_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractor_documents (
    contractor_id character varying(36) NOT NULL,
    doc_category character varying(100) NOT NULL,
    doc_type character varying(50) NOT NULL,
    filename character varying(500) NOT NULL,
    file_path character varying(500) NOT NULL,
    file_size integer NOT NULL,
    mime_type character varying(100),
    extracted_text text,
    extracted_data json,
    storage_key character varying(500),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: contractor_execution_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractor_execution_history (
    id character varying(36) NOT NULL,
    contractor_name character varying(300) NOT NULL,
    package_no character varying(200),
    title text,
    agency_code character varying(200),
    district character varying(200),
    procurement_method character varying(200),
    contract_value_bdt double precision,
    completed_value_bdt double precision,
    contract_start_date character varying(30),
    contract_end_date character varying(30),
    planned_completion_date character varying(30),
    actual_completion_date character varying(30),
    delay_days integer,
    completion_status character varying(100),
    work_status character varying(100),
    progress_pct double precision,
    completed_on_time boolean,
    experience_certificate_no character varying(300),
    is_jvca boolean,
    source character varying(30),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: contractor_finance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractor_finance (
    id character varying(36) NOT NULL,
    contractor_name character varying(300) NOT NULL,
    total_award_value_bdt double precision DEFAULT 0,
    total_experience_value_bdt double precision DEFAULT 0,
    annual_turnover_estimate_bdt double precision DEFAULT 0,
    avg_project_value_bdt double precision DEFAULT 0,
    max_project_value_bdt double precision DEFAULT 0,
    min_project_value_bdt double precision DEFAULT 0,
    project_value_std_dev double precision DEFAULT 0,
    financial_stability_score double precision DEFAULT 0,
    estimated_liquid_assets_bdt double precision DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    financial_exposure_bdt double precision DEFAULT 0
);


--
-- Name: contractor_name_normalization; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.contractor_name_normalization AS
 SELECT id AS contractor_id,
    contractor_name AS original_name,
    public.normalize_contractor_name((contractor_name)::text) AS normalized_name,
    count(*) OVER (PARTITION BY (public.normalize_contractor_name((contractor_name)::text))) AS duplicate_count
   FROM public.contractors c;


--
-- Name: contractor_work_similarity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contractor_work_similarity (
    id character varying(36) NOT NULL,
    contractor_name character varying(300) NOT NULL,
    work_type character varying(100) NOT NULL,
    keyword character varying(100) NOT NULL,
    total_projects integer DEFAULT 0,
    total_value_bdt double precision DEFAULT 0,
    avg_contract_value double precision DEFAULT 0,
    completion_rate double precision DEFAULT 0
);


--
-- Name: crawl_change_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crawl_change_log (
    id bigint NOT NULL,
    table_name character varying(100) NOT NULL,
    record_id character varying(100),
    change_type character varying(20) NOT NULL,
    previous_data jsonb,
    new_data jsonb,
    changed_fields jsonb,
    detected_at timestamp with time zone DEFAULT now()
);


--
-- Name: crawl_change_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.crawl_change_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: crawl_change_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.crawl_change_log_id_seq OWNED BY public.crawl_change_log.id;


--
-- Name: crawl_checkpoints; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crawl_checkpoints (
    id bigint NOT NULL,
    plugin character varying(100) NOT NULL,
    checkpoint_key character varying(200) NOT NULL,
    data jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: crawl_checkpoints_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.crawl_checkpoints_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: crawl_checkpoints_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.crawl_checkpoints_id_seq OWNED BY public.crawl_checkpoints.id;


--
-- Name: crawl_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crawl_documents (
    id bigint NOT NULL,
    tender_id character varying(50) NOT NULL,
    doc_type character varying(50) NOT NULL,
    filename character varying(255) NOT NULL,
    file_path character varying(500) NOT NULL,
    file_size bigint DEFAULT 0,
    file_hash character varying(64),
    source_url text,
    minio_path character varying(500),
    downloaded_at timestamp with time zone DEFAULT now(),
    metadata jsonb
);


--
-- Name: crawl_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.crawl_documents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: crawl_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.crawl_documents_id_seq OWNED BY public.crawl_documents.id;


--
-- Name: crawl_errors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crawl_errors (
    id bigint NOT NULL,
    run_id character varying(50),
    plugin character varying(100) NOT NULL,
    error_type character varying(100) NOT NULL,
    error_message text NOT NULL,
    url text,
    traceback text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: crawl_errors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.crawl_errors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: crawl_errors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.crawl_errors_id_seq OWNED BY public.crawl_errors.id;


--
-- Name: crawl_heartbeats; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crawl_heartbeats (
    worker_id character varying(100) NOT NULL,
    status character varying(50) DEFAULT 'idle'::character varying NOT NULL,
    last_beat timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    metadata jsonb,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: crawl_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crawl_jobs (
    id bigint NOT NULL,
    plugin character varying(100) NOT NULL,
    run_id character varying(50) NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    pages_done integer DEFAULT 0,
    items_done integer DEFAULT 0,
    items_skipped integer DEFAULT 0,
    items_failed integer DEFAULT 0,
    error text,
    config jsonb,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: crawl_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.crawl_jobs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: crawl_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.crawl_jobs_id_seq OWNED BY public.crawl_jobs.id;


--
-- Name: crawl_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crawl_log (
    id integer NOT NULL,
    plugin text,
    status text,
    pages_done integer DEFAULT 0,
    items_done integer DEFAULT 0,
    error text,
    started_at timestamp without time zone DEFAULT now(),
    finished_at timestamp without time zone
);


--
-- Name: crawl_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.crawl_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: crawl_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.crawl_log_id_seq OWNED BY public.crawl_log.id;


--
-- Name: data_quality_checks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_quality_checks (
    id integer NOT NULL,
    check_name character varying(100) NOT NULL,
    check_description text,
    check_query text NOT NULL,
    threshold_violation integer DEFAULT 1000 NOT NULL,
    last_run timestamp without time zone,
    violation_count integer DEFAULT 0,
    severity character varying(20) DEFAULT 'warning'::character varying NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    CONSTRAINT data_quality_checks_severity_check CHECK (((severity)::text = ANY ((ARRAY['warning'::character varying, 'critical'::character varying, 'info'::character varying])::text[])))
);


--
-- Name: data_quality_checks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.data_quality_checks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: data_quality_checks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.data_quality_checks_id_seq OWNED BY public.data_quality_checks.id;


--
-- Name: data_retention_policies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_retention_policies (
    id character varying(36) NOT NULL,
    tenant_id character varying(36),
    resource_type character varying(100) NOT NULL,
    retention_days integer NOT NULL,
    archive_before_delete boolean NOT NULL,
    is_active boolean NOT NULL,
    created_by character varying(36),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: dim_agencies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_agencies (
    agency_id character varying(36) NOT NULL,
    agency_code character varying(50) NOT NULL,
    agency_name character varying(255) NOT NULL,
    division character varying(100),
    region character varying(100),
    is_active boolean,
    last_tender_date timestamp with time zone,
    total_spend_bdt numeric(15,2),
    tender_count integer,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: dim_categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_categories (
    category_id character varying(36) NOT NULL,
    category_name character varying(255) NOT NULL,
    sector character varying(100),
    subsector character varying(100),
    description text,
    tender_count integer,
    avg_tender_value_bdt numeric(15,2),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: dim_contractors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_contractors (
    contractor_id character varying(36) NOT NULL,
    contractor_name character varying(255) NOT NULL,
    registration_number character varying(100),
    category character varying(50),
    zone character varying(10),
    bid_count integer,
    award_count integer,
    total_contract_value_bdt numeric(15,2),
    completion_rate_pct numeric(5,2),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: dim_zones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dim_zones (
    zone_id character varying(10) NOT NULL,
    zone_name character varying(100) NOT NULL,
    region character varying(100) NOT NULL,
    agency_type character varying(50),
    tender_count integer,
    total_spend_bdt numeric(15,2),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: discount_patterns; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.discount_patterns (
    agency_code character varying(20) NOT NULL,
    zone_name character varying(100),
    procurement_method character varying(100),
    sample_size integer NOT NULL,
    avg_npp double precision NOT NULL,
    min_npp double precision NOT NULL,
    max_npp double precision NOT NULL,
    median_npp double precision NOT NULL,
    stddev_npp double precision NOT NULL,
    total_amount_bdt double precision NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    id character varying(36) NOT NULL,
    tender_id character varying(100) NOT NULL,
    doc_type character varying(50) NOT NULL,
    doc_name character varying(255),
    file_path character varying(500),
    file_size integer,
    mime_type character varying(100),
    extracted_text text,
    extracted_data json,
    ocr_required boolean,
    ocr_done boolean,
    is_mapped boolean,
    mapping_errors json,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: ecms_app_package_map; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.ecms_app_package_map AS
 SELECT e.id AS ecms_id,
    e.tender_id,
    e.package_no AS ecms_package_no,
    e.title AS ecms_title,
    e.agency_code,
    e.contractor_name,
    e.contract_value_bdt,
    e.award_date,
    e.work_status,
    e.completion_status,
    e.progress_pct,
    a.id AS app_id,
    a.package_no AS app_package_no,
    a.financial_year,
    a.estimated_cost_bdt AS app_estimate,
    a.status AS app_status,
    a.app_code,
    a.category AS app_category,
    a.ministry,
    a.agency_name,
    a.procuring_entity,
    a.procurement_method,
    a.district AS app_district
   FROM (public.ecms_ongoing e
     LEFT JOIN public.app_records a ON (((e.package_no)::text = (a.package_no)::text)))
  WHERE ((e.package_no IS NOT NULL) AND ((e.package_no)::text <> ''::text));


--
-- Name: ecms_app_package_map_mv; Type: MATERIALIZED VIEW; Schema: public; Owner: -
--

CREATE MATERIALIZED VIEW public.ecms_app_package_map_mv AS
 SELECT ecms_id,
    tender_id,
    ecms_package_no,
    ecms_title,
    agency_code,
    contractor_name,
    contract_value_bdt,
    award_date,
    work_status,
    completion_status,
    progress_pct,
    app_id,
    app_package_no,
    financial_year,
    app_estimate,
    app_status,
    app_code,
    app_category,
    ministry,
    agency_name,
    procuring_entity,
    procurement_method,
    app_district
   FROM public.ecms_app_package_map
  WITH NO DATA;


--
-- Name: econtract_execution; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.econtract_execution (
    package_no character varying(300) NOT NULL,
    title text,
    agency_code character varying(20),
    agency_name character varying(300),
    pe_office character varying(300),
    contractor_name character varying(300),
    contract_value_bdt double precision NOT NULL,
    contract_start_date character varying(20),
    contract_end_date character varying(20),
    award_date character varying(20),
    status character varying(50),
    tender_id character varying(50),
    district character varying(100),
    source_url text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL,
    completed_value_bdt double precision DEFAULT 0,
    planned_completion_date character varying(20),
    actual_completion_date character varying(20),
    completion_status character varying(50),
    work_status character varying(100),
    progress_pct double precision DEFAULT 0,
    delay_days integer DEFAULT 0,
    extension_days integer DEFAULT 0,
    completed_on_time boolean,
    performance_rating character varying(50),
    completion_certificate_no character varying(200),
    bill_no character varying(200),
    fiscal_year character varying(20),
    remarks text,
    raw_payload json,
    data_source character varying(50) DEFAULT 'EEXPERIENCE'::character varying,
    procurement_tender_id character varying(36)
);


--
-- Name: eexperience_completed; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eexperience_completed (
    id character varying(36) NOT NULL,
    tender_id character varying(50),
    package_no character varying(300) NOT NULL,
    title text,
    pe_office character varying(300),
    agency_code character varying(20),
    procurement_method character varying(100),
    contractor_name character varying(300),
    company_unique_id character varying(50),
    experience_certificate_no character varying(200),
    contract_value_bdt double precision DEFAULT 0,
    completed_value_bdt double precision DEFAULT 0,
    contract_start_date character varying(20),
    contract_end_date character varying(20),
    planned_completion_date character varying(20),
    actual_completion_date character varying(20),
    published_date character varying(20),
    award_date character varying(20),
    completion_status character varying(50),
    work_status character varying(100),
    status character varying(50),
    progress_pct double precision DEFAULT 0,
    completed_on_time boolean,
    district character varying(100),
    source_url text,
    procurement_tender_id character varying(36),
    data_source character varying(50) DEFAULT 'EEXPERIENCE_ALL'::character varying,
    raw_payload jsonb,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    tender_ref_no character varying(300),
    package_name text,
    name_of_work text,
    ministry_division character varying(300),
    organization_name character varying(300),
    pe_name character varying(300),
    procurement_nature character varying(100),
    work_category character varying(200),
    contract_no character varying(200),
    physical_progress_pct double precision DEFAULT 0,
    financial_progress_pct double precision DEFAULT 0,
    physical_progress_date character varying(20),
    financial_progress_date character varying(20),
    is_jvca boolean,
    remarks text,
    comments_by_pe text
);


--
-- Name: enriched_app; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enriched_app (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    app_id text,
    ministry text,
    division text,
    organization text,
    pe_office text,
    district text,
    source_file text,
    raw_json jsonb NOT NULL,
    fetched_at timestamp without time zone DEFAULT now()
);


--
-- Name: enriched_awards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enriched_awards (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tender_id text,
    tenderer_id text,
    package_no text,
    agency text,
    pe_name text,
    pe_district text,
    ministry_division text,
    procurement_method text,
    contract_value numeric,
    date_notification_award text,
    economic_operator text,
    ref_no text,
    package_name text,
    beneficial_ownership jsonb,
    source_file text,
    raw_json jsonb NOT NULL,
    fetched_at timestamp without time zone DEFAULT now()
);


--
-- Name: enriched_ecms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.enriched_ecms (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    cert_no text,
    tender_id text,
    package_no text,
    package_name text,
    pe_name text,
    pe_office_name text,
    organization_name text,
    ministry_division text,
    procurement_method text,
    procurement_nature text,
    contract_value numeric,
    company_name text,
    work_completion_status text,
    beneficial_ownership jsonb,
    source text,
    raw_json jsonb NOT NULL,
    fetched_at timestamp without time zone DEFAULT now()
);


--
-- Name: epw3_forms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.epw3_forms (
    tender_id character varying(300) NOT NULL,
    generated_at character varying(50) NOT NULL,
    forms json NOT NULL,
    total_forms integer NOT NULL,
    form_ids json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: experience_certificate_registry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.experience_certificate_registry (
    id character varying(36) NOT NULL,
    certificate_no character varying(300) NOT NULL,
    contractor_name character varying(300) NOT NULL,
    package_no character varying(200),
    tender_id character varying(100),
    agency_code character varying(200),
    contract_value_bdt double precision,
    contract_start_date character varying(30),
    contract_end_date character varying(30),
    completion_status character varying(200),
    is_valid boolean DEFAULT true,
    duplicate_count integer DEFAULT 0
);


--
-- Name: fact_awards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_awards (
    award_id character varying(36) NOT NULL,
    tender_id character varying(36),
    contractor_id character varying(36),
    award_value_bdt numeric(15,2),
    award_date date,
    completion_status character varying(50),
    days_to_award integer,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: fact_bids; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_bids (
    bid_id character varying(36) NOT NULL,
    tender_id character varying(36),
    contractor_id character varying(36),
    bid_amount_bdt numeric(15,2),
    bid_date date,
    is_winner boolean,
    days_to_bid integer,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: fact_tenders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fact_tenders (
    tender_id character varying(36) NOT NULL,
    agency_id character varying(36),
    zone_id character varying(10),
    category_id character varying(36),
    tender_value_bdt numeric(15,2),
    estimated_value_bdt numeric(15,2),
    procurement_method character varying(50),
    tender_type character varying(50),
    status character varying(50),
    published_date date,
    deadline_date date,
    award_date date,
    completion_date date,
    bid_count integer,
    duration_days integer,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: feedback_labels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.feedback_labels (
    id character varying(36) NOT NULL,
    agent_result_id character varying(36),
    tender_id character varying(100),
    label character varying(50),
    score_adjustment double precision,
    reviewer_comment text,
    reviewer_id character varying(36),
    created_at timestamp with time zone
);


--
-- Name: idp_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.idp_configs (
    id character varying(36) NOT NULL,
    tenant_id character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    idp_type character varying(50) NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    provisioning_policy character varying(50) DEFAULT 'jit'::character varying NOT NULL,
    oidc_discovery_url character varying(500),
    oidc_client_id character varying(255),
    oidc_client_secret text,
    oidc_redirect_uri character varying(500),
    oidc_scopes json DEFAULT '["openid", "profile", "email"]'::json NOT NULL,
    saml_entity_id character varying(500),
    saml_sso_url character varying(500),
    saml_certificate text,
    saml_metadata_url character varying(500),
    claim_mappings json DEFAULT '{}'::json NOT NULL,
    role_mappings json DEFAULT '{}'::json NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_sync_at timestamp with time zone
);


--
-- Name: knowledge_edges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.knowledge_edges (
    id uuid NOT NULL,
    source_node_id uuid NOT NULL,
    target_node_id uuid NOT NULL,
    edge_type character varying(50) NOT NULL,
    weight double precision DEFAULT '1'::double precision NOT NULL,
    meta_json json DEFAULT '{}'::json NOT NULL,
    tenant_id character varying(255) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: knowledge_embeddings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.knowledge_embeddings (
    id uuid NOT NULL,
    node_id uuid NOT NULL,
    embedding text NOT NULL,
    embedding_model character varying(255) DEFAULT 'sentence-transformers/all-MiniLM-L6-v2'::character varying NOT NULL,
    tenant_id character varying(255) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: knowledge_entries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.knowledge_entries (
    entry_type character varying(50) NOT NULL,
    tender_id character varying(100),
    data json NOT NULL,
    checksum character varying(64),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL,
    tenant_id character varying(36),
    title character varying(500),
    content text,
    summary text,
    source character varying(50),
    source_url character varying(500),
    source_file character varying(255),
    embedding_id character varying(100),
    embedding_model character varying(100),
    tags json,
    agency character varying(255),
    zone character varying(100),
    procurement_type character varying(50),
    is_archived boolean DEFAULT false
);


--
-- Name: knowledge_nodes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.knowledge_nodes (
    id uuid NOT NULL,
    node_type character varying(50) NOT NULL,
    external_id character varying(255) NOT NULL,
    label character varying(500),
    description text,
    meta_json json DEFAULT '{}'::json NOT NULL,
    tenant_id character varying(255) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: learning_outcomes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.learning_outcomes (
    tender_id character varying(300) NOT NULL,
    submitted boolean NOT NULL,
    won boolean NOT NULL,
    our_bid_amount double precision NOT NULL,
    lert_amount double precision NOT NULL,
    our_discount_pct double precision NOT NULL,
    predicted_win_probability double precision NOT NULL,
    actual_outcome character varying(50) NOT NULL,
    recorded_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: lifecycle; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lifecycle (
    id character varying(36) NOT NULL,
    app_id character varying(100),
    tender_id character varying(100),
    award_tender_id character varying(100),
    match_confidence double precision,
    variance_amount numeric(16,2),
    variance_pct double precision,
    lifecycle_stage character varying(50),
    raw_data json,
    created_at timestamp with time zone
);


--
-- Name: live_tender_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.live_tender_sources (
    procurement_tender_id character varying(36) NOT NULL,
    source_tender_id character varying(500) NOT NULL,
    title text,
    procuring_entity character varying(500),
    published_date character varying(20),
    deadline character varying(20),
    status character varying(50),
    financial_year character varying(20),
    category character varying(100),
    estimated_value_bdt double precision NOT NULL,
    source_file character varying(300),
    source_type character varying(50),
    raw_payload json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: market_rates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.market_rates (
    id character varying(36) NOT NULL,
    item_code character varying(100),
    item_name character varying(300) NOT NULL,
    unit character varying(50),
    current_rate double precision DEFAULT 0,
    previous_rate double precision DEFAULT 0,
    change_percent double precision DEFAULT 0,
    category character varying(100),
    zone character varying(50),
    source character varying(100),
    updated_at timestamp without time zone DEFAULT now()
);


--
-- Name: material_margins; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.material_margins (
    id uuid NOT NULL,
    material_category character varying(100) NOT NULL,
    agency character varying(20) NOT NULL,
    zone character varying(10) NOT NULL,
    sor_code character varying(100),
    sor_description text,
    sor_rate numeric(15,2),
    avg_market_price numeric(15,2),
    margin_bdt numeric(15,2),
    margin_pct numeric(8,2),
    unit character varying(50),
    sample_count integer DEFAULT 0,
    computed_at timestamp without time zone DEFAULT now()
);


--
-- Name: material_prices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.material_prices (
    id uuid NOT NULL,
    material_name character varying(300) NOT NULL,
    category character varying(100),
    price_bdt numeric(15,2),
    unit character varying(50),
    seller character varying(200),
    source_url text,
    zone character varying(10),
    division character varying(50),
    currency character varying(10) DEFAULT 'BDT'::character varying,
    collected_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: npp_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.npp_records (
    id character varying(36) NOT NULL,
    tender_id character varying(100) NOT NULL,
    package_no character varying(255),
    work_name text,
    pe_office character varying(255),
    agency character varying(255),
    zone character varying(100),
    estimated_amount_bdt numeric(16,2),
    lowest_bid numeric(16,2),
    bid_average numeric(16,2),
    lowest_percent_below_oe numeric(8,4),
    average_percent_below_oe numeric(8,4),
    bid_spread_percent numeric(8,4),
    bidder_count integer,
    cluster_detected boolean,
    discount_strategy_detected boolean,
    slt_risk character varying(50),
    likely_market_discount numeric(8,4),
    source_file character varying(500),
    raw_data json,
    created_at timestamp with time zone
);


--
-- Name: nppi_indices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nppi_indices (
    id uuid NOT NULL,
    agency character varying(10) NOT NULL,
    zone character varying(10) NOT NULL,
    category character varying(100),
    period_start date NOT NULL,
    period_end date NOT NULL,
    index_value numeric(10,4),
    base_value numeric(10,4),
    base_period character varying(50),
    created_at timestamp without time zone DEFAULT now()
);


--
-- Name: opening_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.opening_reports (
    id character varying(36) NOT NULL,
    tender_id character varying(100) NOT NULL,
    tenant_id character varying(36),
    opening_date date,
    opening_place character varying(255),
    opened_by character varying(255),
    estimated_amount_bdt numeric(16,2),
    pe_office character varying(255),
    agency character varying(255),
    zone character varying(100),
    package_work_name text,
    bidders json,
    has_slt boolean,
    has_alt boolean,
    winner_name character varying(255),
    winner_amount numeric(16,2),
    winner_discount double precision,
    is_archived boolean,
    raw_data json,
    source_pdf character varying(255),
    source_json character varying(255),
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organizations (
    id character varying(36) NOT NULL,
    tenant_id character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    registration_no character varying(100),
    address text,
    contact_email character varying(255),
    contact_phone character varying(50),
    config json,
    created_at timestamp with time zone
);


--
-- Name: package_tender_bridge; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.package_tender_bridge (
    norm_pkg text NOT NULL,
    tender_id text NOT NULL,
    source text NOT NULL
);


--
-- Name: permissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permissions (
    id character varying(36) NOT NULL,
    resource character varying(50) NOT NULL,
    action character varying(50) NOT NULL,
    description text,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: pf_awards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pf_awards (
    id bigint NOT NULL,
    award_id character varying(50),
    tender_id character varying(50),
    package_no character varying(400),
    company_id bigint,
    procuring_entity_id bigint,
    title text,
    award_date character varying(50),
    award_datetime timestamp with time zone,
    contract_value numeric(18,2),
    status character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    tenant_id bigint,
    source character varying(100),
    data_hash character varying(64),
    details jsonb,
    offline_id character varying(50)
);


--
-- Name: pf_awards_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pf_awards_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pf_awards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pf_awards_id_seq OWNED BY public.pf_awards.id;


--
-- Name: pf_companies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pf_companies (
    id bigint NOT NULL,
    name character varying(400) NOT NULL,
    registration_no character varying(100),
    address text,
    district character varying(100),
    contact character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    tenant_id bigint,
    source character varying(100),
    data_hash character varying(64)
);


--
-- Name: pf_companies_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pf_companies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pf_companies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pf_companies_id_seq OWNED BY public.pf_companies.id;


--
-- Name: pf_debarments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pf_debarments (
    id bigint NOT NULL,
    company_id bigint,
    company_name character varying(400),
    authority character varying(200),
    reason text,
    start_date character varying(50),
    end_date character varying(50),
    status character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    tenant_id bigint,
    source character varying(100),
    data_hash character varying(64)
);


--
-- Name: pf_debarments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pf_debarments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pf_debarments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pf_debarments_id_seq OWNED BY public.pf_debarments.id;


--
-- Name: pf_document_embeddings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pf_document_embeddings (
    id bigint NOT NULL,
    entity_type character varying(50) NOT NULL,
    entity_id bigint NOT NULL,
    doc_type character varying(50),
    text_content text,
    embedding double precision[] NOT NULL,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: pf_document_embeddings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pf_document_embeddings_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pf_document_embeddings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pf_document_embeddings_id_seq OWNED BY public.pf_document_embeddings.id;


--
-- Name: pf_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pf_documents (
    id bigint NOT NULL,
    tender_id character varying(50),
    doc_type character varying(50) NOT NULL,
    filename character varying(255) NOT NULL,
    file_path character varying(500) NOT NULL,
    file_size bigint DEFAULT 0,
    file_hash character varying(64),
    source_url text,
    minio_path character varying(500),
    downloaded_at timestamp with time zone DEFAULT now(),
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    tenant_id bigint,
    source character varying(100),
    data_hash character varying(64)
);


--
-- Name: pf_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pf_documents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pf_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pf_documents_id_seq OWNED BY public.pf_documents.id;


--
-- Name: pf_relationships; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pf_relationships (
    id bigint NOT NULL,
    source_type character varying(50) NOT NULL,
    source_id bigint NOT NULL,
    target_type character varying(50) NOT NULL,
    target_id bigint NOT NULL,
    relationship_type character varying(50) NOT NULL,
    metadata jsonb,
    confidence numeric(5,4) DEFAULT 1.0,
    discovered_by character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    tenant_id bigint,
    source character varying(100),
    data_hash character varying(64)
);


--
-- Name: pf_entity_graph; Type: MATERIALIZED VIEW; Schema: public; Owner: -
--

CREATE MATERIALIZED VIEW public.pf_entity_graph AS
 SELECT r.id AS relationship_id,
    r.source_type AS entity_type,
    r.source_id AS entity_id,
    r.target_type AS related_type,
    r.target_id AS related_id,
    r.relationship_type,
    r.confidence,
    r.created_at AS discovered_at
   FROM public.pf_relationships r
  WHERE (NOT r.is_deleted)
UNION ALL
 SELECT r.id AS relationship_id,
    r.target_type AS entity_type,
    r.target_id AS entity_id,
    r.source_type AS related_type,
    r.source_id AS related_id,
    ((r.relationship_type)::text || '_inverse'::text) AS relationship_type,
    r.confidence,
    r.created_at AS discovered_at
   FROM public.pf_relationships r
  WHERE (NOT r.is_deleted)
  WITH NO DATA;


--
-- Name: pf_experience; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pf_experience (
    id bigint NOT NULL,
    experience_id character varying(50),
    company_id bigint,
    project_name text,
    procuring_entity_id bigint,
    contract_value numeric(18,2),
    completion_date character varying(50),
    completion_datetime timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    tenant_id bigint,
    source character varying(100),
    data_hash character varying(64),
    details jsonb,
    tender_id text,
    tender_ref_no text,
    package_no text,
    package_name text,
    name_of_work text,
    contract_no text,
    contract_start_date text,
    contract_end_date text,
    work_completion_status text,
    procurement_nature text,
    procurement_method text,
    work_category text,
    tender_type text,
    physical_progress numeric,
    financial_progress numeric,
    experience_cert_no text,
    pe_office_name text,
    organization_name text,
    pe_officer_name text,
    ministry_division text,
    company_name text,
    is_jvca text,
    remarks text,
    comments_by_pe text,
    date_physical_progress text,
    date_financial_progress text,
    tender_publication_date text
);


--
-- Name: pf_experience_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pf_experience_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pf_experience_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pf_experience_id_seq OWNED BY public.pf_experience.id;


--
-- Name: pf_procuring_entities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pf_procuring_entities (
    id bigint NOT NULL,
    name character varying(300) NOT NULL,
    organization_id bigint,
    office character varying(200),
    location_id bigint,
    agency_code character varying(20),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    tenant_id bigint,
    source character varying(100),
    data_hash character varying(64)
);


--
-- Name: pf_procuring_entities_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pf_procuring_entities_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pf_procuring_entities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pf_procuring_entities_id_seq OWNED BY public.pf_procuring_entities.id;


--
-- Name: pf_relationships_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pf_relationships_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pf_relationships_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pf_relationships_id_seq OWNED BY public.pf_relationships.id;


--
-- Name: pf_tenders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pf_tenders (
    id bigint NOT NULL,
    tender_id character varying(50) NOT NULL,
    package_no character varying(400),
    app_id bigint,
    procuring_entity_id bigint,
    title text,
    invitation_ref character varying(100),
    status character varying(50),
    publish_date character varying(50),
    closing_date character varying(50),
    publish_datetime timestamp with time zone,
    closing_datetime timestamp with time zone,
    document_price numeric(18,2),
    category character varying(50),
    procurement_nature character varying(50),
    procurement_type character varying(50),
    procurement_method character varying(50),
    pe_office character varying(500),
    district character varying(300),
    agency_code character varying(20),
    source_url text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_deleted boolean DEFAULT false NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    tenant_id bigint,
    source character varying(100),
    data_hash character varying(64),
    details jsonb,
    offline_id character varying(50)
);


--
-- Name: pf_tenders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pf_tenders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pf_tenders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pf_tenders_id_seq OWNED BY public.pf_tenders.id;


--
-- Name: phase2_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phase2_documents (
    name character varying(500) NOT NULL,
    document_type character varying(50) NOT NULL,
    tender_id character varying(36) NOT NULL,
    file_path character varying(500) NOT NULL,
    file_size integer NOT NULL,
    mime_type character varying(100) NOT NULL,
    extracted_data text,
    extraction_status character varying(50) NOT NULL,
    tenant_id character varying(64) NOT NULL,
    created_by character varying(36) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: phase2_team_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phase2_team_members (
    email character varying(255) NOT NULL,
    full_name character varying(255) NOT NULL,
    role public.teamrole NOT NULL,
    department character varying(255),
    phone character varying(20),
    tenant_id character varying(64) NOT NULL,
    user_id character varying(36),
    is_active boolean NOT NULL,
    invited_at timestamp without time zone NOT NULL,
    joined_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: phase2_teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.phase2_teams (
    tenant_id character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    max_members integer NOT NULL,
    settings text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: ppr_evaluations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ppr_evaluations (
    evaluation_type character varying(50) NOT NULL,
    tender_id character varying(300) NOT NULL,
    input_data json NOT NULL,
    result_data json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL,
    schedule_type character varying(50),
    schedule_label character varying(255),
    criteria text,
    total_marks double precision,
    max_marks double precision,
    percentage double precision,
    passed boolean DEFAULT false NOT NULL,
    raw_data json,
    agent_result_id character varying(36)
);


--
-- Name: ppr_rule_profiles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ppr_rule_profiles (
    rule_key character varying(50) NOT NULL,
    effective_from timestamp without time zone NOT NULL,
    effective_to timestamp without time zone,
    legacy_band_pct double precision NOT NULL,
    slt_threshold_pct double precision NOT NULL,
    alt_threshold_pct double precision NOT NULL,
    nppi_window_days integer NOT NULL,
    policy json NOT NULL,
    notes text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: ppr_schedules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ppr_schedules (
    id character varying(36) NOT NULL,
    agent_result_id character varying(36),
    tender_id character varying(100),
    schedule_type character varying(20),
    schedule_label character varying(100),
    criteria json,
    total_marks double precision,
    max_marks double precision,
    percentage double precision,
    passed boolean,
    created_at timestamp with time zone
);


--
-- Name: pre_computed_intelligence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pre_computed_intelligence (
    id character varying(36) NOT NULL,
    cache_key character varying(255) NOT NULL,
    cache_data json,
    intelligence_type character varying(50),
    agency character varying(255),
    category character varying(100),
    zone character varying(100),
    tender_id character varying(100),
    expires_at timestamp with time zone,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: prediction_feedback; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prediction_feedback (
    feedback_id character varying(36) NOT NULL,
    prediction_id character varying(36) NOT NULL,
    predicted_price numeric(15,2) NOT NULL,
    predicted_low numeric(15,2) NOT NULL,
    predicted_high numeric(15,2) NOT NULL,
    actual_price numeric(15,2) NOT NULL,
    prediction_error double precision NOT NULL,
    tender_id character varying(36),
    contractor_id character varying(36),
    is_useful boolean NOT NULL,
    confidence_in_feedback double precision NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: procurement_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.procurement_types (
    id character varying(36) NOT NULL,
    code character varying(30) NOT NULL,
    procurement_method character varying(30),
    label character varying(100) NOT NULL
);


--
-- Name: rate_analysis; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rate_analysis (
    id character varying(36) NOT NULL,
    rate_id character varying(100) NOT NULL,
    agency character varying(255),
    zone character varying(100),
    procurement_type character varying(255),
    item_code character varying(100),
    item_description text,
    sor_rate numeric(16,2),
    quoted_rate numeric(16,2),
    rate_diff_pct numeric(8,4),
    market_trend character varying(100),
    raw_data json,
    source_file character varying(500),
    created_at timestamp with time zone,
    sor_code character varying(50),
    sor_category character varying(100),
    sub_item_no integer DEFAULT 1,
    sub_description character varying(300),
    sub_unit character varying(50),
    sub_quantity numeric(12,4) DEFAULT 0,
    component_type character varying(30) DEFAULT 'material'::character varying,
    material_category character varying(100),
    remarks text,
    parent_unit character varying(50) DEFAULT 'unit'::character varying
);


--
-- Name: raw_app_listings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_app_listings (
    id integer NOT NULL,
    source text,
    raw_data jsonb,
    crawled_at timestamp without time zone DEFAULT now()
);


--
-- Name: raw_app_listings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.raw_app_listings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: raw_app_listings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.raw_app_listings_id_seq OWNED BY public.raw_app_listings.id;


--
-- Name: raw_app_packages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_app_packages (
    id integer NOT NULL,
    source text,
    raw_data jsonb,
    crawled_at timestamp without time zone DEFAULT now()
);


--
-- Name: raw_app_packages_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.raw_app_packages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: raw_app_packages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.raw_app_packages_id_seq OWNED BY public.raw_app_packages.id;


--
-- Name: raw_awards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_awards (
    id integer NOT NULL,
    source text,
    raw_data jsonb,
    crawled_at timestamp without time zone DEFAULT now()
);


--
-- Name: raw_awards_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.raw_awards_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: raw_awards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.raw_awards_id_seq OWNED BY public.raw_awards.id;


--
-- Name: raw_crawl_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_crawl_data (
    id bigint NOT NULL,
    table_name character varying(100) NOT NULL,
    source character varying(100) NOT NULL,
    data jsonb NOT NULL,
    data_hash character varying(64),
    crawled_at timestamp with time zone DEFAULT now(),
    processed boolean DEFAULT false,
    processed_at timestamp with time zone
);


--
-- Name: raw_crawl_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.raw_crawl_data_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: raw_crawl_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.raw_crawl_data_id_seq OWNED BY public.raw_crawl_data.id;


--
-- Name: raw_debarment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_debarment (
    id integer NOT NULL,
    source text,
    raw_data jsonb,
    crawled_at timestamp without time zone DEFAULT now()
);


--
-- Name: raw_debarment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.raw_debarment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: raw_debarment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.raw_debarment_id_seq OWNED BY public.raw_debarment.id;


--
-- Name: raw_experience; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_experience (
    id integer NOT NULL,
    source text,
    raw_data jsonb,
    crawled_at timestamp without time zone DEFAULT now()
);


--
-- Name: raw_experience_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.raw_experience_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: raw_experience_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.raw_experience_id_seq OWNED BY public.raw_experience.id;


--
-- Name: raw_import_batches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_import_batches (
    batch_id text NOT NULL,
    source_root text NOT NULL,
    file_count integer DEFAULT 0 NOT NULL,
    record_count bigint DEFAULT 0 NOT NULL,
    total_bytes bigint DEFAULT 0 NOT NULL,
    status text DEFAULT 'started'::text NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone
);


--
-- Name: raw_json_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_json_documents (
    raw_id text NOT NULL,
    batch_id text,
    source_family text NOT NULL,
    source_path text NOT NULL,
    source_index integer DEFAULT 0 NOT NULL,
    source_size_bytes bigint DEFAULT 0 NOT NULL,
    source_mtime timestamp with time zone,
    record_key text,
    package_no text,
    tender_id text,
    contractor_name text,
    amount_raw text,
    raw_payload jsonb NOT NULL,
    payload_sha256 text NOT NULL,
    imported_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: raw_offline_awards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_offline_awards (
    id integer NOT NULL,
    source text,
    raw_data jsonb,
    crawled_at timestamp without time zone DEFAULT now()
);


--
-- Name: raw_offline_awards_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.raw_offline_awards_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: raw_offline_awards_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.raw_offline_awards_id_seq OWNED BY public.raw_offline_awards.id;


--
-- Name: raw_offline_tenders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_offline_tenders (
    id integer NOT NULL,
    source text,
    raw_data jsonb,
    crawled_at timestamp without time zone DEFAULT now()
);


--
-- Name: raw_offline_tenders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.raw_offline_tenders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: raw_offline_tenders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.raw_offline_tenders_id_seq OWNED BY public.raw_offline_tenders.id;


--
-- Name: raw_tenders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_tenders (
    id integer NOT NULL,
    source text,
    raw_data jsonb,
    crawled_at timestamp without time zone DEFAULT now()
);


--
-- Name: raw_tenders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.raw_tenders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: raw_tenders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.raw_tenders_id_seq OWNED BY public.raw_tenders.id;


--
-- Name: refresh_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refresh_tokens (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    tenant_id character varying(64),
    token_hash character varying(64) NOT NULL,
    family_id character varying(36) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    rotated_at timestamp with time zone,
    replaced_by character varying(36),
    revoked_at timestamp with time zone,
    revoke_reason character varying(50),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: regulation_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.regulation_documents (
    id character varying(36) NOT NULL,
    code character varying(50) NOT NULL,
    title character varying(500) NOT NULL,
    issuing_authority character varying(255),
    source_url text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: regulation_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.regulation_versions (
    id character varying(36) NOT NULL,
    document_id character varying(36) NOT NULL,
    version_label character varying(50) NOT NULL,
    effective_from date NOT NULL,
    superseded_date date,
    is_current boolean NOT NULL,
    notes text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: roles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.roles (
    id character varying(36) NOT NULL,
    tenant_id character varying(36),
    name character varying(100) NOT NULL,
    description text,
    is_system boolean NOT NULL,
    permission_ids json NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: rule_citations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rule_citations (
    id character varying(36) NOT NULL,
    rule_version_id character varying(36) NOT NULL,
    clause_id character varying(36),
    circular_id character varying(36),
    citation_text character varying(255) NOT NULL,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: rule_execution_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rule_execution_logs (
    id character varying(36) NOT NULL,
    rule_version_id character varying(36) NOT NULL,
    tender_id character varying(100),
    agent_id character varying(100),
    trace_id character varying(36),
    request_id character varying(36),
    tenant_id character varying(36),
    inputs json NOT NULL,
    intermediate_values json NOT NULL,
    outputs json NOT NULL,
    decision character varying(50),
    citation_snapshot json NOT NULL,
    executed_at timestamp with time zone NOT NULL,
    actor character varying(100)
);


--
-- Name: rule_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rule_versions (
    id character varying(36) NOT NULL,
    rule_id_fk character varying(36) NOT NULL,
    regulation_version_id character varying(36) NOT NULL,
    version_label character varying(50) NOT NULL,
    formula_kind character varying(30) NOT NULL,
    parameters json NOT NULL,
    explanation_template text,
    status character varying(20) NOT NULL,
    effective_from date NOT NULL,
    superseded_date date,
    created_by character varying(36),
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rules (
    id character varying(36) NOT NULL,
    rule_id character varying(100) NOT NULL,
    category character varying(50) NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    is_legal_mandate boolean NOT NULL,
    procurement_types json NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: rulesets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rulesets (
    id character varying(36) NOT NULL,
    tenant_id character varying(36),
    name character varying(255) NOT NULL,
    ruleset_type character varying(50),
    version character varying(20) NOT NULL,
    rules json NOT NULL,
    description text,
    active boolean,
    created_by character varying(36),
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: slt_audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.slt_audit_logs (
    evaluation_id character varying(36),
    tender_id character varying(100) NOT NULL,
    action character varying(100) NOT NULL,
    actor character varying(100) NOT NULL,
    payload json NOT NULL,
    source_mode character varying(50) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: slt_evaluation_bids; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.slt_evaluation_bids (
    evaluation_id character varying(36) NOT NULL,
    bidder_name character varying(255) NOT NULL,
    quoted_price double precision NOT NULL,
    deviation_percent double precision NOT NULL,
    is_slt boolean NOT NULL,
    disqualified boolean NOT NULL,
    elimination_reason text,
    remarks text,
    rule_key character varying(50) NOT NULL,
    evaluation_mode character varying(20) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: slt_evaluation_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.slt_evaluation_runs (
    tender_id character varying(100) NOT NULL,
    tender_open_date character varying(20),
    rule_key character varying(50) NOT NULL,
    evaluation_mode character varying(20) NOT NULL,
    source_mode character varying(50) NOT NULL,
    official_estimate double precision NOT NULL,
    nppi double precision NOT NULL,
    xnppi double precision NOT NULL,
    average_tender_price double precision NOT NULL,
    weighted_average double precision NOT NULL,
    standard_deviation double precision NOT NULL,
    lower_limit double precision NOT NULL,
    bidder_count integer NOT NULL,
    responsive_bidder_count integer NOT NULL,
    status character varying(50) NOT NULL,
    thresholds json NOT NULL,
    formula_inputs json NOT NULL,
    result_json json NOT NULL,
    ter_note text,
    data_sources json NOT NULL,
    evaluation_date character varying(20),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: sor_rates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sor_rates (
    agency public.soragency NOT NULL,
    code character varying(100) NOT NULL,
    normalized_code character varying(100) NOT NULL,
    description character varying(500) NOT NULL,
    unit character varying(50) NOT NULL,
    zone_a double precision NOT NULL,
    zone_b double precision NOT NULL,
    zone_c double precision NOT NULL,
    zone_d double precision NOT NULL,
    edition_year integer,
    is_active boolean NOT NULL,
    source_file character varying(255),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: sso_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sso_sessions (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    tenant_id character varying(36) NOT NULL,
    idp_config_id character varying(36) NOT NULL,
    state character varying(255),
    nonce character varying(255),
    session_index character varying(255),
    idp_subject_id character varying(255) NOT NULL,
    idp_name_id character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    logged_out_at timestamp with time zone
);


--
-- Name: staging_awards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staging_awards (
    staging_id text NOT NULL,
    raw_id text,
    source_family text NOT NULL,
    source_path text,
    package_no text,
    normalized_package_no text,
    tender_id text,
    title text,
    agency_code text,
    district text,
    pe_office text,
    contractor_name text,
    amount_raw text,
    amount_normalized_bdt double precision DEFAULT 0 NOT NULL,
    amount_confidence double precision DEFAULT 0 NOT NULL,
    source_date date,
    confidence_score double precision DEFAULT 0 NOT NULL,
    raw_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    parsed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: staging_ecms_ongoing; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staging_ecms_ongoing (
    staging_id text NOT NULL,
    raw_id text,
    source_family text NOT NULL,
    source_path text,
    package_no text,
    normalized_package_no text,
    tender_id text,
    title text,
    agency_code text,
    district text,
    pe_office text,
    contractor_name text,
    amount_raw text,
    amount_normalized_bdt double precision DEFAULT 0 NOT NULL,
    amount_confidence double precision DEFAULT 0 NOT NULL,
    source_date date,
    confidence_score double precision DEFAULT 0 NOT NULL,
    raw_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    parsed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: staging_econtracts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staging_econtracts (
    staging_id text NOT NULL,
    raw_id text,
    source_family text NOT NULL,
    source_path text,
    package_no text,
    normalized_package_no text,
    tender_id text,
    title text,
    agency_code text,
    district text,
    pe_office text,
    contractor_name text,
    amount_raw text,
    amount_normalized_bdt double precision DEFAULT 0 NOT NULL,
    amount_confidence double precision DEFAULT 0 NOT NULL,
    source_date date,
    confidence_score double precision DEFAULT 0 NOT NULL,
    raw_payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    parsed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: staging_enriched_awards; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staging_enriched_awards (
    tender_id text,
    package_no text,
    normalized_package_no text,
    ref_no text,
    title text,
    contractor_name text,
    economic_operator text,
    tenderer_id text,
    contract_value_bdt double precision,
    value_crore_bdt double precision,
    date_advertisement date,
    date_notification_award date,
    date_contract_signing date,
    date_contract_start date,
    date_contract_completion date,
    contract_duration_days integer,
    agency_code text,
    agency_name text,
    ministry text,
    division text,
    district text,
    procuring_entity text,
    pe_name text,
    procurement_method text,
    contract_award_for text,
    budget_source text,
    project_name text,
    beneficial_ownership jsonb,
    owner_count integer,
    detail_url text,
    source text,
    crawled_at timestamp with time zone
);


--
-- Name: staging_enriched_ecms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staging_enriched_ecms (
    tender_id text,
    package_no text,
    normalized_package_no text,
    cert_no text,
    contract_no text,
    name_of_work text,
    package_name text,
    company_name text,
    is_jvca text,
    contract_value double precision,
    work_completion_status text,
    contract_start_date date,
    contract_end_date date,
    contract_duration_days integer,
    physical_progress_pct double precision,
    financial_progress_pct double precision,
    date_physical_progress date,
    date_financial_progress date,
    overrun_days integer,
    organization_name text,
    ministry_division text,
    pe_office_name text,
    procurement_nature text,
    procurement_method text,
    work_category text,
    remarks text,
    comments_by_pe text
);


--
-- Name: subscription_plans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscription_plans (
    id character varying(36) NOT NULL,
    name character varying(100) NOT NULL,
    monthly_tender_limit integer,
    monthly_price_bdt numeric(12,2),
    features json,
    is_active boolean,
    created_at timestamp with time zone
);


--
-- Name: tenant_members; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenant_members (
    id character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    tenant_id character varying(36) NOT NULL,
    role_id character varying(36) NOT NULL,
    is_owner boolean NOT NULL,
    joined_at timestamp with time zone NOT NULL
);


--
-- Name: tenants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tenants (
    id character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    slug character varying(100) NOT NULL,
    plan character varying(50),
    config json,
    is_active boolean,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: tender_data_pool; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tender_data_pool (
    id character varying(36) NOT NULL,
    tender_id character varying(100) NOT NULL,
    package_no character varying(100),
    work_name text,
    procuring_entity character varying(255),
    pe_office character varying(255),
    zone character varying(100),
    division character varying(100),
    district character varying(100),
    publication_date timestamp without time zone,
    closing_date timestamp without time zone,
    opening_date timestamp without time zone,
    tender_security_amount numeric(16,2),
    performance_security_amount numeric(16,2),
    completion_period_days integer,
    estimated_amount_bdt numeric(16,2),
    tender_fee numeric(12,2),
    min_experience_years integer,
    min_turnover_bdt numeric(16,2),
    min_liquid_assets_bdt numeric(16,2),
    min_annual_construction_volume numeric(16,2),
    similar_works_required integer,
    required_equipment json,
    required_personnel json,
    required_licenses json,
    special_qualifications json,
    boq_items json,
    boq_total numeric(16,2),
    nit_url text,
    tds_url text,
    boq_url text,
    drawings_url text,
    corrigendum_urls json,
    extraction_status character varying(20),
    source_format character varying(10),
    raw_data_ref text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: tender_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tender_documents (
    tender_id character varying(36) NOT NULL,
    doc_type public.documenttype NOT NULL,
    filename character varying(255) NOT NULL,
    file_path character varying(500) NOT NULL,
    file_size integer NOT NULL,
    mime_type character varying(100),
    extracted_text text,
    attributes json NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: tender_preparations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tender_preparations (
    id character varying(36) NOT NULL,
    tender_id character varying(100) NOT NULL,
    tenant_id character varying(36),
    forms_required json,
    forms_completed json,
    forms_missing json,
    document_map json,
    status character varying(50),
    completeness_pct double precision,
    contract_signing_required json,
    contract_signing_completed json,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);


--
-- Name: tender_price_models; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tender_price_models (
    id character varying(36) NOT NULL,
    model_version character varying(50) NOT NULL,
    model_blob bytea,
    feature_importance_json json,
    validation_rmse double precision,
    validation_r2 double precision,
    training_rmse double precision,
    training_r2 double precision,
    training_samples integer,
    is_active boolean DEFAULT false NOT NULL,
    trained_at timestamp with time zone,
    deployed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: tender_qualification_scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tender_qualification_scores (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tender_id text NOT NULL,
    contractor_id text NOT NULL,
    contractor_name text,
    qualification_score numeric(5,2) NOT NULL,
    recommendation text NOT NULL,
    confidence_pct numeric(5,2) NOT NULL,
    factors jsonb DEFAULT '{}'::jsonb NOT NULL,
    risk_factors jsonb DEFAULT '[]'::jsonb NOT NULL,
    explanation text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: tender_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tender_reports (
    id character varying(36) NOT NULL,
    tender_id character varying(100) NOT NULL,
    report_type character varying(50),
    report_data json,
    summary text,
    recommendations json,
    generated_by character varying(100),
    created_at timestamp with time zone
);


--
-- Name: tender_usage_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tender_usage_logs (
    id character varying(36) NOT NULL,
    tenant_id character varying(36) NOT NULL,
    tender_id character varying(100) NOT NULL,
    action character varying(50),
    quota_consumed integer,
    created_at timestamp with time zone
);


--
-- Name: user_queries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_queries (
    id character varying(36) NOT NULL,
    query_text text,
    query_type character varying(50),
    tender_id character varying(100),
    context json,
    response_summary text,
    response_time_ms integer,
    was_cached boolean,
    user_satisfaction character varying(20),
    created_at timestamp with time zone
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    email character varying(255) NOT NULL,
    hashed_password character varying(255) NOT NULL,
    full_name character varying(255),
    plan public.userplan NOT NULL,
    is_active boolean NOT NULL,
    is_superuser boolean NOT NULL,
    gpt_quota_used integer NOT NULL,
    gpt_quota_limit integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL,
    tenant_id character varying(36),
    role character varying(50) DEFAULT 'viewer'::character varying NOT NULL
);


--
-- Name: v_unmapped; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.v_unmapped (
    count bigint
);


--
-- Name: vw_category_trends; Type: MATERIALIZED VIEW; Schema: public; Owner: -
--

CREATE MATERIALIZED VIEW public.vw_category_trends AS
 SELECT c.category_id,
    c.category_name,
    c.sector,
    (date_trunc('month'::text, (t.published_date)::timestamp with time zone))::date AS month,
    count(DISTINCT t.tender_id) AS tender_count,
    sum(t.tender_value_bdt) AS total_value_bdt,
    avg(t.tender_value_bdt) AS avg_value_bdt
   FROM (public.fact_tenders t
     LEFT JOIN public.dim_categories c ON (((t.category_id)::text = (c.category_id)::text)))
  WHERE (t.published_date IS NOT NULL)
  GROUP BY c.category_id, c.category_name, c.sector, (date_trunc('month'::text, (t.published_date)::timestamp with time zone))
  WITH NO DATA;


--
-- Name: vw_contractor_performance; Type: MATERIALIZED VIEW; Schema: public; Owner: -
--

CREATE MATERIALIZED VIEW public.vw_contractor_performance AS
 SELECT c.contractor_id,
    c.contractor_name,
    count(DISTINCT b.bid_id) AS total_bids,
    count(DISTINCT
        CASE
            WHEN b.is_winner THEN b.bid_id
            ELSE NULL::character varying
        END) AS won_bids,
    round(((100.0 * (count(DISTINCT
        CASE
            WHEN b.is_winner THEN b.bid_id
            ELSE NULL::character varying
        END))::numeric) / (NULLIF(count(DISTINCT b.bid_id), 0))::numeric), 2) AS win_rate_pct,
    avg(b.bid_amount_bdt) AS avg_bid_amount_bdt,
    avg(a.award_value_bdt) AS avg_award_value_bdt,
    count(DISTINCT a.award_id) AS award_count
   FROM ((public.dim_contractors c
     LEFT JOIN public.fact_bids b ON (((c.contractor_id)::text = (b.contractor_id)::text)))
     LEFT JOIN public.fact_awards a ON (((c.contractor_id)::text = (a.contractor_id)::text)))
  GROUP BY c.contractor_id, c.contractor_name
  WITH NO DATA;


--
-- Name: vw_market_by_agency; Type: MATERIALIZED VIEW; Schema: public; Owner: -
--

CREATE MATERIALIZED VIEW public.vw_market_by_agency AS
 SELECT a.agency_id,
    a.agency_code,
    a.agency_name,
    count(DISTINCT t.tender_id) AS tender_count,
    sum(t.tender_value_bdt) AS total_value_bdt,
    avg(t.tender_value_bdt) AS avg_value_bdt,
    avg(t.duration_days) AS avg_duration_days,
    count(DISTINCT
        CASE
            WHEN ((t.status)::text = 'awarded'::text) THEN t.tender_id
            ELSE NULL::character varying
        END) AS awarded_count
   FROM (public.dim_agencies a
     LEFT JOIN public.fact_tenders t ON (((a.agency_id)::text = (t.agency_id)::text)))
  GROUP BY a.agency_id, a.agency_code, a.agency_name
  WITH NO DATA;


--
-- Name: vw_market_by_zone; Type: MATERIALIZED VIEW; Schema: public; Owner: -
--

CREATE MATERIALIZED VIEW public.vw_market_by_zone AS
 SELECT z.zone_id,
    z.zone_name,
    z.region,
    EXTRACT(year_month FROM t.published_date) AS year_month,
    count(DISTINCT t.tender_id) AS tender_count,
    sum(t.tender_value_bdt) AS total_value_bdt,
    avg(t.tender_value_bdt) AS avg_value_bdt
   FROM (public.dim_zones z
     LEFT JOIN public.fact_tenders t ON (((z.zone_id)::text = (t.zone_id)::text)))
  WHERE (t.published_date IS NOT NULL)
  GROUP BY z.zone_id, z.zone_name, z.region, (EXTRACT(year_month FROM t.published_date))
  WITH NO DATA;


--
-- Name: vw_tender_volume_monthly; Type: MATERIALIZED VIEW; Schema: public; Owner: -
--

CREATE MATERIALIZED VIEW public.vw_tender_volume_monthly AS
 SELECT (date_trunc('month'::text, (t.published_date)::timestamp with time zone))::date AS month,
    z.zone_id,
    count(DISTINCT t.tender_id) AS tender_count,
    sum(t.tender_value_bdt) AS total_value_bdt,
    avg(t.tender_value_bdt) AS avg_value_bdt
   FROM (public.fact_tenders t
     LEFT JOIN public.dim_zones z ON (((t.zone_id)::text = (z.zone_id)::text)))
  WHERE (t.published_date IS NOT NULL)
  GROUP BY (date_trunc('month'::text, (t.published_date)::timestamp with time zone)), z.zone_id
  WITH NO DATA;


--
-- Name: webhook_delivery_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook_delivery_logs (
    id character varying(36) NOT NULL,
    subscription_id character varying(36) NOT NULL,
    event_type character varying(100) NOT NULL,
    event_id character varying(100),
    payload json,
    payload_size_bytes integer NOT NULL,
    status_code integer,
    response_body text,
    response_time_ms integer NOT NULL,
    attempt_number integer NOT NULL,
    error_message text,
    stack_trace text,
    created_at timestamp with time zone NOT NULL
);


--
-- Name: webhook_subscriptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook_subscriptions (
    id character varying(36) NOT NULL,
    tenant_id character varying(36),
    url text NOT NULL,
    secret character varying(255),
    event_types json NOT NULL,
    event_filter text,
    is_active boolean NOT NULL,
    is_verified boolean NOT NULL,
    success_count integer NOT NULL,
    failure_count integer NOT NULL,
    last_status character varying(20),
    last_delivered_at timestamp with time zone,
    last_error text,
    max_retries integer NOT NULL,
    retry_interval_seconds integer NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by character varying(36)
);


--
-- Name: zone_intelligence; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.zone_intelligence (
    zone_name character varying(100) NOT NULL,
    total_contracts integer NOT NULL,
    total_amount_bdt double precision NOT NULL,
    active_agencies integer NOT NULL,
    avg_npp double precision NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: zones; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.zones (
    zone_name character varying(100) NOT NULL,
    zone_type character varying(20) NOT NULL,
    parent_zone_id character varying(36),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    id character varying(36) NOT NULL
);


--
-- Name: bid_recommendations; Type: TABLE; Schema: tender; Owner: -
--

CREATE TABLE tender.bid_recommendations (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    workspace_id character varying(36),
    should_bid boolean,
    recommendation character varying(50),
    confidence double precision,
    rationale text,
    risks json,
    recommendations json,
    expected_margin_low double precision,
    expected_margin_high double precision,
    required_resources json,
    evidence_chain_id character varying(36),
    summary text,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: boq_analyses; Type: TABLE; Schema: tender; Owner: -
--

CREATE TABLE tender.boq_analyses (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    workspace_id character varying(36),
    items json,
    anomalies json,
    total_quantity double precision,
    total_amount double precision,
    item_count integer,
    summary text,
    evidence_chain_id character varying(36),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: boq_items; Type: TABLE; Schema: tender; Owner: -
--

CREATE TABLE tender.boq_items (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    item_number character varying(50) NOT NULL,
    description character varying(500) NOT NULL,
    unit character varying(50) NOT NULL,
    quantity double precision NOT NULL,
    rate double precision,
    amount double precision,
    sor_reference character varying(100),
    normalized_description character varying(500),
    category character varying(100),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: compliance_results; Type: TABLE; Schema: tender; Owner: -
--

CREATE TABLE tender.compliance_results (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    workspace_id character varying(36),
    status character varying(50),
    checks json,
    violations json,
    score double precision,
    summary text,
    evidence_chain_id character varying(36),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: opportunities; Type: TABLE; Schema: tender; Owner: -
--

CREATE TABLE tender.opportunities (
    id character varying(36) NOT NULL,
    egp_reference character varying(100) NOT NULL,
    title character varying(500) NOT NULL,
    description text,
    procuring_entity_name character varying(300) NOT NULL,
    procuring_entity_id character varying(36),
    source character varying(50),
    status character varying(50),
    estimated_value double precision,
    currency character varying(3),
    published_date timestamp without time zone,
    submission_deadline timestamp without time zone,
    tender_document_ids json,
    category character varying(100),
    location character varying(200),
    metadata json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: qualification_criteria; Type: TABLE; Schema: tender; Owner: -
--

CREATE TABLE tender.qualification_criteria (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    criterion_type character varying(50) NOT NULL,
    description character varying(2000) NOT NULL,
    minimum_value double precision,
    unit character varying(50),
    is_mandatory boolean,
    clause_reference character varying(100),
    evidence_required json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: qualification_results; Type: TABLE; Schema: tender; Owner: -
--

CREATE TABLE tender.qualification_results (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    contractor_id character varying(36) NOT NULL,
    workspace_id character varying(36),
    status character varying(50),
    criteria_results json,
    score double precision,
    summary text,
    evidence_chain_id character varying(36),
    evaluated_by character varying(100),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: win_predictions; Type: TABLE; Schema: tender; Owner: -
--

CREATE TABLE tender.win_predictions (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    contractor_id character varying(36),
    workspace_id character varying(36),
    probability double precision,
    confidence double precision,
    status character varying(50),
    factors json,
    historical_match_score double precision,
    competition_count integer,
    agency_familiarity double precision,
    summary text,
    evidence_chain_id character varying(36),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: workspaces; Type: TABLE; Schema: tender; Owner: -
--

CREATE TABLE tender.workspaces (
    id character varying(36) NOT NULL,
    opportunity_id character varying(36) NOT NULL,
    current_phase character varying(50) NOT NULL,
    state character varying(50) NOT NULL,
    procuring_entity_id character varying(36),
    contractor_id character varying(36),
    tender_documents json,
    discovered_at timestamp without time zone NOT NULL,
    submission_deadline timestamp without time zone,
    submitted_at timestamp without time zone,
    awarded_at timestamp without time zone,
    estimated_value double precision,
    bid_amount double precision,
    currency character varying(3),
    qualification_ref character varying(36),
    boq_analysis_ref character varying(36),
    pricing_ref character varying(36),
    risk_ref character varying(36),
    compliance_ref character varying(36),
    win_prediction_ref character varying(36),
    strategy_ref character varying(36),
    action_log json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: agency_extraction_rules id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agency_extraction_rules ALTER COLUMN id SET DEFAULT nextval('public.agency_extraction_rules_id_seq'::regclass);


--
-- Name: agent_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_logs ALTER COLUMN id SET DEFAULT nextval('public.agent_logs_id_seq'::regclass);


--
-- Name: amount_normalization_audit id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.amount_normalization_audit ALTER COLUMN id SET DEFAULT nextval('public.amount_normalization_audit_id_seq'::regclass);


--
-- Name: app_tender_link id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_tender_link ALTER COLUMN id SET DEFAULT nextval('public.app_tender_link_id_seq'::regclass);


--
-- Name: clean_intel_agency_award_pattern id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_award_pattern ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_agency_award_pattern_id_seq'::regclass);


--
-- Name: clean_intel_agency_bidder_statistics id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_bidder_statistics ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_agency_bidder_statistics_id_seq'::regclass);


--
-- Name: clean_intel_agency_budget id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_budget ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_agency_budget_id_seq'::regclass);


--
-- Name: clean_intel_agency_contractor_network id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_contractor_network ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_agency_contractor_network_id_seq'::regclass);


--
-- Name: clean_intel_agency_delay_index id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_delay_index ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_agency_delay_index_id_seq'::regclass);


--
-- Name: clean_intel_agency_office_map id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_office_map ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_agency_office_map_id_seq'::regclass);


--
-- Name: clean_intel_agency_profile id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_profile ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_agency_profile_id_seq'::regclass);


--
-- Name: clean_intel_app_structure_summary id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_app_structure_summary ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_app_structure_summary_id_seq'::regclass);


--
-- Name: clean_intel_award_by_category id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_award_by_category ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_award_by_category_id_seq'::regclass);


--
-- Name: clean_intel_award_by_region id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_award_by_region ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_award_by_region_id_seq'::regclass);


--
-- Name: clean_intel_award_competitiveness id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_award_competitiveness ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_award_competitiveness_id_seq'::regclass);


--
-- Name: clean_intel_award_delay id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_award_delay ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_award_delay_id_seq'::regclass);


--
-- Name: clean_intel_award_summary id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_award_summary ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_award_summary_id_seq'::regclass);


--
-- Name: clean_intel_bid_discount_analysis id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_bid_discount_analysis ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_bid_discount_analysis_id_seq'::regclass);


--
-- Name: clean_intel_competitor_bid_aggressiveness id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_competitor_bid_aggressiveness ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_competitor_bid_aggressiveness_id_seq'::regclass);


--
-- Name: clean_intel_competitor_discount_pattern id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_competitor_discount_pattern ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_competitor_discount_pattern_id_seq'::regclass);


--
-- Name: clean_intel_competitor_market_share id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_competitor_market_share ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_competitor_market_share_id_seq'::regclass);


--
-- Name: clean_intel_competitor_profile id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_competitor_profile ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_competitor_profile_id_seq'::regclass);


--
-- Name: clean_intel_competitor_win_pattern id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_competitor_win_pattern ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_competitor_win_pattern_id_seq'::regclass);


--
-- Name: clean_intel_contractor_competitiveness id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_competitiveness ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_contractor_competitiveness_id_seq'::regclass);


--
-- Name: clean_intel_contractor_competitor_network id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_competitor_network ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_contractor_competitor_network_id_seq'::regclass);


--
-- Name: clean_intel_contractor_dna id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_dna ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_contractor_dna_id_seq'::regclass);


--
-- Name: clean_intel_contractor_experience_enriched id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_experience_enriched ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_contractor_experience_enriched_id_seq'::regclass);


--
-- Name: clean_intel_contractor_geographic_preference id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_geographic_preference ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_contractor_geographic_preference_id_seq'::regclass);


--
-- Name: clean_intel_contractor_growth_trend id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_growth_trend ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_contractor_growth_trend_id_seq'::regclass);


--
-- Name: clean_intel_contractor_heatmap id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_heatmap ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_contractor_heatmap_id_seq'::regclass);


--
-- Name: clean_intel_contractor_profile id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_profile ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_contractor_profile_id_seq'::regclass);


--
-- Name: clean_intel_contractor_recommendation id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_recommendation ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_contractor_recommendation_id_seq'::regclass);


--
-- Name: clean_intel_contractor_risk id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_risk ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_contractor_risk_id_seq'::regclass);


--
-- Name: clean_intel_contractor_sector_preference id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_sector_preference ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_contractor_sector_preference_id_seq'::regclass);


--
-- Name: clean_intel_contractor_success_rate id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_success_rate ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_contractor_success_rate_id_seq'::regclass);


--
-- Name: clean_intel_district_market id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_district_market ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_district_market_id_seq'::regclass);


--
-- Name: clean_intel_division_market id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_division_market ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_division_market_id_seq'::regclass);


--
-- Name: clean_intel_estimated_margin id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_estimated_margin ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_estimated_margin_id_seq'::regclass);


--
-- Name: clean_intel_expected_discount id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_expected_discount ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_expected_discount_id_seq'::regclass);


--
-- Name: clean_intel_feature_contractor id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_feature_contractor ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_feature_contractor_id_seq'::regclass);


--
-- Name: clean_intel_feature_market id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_feature_market ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_feature_market_id_seq'::regclass);


--
-- Name: clean_intel_feature_tender id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_feature_tender ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_feature_tender_id_seq'::regclass);


--
-- Name: clean_intel_likely_bidders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_likely_bidders ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_likely_bidders_id_seq'::regclass);


--
-- Name: clean_intel_likely_winner id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_likely_winner ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_likely_winner_id_seq'::regclass);


--
-- Name: clean_intel_market_price_index id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_market_price_index ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_market_price_index_id_seq'::regclass);


--
-- Name: clean_intel_market_snapshot id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_market_snapshot ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_market_snapshot_id_seq'::regclass);


--
-- Name: clean_intel_operational_metrics id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_operational_metrics ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_operational_metrics_id_seq'::regclass);


--
-- Name: clean_intel_regional_discount id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_regional_discount ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_regional_discount_id_seq'::regclass);


--
-- Name: clean_intel_regional_price_index id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_regional_price_index ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_regional_price_index_id_seq'::regclass);


--
-- Name: clean_intel_repeat_winner_analysis id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_repeat_winner_analysis ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_repeat_winner_analysis_id_seq'::regclass);


--
-- Name: clean_intel_tender_anomaly_detection id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_tender_anomaly_detection ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_tender_anomaly_detection_id_seq'::regclass);


--
-- Name: clean_intel_tender_complexity id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_tender_complexity ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_tender_complexity_id_seq'::regclass);


--
-- Name: clean_intel_tender_risk_score id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_tender_risk_score ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_tender_risk_score_id_seq'::regclass);


--
-- Name: clean_intel_tender_seasonality id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_tender_seasonality ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_tender_seasonality_id_seq'::regclass);


--
-- Name: clean_intel_tender_summary id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_tender_summary ALTER COLUMN id SET DEFAULT nextval('public.clean_intel_tender_summary_id_seq'::regclass);


--
-- Name: crawl_change_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_change_log ALTER COLUMN id SET DEFAULT nextval('public.crawl_change_log_id_seq'::regclass);


--
-- Name: crawl_checkpoints id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_checkpoints ALTER COLUMN id SET DEFAULT nextval('public.crawl_checkpoints_id_seq'::regclass);


--
-- Name: crawl_documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_documents ALTER COLUMN id SET DEFAULT nextval('public.crawl_documents_id_seq'::regclass);


--
-- Name: crawl_errors id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_errors ALTER COLUMN id SET DEFAULT nextval('public.crawl_errors_id_seq'::regclass);


--
-- Name: crawl_jobs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_jobs ALTER COLUMN id SET DEFAULT nextval('public.crawl_jobs_id_seq'::regclass);


--
-- Name: crawl_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_log ALTER COLUMN id SET DEFAULT nextval('public.crawl_log_id_seq'::regclass);


--
-- Name: data_quality_checks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_quality_checks ALTER COLUMN id SET DEFAULT nextval('public.data_quality_checks_id_seq'::regclass);


--
-- Name: pf_awards id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_awards ALTER COLUMN id SET DEFAULT nextval('public.pf_awards_id_seq'::regclass);


--
-- Name: pf_companies id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_companies ALTER COLUMN id SET DEFAULT nextval('public.pf_companies_id_seq'::regclass);


--
-- Name: pf_debarments id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_debarments ALTER COLUMN id SET DEFAULT nextval('public.pf_debarments_id_seq'::regclass);


--
-- Name: pf_document_embeddings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_document_embeddings ALTER COLUMN id SET DEFAULT nextval('public.pf_document_embeddings_id_seq'::regclass);


--
-- Name: pf_documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_documents ALTER COLUMN id SET DEFAULT nextval('public.pf_documents_id_seq'::regclass);


--
-- Name: pf_experience id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_experience ALTER COLUMN id SET DEFAULT nextval('public.pf_experience_id_seq'::regclass);


--
-- Name: pf_procuring_entities id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_procuring_entities ALTER COLUMN id SET DEFAULT nextval('public.pf_procuring_entities_id_seq'::regclass);


--
-- Name: pf_relationships id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_relationships ALTER COLUMN id SET DEFAULT nextval('public.pf_relationships_id_seq'::regclass);


--
-- Name: pf_tenders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_tenders ALTER COLUMN id SET DEFAULT nextval('public.pf_tenders_id_seq'::regclass);


--
-- Name: raw_app_listings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_app_listings ALTER COLUMN id SET DEFAULT nextval('public.raw_app_listings_id_seq'::regclass);


--
-- Name: raw_app_packages id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_app_packages ALTER COLUMN id SET DEFAULT nextval('public.raw_app_packages_id_seq'::regclass);


--
-- Name: raw_awards id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_awards ALTER COLUMN id SET DEFAULT nextval('public.raw_awards_id_seq'::regclass);


--
-- Name: raw_crawl_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_crawl_data ALTER COLUMN id SET DEFAULT nextval('public.raw_crawl_data_id_seq'::regclass);


--
-- Name: raw_debarment id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_debarment ALTER COLUMN id SET DEFAULT nextval('public.raw_debarment_id_seq'::regclass);


--
-- Name: raw_experience id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_experience ALTER COLUMN id SET DEFAULT nextval('public.raw_experience_id_seq'::regclass);


--
-- Name: raw_offline_awards id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_offline_awards ALTER COLUMN id SET DEFAULT nextval('public.raw_offline_awards_id_seq'::regclass);


--
-- Name: raw_offline_tenders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_offline_tenders ALTER COLUMN id SET DEFAULT nextval('public.raw_offline_tenders_id_seq'::regclass);


--
-- Name: raw_tenders id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_tenders ALTER COLUMN id SET DEFAULT nextval('public.raw_tenders_id_seq'::regclass);


--
-- Name: amendments amendments_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.amendments
    ADD CONSTRAINT amendments_pkey PRIMARY KEY (id);


--
-- Name: bid_security_requirements bid_security_requirements_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.bid_security_requirements
    ADD CONSTRAINT bid_security_requirements_pkey PRIMARY KEY (id);


--
-- Name: budget_lines budget_lines_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.budget_lines
    ADD CONSTRAINT budget_lines_pkey PRIMARY KEY (id);


--
-- Name: circulars circulars_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.circulars
    ADD CONSTRAINT circulars_pkey PRIMARY KEY (id);


--
-- Name: clauses clauses_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.clauses
    ADD CONSTRAINT clauses_pkey PRIMARY KEY (id);


--
-- Name: competitor_patterns competitor_patterns_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.competitor_patterns
    ADD CONSTRAINT competitor_patterns_pkey PRIMARY KEY (id);


--
-- Name: cost_estimates cost_estimates_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.cost_estimates
    ADD CONSTRAINT cost_estimates_pkey PRIMARY KEY (id);


--
-- Name: decisions decisions_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.decisions
    ADD CONSTRAINT decisions_pkey PRIMARY KEY (id);


--
-- Name: escalation_indices escalation_indices_index_code_key; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.escalation_indices
    ADD CONSTRAINT escalation_indices_index_code_key UNIQUE (index_code);


--
-- Name: escalation_indices escalation_indices_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.escalation_indices
    ADD CONSTRAINT escalation_indices_pkey PRIMARY KEY (id);


--
-- Name: estimate_sessions estimate_sessions_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.estimate_sessions
    ADD CONSTRAINT estimate_sessions_pkey PRIMARY KEY (id);


--
-- Name: financial_kpis financial_kpis_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.financial_kpis
    ADD CONSTRAINT financial_kpis_pkey PRIMARY KEY (id);


--
-- Name: financial_pipeline_summaries financial_pipeline_summaries_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.financial_pipeline_summaries
    ADD CONSTRAINT financial_pipeline_summaries_pkey PRIMARY KEY (id);


--
-- Name: financial_risks financial_risks_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.financial_risks
    ADD CONSTRAINT financial_risks_pkey PRIMARY KEY (id);


--
-- Name: financial_workflows financial_workflows_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.financial_workflows
    ADD CONSTRAINT financial_workflows_pkey PRIMARY KEY (id);


--
-- Name: formula_definitions formula_definitions_formula_name_key; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.formula_definitions
    ADD CONSTRAINT formula_definitions_formula_name_key UNIQUE (formula_name);


--
-- Name: formula_definitions formula_definitions_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.formula_definitions
    ADD CONSTRAINT formula_definitions_pkey PRIMARY KEY (id);


--
-- Name: formula_parameters formula_parameters_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.formula_parameters
    ADD CONSTRAINT formula_parameters_pkey PRIMARY KEY (id);


--
-- Name: historical_prices historical_prices_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.historical_prices
    ADD CONSTRAINT historical_prices_pkey PRIMARY KEY (id);


--
-- Name: legal_citations legal_citations_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.legal_citations
    ADD CONSTRAINT legal_citations_pkey PRIMARY KEY (id);


--
-- Name: margin_simulations margin_simulations_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.margin_simulations
    ADD CONSTRAINT margin_simulations_pkey PRIMARY KEY (id);


--
-- Name: market_rates market_rates_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.market_rates
    ADD CONSTRAINT market_rates_pkey PRIMARY KEY (id);


--
-- Name: nppi_datasets nppi_datasets_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.nppi_datasets
    ADD CONSTRAINT nppi_datasets_pkey PRIMARY KEY (id);


--
-- Name: nppi_projects nppi_projects_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.nppi_projects
    ADD CONSTRAINT nppi_projects_pkey PRIMARY KEY (id);


--
-- Name: nppi_projects nppi_projects_project_code_key; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.nppi_projects
    ADD CONSTRAINT nppi_projects_project_code_key UNIQUE (project_code);


--
-- Name: payment_schedules payment_schedules_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.payment_schedules
    ADD CONSTRAINT payment_schedules_pkey PRIMARY KEY (id);


--
-- Name: performance_guarantees performance_guarantees_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.performance_guarantees
    ADD CONSTRAINT performance_guarantees_pkey PRIMARY KEY (id);


--
-- Name: procurement_type_defs procurement_type_defs_code_key; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.procurement_type_defs
    ADD CONSTRAINT procurement_type_defs_code_key UNIQUE (code);


--
-- Name: procurement_type_defs procurement_type_defs_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.procurement_type_defs
    ADD CONSTRAINT procurement_type_defs_pkey PRIMARY KEY (id);


--
-- Name: rate_analyses rate_analyses_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.rate_analyses
    ADD CONSTRAINT rate_analyses_pkey PRIMARY KEY (id);


--
-- Name: regulation_documents regulation_documents_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.regulation_documents
    ADD CONSTRAINT regulation_documents_pkey PRIMARY KEY (id);


--
-- Name: regulation_versions regulation_versions_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.regulation_versions
    ADD CONSTRAINT regulation_versions_pkey PRIMARY KEY (id);


--
-- Name: rule_definitions rule_definitions_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.rule_definitions
    ADD CONSTRAINT rule_definitions_pkey PRIMARY KEY (id);


--
-- Name: rule_definitions rule_definitions_rule_id_key; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.rule_definitions
    ADD CONSTRAINT rule_definitions_rule_id_key UNIQUE (rule_id);


--
-- Name: rule_execution_logs rule_execution_logs_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.rule_execution_logs
    ADD CONSTRAINT rule_execution_logs_pkey PRIMARY KEY (id);


--
-- Name: scenario_results scenario_results_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.scenario_results
    ADD CONSTRAINT scenario_results_pkey PRIMARY KEY (id);


--
-- Name: sensitivity_analyses sensitivity_analyses_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.sensitivity_analyses
    ADD CONSTRAINT sensitivity_analyses_pkey PRIMARY KEY (id);


--
-- Name: slt_assessments slt_assessments_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.slt_assessments
    ADD CONSTRAINT slt_assessments_pkey PRIMARY KEY (id);


--
-- Name: weighted_average_calculations weighted_average_calculations_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.weighted_average_calculations
    ADD CONSTRAINT weighted_average_calculations_pkey PRIMARY KEY (id);


--
-- Name: working_capital working_capital_pkey; Type: CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.working_capital
    ADD CONSTRAINT working_capital_pkey PRIMARY KEY (id);


--
-- Name: clauses clauses_pkey; Type: CONSTRAINT; Schema: knowledge; Owner: -
--

ALTER TABLE ONLY knowledge.clauses
    ADD CONSTRAINT clauses_pkey PRIMARY KEY (id);


--
-- Name: dictionary_terms dictionary_terms_pkey; Type: CONSTRAINT; Schema: knowledge; Owner: -
--

ALTER TABLE ONLY knowledge.dictionary_terms
    ADD CONSTRAINT dictionary_terms_pkey PRIMARY KEY (id);


--
-- Name: document_nodes document_nodes_pkey; Type: CONSTRAINT; Schema: knowledge; Owner: -
--

ALTER TABLE ONLY knowledge.document_nodes
    ADD CONSTRAINT document_nodes_pkey PRIMARY KEY (id);


--
-- Name: document_relationships document_relationships_pkey; Type: CONSTRAINT; Schema: knowledge; Owner: -
--

ALTER TABLE ONLY knowledge.document_relationships
    ADD CONSTRAINT document_relationships_pkey PRIMARY KEY (id);


--
-- Name: agency_extraction_rules agency_extraction_rules_pattern_match_field_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agency_extraction_rules
    ADD CONSTRAINT agency_extraction_rules_pattern_match_field_key UNIQUE (pattern, match_field);


--
-- Name: agency_extraction_rules agency_extraction_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agency_extraction_rules
    ADD CONSTRAINT agency_extraction_rules_pkey PRIMARY KEY (id);


--
-- Name: agent_brain_messages agent_brain_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_brain_messages
    ADD CONSTRAINT agent_brain_messages_pkey PRIMARY KEY (id);


--
-- Name: agent_jobs agent_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_jobs
    ADD CONSTRAINT agent_jobs_pkey PRIMARY KEY (id);


--
-- Name: agent_logs agent_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_logs
    ADD CONSTRAINT agent_logs_pkey PRIMARY KEY (id);


--
-- Name: agent_results agent_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_results
    ADD CONSTRAINT agent_results_pkey PRIMARY KEY (id);


--
-- Name: agent_thoughts agent_thoughts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_thoughts
    ADD CONSTRAINT agent_thoughts_pkey PRIMARY KEY (id);


--
-- Name: alembic_version_commercial alembic_version_commercial_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version_commercial
    ADD CONSTRAINT alembic_version_commercial_pkc PRIMARY KEY (version_num);


--
-- Name: alembic_version_knowledge alembic_version_knowledge_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version_knowledge
    ADD CONSTRAINT alembic_version_knowledge_pkc PRIMARY KEY (version_num);


--
-- Name: alembic_version_tender alembic_version_tender_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version_tender
    ADD CONSTRAINT alembic_version_tender_pkc PRIMARY KEY (version_num);


--
-- Name: amount_normalization_audit amount_normalization_audit_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.amount_normalization_audit
    ADD CONSTRAINT amount_normalization_audit_pkey PRIMARY KEY (id);


--
-- Name: app_tender_link app_tender_link_app_id_pkg_id_tender_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_tender_link
    ADD CONSTRAINT app_tender_link_app_id_pkg_id_tender_id_key UNIQUE (app_id, pkg_id, tender_id);


--
-- Name: app_tender_link app_tender_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_tender_link
    ADD CONSTRAINT app_tender_link_pkey PRIMARY KEY (id);


--
-- Name: awards awards_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.awards
    ADD CONSTRAINT awards_pkey PRIMARY KEY (id);


--
-- Name: canonical_app_packages canonical_app_packages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_app_packages
    ADD CONSTRAINT canonical_app_packages_pkey PRIMARY KEY (canonical_app_id);


--
-- Name: canonical_awards canonical_awards_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_awards
    ADD CONSTRAINT canonical_awards_pkey PRIMARY KEY (canonical_award_id);


--
-- Name: canonical_contractor_aliases canonical_contractor_aliases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_contractor_aliases
    ADD CONSTRAINT canonical_contractor_aliases_pkey PRIMARY KEY (alias_key);


--
-- Name: canonical_contractor_dna canonical_contractor_dna_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_contractor_dna
    ADD CONSTRAINT canonical_contractor_dna_pkey PRIMARY KEY (canonical_contractor_id);


--
-- Name: canonical_contractor_jv_members canonical_contractor_jv_members_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_contractor_jv_members
    ADD CONSTRAINT canonical_contractor_jv_members_pkey PRIMARY KEY (jv_canonical_contractor_id, member_canonical_contractor_id);


--
-- Name: canonical_contractors canonical_contractors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_contractors
    ADD CONSTRAINT canonical_contractors_pkey PRIMARY KEY (canonical_contractor_id);


--
-- Name: canonical_contracts canonical_contracts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_contracts
    ADD CONSTRAINT canonical_contracts_pkey PRIMARY KEY (canonical_contract_id);


--
-- Name: canonical_identity_repair_queue canonical_identity_repair_que_entity_type_source_table_sour_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_identity_repair_queue
    ADD CONSTRAINT canonical_identity_repair_que_entity_type_source_table_sour_key UNIQUE (entity_type, source_table, source_id, issue_type);


--
-- Name: canonical_identity_repair_queue canonical_identity_repair_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_identity_repair_queue
    ADD CONSTRAINT canonical_identity_repair_queue_pkey PRIMARY KEY (repair_id);


--
-- Name: canonical_tenders canonical_tenders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_tenders
    ADD CONSTRAINT canonical_tenders_pkey PRIMARY KEY (canonical_package_key);


--
-- Name: clean_intel_agency_award_pattern clean_intel_agency_award_pattern_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_award_pattern
    ADD CONSTRAINT clean_intel_agency_award_pattern_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_agency_bidder_statistics clean_intel_agency_bidder_statistics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_bidder_statistics
    ADD CONSTRAINT clean_intel_agency_bidder_statistics_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_agency_budget clean_intel_agency_budget_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_budget
    ADD CONSTRAINT clean_intel_agency_budget_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_agency_contractor_network clean_intel_agency_contractor_network_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_contractor_network
    ADD CONSTRAINT clean_intel_agency_contractor_network_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_agency_delay_index clean_intel_agency_delay_index_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_delay_index
    ADD CONSTRAINT clean_intel_agency_delay_index_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_agency_office_map clean_intel_agency_office_map_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_office_map
    ADD CONSTRAINT clean_intel_agency_office_map_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_agency_profile clean_intel_agency_profile_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_agency_profile
    ADD CONSTRAINT clean_intel_agency_profile_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_app_structure_summary clean_intel_app_structure_summary_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_app_structure_summary
    ADD CONSTRAINT clean_intel_app_structure_summary_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_award_by_category clean_intel_award_by_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_award_by_category
    ADD CONSTRAINT clean_intel_award_by_category_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_award_by_region clean_intel_award_by_region_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_award_by_region
    ADD CONSTRAINT clean_intel_award_by_region_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_award_competitiveness clean_intel_award_competitiveness_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_award_competitiveness
    ADD CONSTRAINT clean_intel_award_competitiveness_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_award_delay clean_intel_award_delay_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_award_delay
    ADD CONSTRAINT clean_intel_award_delay_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_award_summary clean_intel_award_summary_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_award_summary
    ADD CONSTRAINT clean_intel_award_summary_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_bid_discount_analysis clean_intel_bid_discount_analysis_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_bid_discount_analysis
    ADD CONSTRAINT clean_intel_bid_discount_analysis_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_competitor_bid_aggressiveness clean_intel_competitor_bid_aggressiveness_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_competitor_bid_aggressiveness
    ADD CONSTRAINT clean_intel_competitor_bid_aggressiveness_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_competitor_discount_pattern clean_intel_competitor_discount_pattern_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_competitor_discount_pattern
    ADD CONSTRAINT clean_intel_competitor_discount_pattern_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_competitor_market_share clean_intel_competitor_market_share_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_competitor_market_share
    ADD CONSTRAINT clean_intel_competitor_market_share_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_competitor_profile clean_intel_competitor_profile_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_competitor_profile
    ADD CONSTRAINT clean_intel_competitor_profile_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_competitor_win_pattern clean_intel_competitor_win_pattern_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_competitor_win_pattern
    ADD CONSTRAINT clean_intel_competitor_win_pattern_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_contractor_competitiveness clean_intel_contractor_competitiveness_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_competitiveness
    ADD CONSTRAINT clean_intel_contractor_competitiveness_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_contractor_competitor_network clean_intel_contractor_competitor_network_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_competitor_network
    ADD CONSTRAINT clean_intel_contractor_competitor_network_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_contractor_dna clean_intel_contractor_dna_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_dna
    ADD CONSTRAINT clean_intel_contractor_dna_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_contractor_experience_enriched clean_intel_contractor_experience_enriched_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_experience_enriched
    ADD CONSTRAINT clean_intel_contractor_experience_enriched_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_contractor_geographic_preference clean_intel_contractor_geographic_preference_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_geographic_preference
    ADD CONSTRAINT clean_intel_contractor_geographic_preference_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_contractor_growth_trend clean_intel_contractor_growth_trend_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_growth_trend
    ADD CONSTRAINT clean_intel_contractor_growth_trend_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_contractor_heatmap clean_intel_contractor_heatmap_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_heatmap
    ADD CONSTRAINT clean_intel_contractor_heatmap_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_contractor_profile clean_intel_contractor_profile_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_profile
    ADD CONSTRAINT clean_intel_contractor_profile_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_contractor_recommendation clean_intel_contractor_recommendation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_recommendation
    ADD CONSTRAINT clean_intel_contractor_recommendation_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_contractor_risk clean_intel_contractor_risk_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_risk
    ADD CONSTRAINT clean_intel_contractor_risk_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_contractor_sector_preference clean_intel_contractor_sector_preference_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_sector_preference
    ADD CONSTRAINT clean_intel_contractor_sector_preference_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_contractor_success_rate clean_intel_contractor_success_rate_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_contractor_success_rate
    ADD CONSTRAINT clean_intel_contractor_success_rate_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_district_market clean_intel_district_market_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_district_market
    ADD CONSTRAINT clean_intel_district_market_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_division_market clean_intel_division_market_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_division_market
    ADD CONSTRAINT clean_intel_division_market_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_estimated_margin clean_intel_estimated_margin_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_estimated_margin
    ADD CONSTRAINT clean_intel_estimated_margin_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_expected_discount clean_intel_expected_discount_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_expected_discount
    ADD CONSTRAINT clean_intel_expected_discount_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_feature_contractor clean_intel_feature_contractor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_feature_contractor
    ADD CONSTRAINT clean_intel_feature_contractor_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_feature_market clean_intel_feature_market_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_feature_market
    ADD CONSTRAINT clean_intel_feature_market_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_feature_tender clean_intel_feature_tender_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_feature_tender
    ADD CONSTRAINT clean_intel_feature_tender_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_likely_bidders clean_intel_likely_bidders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_likely_bidders
    ADD CONSTRAINT clean_intel_likely_bidders_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_likely_winner clean_intel_likely_winner_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_likely_winner
    ADD CONSTRAINT clean_intel_likely_winner_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_market_price_index clean_intel_market_price_index_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_market_price_index
    ADD CONSTRAINT clean_intel_market_price_index_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_market_snapshot clean_intel_market_snapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_market_snapshot
    ADD CONSTRAINT clean_intel_market_snapshot_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_operational_metrics clean_intel_operational_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_operational_metrics
    ADD CONSTRAINT clean_intel_operational_metrics_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_regional_discount clean_intel_regional_discount_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_regional_discount
    ADD CONSTRAINT clean_intel_regional_discount_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_regional_price_index clean_intel_regional_price_index_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_regional_price_index
    ADD CONSTRAINT clean_intel_regional_price_index_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_repeat_winner_analysis clean_intel_repeat_winner_analysis_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_repeat_winner_analysis
    ADD CONSTRAINT clean_intel_repeat_winner_analysis_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_tender_anomaly_detection clean_intel_tender_anomaly_detection_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_tender_anomaly_detection
    ADD CONSTRAINT clean_intel_tender_anomaly_detection_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_tender_complexity clean_intel_tender_complexity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_tender_complexity
    ADD CONSTRAINT clean_intel_tender_complexity_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_tender_risk_score clean_intel_tender_risk_score_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_tender_risk_score
    ADD CONSTRAINT clean_intel_tender_risk_score_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_tender_seasonality clean_intel_tender_seasonality_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_tender_seasonality
    ADD CONSTRAINT clean_intel_tender_seasonality_pkey PRIMARY KEY (id);


--
-- Name: clean_intel_tender_summary clean_intel_tender_summary_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clean_intel_tender_summary
    ADD CONSTRAINT clean_intel_tender_summary_pkey PRIMARY KEY (id);


--
-- Name: client_priority_states client_priority_states_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_priority_states
    ADD CONSTRAINT client_priority_states_pkey PRIMARY KEY (id);


--
-- Name: client_subscriptions client_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_subscriptions
    ADD CONSTRAINT client_subscriptions_pkey PRIMARY KEY (id);


--
-- Name: compliance_checks compliance_checks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compliance_checks
    ADD CONSTRAINT compliance_checks_pkey PRIMARY KEY (id);


--
-- Name: contractor_agency_experience contractor_agency_experience_contractor_name_agency_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_agency_experience
    ADD CONSTRAINT contractor_agency_experience_contractor_name_agency_code_key UNIQUE (contractor_name, agency_code);


--
-- Name: contractor_agency_experience contractor_agency_experience_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_agency_experience
    ADD CONSTRAINT contractor_agency_experience_pkey PRIMARY KEY (id);


--
-- Name: contractor_capacity contractor_capacity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_capacity
    ADD CONSTRAINT contractor_capacity_pkey PRIMARY KEY (id);


--
-- Name: contractor_district_experience contractor_district_experience_contractor_name_district_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_district_experience
    ADD CONSTRAINT contractor_district_experience_contractor_name_district_key UNIQUE (contractor_name, district);


--
-- Name: contractor_district_experience contractor_district_experience_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_district_experience
    ADD CONSTRAINT contractor_district_experience_pkey PRIMARY KEY (id);


--
-- Name: contractor_dna_v2 contractor_dna_v2_contractor_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_dna_v2
    ADD CONSTRAINT contractor_dna_v2_contractor_id_key UNIQUE (contractor_id);


--
-- Name: contractor_dna_v2 contractor_dna_v2_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_dna_v2
    ADD CONSTRAINT contractor_dna_v2_pkey PRIMARY KEY (id);


--
-- Name: contractor_execution_history contractor_execution_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_execution_history
    ADD CONSTRAINT contractor_execution_history_pkey PRIMARY KEY (id);


--
-- Name: contractor_finance contractor_finance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_finance
    ADD CONSTRAINT contractor_finance_pkey PRIMARY KEY (id);


--
-- Name: contractor_work_similarity contractor_work_similarity_contractor_name_work_type_keywor_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_work_similarity
    ADD CONSTRAINT contractor_work_similarity_contractor_name_work_type_keywor_key UNIQUE (contractor_name, work_type, keyword);


--
-- Name: contractor_work_similarity contractor_work_similarity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_work_similarity
    ADD CONSTRAINT contractor_work_similarity_pkey PRIMARY KEY (id);


--
-- Name: crawl_change_log crawl_change_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_change_log
    ADD CONSTRAINT crawl_change_log_pkey PRIMARY KEY (id);


--
-- Name: crawl_checkpoints crawl_checkpoints_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_checkpoints
    ADD CONSTRAINT crawl_checkpoints_pkey PRIMARY KEY (id);


--
-- Name: crawl_checkpoints crawl_checkpoints_plugin_checkpoint_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_checkpoints
    ADD CONSTRAINT crawl_checkpoints_plugin_checkpoint_key_key UNIQUE (plugin, checkpoint_key);


--
-- Name: crawl_documents crawl_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_documents
    ADD CONSTRAINT crawl_documents_pkey PRIMARY KEY (id);


--
-- Name: crawl_errors crawl_errors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_errors
    ADD CONSTRAINT crawl_errors_pkey PRIMARY KEY (id);


--
-- Name: crawl_heartbeats crawl_heartbeats_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_heartbeats
    ADD CONSTRAINT crawl_heartbeats_pkey PRIMARY KEY (worker_id);


--
-- Name: crawl_jobs crawl_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_jobs
    ADD CONSTRAINT crawl_jobs_pkey PRIMARY KEY (id);


--
-- Name: crawl_jobs crawl_jobs_run_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_jobs
    ADD CONSTRAINT crawl_jobs_run_id_key UNIQUE (run_id);


--
-- Name: crawl_log crawl_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crawl_log
    ADD CONSTRAINT crawl_log_pkey PRIMARY KEY (id);


--
-- Name: data_quality_checks data_quality_checks_check_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_quality_checks
    ADD CONSTRAINT data_quality_checks_check_name_key UNIQUE (check_name);


--
-- Name: data_quality_checks data_quality_checks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_quality_checks
    ADD CONSTRAINT data_quality_checks_pkey PRIMARY KEY (id);


--
-- Name: dim_agencies dim_agencies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_agencies
    ADD CONSTRAINT dim_agencies_pkey PRIMARY KEY (agency_id);


--
-- Name: dim_categories dim_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_categories
    ADD CONSTRAINT dim_categories_pkey PRIMARY KEY (category_id);


--
-- Name: dim_contractors dim_contractors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_contractors
    ADD CONSTRAINT dim_contractors_pkey PRIMARY KEY (contractor_id);


--
-- Name: dim_zones dim_zones_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dim_zones
    ADD CONSTRAINT dim_zones_pkey PRIMARY KEY (zone_id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: ecms_ongoing ecms_ongoing_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ecms_ongoing
    ADD CONSTRAINT ecms_ongoing_pkey PRIMARY KEY (id);


--
-- Name: eexperience_completed eexperience_completed_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eexperience_completed
    ADD CONSTRAINT eexperience_completed_pkey PRIMARY KEY (id);


--
-- Name: enriched_app enriched_app_app_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enriched_app
    ADD CONSTRAINT enriched_app_app_id_key UNIQUE (app_id);


--
-- Name: enriched_app enriched_app_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enriched_app
    ADD CONSTRAINT enriched_app_pkey PRIMARY KEY (id);


--
-- Name: enriched_awards enriched_awards_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enriched_awards
    ADD CONSTRAINT enriched_awards_pkey PRIMARY KEY (id);


--
-- Name: enriched_ecms enriched_ecms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.enriched_ecms
    ADD CONSTRAINT enriched_ecms_pkey PRIMARY KEY (id);


--
-- Name: experience_certificate_registry experience_certificate_registry_certificate_no_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.experience_certificate_registry
    ADD CONSTRAINT experience_certificate_registry_certificate_no_key UNIQUE (certificate_no);


--
-- Name: experience_certificate_registry experience_certificate_registry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.experience_certificate_registry
    ADD CONSTRAINT experience_certificate_registry_pkey PRIMARY KEY (id);


--
-- Name: fact_awards fact_awards_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_awards
    ADD CONSTRAINT fact_awards_pkey PRIMARY KEY (award_id);


--
-- Name: fact_bids fact_bids_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_bids
    ADD CONSTRAINT fact_bids_pkey PRIMARY KEY (bid_id);


--
-- Name: fact_tenders fact_tenders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_tenders
    ADD CONSTRAINT fact_tenders_pkey PRIMARY KEY (tender_id);


--
-- Name: feedback_labels feedback_labels_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feedback_labels
    ADD CONSTRAINT feedback_labels_pkey PRIMARY KEY (id);


--
-- Name: idp_configs idp_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.idp_configs
    ADD CONSTRAINT idp_configs_pkey PRIMARY KEY (id);


--
-- Name: lifecycle lifecycle_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lifecycle
    ADD CONSTRAINT lifecycle_pkey PRIMARY KEY (id);


--
-- Name: market_rates market_rates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.market_rates
    ADD CONSTRAINT market_rates_pkey PRIMARY KEY (id);


--
-- Name: material_margins material_margins_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_margins
    ADD CONSTRAINT material_margins_pkey PRIMARY KEY (id);


--
-- Name: material_prices material_prices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.material_prices
    ADD CONSTRAINT material_prices_pkey PRIMARY KEY (id);


--
-- Name: npp_records npp_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.npp_records
    ADD CONSTRAINT npp_records_pkey PRIMARY KEY (id);


--
-- Name: nppi_indices nppi_indices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nppi_indices
    ADD CONSTRAINT nppi_indices_pkey PRIMARY KEY (id);


--
-- Name: opening_reports opening_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opening_reports
    ADD CONSTRAINT opening_reports_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: package_tender_bridge package_tender_bridge_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.package_tender_bridge
    ADD CONSTRAINT package_tender_bridge_pkey PRIMARY KEY (norm_pkg, tender_id);


--
-- Name: pf_awards pf_awards_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_awards
    ADD CONSTRAINT pf_awards_pkey PRIMARY KEY (id);


--
-- Name: pf_companies pf_companies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_companies
    ADD CONSTRAINT pf_companies_pkey PRIMARY KEY (id);


--
-- Name: pf_companies pf_companies_registration_no_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_companies
    ADD CONSTRAINT pf_companies_registration_no_key UNIQUE (registration_no);


--
-- Name: pf_debarments pf_debarments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_debarments
    ADD CONSTRAINT pf_debarments_pkey PRIMARY KEY (id);


--
-- Name: pf_document_embeddings pf_document_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_document_embeddings
    ADD CONSTRAINT pf_document_embeddings_pkey PRIMARY KEY (id);


--
-- Name: pf_documents pf_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_documents
    ADD CONSTRAINT pf_documents_pkey PRIMARY KEY (id);


--
-- Name: pf_experience pf_experience_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_experience
    ADD CONSTRAINT pf_experience_pkey PRIMARY KEY (id);


--
-- Name: pf_procuring_entities pf_procuring_entities_name_organization_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_procuring_entities
    ADD CONSTRAINT pf_procuring_entities_name_organization_id_key UNIQUE (name, organization_id);


--
-- Name: pf_procuring_entities pf_procuring_entities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_procuring_entities
    ADD CONSTRAINT pf_procuring_entities_pkey PRIMARY KEY (id);


--
-- Name: pf_relationships pf_relationships_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_relationships
    ADD CONSTRAINT pf_relationships_pkey PRIMARY KEY (id);


--
-- Name: pf_tenders pf_tenders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_tenders
    ADD CONSTRAINT pf_tenders_pkey PRIMARY KEY (id);


--
-- Name: pf_tenders pf_tenders_tender_id_package_no_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_tenders
    ADD CONSTRAINT pf_tenders_tender_id_package_no_key UNIQUE (tender_id, package_no);


--
-- Name: agencies pk_agencies; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agencies
    ADD CONSTRAINT pk_agencies PRIMARY KEY (id);


--
-- Name: agency_intelligence pk_agency_intelligence; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agency_intelligence
    ADD CONSTRAINT pk_agency_intelligence PRIMARY KEY (id);


--
-- Name: amendments pk_amendments; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.amendments
    ADD CONSTRAINT pk_amendments PRIMARY KEY (id);


--
-- Name: app_records pk_app_records; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_records
    ADD CONSTRAINT pk_app_records PRIMARY KEY (id);


--
-- Name: archived_records pk_archived_records; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.archived_records
    ADD CONSTRAINT pk_archived_records PRIMARY KEY (id);


--
-- Name: audit_logs pk_audit_logs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT pk_audit_logs PRIMARY KEY (id);


--
-- Name: award_intelligence pk_award_intelligence; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.award_intelligence
    ADD CONSTRAINT pk_award_intelligence PRIMARY KEY (id);


--
-- Name: award_records pk_award_records; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.award_records
    ADD CONSTRAINT pk_award_records PRIMARY KEY (id);


--
-- Name: award_records_v2 pk_award_records_v2; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.award_records_v2
    ADD CONSTRAINT pk_award_records_v2 PRIMARY KEY (id);


--
-- Name: bid_price_models pk_bid_price_models; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bid_price_models
    ADD CONSTRAINT pk_bid_price_models PRIMARY KEY (id);


--
-- Name: boq_comparisons pk_boq_comparisons; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.boq_comparisons
    ADD CONSTRAINT pk_boq_comparisons PRIMARY KEY (id);


--
-- Name: boq_items pk_boq_items; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.boq_items
    ADD CONSTRAINT pk_boq_items PRIMARY KEY (id);


--
-- Name: boq_jobs pk_boq_jobs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.boq_jobs
    ADD CONSTRAINT pk_boq_jobs PRIMARY KEY (id);


--
-- Name: bwdb_alerts pk_bwdb_alerts; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bwdb_alerts
    ADD CONSTRAINT pk_bwdb_alerts PRIMARY KEY (id);


--
-- Name: circulars pk_circulars; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.circulars
    ADD CONSTRAINT pk_circulars PRIMARY KEY (id);


--
-- Name: clauses pk_clauses; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clauses
    ADD CONSTRAINT pk_clauses PRIMARY KEY (id);


--
-- Name: competitor_awards pk_competitor_awards; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competitor_awards
    ADD CONSTRAINT pk_competitor_awards PRIMARY KEY (id);


--
-- Name: competitor_profiles pk_competitor_profiles; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competitor_profiles
    ADD CONSTRAINT pk_competitor_profiles PRIMARY KEY (id);


--
-- Name: contractor_dna pk_contractor_dna; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_dna
    ADD CONSTRAINT pk_contractor_dna PRIMARY KEY (id);


--
-- Name: contractor_documents pk_contractor_documents; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractor_documents
    ADD CONSTRAINT pk_contractor_documents PRIMARY KEY (id);


--
-- Name: contractors pk_contractors; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contractors
    ADD CONSTRAINT pk_contractors PRIMARY KEY (id);


--
-- Name: data_retention_policies pk_data_retention_policies; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_retention_policies
    ADD CONSTRAINT pk_data_retention_policies PRIMARY KEY (id);


--
-- Name: discount_patterns pk_discount_patterns; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.discount_patterns
    ADD CONSTRAINT pk_discount_patterns PRIMARY KEY (id);


--
-- Name: econtract_execution pk_econtract_execution; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.econtract_execution
    ADD CONSTRAINT pk_econtract_execution PRIMARY KEY (id);


--
-- Name: epw3_forms pk_epw3_forms; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.epw3_forms
    ADD CONSTRAINT pk_epw3_forms PRIMARY KEY (id);


--
-- Name: knowledge_edges pk_knowledge_edges; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_edges
    ADD CONSTRAINT pk_knowledge_edges PRIMARY KEY (id);


--
-- Name: knowledge_embeddings pk_knowledge_embeddings; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_embeddings
    ADD CONSTRAINT pk_knowledge_embeddings PRIMARY KEY (id);


--
-- Name: knowledge_entries pk_knowledge_entries; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_entries
    ADD CONSTRAINT pk_knowledge_entries PRIMARY KEY (id);


--
-- Name: knowledge_nodes pk_knowledge_nodes; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_nodes
    ADD CONSTRAINT pk_knowledge_nodes PRIMARY KEY (id);


--
-- Name: learning_outcomes pk_learning_outcomes; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.learning_outcomes
    ADD CONSTRAINT pk_learning_outcomes PRIMARY KEY (id);


--
-- Name: live_tender_sources pk_live_tender_sources; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.live_tender_sources
    ADD CONSTRAINT pk_live_tender_sources PRIMARY KEY (id);


--
-- Name: permissions pk_permissions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permissions
    ADD CONSTRAINT pk_permissions PRIMARY KEY (id);


--
-- Name: phase2_documents pk_phase2_documents; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phase2_documents
    ADD CONSTRAINT pk_phase2_documents PRIMARY KEY (id);


--
-- Name: phase2_team_members pk_phase2_team_members; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phase2_team_members
    ADD CONSTRAINT pk_phase2_team_members PRIMARY KEY (id);


--
-- Name: phase2_teams pk_phase2_teams; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phase2_teams
    ADD CONSTRAINT pk_phase2_teams PRIMARY KEY (id);


--
-- Name: ppr_evaluations pk_ppr_evaluations; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ppr_evaluations
    ADD CONSTRAINT pk_ppr_evaluations PRIMARY KEY (id);


--
-- Name: ppr_rule_profiles pk_ppr_rule_profiles; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ppr_rule_profiles
    ADD CONSTRAINT pk_ppr_rule_profiles PRIMARY KEY (id);


--
-- Name: prediction_feedback pk_prediction_feedback; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prediction_feedback
    ADD CONSTRAINT pk_prediction_feedback PRIMARY KEY (feedback_id);


--
-- Name: procurement_lifecycle pk_procurement_lifecycle; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.procurement_lifecycle
    ADD CONSTRAINT pk_procurement_lifecycle PRIMARY KEY (id);


--
-- Name: procurement_tenders pk_procurement_tenders; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.procurement_tenders
    ADD CONSTRAINT pk_procurement_tenders PRIMARY KEY (id);


--
-- Name: procurement_types pk_procurement_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.procurement_types
    ADD CONSTRAINT pk_procurement_types PRIMARY KEY (id);


--
-- Name: refresh_tokens pk_refresh_tokens; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT pk_refresh_tokens PRIMARY KEY (id);


--
-- Name: regulation_documents pk_regulation_documents; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regulation_documents
    ADD CONSTRAINT pk_regulation_documents PRIMARY KEY (id);


--
-- Name: regulation_versions pk_regulation_versions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regulation_versions
    ADD CONSTRAINT pk_regulation_versions PRIMARY KEY (id);


--
-- Name: roles pk_roles; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT pk_roles PRIMARY KEY (id);


--
-- Name: rule_citations pk_rule_citations; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rule_citations
    ADD CONSTRAINT pk_rule_citations PRIMARY KEY (id);


--
-- Name: rule_execution_logs pk_rule_execution_logs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rule_execution_logs
    ADD CONSTRAINT pk_rule_execution_logs PRIMARY KEY (id);


--
-- Name: rule_versions pk_rule_versions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rule_versions
    ADD CONSTRAINT pk_rule_versions PRIMARY KEY (id);


--
-- Name: rules pk_rules; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rules
    ADD CONSTRAINT pk_rules PRIMARY KEY (id);


--
-- Name: slt_audit_logs pk_slt_audit_logs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.slt_audit_logs
    ADD CONSTRAINT pk_slt_audit_logs PRIMARY KEY (id);


--
-- Name: slt_evaluation_bids pk_slt_evaluation_bids; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.slt_evaluation_bids
    ADD CONSTRAINT pk_slt_evaluation_bids PRIMARY KEY (id);


--
-- Name: slt_evaluation_runs pk_slt_evaluation_runs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.slt_evaluation_runs
    ADD CONSTRAINT pk_slt_evaluation_runs PRIMARY KEY (id);


--
-- Name: sor_rates pk_sor_rates; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sor_rates
    ADD CONSTRAINT pk_sor_rates PRIMARY KEY (id);


--
-- Name: tenant_members pk_tenant_members; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_members
    ADD CONSTRAINT pk_tenant_members PRIMARY KEY (id);


--
-- Name: tender_documents pk_tender_documents; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tender_documents
    ADD CONSTRAINT pk_tender_documents PRIMARY KEY (id);


--
-- Name: tender_price_models pk_tender_price_models; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tender_price_models
    ADD CONSTRAINT pk_tender_price_models PRIMARY KEY (id);


--
-- Name: tenders pk_tenders; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenders
    ADD CONSTRAINT pk_tenders PRIMARY KEY (id);


--
-- Name: users pk_users; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT pk_users PRIMARY KEY (id);


--
-- Name: webhook_delivery_logs pk_webhook_delivery_logs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_delivery_logs
    ADD CONSTRAINT pk_webhook_delivery_logs PRIMARY KEY (id);


--
-- Name: webhook_subscriptions pk_webhook_subscriptions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_subscriptions
    ADD CONSTRAINT pk_webhook_subscriptions PRIMARY KEY (id);


--
-- Name: zone_intelligence pk_zone_intelligence; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.zone_intelligence
    ADD CONSTRAINT pk_zone_intelligence PRIMARY KEY (id);


--
-- Name: zones pk_zones; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.zones
    ADD CONSTRAINT pk_zones PRIMARY KEY (id);


--
-- Name: ppr_schedules ppr_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ppr_schedules
    ADD CONSTRAINT ppr_schedules_pkey PRIMARY KEY (id);


--
-- Name: pre_computed_intelligence pre_computed_intelligence_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pre_computed_intelligence
    ADD CONSTRAINT pre_computed_intelligence_pkey PRIMARY KEY (id);


--
-- Name: rate_analysis rate_analysis_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rate_analysis
    ADD CONSTRAINT rate_analysis_pkey PRIMARY KEY (id);


--
-- Name: raw_app_listings raw_app_listings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_app_listings
    ADD CONSTRAINT raw_app_listings_pkey PRIMARY KEY (id);


--
-- Name: raw_app_packages raw_app_packages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_app_packages
    ADD CONSTRAINT raw_app_packages_pkey PRIMARY KEY (id);


--
-- Name: raw_awards raw_awards_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_awards
    ADD CONSTRAINT raw_awards_pkey PRIMARY KEY (id);


--
-- Name: raw_crawl_data raw_crawl_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_crawl_data
    ADD CONSTRAINT raw_crawl_data_pkey PRIMARY KEY (id);


--
-- Name: raw_debarment raw_debarment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_debarment
    ADD CONSTRAINT raw_debarment_pkey PRIMARY KEY (id);


--
-- Name: raw_experience raw_experience_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_experience
    ADD CONSTRAINT raw_experience_pkey PRIMARY KEY (id);


--
-- Name: raw_import_batches raw_import_batches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_import_batches
    ADD CONSTRAINT raw_import_batches_pkey PRIMARY KEY (batch_id);


--
-- Name: raw_json_documents raw_json_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_json_documents
    ADD CONSTRAINT raw_json_documents_pkey PRIMARY KEY (raw_id);


--
-- Name: raw_json_documents raw_json_documents_source_path_source_index_payload_sha256_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_json_documents
    ADD CONSTRAINT raw_json_documents_source_path_source_index_payload_sha256_key UNIQUE (source_path, source_index, payload_sha256);


--
-- Name: raw_offline_awards raw_offline_awards_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_offline_awards
    ADD CONSTRAINT raw_offline_awards_pkey PRIMARY KEY (id);


--
-- Name: raw_offline_tenders raw_offline_tenders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_offline_tenders
    ADD CONSTRAINT raw_offline_tenders_pkey PRIMARY KEY (id);


--
-- Name: raw_tenders raw_tenders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_tenders
    ADD CONSTRAINT raw_tenders_pkey PRIMARY KEY (id);


--
-- Name: rulesets rulesets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rulesets
    ADD CONSTRAINT rulesets_pkey PRIMARY KEY (id);


--
-- Name: sso_sessions sso_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sso_sessions
    ADD CONSTRAINT sso_sessions_pkey PRIMARY KEY (id);


--
-- Name: staging_app_packages staging_app_packages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staging_app_packages
    ADD CONSTRAINT staging_app_packages_pkey PRIMARY KEY (staging_id);


--
-- Name: staging_awards staging_awards_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staging_awards
    ADD CONSTRAINT staging_awards_pkey PRIMARY KEY (staging_id);


--
-- Name: staging_ecms_ongoing staging_ecms_ongoing_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staging_ecms_ongoing
    ADD CONSTRAINT staging_ecms_ongoing_pkey PRIMARY KEY (staging_id);


--
-- Name: staging_econtracts staging_econtracts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staging_econtracts
    ADD CONSTRAINT staging_econtracts_pkey PRIMARY KEY (staging_id);


--
-- Name: subscription_plans subscription_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_plans
    ADD CONSTRAINT subscription_plans_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_pkey PRIMARY KEY (id);


--
-- Name: tenants tenants_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenants
    ADD CONSTRAINT tenants_slug_key UNIQUE (slug);


--
-- Name: tender_data_pool tender_data_pool_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tender_data_pool
    ADD CONSTRAINT tender_data_pool_pkey PRIMARY KEY (id);


--
-- Name: tender_preparations tender_preparations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tender_preparations
    ADD CONSTRAINT tender_preparations_pkey PRIMARY KEY (id);


--
-- Name: tender_qualification_scores tender_qualification_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tender_qualification_scores
    ADD CONSTRAINT tender_qualification_scores_pkey PRIMARY KEY (id);


--
-- Name: tender_reports tender_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tender_reports
    ADD CONSTRAINT tender_reports_pkey PRIMARY KEY (id);


--
-- Name: tender_usage_logs tender_usage_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tender_usage_logs
    ADD CONSTRAINT tender_usage_logs_pkey PRIMARY KEY (id);


--
-- Name: circulars uq_circulars_circular_no; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.circulars
    ADD CONSTRAINT uq_circulars_circular_no UNIQUE (circular_no);


--
-- Name: procurement_lifecycle uq_proc_lifecycle; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.procurement_lifecycle
    ADD CONSTRAINT uq_proc_lifecycle UNIQUE (package_no, winner, award_date);


--
-- Name: procurement_types uq_procurement_types_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.procurement_types
    ADD CONSTRAINT uq_procurement_types_code UNIQUE (code);


--
-- Name: procurement_tenders uq_pt_package; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.procurement_tenders
    ADD CONSTRAINT uq_pt_package UNIQUE (package_no);


--
-- Name: refresh_tokens uq_refresh_tokens_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash);


--
-- Name: regulation_documents uq_regulation_documents_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regulation_documents
    ADD CONSTRAINT uq_regulation_documents_code UNIQUE (code);


--
-- Name: sso_sessions uq_sso_sessions_idp_subject_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sso_sessions
    ADD CONSTRAINT uq_sso_sessions_idp_subject_id UNIQUE (idp_subject_id);


--
-- Name: user_queries user_queries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_queries
    ADD CONSTRAINT user_queries_pkey PRIMARY KEY (id);


--
-- Name: bid_recommendations bid_recommendations_pkey; Type: CONSTRAINT; Schema: tender; Owner: -
--

ALTER TABLE ONLY tender.bid_recommendations
    ADD CONSTRAINT bid_recommendations_pkey PRIMARY KEY (id);


--
-- Name: boq_analyses boq_analyses_pkey; Type: CONSTRAINT; Schema: tender; Owner: -
--

ALTER TABLE ONLY tender.boq_analyses
    ADD CONSTRAINT boq_analyses_pkey PRIMARY KEY (id);


--
-- Name: boq_items boq_items_pkey; Type: CONSTRAINT; Schema: tender; Owner: -
--

ALTER TABLE ONLY tender.boq_items
    ADD CONSTRAINT boq_items_pkey PRIMARY KEY (id);


--
-- Name: compliance_results compliance_results_pkey; Type: CONSTRAINT; Schema: tender; Owner: -
--

ALTER TABLE ONLY tender.compliance_results
    ADD CONSTRAINT compliance_results_pkey PRIMARY KEY (id);


--
-- Name: opportunities opportunities_egp_reference_key; Type: CONSTRAINT; Schema: tender; Owner: -
--

ALTER TABLE ONLY tender.opportunities
    ADD CONSTRAINT opportunities_egp_reference_key UNIQUE (egp_reference);


--
-- Name: opportunities opportunities_pkey; Type: CONSTRAINT; Schema: tender; Owner: -
--

ALTER TABLE ONLY tender.opportunities
    ADD CONSTRAINT opportunities_pkey PRIMARY KEY (id);


--
-- Name: qualification_criteria qualification_criteria_pkey; Type: CONSTRAINT; Schema: tender; Owner: -
--

ALTER TABLE ONLY tender.qualification_criteria
    ADD CONSTRAINT qualification_criteria_pkey PRIMARY KEY (id);


--
-- Name: qualification_results qualification_results_pkey; Type: CONSTRAINT; Schema: tender; Owner: -
--

ALTER TABLE ONLY tender.qualification_results
    ADD CONSTRAINT qualification_results_pkey PRIMARY KEY (id);


--
-- Name: win_predictions win_predictions_pkey; Type: CONSTRAINT; Schema: tender; Owner: -
--

ALTER TABLE ONLY tender.win_predictions
    ADD CONSTRAINT win_predictions_pkey PRIMARY KEY (id);


--
-- Name: workspaces workspaces_pkey; Type: CONSTRAINT; Schema: tender; Owner: -
--

ALTER TABLE ONLY tender.workspaces
    ADD CONSTRAINT workspaces_pkey PRIMARY KEY (id);


--
-- Name: idx_amendments_doc; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_amendments_doc ON commercial.amendments USING btree (document_id);


--
-- Name: idx_bidsec_opp; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_bidsec_opp ON commercial.bid_security_requirements USING btree (opportunity_id);


--
-- Name: idx_budget_code; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_budget_code ON commercial.budget_lines USING btree (budget_code);


--
-- Name: idx_budget_opp; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_budget_opp ON commercial.budget_lines USING btree (opportunity_id);


--
-- Name: idx_clauses_number; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_clauses_number ON commercial.clauses USING btree (clause_number);


--
-- Name: idx_clauses_version; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_clauses_version ON commercial.clauses USING btree (version_id);


--
-- Name: idx_comp_patterns_id; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_comp_patterns_id ON commercial.competitor_patterns USING btree (contractor_id);


--
-- Name: idx_decisions_tender; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_decisions_tender ON commercial.decisions USING btree (tender_id);


--
-- Name: idx_esc_index_code; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_esc_index_code ON commercial.escalation_indices USING btree (index_code);


--
-- Name: idx_est_sess_opp; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_est_sess_opp ON commercial.estimate_sessions USING btree (opportunity_id);


--
-- Name: idx_exec_logs_rule; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_exec_logs_rule ON commercial.rule_execution_logs USING btree (rule_id);


--
-- Name: idx_exec_logs_tender; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_exec_logs_tender ON commercial.rule_execution_logs USING btree (tender_id);


--
-- Name: idx_fin_wf_opp; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_fin_wf_opp ON commercial.financial_workflows USING btree (opportunity_id);


--
-- Name: idx_fin_wf_type; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_fin_wf_type ON commercial.financial_workflows USING btree (workflow_type);


--
-- Name: idx_formula_params_rule; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_formula_params_rule ON commercial.formula_parameters USING btree (rule_id);


--
-- Name: idx_legal_cit_clause; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_legal_cit_clause ON commercial.legal_citations USING btree (clause_number);


--
-- Name: idx_nppi_agency; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_nppi_agency ON commercial.nppi_datasets USING btree (agency);


--
-- Name: idx_nppi_proj_code; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_nppi_proj_code ON commercial.nppi_projects USING btree (project_code);


--
-- Name: idx_nppi_zone; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_nppi_zone ON commercial.nppi_datasets USING btree (zone);


--
-- Name: idx_perf_opp; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_perf_opp ON commercial.performance_guarantees USING btree (opportunity_id);


--
-- Name: idx_reg_versions_doc; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_reg_versions_doc ON commercial.regulation_versions USING btree (document_id);


--
-- Name: idx_rule_defs_rule_id; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_rule_defs_rule_id ON commercial.rule_definitions USING btree (rule_id);


--
-- Name: idx_rule_defs_status; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_rule_defs_status ON commercial.rule_definitions USING btree (status);


--
-- Name: idx_sa_opp; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_sa_opp ON commercial.sensitivity_analyses USING btree (opportunity_id);


--
-- Name: idx_slt_calc; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_slt_calc ON commercial.slt_assessments USING btree (calculation_id);


--
-- Name: idx_wac_tender; Type: INDEX; Schema: commercial; Owner: -
--

CREATE INDEX idx_wac_tender ON commercial.weighted_average_calculations USING btree (tender_id);


--
-- Name: ix_clauses_parent; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE INDEX ix_clauses_parent ON knowledge.clauses USING btree (parent_clause_id) WHERE (parent_clause_id IS NOT NULL);


--
-- Name: ix_clauses_source_number; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE UNIQUE INDEX ix_clauses_source_number ON knowledge.clauses USING btree (source, clause_number) WHERE (is_active = true);


--
-- Name: ix_dictionary_terms_abbreviation_of; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE INDEX ix_dictionary_terms_abbreviation_of ON knowledge.dictionary_terms USING btree (abbreviation_of) WHERE (abbreviation_of IS NOT NULL);


--
-- Name: ix_dictionary_terms_term_language; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE UNIQUE INDEX ix_dictionary_terms_term_language ON knowledge.dictionary_terms USING btree (term, language) WHERE (is_active = true);


--
-- Name: ix_knowledge_clauses_clause_number; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE INDEX ix_knowledge_clauses_clause_number ON knowledge.clauses USING btree (clause_number);


--
-- Name: ix_knowledge_clauses_source; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE INDEX ix_knowledge_clauses_source ON knowledge.clauses USING btree (source);


--
-- Name: ix_knowledge_dictionary_terms_category; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE INDEX ix_knowledge_dictionary_terms_category ON knowledge.dictionary_terms USING btree (category);


--
-- Name: ix_knowledge_dictionary_terms_domain; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE INDEX ix_knowledge_dictionary_terms_domain ON knowledge.dictionary_terms USING btree (domain);


--
-- Name: ix_knowledge_dictionary_terms_term; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE INDEX ix_knowledge_dictionary_terms_term ON knowledge.dictionary_terms USING btree (term);


--
-- Name: ix_knowledge_document_nodes_contract_id; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE INDEX ix_knowledge_document_nodes_contract_id ON knowledge.document_nodes USING btree (contract_id);


--
-- Name: ix_knowledge_document_nodes_document_type; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE INDEX ix_knowledge_document_nodes_document_type ON knowledge.document_nodes USING btree (document_type);


--
-- Name: ix_knowledge_document_nodes_project_id; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE INDEX ix_knowledge_document_nodes_project_id ON knowledge.document_nodes USING btree (project_id);


--
-- Name: ix_knowledge_document_relationships_source_document_id; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE INDEX ix_knowledge_document_relationships_source_document_id ON knowledge.document_relationships USING btree (source_document_id);


--
-- Name: ix_knowledge_document_relationships_target_document_id; Type: INDEX; Schema: knowledge; Owner: -
--

CREATE INDEX ix_knowledge_document_relationships_target_document_id ON knowledge.document_relationships USING btree (target_document_id);


--
-- Name: app_unmatched_tmp_norm_pkg_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX app_unmatched_tmp_norm_pkg_idx ON public.app_unmatched_tmp USING btree (norm_pkg);


--
-- Name: atl_fanout_tmp_tender_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX atl_fanout_tmp_tender_id_idx ON public.atl_fanout_tmp USING btree (tender_id);


--
-- Name: clean_intel_agency_award_pattern_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_agency_award_pattern_key_id_idx ON public.clean_intel_agency_award_pattern USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_agency_bidder_statistics_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_agency_bidder_statistics_key_id_idx ON public.clean_intel_agency_bidder_statistics USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_agency_budget_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_agency_budget_key_id_idx ON public.clean_intel_agency_budget USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_agency_contractor_network_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_agency_contractor_network_key_id_idx ON public.clean_intel_agency_contractor_network USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_agency_delay_index_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_agency_delay_index_key_id_idx ON public.clean_intel_agency_delay_index USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_agency_office_map_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_agency_office_map_key_id_idx ON public.clean_intel_agency_office_map USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_agency_profile_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_agency_profile_key_id_idx ON public.clean_intel_agency_profile USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_app_structure_summary_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_app_structure_summary_key_id_idx ON public.clean_intel_app_structure_summary USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_award_by_category_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_award_by_category_key_id_idx ON public.clean_intel_award_by_category USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_award_by_region_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_award_by_region_key_id_idx ON public.clean_intel_award_by_region USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_award_competitiveness_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_award_competitiveness_key_id_idx ON public.clean_intel_award_competitiveness USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_award_delay_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_award_delay_key_id_idx ON public.clean_intel_award_delay USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_award_summary_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_award_summary_key_id_idx ON public.clean_intel_award_summary USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_bid_discount_analysis_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_bid_discount_analysis_key_id_idx ON public.clean_intel_bid_discount_analysis USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_competitor_bid_aggressiveness_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_competitor_bid_aggressiveness_key_id_idx ON public.clean_intel_competitor_bid_aggressiveness USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_competitor_discount_pattern_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_competitor_discount_pattern_key_id_idx ON public.clean_intel_competitor_discount_pattern USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_competitor_market_share_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_competitor_market_share_key_id_idx ON public.clean_intel_competitor_market_share USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_competitor_profile_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_competitor_profile_key_id_idx ON public.clean_intel_competitor_profile USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_competitor_win_pattern_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_competitor_win_pattern_key_id_idx ON public.clean_intel_competitor_win_pattern USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_contractor_competitiveness_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_contractor_competitiveness_key_id_idx ON public.clean_intel_contractor_competitiveness USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_contractor_competitor_network_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_contractor_competitor_network_key_id_idx ON public.clean_intel_contractor_competitor_network USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_contractor_dna_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_contractor_dna_key_id_idx ON public.clean_intel_contractor_dna USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_contractor_experience_enriched_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_contractor_experience_enriched_key_id_idx ON public.clean_intel_contractor_experience_enriched USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_contractor_geographic_preference_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_contractor_geographic_preference_key_id_idx ON public.clean_intel_contractor_geographic_preference USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_contractor_growth_trend_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_contractor_growth_trend_key_id_idx ON public.clean_intel_contractor_growth_trend USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_contractor_heatmap_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_contractor_heatmap_key_id_idx ON public.clean_intel_contractor_heatmap USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_contractor_profile_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_contractor_profile_key_id_idx ON public.clean_intel_contractor_profile USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_contractor_recommendation_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_contractor_recommendation_key_id_idx ON public.clean_intel_contractor_recommendation USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_contractor_risk_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_contractor_risk_key_id_idx ON public.clean_intel_contractor_risk USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_contractor_sector_preference_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_contractor_sector_preference_key_id_idx ON public.clean_intel_contractor_sector_preference USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_contractor_success_rate_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_contractor_success_rate_key_id_idx ON public.clean_intel_contractor_success_rate USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_district_market_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_district_market_key_id_idx ON public.clean_intel_district_market USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_division_market_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_division_market_key_id_idx ON public.clean_intel_division_market USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_estimated_margin_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_estimated_margin_key_id_idx ON public.clean_intel_estimated_margin USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_expected_discount_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_expected_discount_key_id_idx ON public.clean_intel_expected_discount USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_feature_contractor_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_feature_contractor_key_id_idx ON public.clean_intel_feature_contractor USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_feature_market_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_feature_market_key_id_idx ON public.clean_intel_feature_market USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_feature_tender_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_feature_tender_key_id_idx ON public.clean_intel_feature_tender USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_likely_bidders_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_likely_bidders_key_id_idx ON public.clean_intel_likely_bidders USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_likely_winner_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_likely_winner_key_id_idx ON public.clean_intel_likely_winner USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_market_price_index_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_market_price_index_key_id_idx ON public.clean_intel_market_price_index USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_market_snapshot_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_market_snapshot_key_id_idx ON public.clean_intel_market_snapshot USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_operational_metrics_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_operational_metrics_key_id_idx ON public.clean_intel_operational_metrics USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_regional_discount_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_regional_discount_key_id_idx ON public.clean_intel_regional_discount USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_regional_price_index_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_regional_price_index_key_id_idx ON public.clean_intel_regional_price_index USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_repeat_winner_analysis_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_repeat_winner_analysis_key_id_idx ON public.clean_intel_repeat_winner_analysis USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_tender_anomaly_detection_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_tender_anomaly_detection_key_id_idx ON public.clean_intel_tender_anomaly_detection USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_tender_complexity_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_tender_complexity_key_id_idx ON public.clean_intel_tender_complexity USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_tender_risk_score_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_tender_risk_score_key_id_idx ON public.clean_intel_tender_risk_score USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_tender_seasonality_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_tender_seasonality_key_id_idx ON public.clean_intel_tender_seasonality USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_tender_summary_key_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_tender_summary_key_id_idx ON public.clean_intel_tender_summary USING btree (key_id) WHERE (key_id IS NOT NULL);


--
-- Name: clean_intel_works_agencies_next_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX clean_intel_works_agencies_next_id_idx ON public.clean_intel_works_agencies USING btree (id);


--
-- Name: clean_intel_works_agencies_next_key_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_works_agencies_next_key_idx ON public.clean_intel_works_agencies USING btree (key_id);


--
-- Name: clean_intel_works_award_trends_next_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX clean_intel_works_award_trends_next_id_idx ON public.clean_intel_works_award_trends USING btree (id);


--
-- Name: clean_intel_works_award_trends_next_key_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_works_award_trends_next_key_idx ON public.clean_intel_works_award_trends USING btree (key_id);


--
-- Name: clean_intel_works_contractors_next_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX clean_intel_works_contractors_next_id_idx ON public.clean_intel_works_contractors USING btree (id);


--
-- Name: clean_intel_works_contractors_next_key_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_works_contractors_next_key_idx ON public.clean_intel_works_contractors USING btree (key_id);


--
-- Name: clean_intel_works_lifecycle_next_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX clean_intel_works_lifecycle_next_id_idx ON public.clean_intel_works_lifecycle USING btree (id);


--
-- Name: clean_intel_works_lifecycle_next_key_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_works_lifecycle_next_key_idx ON public.clean_intel_works_lifecycle USING btree (key_id);


--
-- Name: clean_intel_works_zones_next_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX clean_intel_works_zones_next_id_idx ON public.clean_intel_works_zones USING btree (id);


--
-- Name: clean_intel_works_zones_next_key_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX clean_intel_works_zones_next_key_idx ON public.clean_intel_works_zones USING btree (key_id);


--
-- Name: idx_aem_app_pkg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aem_app_pkg ON public.app_ecms_award_map_mv USING btree (app_package_no);


--
-- Name: idx_aem_app_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aem_app_tender ON public.app_ecms_award_map_mv USING btree (app_tender_id);


--
-- Name: idx_aem_award_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aem_award_tender ON public.app_ecms_award_map_mv USING btree (award_tender_id);


--
-- Name: idx_aem_ecms_pkg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aem_ecms_pkg ON public.app_ecms_award_map_mv USING btree (ecms_package_no);


--
-- Name: idx_aem_ecms_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aem_ecms_tender ON public.app_ecms_award_map_mv USING btree (ecms_tender_id);


--
-- Name: idx_aer_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aer_category ON public.agency_extraction_rules USING btree (category);


--
-- Name: idx_aer_confidence; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aer_confidence ON public.agency_extraction_rules USING btree (confidence);


--
-- Name: idx_aer_field; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aer_field ON public.agency_extraction_rules USING btree (match_field);


--
-- Name: idx_aer_match_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aer_match_lookup ON public.agency_extraction_rules USING btree (match_field, priority DESC, pattern);


--
-- Name: idx_aer_pattern; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aer_pattern ON public.agency_extraction_rules USING btree (pattern);


--
-- Name: idx_aer_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aer_priority ON public.agency_extraction_rules USING btree (priority);


--
-- Name: idx_agency_perf_summary_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agency_perf_summary_code ON public.agency_performance_summary USING btree (agency_code);


--
-- Name: idx_agency_perf_summary_value; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agency_perf_summary_value ON public.agency_performance_summary USING btree (total_value_bdt DESC);


--
-- Name: idx_agent_result_agent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_result_agent ON public.agent_results USING btree (agent_id);


--
-- Name: idx_agent_result_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_result_status ON public.agent_results USING btree (status);


--
-- Name: idx_agent_result_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_agent_result_tender ON public.agent_results USING btree (tender_id);


--
-- Name: idx_app_pkg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_app_pkg ON public.raw_app_packages USING btree (((raw_data ->> 'app_id'::text)), ((raw_data ->> 'pkg_id'::text)));


--
-- Name: idx_app_records_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_app_records_category ON public.app_records USING btree (category) WHERE (category IS NOT NULL);


--
-- Name: idx_app_records_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_app_records_status ON public.app_records USING btree (status) WHERE (status IS NOT NULL);


--
-- Name: idx_arv2_agency_amount; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_arv2_agency_amount ON public.award_records_v2 USING btree (agency_code, amount_bdt DESC);


--
-- Name: idx_arv2_contractor_amount; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_arv2_contractor_amount ON public.award_records_v2 USING btree (contractor_name, amount_bdt DESC);


--
-- Name: idx_arv2_district_amount; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_arv2_district_amount ON public.award_records_v2 USING btree (district, amount_bdt DESC);


--
-- Name: idx_award_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_award_contractor ON public.awards USING btree (contractor_name);


--
-- Name: idx_award_map_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_award_map_agency ON public.award_full_map USING btree (agency_code);


--
-- Name: idx_award_map_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_award_map_contractor ON public.award_full_map USING btree (contractor_name);


--
-- Name: idx_award_map_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_award_map_date ON public.award_full_map USING btree (award_date);


--
-- Name: idx_award_map_fy; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_award_map_fy ON public.award_full_map USING btree (financial_year);


--
-- Name: idx_award_map_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_award_map_package ON public.award_full_map USING btree (package_no);


--
-- Name: idx_award_map_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_award_map_tender_id ON public.award_full_map USING btree (tender_id);


--
-- Name: idx_award_records_contractor_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_award_records_contractor_trgm ON public.award_records USING gin (contractor_name public.gin_trgm_ops);


--
-- Name: idx_award_records_v2_contractor_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_award_records_v2_contractor_trgm ON public.award_records_v2 USING gin (contractor_name public.gin_trgm_ops);


--
-- Name: idx_award_records_v2_fts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_award_records_v2_fts ON public.award_records_v2 USING gin (to_tsvector('simple'::regconfig, ((((COALESCE(title, ''::text) || ' '::text) || (COALESCE(contractor_name, ''::character varying))::text) || ' '::text) || (COALESCE(procuring_entity, ''::character varying))::text)));


--
-- Name: idx_award_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_award_tender_id ON public.awards USING btree (tender_id);


--
-- Name: idx_contractor_dna_health_score; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contractor_dna_health_score ON public.contractor_dna USING btree (health_score DESC) WHERE (health_score IS NOT NULL);


--
-- Name: idx_contractor_dna_preferred_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contractor_dna_preferred_agency ON public.contractor_dna USING btree (preferred_agency) WHERE (preferred_agency IS NOT NULL);


--
-- Name: idx_contractor_dna_win_rate; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contractor_dna_win_rate ON public.contractor_dna USING btree (win_rate DESC) WHERE (win_rate IS NOT NULL);


--
-- Name: idx_contractors_fts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contractors_fts ON public.contractors USING gin (to_tsvector('simple'::regconfig, (COALESCE(contractor_name, ''::character varying))::text));


--
-- Name: idx_contractors_name_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contractors_name_trgm ON public.contractors USING gin (contractor_name public.gin_trgm_ops);


--
-- Name: idx_cps_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cps_tenant ON public.client_priority_states USING btree (tenant_id);


--
-- Name: idx_cps_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cps_tender ON public.client_priority_states USING btree (tender_id);


--
-- Name: idx_doc_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_doc_tender_id ON public.documents USING btree (tender_id);


--
-- Name: idx_ecms_app_map_app_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ecms_app_map_app_package ON public.ecms_app_package_map_mv USING btree (app_package_no);


--
-- Name: idx_ecms_app_map_ecms_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ecms_app_map_ecms_id ON public.ecms_app_package_map_mv USING btree (ecms_id);


--
-- Name: idx_ecms_app_map_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ecms_app_map_package ON public.ecms_app_package_map_mv USING btree (ecms_package_no);


--
-- Name: idx_ecms_app_map_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ecms_app_map_tender ON public.ecms_app_package_map_mv USING btree (tender_id);


--
-- Name: idx_exp_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exp_tender_id ON public.raw_experience USING btree (((raw_data ->> 'tender_id'::text)));


--
-- Name: idx_feature_award_gin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_feature_award_gin ON public.clean_intel_feature_award USING gin (data);


--
-- Name: idx_knowledge_entries_tender_id_entry_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_knowledge_entries_tender_id_entry_type ON public.knowledge_entries USING btree (tender_id, entry_type);


--
-- Name: idx_knowledge_entries_tender_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_knowledge_entries_tender_type ON public.knowledge_entries USING btree (tender_id, entry_type);


--
-- Name: idx_knowledge_type_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_knowledge_type_tender ON public.knowledge_entries USING btree (entry_type, tender_id);


--
-- Name: idx_lifecycle_agency_award_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lifecycle_agency_award_date ON public.procurement_lifecycle USING btree (agency_code, award_date DESC);


--
-- Name: idx_lifecycle_app; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lifecycle_app ON public.lifecycle USING btree (app_id);


--
-- Name: idx_lifecycle_award; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lifecycle_award ON public.lifecycle USING btree (award_tender_id);


--
-- Name: idx_lifecycle_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lifecycle_tender ON public.lifecycle USING btree (tender_id);


--
-- Name: idx_lifecycle_title_package_fts; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lifecycle_title_package_fts ON public.procurement_lifecycle USING gin (to_tsvector('simple'::regconfig, ((COALESCE(title, ''::text) || ' '::text) || (COALESCE(package_no, ''::character varying))::text)));


--
-- Name: idx_lifecycle_title_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lifecycle_title_trgm ON public.procurement_lifecycle USING gin (title public.gin_trgm_ops) WHERE (title IS NOT NULL);


--
-- Name: idx_link_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_link_tender ON public.app_tender_link USING btree (tender_id);


--
-- Name: idx_margin_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_margin_category ON public.material_margins USING btree (material_category, agency, zone);


--
-- Name: idx_margin_code_agency_zone; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_margin_code_agency_zone ON public.material_margins USING btree (sor_code, agency, zone);


--
-- Name: idx_material_prices_cat; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_material_prices_cat ON public.material_prices USING btree (category);


--
-- Name: idx_material_prices_collected; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_material_prices_collected ON public.material_prices USING btree (collected_at);


--
-- Name: idx_npp_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_npp_agency ON public.npp_records USING btree (agency);


--
-- Name: idx_npp_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_npp_tender_id ON public.npp_records USING btree (tender_id);


--
-- Name: idx_nppi_agency_zone; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nppi_agency_zone ON public.nppi_indices USING btree (agency, zone, period_start);


--
-- Name: idx_offline_award_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_offline_award_tender_id ON public.raw_offline_awards USING btree (((raw_data ->> 'tender_id'::text)));


--
-- Name: idx_offline_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_offline_tender_id ON public.raw_offline_tenders USING btree (((raw_data ->> 'tender_id'::text)));


--
-- Name: idx_opening_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_opening_tender_id ON public.opening_reports USING btree (tender_id);


--
-- Name: idx_pci_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pci_key ON public.pre_computed_intelligence USING btree (cache_key);


--
-- Name: idx_pci_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pci_type ON public.pre_computed_intelligence USING btree (intelligence_type);


--
-- Name: idx_pf_experience_work_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pf_experience_work_trgm ON public.pf_experience USING gin (name_of_work public.gin_trgm_ops) WHERE (name_of_work IS NOT NULL);


--
-- Name: idx_rate_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rate_agency ON public.rate_analysis USING btree (agency);


--
-- Name: idx_rate_analysis_sor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rate_analysis_sor ON public.rate_analysis USING btree (sor_code);


--
-- Name: idx_rate_analysis_sor_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rate_analysis_sor_code ON public.rate_analysis USING btree (sor_code);


--
-- Name: idx_rate_rate_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rate_rate_id ON public.rate_analysis USING btree (rate_id);


--
-- Name: idx_sub_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sub_status ON public.client_subscriptions USING btree (status);


--
-- Name: idx_sub_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sub_tenant ON public.client_subscriptions USING btree (tenant_id);


--
-- Name: idx_tdp_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tdp_tender_id ON public.tender_data_pool USING btree (tender_id);


--
-- Name: idx_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tender_id ON public.raw_tenders USING btree (((raw_data ->> 'tender_id'::text)));


--
-- Name: idx_tender_qualification_scores_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tender_qualification_scores_contractor ON public.tender_qualification_scores USING btree (contractor_id, created_at DESC);


--
-- Name: idx_tender_qualification_scores_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tender_qualification_scores_tender ON public.tender_qualification_scores USING btree (tender_id, created_at DESC);


--
-- Name: idx_thought_agent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_thought_agent ON public.agent_thoughts USING btree (agent_id);


--
-- Name: idx_thought_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_thought_status ON public.agent_thoughts USING btree (status);


--
-- Name: idx_usage_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_tenant ON public.tender_usage_logs USING btree (tenant_id);


--
-- Name: idx_usage_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_tender ON public.tender_usage_logs USING btree (tender_id);


--
-- Name: ix_agencies_agency_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_agencies_agency_code ON public.agencies USING btree (agency_code);


--
-- Name: ix_agency_intelligence_agency_code; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_agency_intelligence_agency_code ON public.agency_intelligence USING btree (agency_code);


--
-- Name: ix_agent_brain_messages_recipient_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_brain_messages_recipient_id ON public.agent_brain_messages USING btree (recipient_id);


--
-- Name: ix_agent_brain_messages_sender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_brain_messages_sender_id ON public.agent_brain_messages USING btree (sender_id);


--
-- Name: ix_agent_brain_messages_thread_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_brain_messages_thread_id ON public.agent_brain_messages USING btree (thread_id);


--
-- Name: ix_agent_jobs_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_jobs_agent_id ON public.agent_jobs USING btree (agent_id);


--
-- Name: ix_agent_jobs_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_jobs_request_id ON public.agent_jobs USING btree (request_id);


--
-- Name: ix_agent_jobs_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_jobs_tender_id ON public.agent_jobs USING btree (tender_id);


--
-- Name: ix_agent_logs_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_logs_agent_id ON public.agent_logs USING btree (agent_id);


--
-- Name: ix_agent_logs_result_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_logs_result_id ON public.agent_logs USING btree (result_id);


--
-- Name: ix_agent_logs_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_logs_tender_id ON public.agent_logs USING btree (tender_id);


--
-- Name: ix_agent_results_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_results_agent_id ON public.agent_results USING btree (agent_id);


--
-- Name: ix_agent_results_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_results_request_id ON public.agent_results USING btree (request_id);


--
-- Name: ix_agent_results_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_results_tender_id ON public.agent_results USING btree (tender_id);


--
-- Name: ix_agent_thoughts_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_thoughts_agent_id ON public.agent_thoughts USING btree (agent_id);


--
-- Name: ix_agent_thoughts_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_agent_thoughts_tender_id ON public.agent_thoughts USING btree (tender_id);


--
-- Name: ix_amendments_effective_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_amendments_effective_date ON public.amendments USING btree (effective_date);


--
-- Name: ix_amendments_regulation_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_amendments_regulation_version_id ON public.amendments USING btree (regulation_version_id);


--
-- Name: ix_app_records_package_no; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_app_records_package_no ON public.app_records USING btree (package_no);


--
-- Name: ix_app_records_procurement_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_app_records_procurement_tender_id ON public.app_records USING btree (procurement_tender_id);


--
-- Name: ix_app_records_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_app_records_tender_id ON public.app_records USING btree (procurement_tender_id);


--
-- Name: ix_ar_normalized_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ar_normalized_package ON public.app_records USING btree (normalized_package_no);


--
-- Name: ix_archived_records_delete_after; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_archived_records_delete_after ON public.archived_records USING btree (delete_after);


--
-- Name: ix_archived_records_resource_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_archived_records_resource_type ON public.archived_records USING btree (resource_type);


--
-- Name: ix_archived_records_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_archived_records_source_id ON public.archived_records USING btree (source_id);


--
-- Name: ix_archived_records_source_table; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_archived_records_source_table ON public.archived_records USING btree (source_table);


--
-- Name: ix_archived_records_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_archived_records_tenant_id ON public.archived_records USING btree (tenant_id);


--
-- Name: ix_archived_records_tenant_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_archived_records_tenant_resource ON public.archived_records USING btree (tenant_id, resource_type, archived_at);


--
-- Name: ix_arv2_agency_amount; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_arv2_agency_amount ON public.award_records_v2 USING btree (agency_code) WHERE (amount_bdt > (0)::double precision);


--
-- Name: ix_arv2_agency_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_arv2_agency_code ON public.award_records_v2 USING btree (agency_code);


--
-- Name: ix_arv2_agency_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_arv2_agency_date ON public.award_records_v2 USING btree (agency_code, award_date);


--
-- Name: ix_arv2_award_year; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_arv2_award_year ON public.award_records_v2 USING btree ("substring"((award_date)::text, '\d{4}'::text)) WHERE (amount_bdt > (0)::double precision);


--
-- Name: ix_arv2_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_arv2_contractor ON public.award_records_v2 USING btree (contractor_name);


--
-- Name: ix_arv2_contractor_amount; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_arv2_contractor_amount ON public.award_records_v2 USING btree (contractor_name) WHERE (amount_bdt > (0)::double precision);


--
-- Name: ix_arv2_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_arv2_date ON public.award_records_v2 USING btree (award_date);


--
-- Name: ix_arv2_district_amount; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_arv2_district_amount ON public.award_records_v2 USING btree (district) WHERE ((amount_bdt > (0)::double precision) AND (district IS NOT NULL));


--
-- Name: ix_arv2_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_arv2_tender ON public.award_records_v2 USING btree (procurement_tender_id);


--
-- Name: ix_arv2_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_arv2_tender_id ON public.award_records_v2 USING btree (tender_id);


--
-- Name: ix_arv2_tender_winner_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_arv2_tender_winner_date ON public.award_records_v2 USING btree (tender_id, contractor_name, award_date);


--
-- Name: ix_audit_entry_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_entry_hash ON public.audit_logs USING btree (entry_hash);


--
-- Name: ix_audit_logs_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_action ON public.audit_logs USING btree (action);


--
-- Name: ix_audit_logs_actor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_actor_id ON public.audit_logs USING btree (actor_id);


--
-- Name: ix_audit_logs_request_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_request_id ON public.audit_logs USING btree (request_id);


--
-- Name: ix_audit_logs_resource_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_resource_id ON public.audit_logs USING btree (resource_id);


--
-- Name: ix_audit_logs_resource_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_resource_type ON public.audit_logs USING btree (resource_type);


--
-- Name: ix_audit_logs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_tenant_id ON public.audit_logs USING btree (tenant_id);


--
-- Name: ix_audit_logs_trace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_trace_id ON public.audit_logs USING btree (trace_id);


--
-- Name: ix_audit_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_resource ON public.audit_logs USING btree (resource_type, resource_id);


--
-- Name: ix_audit_tenant_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_tenant_created ON public.audit_logs USING btree (tenant_id, created_at);


--
-- Name: ix_av2_normalized_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_av2_normalized_package ON public.award_records_v2 USING btree (normalized_package_no);


--
-- Name: ix_award_contractor_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_contractor_date ON public.award_records USING btree (contractor_name, award_date);


--
-- Name: ix_award_district_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_district_type ON public.award_records USING btree (district, work_type);


--
-- Name: ix_award_entity_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_entity_date ON public.award_records USING btree (procuring_entity, award_date);


--
-- Name: ix_award_intelligence_agency_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_intelligence_agency_code ON public.award_intelligence USING btree (agency_code);


--
-- Name: ix_award_records_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_records_contractor ON public.award_records USING btree (contractor_name);


--
-- Name: ix_award_records_contractor_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_records_contractor_name ON public.award_records USING btree (contractor_name);


--
-- Name: ix_award_records_discount_pct; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_records_discount_pct ON public.award_records USING btree (discount_pct);


--
-- Name: ix_award_records_district; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_records_district ON public.award_records USING btree (district);


--
-- Name: ix_award_records_procuring_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_records_procuring_entity ON public.award_records USING btree (procuring_entity);


--
-- Name: ix_award_records_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_records_source ON public.award_records USING btree (source);


--
-- Name: ix_award_records_source_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_records_source_id ON public.award_records USING btree (source_id);


--
-- Name: ix_award_records_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_records_tender_id ON public.award_records USING btree (tender_id);


--
-- Name: ix_award_records_v2_contractor_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_records_v2_contractor_name ON public.award_records_v2 USING btree (contractor_name);


--
-- Name: ix_award_records_v2_package_no; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_records_v2_package_no ON public.award_records_v2 USING btree (package_no);


--
-- Name: ix_award_records_v2_procurement_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_award_records_v2_procurement_tender_id ON public.award_records_v2 USING btree (procurement_tender_id);


--
-- Name: ix_awards_contractor_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_awards_contractor_name ON public.awards USING btree (contractor_name);


--
-- Name: ix_awards_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_awards_tender_id ON public.awards USING btree (tender_id);


--
-- Name: ix_boq_comparisons_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_boq_comparisons_tender_id ON public.boq_comparisons USING btree (tender_id);


--
-- Name: ix_boq_comparisons_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_boq_comparisons_user_id ON public.boq_comparisons USING btree (user_id);


--
-- Name: ix_boq_items_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_boq_items_code ON public.boq_items USING btree (code);


--
-- Name: ix_boq_items_flag; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_boq_items_flag ON public.boq_items USING btree (flag);


--
-- Name: ix_boq_items_tender_flag; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_boq_items_tender_flag ON public.boq_items USING btree (tender_id, flag);


--
-- Name: ix_boq_items_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_boq_items_tender_id ON public.boq_items USING btree (tender_id);


--
-- Name: ix_boq_jobs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_boq_jobs_status ON public.boq_jobs USING btree (status);


--
-- Name: ix_boq_jobs_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_boq_jobs_user_created ON public.boq_jobs USING btree (user_id, created_at);


--
-- Name: ix_boq_jobs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_boq_jobs_user_id ON public.boq_jobs USING btree (user_id);


--
-- Name: ix_bpm_deployed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bpm_deployed_at ON public.bid_price_models USING btree (deployed_at);


--
-- Name: ix_bpm_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_bpm_is_active ON public.bid_price_models USING btree (is_active);


--
-- Name: ix_bwdb_alerts_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_bwdb_alerts_tender_id ON public.bwdb_alerts USING btree (tender_id);


--
-- Name: ix_canonical_aliases_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_aliases_contractor ON public.canonical_contractor_aliases USING btree (canonical_contractor_id);


--
-- Name: ix_canonical_aliases_norm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_aliases_norm ON public.canonical_contractor_aliases USING btree (normalized_alias);


--
-- Name: ix_canonical_app_packages_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_app_packages_package ON public.canonical_app_packages USING btree (canonical_package_key);


--
-- Name: ix_canonical_awards_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_awards_contractor ON public.canonical_awards USING btree (canonical_contractor_id);


--
-- Name: ix_canonical_awards_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_awards_package ON public.canonical_awards USING btree (canonical_package_key);


--
-- Name: ix_canonical_awards_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_awards_tender_id ON public.canonical_awards USING btree (tender_id);


--
-- Name: ix_canonical_contractors_capacity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_contractors_capacity ON public.canonical_contractors USING btree (tender_capacity_bdt DESC);


--
-- Name: ix_canonical_contractors_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_contractors_name ON public.canonical_contractors USING btree (canonical_name);


--
-- Name: ix_canonical_contracts_amount; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_contracts_amount ON public.canonical_contracts USING btree (amount_normalized_bdt DESC);


--
-- Name: ix_canonical_contracts_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_contracts_contractor ON public.canonical_contracts USING btree (canonical_contractor_id);


--
-- Name: ix_canonical_contracts_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_contracts_package ON public.canonical_contracts USING btree (canonical_package_key);


--
-- Name: ix_canonical_contracts_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_contracts_source ON public.canonical_contracts USING btree (source_table, source_id);


--
-- Name: ix_canonical_contracts_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_contracts_tender_id ON public.canonical_contracts USING btree (tender_id);


--
-- Name: ix_canonical_dna_capacity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_dna_capacity ON public.canonical_contractor_dna USING btree (tender_capacity_bdt DESC);


--
-- Name: ix_canonical_tenders_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_tenders_package ON public.canonical_tenders USING btree (normalized_package_no);


--
-- Name: ix_canonical_tenders_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_canonical_tenders_tender_id ON public.canonical_tenders USING btree (tender_id);


--
-- Name: ix_cap_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cap_tender_id ON public.canonical_app_packages USING btree (tender_id);


--
-- Name: ix_cdna_v2_agency_affinity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cdna_v2_agency_affinity ON public.contractor_dna_v2 USING gin (agency_affinity);


--
-- Name: ix_cdna_v2_contractor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cdna_v2_contractor_id ON public.contractor_dna_v2 USING btree (contractor_id);


--
-- Name: ix_cdna_v2_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cdna_v2_name ON public.contractor_dna_v2 USING btree (contractor_name);


--
-- Name: ix_cdna_v2_total_bids_desc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cdna_v2_total_bids_desc ON public.contractor_dna_v2 USING btree (total_bids DESC);


--
-- Name: ix_cdna_v2_win_rate_desc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cdna_v2_win_rate_desc ON public.contractor_dna_v2 USING btree (win_rate DESC);


--
-- Name: ix_cdna_v2_zone_affinity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cdna_v2_zone_affinity ON public.contractor_dna_v2 USING gin (zone_affinity);


--
-- Name: ix_change_log_table; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_log_table ON public.crawl_change_log USING btree (table_name);


--
-- Name: ix_change_log_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_change_log_time ON public.crawl_change_log USING btree (detected_at);


--
-- Name: ix_checkpoint_plugin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_checkpoint_plugin ON public.crawl_checkpoints USING btree (plugin);


--
-- Name: ix_circulars_issue_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_circulars_issue_date ON public.circulars USING btree (issue_date);


--
-- Name: ix_clause_version_ref; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_clause_version_ref ON public.clauses USING btree (regulation_version_id, clause_ref);


--
-- Name: ix_clauses_regulation_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_clauses_regulation_version_id ON public.clauses USING btree (regulation_version_id);


--
-- Name: ix_competitor_active_amount; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competitor_active_amount ON public.competitor_profiles USING btree (last_award_date, total_awarded_amount);


--
-- Name: ix_competitor_award_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_competitor_award_unique ON public.competitor_awards USING btree (competitor_id, award_id);


--
-- Name: ix_competitor_awards_award_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competitor_awards_award_id ON public.competitor_awards USING btree (award_id);


--
-- Name: ix_competitor_awards_competitor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competitor_awards_competitor_id ON public.competitor_awards USING btree (competitor_id);


--
-- Name: ix_competitor_district_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competitor_district_category ON public.competitor_profiles USING btree (district, category);


--
-- Name: ix_competitor_profiles_district; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competitor_profiles_district ON public.competitor_profiles USING btree (district);


--
-- Name: ix_competitor_profiles_license_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competitor_profiles_license_number ON public.competitor_profiles USING btree (license_number);


--
-- Name: ix_competitor_profiles_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_competitor_profiles_name ON public.competitor_profiles USING btree (name);


--
-- Name: ix_competitor_profiles_normalized; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competitor_profiles_normalized ON public.competitor_profiles USING btree (normalized_name);


--
-- Name: ix_competitor_profiles_normalized_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_competitor_profiles_normalized_name ON public.competitor_profiles USING btree (normalized_name);


--
-- Name: ix_compliance_checks_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_compliance_checks_tender_id ON public.compliance_checks USING btree (tender_id);


--
-- Name: ix_contractor_capacity_contractor_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contractor_capacity_contractor_name ON public.contractor_capacity USING btree (contractor_name);


--
-- Name: ix_contractor_dna_contractor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_contractor_dna_contractor_id ON public.contractor_dna USING btree (contractor_id);


--
-- Name: ix_contractor_docs_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contractor_docs_category ON public.contractor_documents USING btree (contractor_id, doc_category);


--
-- Name: ix_contractor_docs_contractor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contractor_docs_contractor_id ON public.contractor_documents USING btree (contractor_id);


--
-- Name: ix_contractor_documents_contractor_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contractor_documents_contractor_id ON public.contractor_documents USING btree (contractor_id);


--
-- Name: ix_contractor_documents_doc_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contractor_documents_doc_category ON public.contractor_documents USING btree (doc_category);


--
-- Name: ix_contractor_finance_contractor_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contractor_finance_contractor_name ON public.contractor_finance USING btree (contractor_name);


--
-- Name: ix_contractors_contractor_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_contractors_contractor_name ON public.contractors USING btree (contractor_name);


--
-- Name: ix_crawl_jobs_plugin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_crawl_jobs_plugin ON public.crawl_jobs USING btree (plugin);


--
-- Name: ix_crawl_jobs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_crawl_jobs_status ON public.crawl_jobs USING btree (status);


--
-- Name: ix_ct_normpkg_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ct_normpkg_trgm ON public.canonical_tenders USING gin (normalized_package_no public.gin_trgm_ops);


--
-- Name: ix_ct_spaceless_pkg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ct_spaceless_pkg ON public.canonical_tenders USING btree (replace(normalized_package_no, ' '::text, ''::text));


--
-- Name: ix_data_retention_policies_resource_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_data_retention_policies_resource_type ON public.data_retention_policies USING btree (resource_type);


--
-- Name: ix_data_retention_policies_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_data_retention_policies_tenant_id ON public.data_retention_policies USING btree (tenant_id);


--
-- Name: ix_dim_agencies_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dim_agencies_code ON public.dim_agencies USING btree (agency_code);


--
-- Name: ix_dim_agencies_division; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dim_agencies_division ON public.dim_agencies USING btree (division);


--
-- Name: ix_dim_categories_sector; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dim_categories_sector ON public.dim_categories USING btree (sector);


--
-- Name: ix_dim_contractors_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dim_contractors_name ON public.dim_contractors USING btree (contractor_name);


--
-- Name: ix_dim_contractors_zone; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dim_contractors_zone ON public.dim_contractors USING btree (zone);


--
-- Name: ix_dim_zones_region; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dim_zones_region ON public.dim_zones USING btree (region);


--
-- Name: ix_dim_zones_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dim_zones_type ON public.dim_zones USING btree (agency_type);


--
-- Name: ix_doc_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_doc_tender_id ON public.crawl_documents USING btree (tender_id);


--
-- Name: ix_doc_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_doc_type ON public.crawl_documents USING btree (doc_type);


--
-- Name: ix_documents_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documents_tender_id ON public.documents USING btree (tender_id);


--
-- Name: ix_ec_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ec_agency ON public.eexperience_completed USING btree (agency_code);


--
-- Name: ix_ec_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ec_contractor ON public.eexperience_completed USING btree (contractor_name);


--
-- Name: ix_ec_package_no; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ec_package_no ON public.eexperience_completed USING btree (package_no);


--
-- Name: ix_ec_ptid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ec_ptid ON public.eexperience_completed USING btree (procurement_tender_id);


--
-- Name: ix_ecms_ongoing_tender_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ecms_ongoing_tender_package ON public.ecms_ongoing USING btree (tender_id, package_no);


--
-- Name: ix_econtract_execution_agency_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_econtract_execution_agency_code ON public.econtract_execution USING btree (agency_code);


--
-- Name: ix_econtract_execution_contractor_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_econtract_execution_contractor_name ON public.econtract_execution USING btree (contractor_name);


--
-- Name: ix_econtract_execution_package_no; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_econtract_execution_package_no ON public.econtract_execution USING btree (package_no);


--
-- Name: ix_ee_procurement_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ee_procurement_tender_id ON public.econtract_execution USING btree (procurement_tender_id);


--
-- Name: ix_eexperience_completed_tender_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eexperience_completed_tender_package ON public.eexperience_completed USING btree (tender_id, package_no);


--
-- Name: ix_enriched_app_app_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enriched_app_app_id ON public.enriched_app USING btree (app_id);


--
-- Name: ix_enriched_awards_package_no; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enriched_awards_package_no ON public.enriched_awards USING btree (package_no);


--
-- Name: ix_enriched_awards_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enriched_awards_tender_id ON public.enriched_awards USING btree (tender_id);


--
-- Name: ix_enriched_ecms_package_no; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enriched_ecms_package_no ON public.enriched_ecms USING btree (package_no);


--
-- Name: ix_enriched_ecms_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_enriched_ecms_tender_id ON public.enriched_ecms USING btree (tender_id);


--
-- Name: ix_eo_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eo_agency ON public.ecms_ongoing USING btree (agency_code);


--
-- Name: ix_eo_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eo_contractor ON public.ecms_ongoing USING btree (contractor_name);


--
-- Name: ix_eo_package_no; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eo_package_no ON public.ecms_ongoing USING btree (package_no);


--
-- Name: ix_eo_ptid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_eo_ptid ON public.ecms_ongoing USING btree (procurement_tender_id);


--
-- Name: ix_epw3_forms_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_epw3_forms_tender_id ON public.epw3_forms USING btree (tender_id);


--
-- Name: ix_error_plugin; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_error_plugin ON public.crawl_errors USING btree (plugin);


--
-- Name: ix_error_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_error_type ON public.crawl_errors USING btree (error_type);


--
-- Name: ix_fact_awards_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fact_awards_contractor ON public.fact_awards USING btree (contractor_id);


--
-- Name: ix_fact_awards_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fact_awards_date ON public.fact_awards USING btree (award_date);


--
-- Name: ix_fact_awards_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fact_awards_tender ON public.fact_awards USING btree (tender_id);


--
-- Name: ix_fact_bids_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fact_bids_contractor ON public.fact_bids USING btree (contractor_id);


--
-- Name: ix_fact_bids_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fact_bids_date ON public.fact_bids USING btree (bid_date);


--
-- Name: ix_fact_bids_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fact_bids_tender ON public.fact_bids USING btree (tender_id);


--
-- Name: ix_fact_bids_winner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fact_bids_winner ON public.fact_bids USING btree (is_winner);


--
-- Name: ix_fact_tenders_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fact_tenders_agency ON public.fact_tenders USING btree (agency_id);


--
-- Name: ix_fact_tenders_award; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fact_tenders_award ON public.fact_tenders USING btree (award_date);


--
-- Name: ix_fact_tenders_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fact_tenders_category ON public.fact_tenders USING btree (category_id);


--
-- Name: ix_fact_tenders_published; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fact_tenders_published ON public.fact_tenders USING btree (published_date);


--
-- Name: ix_fact_tenders_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fact_tenders_status ON public.fact_tenders USING btree (status);


--
-- Name: ix_fact_tenders_zone; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fact_tenders_zone ON public.fact_tenders USING btree (zone_id);


--
-- Name: ix_feedback_labels_agent_result_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_feedback_labels_agent_result_id ON public.feedback_labels USING btree (agent_result_id);


--
-- Name: ix_feedback_labels_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_feedback_labels_tender_id ON public.feedback_labels USING btree (tender_id);


--
-- Name: ix_idp_configs_enabled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_idp_configs_enabled ON public.idp_configs USING btree (enabled);


--
-- Name: ix_idp_configs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_idp_configs_tenant_id ON public.idp_configs USING btree (tenant_id);


--
-- Name: ix_knowledge_edges_source_target; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_edges_source_target ON public.knowledge_edges USING btree (source_node_id, target_node_id);


--
-- Name: ix_knowledge_edges_target; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_edges_target ON public.knowledge_edges USING btree (target_node_id);


--
-- Name: ix_knowledge_edges_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_edges_tenant_id ON public.knowledge_edges USING btree (tenant_id);


--
-- Name: ix_knowledge_edges_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_edges_type ON public.knowledge_edges USING btree (edge_type);


--
-- Name: ix_knowledge_embeddings_model; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_embeddings_model ON public.knowledge_embeddings USING btree (embedding_model);


--
-- Name: ix_knowledge_embeddings_node_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_embeddings_node_id ON public.knowledge_embeddings USING btree (node_id);


--
-- Name: ix_knowledge_embeddings_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_embeddings_tenant_id ON public.knowledge_embeddings USING btree (tenant_id);


--
-- Name: ix_knowledge_entries_checksum; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_entries_checksum ON public.knowledge_entries USING btree (checksum);


--
-- Name: ix_knowledge_entries_entry_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_entries_entry_type ON public.knowledge_entries USING btree (entry_type);


--
-- Name: ix_knowledge_entries_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_entries_tender_id ON public.knowledge_entries USING btree (tender_id);


--
-- Name: ix_knowledge_nodes_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_nodes_tenant_id ON public.knowledge_nodes USING btree (tenant_id);


--
-- Name: ix_knowledge_nodes_type_external_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_knowledge_nodes_type_external_id ON public.knowledge_nodes USING btree (node_type, external_id);


--
-- Name: ix_learning_outcomes_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_learning_outcomes_tender_id ON public.learning_outcomes USING btree (tender_id);


--
-- Name: ix_lifecycle_app_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lifecycle_app_id ON public.lifecycle USING btree (app_id);


--
-- Name: ix_lifecycle_award_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lifecycle_award_tender_id ON public.lifecycle USING btree (award_tender_id);


--
-- Name: ix_lifecycle_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lifecycle_tender_id ON public.lifecycle USING btree (tender_id);


--
-- Name: ix_live_tender_sources_procurement_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_live_tender_sources_procurement_tender_id ON public.live_tender_sources USING btree (procurement_tender_id);


--
-- Name: ix_live_tender_sources_source_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_live_tender_sources_source_tender_id ON public.live_tender_sources USING btree (source_tender_id);


--
-- Name: ix_market_rates_category_zone; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_market_rates_category_zone ON public.market_rates USING btree (category, zone);


--
-- Name: ix_npp_records_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_npp_records_agency ON public.npp_records USING btree (agency);


--
-- Name: ix_npp_records_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_npp_records_tender_id ON public.npp_records USING btree (tender_id);


--
-- Name: ix_opening_reports_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_opening_reports_agency ON public.opening_reports USING btree (agency);


--
-- Name: ix_opening_reports_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_opening_reports_tender_id ON public.opening_reports USING btree (tender_id);


--
-- Name: ix_permissions_resource_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_permissions_resource_action ON public.permissions USING btree (resource, action);


--
-- Name: ix_pf_award_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_award_company ON public.pf_awards USING btree (company_id);


--
-- Name: ix_pf_award_pe; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_award_pe ON public.pf_awards USING btree (procuring_entity_id);


--
-- Name: ix_pf_award_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_award_tender ON public.pf_awards USING btree (tender_id);


--
-- Name: ix_pf_company_district; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_company_district ON public.pf_companies USING btree (district);


--
-- Name: ix_pf_company_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_company_name ON public.pf_companies USING btree (name);


--
-- Name: ix_pf_deb_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_deb_company ON public.pf_debarments USING btree (company_id);


--
-- Name: ix_pf_doc_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_doc_tender ON public.pf_documents USING btree (tender_id);


--
-- Name: ix_pf_doc_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_doc_type ON public.pf_documents USING btree (doc_type);


--
-- Name: ix_pf_emb_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_emb_entity ON public.pf_document_embeddings USING btree (entity_type, entity_id);


--
-- Name: ix_pf_emb_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_emb_type ON public.pf_document_embeddings USING btree (doc_type);


--
-- Name: ix_pf_exp_company; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_exp_company ON public.pf_experience USING btree (company_id);


--
-- Name: ix_pf_exp_pe; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_exp_pe ON public.pf_experience USING btree (procuring_entity_id);


--
-- Name: ix_pf_exp_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_exp_tender ON public.pf_experience USING btree (tender_id) WHERE (tender_id IS NOT NULL);


--
-- Name: ix_pf_graph_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_graph_entity ON public.pf_entity_graph USING btree (entity_type, entity_id);


--
-- Name: ix_pf_graph_related; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_graph_related ON public.pf_entity_graph USING btree (related_type, related_id);


--
-- Name: ix_pf_graph_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_graph_type ON public.pf_entity_graph USING btree (entity_type, relationship_type);


--
-- Name: ix_pf_graph_uniq; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_pf_graph_uniq ON public.pf_entity_graph USING btree (relationship_id, entity_type, entity_id);


--
-- Name: ix_pf_pe_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_pe_agency ON public.pf_procuring_entities USING btree (agency_code);


--
-- Name: ix_pf_pe_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_pe_location ON public.pf_procuring_entities USING btree (location_id);


--
-- Name: ix_pf_rel_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_rel_source ON public.pf_relationships USING btree (source_type, source_id);


--
-- Name: ix_pf_rel_src_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_rel_src_type ON public.pf_relationships USING btree (source_type, relationship_type);


--
-- Name: ix_pf_rel_target; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_rel_target ON public.pf_relationships USING btree (target_type, target_id);


--
-- Name: ix_pf_rel_tgt_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_rel_tgt_type ON public.pf_relationships USING btree (target_type, relationship_type);


--
-- Name: ix_pf_rel_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_rel_type ON public.pf_relationships USING btree (relationship_type);


--
-- Name: ix_pf_tender_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_tender_agency ON public.pf_tenders USING btree (agency_code);


--
-- Name: ix_pf_tender_closing; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_tender_closing ON public.pf_tenders USING btree (closing_datetime);


--
-- Name: ix_pf_tender_pe; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_tender_pe ON public.pf_tenders USING btree (procuring_entity_id);


--
-- Name: ix_pf_tender_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pf_tender_status ON public.pf_tenders USING btree (status);


--
-- Name: ix_phase2_documents_document_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_phase2_documents_document_type ON public.phase2_documents USING btree (document_type);


--
-- Name: ix_phase2_documents_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_phase2_documents_tenant ON public.phase2_documents USING btree (tenant_id);


--
-- Name: ix_phase2_documents_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_phase2_documents_tenant_id ON public.phase2_documents USING btree (tenant_id);


--
-- Name: ix_phase2_documents_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_phase2_documents_tender_id ON public.phase2_documents USING btree (tender_id);


--
-- Name: ix_phase2_documents_tender_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_phase2_documents_tender_type ON public.phase2_documents USING btree (tender_id, document_type);


--
-- Name: ix_phase2_team_members_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_phase2_team_members_email ON public.phase2_team_members USING btree (email);


--
-- Name: ix_phase2_team_members_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_phase2_team_members_is_active ON public.phase2_team_members USING btree (is_active);


--
-- Name: ix_phase2_team_members_tenant_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_phase2_team_members_tenant_active ON public.phase2_team_members USING btree (tenant_id, is_active);


--
-- Name: ix_phase2_team_members_tenant_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_phase2_team_members_tenant_email ON public.phase2_team_members USING btree (tenant_id, email);


--
-- Name: ix_phase2_team_members_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_phase2_team_members_tenant_id ON public.phase2_team_members USING btree (tenant_id);


--
-- Name: ix_phase2_teams_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_phase2_teams_tenant_id ON public.phase2_teams USING btree (tenant_id);


--
-- Name: ix_pkgmap_tid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pkgmap_tid ON public.award_pkg_map USING btree (tender_id);


--
-- Name: ix_pkgsrc_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pkgsrc_key ON public.award_pkg_src USING btree (award_key);


--
-- Name: ix_pkgsrc_tid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pkgsrc_tid ON public.award_pkg_src USING btree (tender_id);


--
-- Name: ix_pl_agency_zone_award; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pl_agency_zone_award ON public.procurement_lifecycle USING btree (agency_code, zone_name, award_date DESC NULLS LAST);


--
-- Name: ix_pl_award_date_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pl_award_date_package ON public.procurement_lifecycle USING btree (award_date DESC NULLS LAST, package_no);


--
-- Name: ix_pl_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pl_tender_id ON public.procurement_lifecycle USING btree (tender_id);


--
-- Name: ix_ppr_evaluations_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ppr_evaluations_tender_id ON public.ppr_evaluations USING btree (tender_id);


--
-- Name: ix_ppr_rule_profiles_effective_from; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ppr_rule_profiles_effective_from ON public.ppr_rule_profiles USING btree (effective_from);


--
-- Name: ix_ppr_rule_profiles_effective_to; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ppr_rule_profiles_effective_to ON public.ppr_rule_profiles USING btree (effective_to);


--
-- Name: ix_ppr_rule_profiles_rule_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_ppr_rule_profiles_rule_key ON public.ppr_rule_profiles USING btree (rule_key);


--
-- Name: ix_ppr_schedules_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ppr_schedules_tender_id ON public.ppr_schedules USING btree (tender_id);


--
-- Name: ix_pre_computed_intelligence_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pre_computed_intelligence_agency ON public.pre_computed_intelligence USING btree (agency);


--
-- Name: ix_pre_computed_intelligence_cache_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_pre_computed_intelligence_cache_key ON public.pre_computed_intelligence USING btree (cache_key);


--
-- Name: ix_pre_computed_intelligence_intelligence_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pre_computed_intelligence_intelligence_type ON public.pre_computed_intelligence USING btree (intelligence_type);


--
-- Name: ix_pre_computed_intelligence_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pre_computed_intelligence_tender_id ON public.pre_computed_intelligence USING btree (tender_id);


--
-- Name: ix_prediction_feedback_prediction; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_prediction_feedback_prediction ON public.prediction_feedback USING btree (prediction_id);


--
-- Name: ix_prediction_feedback_prediction_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_prediction_feedback_prediction_id ON public.prediction_feedback USING btree (prediction_id);


--
-- Name: ix_prediction_feedback_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_prediction_feedback_tender ON public.prediction_feedback USING btree (tender_id);


--
-- Name: ix_proc_lifecycle_dedup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_proc_lifecycle_dedup ON public.procurement_lifecycle USING btree (package_no, winner, award_date);


--
-- Name: ix_procurement_lifecycle_agency_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_procurement_lifecycle_agency_code ON public.procurement_lifecycle USING btree (agency_code);


--
-- Name: ix_procurement_lifecycle_package_no; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_procurement_lifecycle_package_no ON public.procurement_lifecycle USING btree (package_no);


--
-- Name: ix_procurement_lifecycle_winner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_procurement_lifecycle_winner ON public.procurement_lifecycle USING btree (winner);


--
-- Name: ix_procurement_lifecycle_zone_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_procurement_lifecycle_zone_name ON public.procurement_lifecycle USING btree (zone_name);


--
-- Name: ix_procurement_tenders_agency_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_procurement_tenders_agency_code ON public.procurement_tenders USING btree (agency_code);


--
-- Name: ix_procurement_tenders_package_no; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_procurement_tenders_package_no ON public.procurement_tenders USING btree (package_no);


--
-- Name: ix_pt_normalized_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pt_normalized_package ON public.procurement_tenders USING btree (normalized_package_no);


--
-- Name: ix_pt_package_lower; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pt_package_lower ON public.procurement_tenders USING btree (lower('package_no'::text));


--
-- Name: ix_rate_analysis_rate_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rate_analysis_rate_id ON public.rate_analysis USING btree (rate_id);


--
-- Name: ix_raw_data_crawled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_raw_data_crawled ON public.raw_crawl_data USING btree (crawled_at);


--
-- Name: ix_raw_data_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_raw_data_hash ON public.raw_crawl_data USING btree (data_hash);


--
-- Name: ix_raw_data_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_raw_data_source ON public.raw_crawl_data USING btree (source);


--
-- Name: ix_raw_data_table; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_raw_data_table ON public.raw_crawl_data USING btree (table_name);


--
-- Name: ix_raw_json_family; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_raw_json_family ON public.raw_json_documents USING btree (source_family);


--
-- Name: ix_raw_json_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_raw_json_hash ON public.raw_json_documents USING btree (payload_sha256);


--
-- Name: ix_raw_json_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_raw_json_package ON public.raw_json_documents USING btree (package_no);


--
-- Name: ix_raw_json_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_raw_json_tender ON public.raw_json_documents USING btree (tender_id);


--
-- Name: ix_refresh_tokens_family_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_refresh_tokens_family_active ON public.refresh_tokens USING btree (family_id, revoked_at);


--
-- Name: ix_refresh_tokens_family_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_refresh_tokens_family_id ON public.refresh_tokens USING btree (family_id);


--
-- Name: ix_refresh_tokens_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_refresh_tokens_token_hash ON public.refresh_tokens USING btree (token_hash);


--
-- Name: ix_refresh_tokens_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_refresh_tokens_user_id ON public.refresh_tokens USING btree (user_id);


--
-- Name: ix_regdocs_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_regdocs_code ON public.regulation_documents USING btree (code);


--
-- Name: ix_regulation_versions_document_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_regulation_versions_document_id ON public.regulation_versions USING btree (document_id);


--
-- Name: ix_regulation_versions_effective_from; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_regulation_versions_effective_from ON public.regulation_versions USING btree (effective_from);


--
-- Name: ix_regulation_versions_superseded_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_regulation_versions_superseded_date ON public.regulation_versions USING btree (superseded_date);


--
-- Name: ix_regversion_doc_effective; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_regversion_doc_effective ON public.regulation_versions USING btree (document_id, effective_from);


--
-- Name: ix_repair_queue_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_repair_queue_entity ON public.canonical_identity_repair_queue USING btree (entity_type, entity_key);


--
-- Name: ix_repair_queue_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_repair_queue_status ON public.canonical_identity_repair_queue USING btree (status, severity);


--
-- Name: ix_retention_policy_lookup; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_retention_policy_lookup ON public.data_retention_policies USING btree (tenant_id, resource_type, is_active);


--
-- Name: ix_roles_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_roles_name ON public.roles USING btree (name);


--
-- Name: ix_roles_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_roles_tenant_id ON public.roles USING btree (tenant_id);


--
-- Name: ix_rule_citations_rule_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rule_citations_rule_version_id ON public.rule_citations USING btree (rule_version_id);


--
-- Name: ix_rule_execution_logs_agent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rule_execution_logs_agent_id ON public.rule_execution_logs USING btree (agent_id);


--
-- Name: ix_rule_execution_logs_executed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rule_execution_logs_executed_at ON public.rule_execution_logs USING btree (executed_at);


--
-- Name: ix_rule_execution_logs_rule_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rule_execution_logs_rule_version_id ON public.rule_execution_logs USING btree (rule_version_id);


--
-- Name: ix_rule_execution_logs_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rule_execution_logs_tenant_id ON public.rule_execution_logs USING btree (tenant_id);


--
-- Name: ix_rule_execution_logs_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rule_execution_logs_tender_id ON public.rule_execution_logs USING btree (tender_id);


--
-- Name: ix_rule_execution_logs_trace_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rule_execution_logs_trace_id ON public.rule_execution_logs USING btree (trace_id);


--
-- Name: ix_rule_versions_effective_from; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rule_versions_effective_from ON public.rule_versions USING btree (effective_from);


--
-- Name: ix_rule_versions_regulation_version_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rule_versions_regulation_version_id ON public.rule_versions USING btree (regulation_version_id);


--
-- Name: ix_rule_versions_rule_id_fk; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rule_versions_rule_id_fk ON public.rule_versions USING btree (rule_id_fk);


--
-- Name: ix_rule_versions_superseded_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rule_versions_superseded_date ON public.rule_versions USING btree (superseded_date);


--
-- Name: ix_ruleexec_ruleversion_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ruleexec_ruleversion_time ON public.rule_execution_logs USING btree (rule_version_id, executed_at);


--
-- Name: ix_ruleexec_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ruleexec_tender ON public.rule_execution_logs USING btree (tender_id);


--
-- Name: ix_rules_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_rules_category ON public.rules USING btree (category);


--
-- Name: ix_rules_rule_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_rules_rule_id ON public.rules USING btree (rule_id);


--
-- Name: ix_ruleversion_rule_effective; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ruleversion_rule_effective ON public.rule_versions USING btree (rule_id_fk, effective_from);


--
-- Name: ix_ruleversion_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ruleversion_status ON public.rule_versions USING btree (status);


--
-- Name: ix_sea_contractor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sea_contractor ON public.staging_enriched_awards USING btree (contractor_name);


--
-- Name: ix_sea_pkg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sea_pkg ON public.staging_enriched_awards USING btree (normalized_package_no);


--
-- Name: ix_sea_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sea_tender ON public.staging_enriched_awards USING btree (tender_id);


--
-- Name: ix_see_pkg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_see_pkg ON public.staging_enriched_ecms USING btree (normalized_package_no);


--
-- Name: ix_see_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_see_tender ON public.staging_enriched_ecms USING btree (tender_id);


--
-- Name: ix_slt_audit_logs_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_audit_logs_action ON public.slt_audit_logs USING btree (action);


--
-- Name: ix_slt_audit_logs_evaluation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_audit_logs_evaluation_id ON public.slt_audit_logs USING btree (evaluation_id);


--
-- Name: ix_slt_audit_logs_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_audit_logs_tender_id ON public.slt_audit_logs USING btree (tender_id);


--
-- Name: ix_slt_evaluation_bids_bidder_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_evaluation_bids_bidder_name ON public.slt_evaluation_bids USING btree (bidder_name);


--
-- Name: ix_slt_evaluation_bids_disqualified; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_evaluation_bids_disqualified ON public.slt_evaluation_bids USING btree (disqualified);


--
-- Name: ix_slt_evaluation_bids_evaluation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_evaluation_bids_evaluation_id ON public.slt_evaluation_bids USING btree (evaluation_id);


--
-- Name: ix_slt_evaluation_bids_evaluation_mode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_evaluation_bids_evaluation_mode ON public.slt_evaluation_bids USING btree (evaluation_mode);


--
-- Name: ix_slt_evaluation_bids_is_slt; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_evaluation_bids_is_slt ON public.slt_evaluation_bids USING btree (is_slt);


--
-- Name: ix_slt_evaluation_bids_rule_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_evaluation_bids_rule_key ON public.slt_evaluation_bids USING btree (rule_key);


--
-- Name: ix_slt_evaluation_runs_evaluation_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_evaluation_runs_evaluation_date ON public.slt_evaluation_runs USING btree (evaluation_date);


--
-- Name: ix_slt_evaluation_runs_evaluation_mode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_evaluation_runs_evaluation_mode ON public.slt_evaluation_runs USING btree (evaluation_mode);


--
-- Name: ix_slt_evaluation_runs_rule_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_evaluation_runs_rule_key ON public.slt_evaluation_runs USING btree (rule_key);


--
-- Name: ix_slt_evaluation_runs_source_mode; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_evaluation_runs_source_mode ON public.slt_evaluation_runs USING btree (source_mode);


--
-- Name: ix_slt_evaluation_runs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_evaluation_runs_status ON public.slt_evaluation_runs USING btree (status);


--
-- Name: ix_slt_evaluation_runs_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_evaluation_runs_tender_id ON public.slt_evaluation_runs USING btree (tender_id);


--
-- Name: ix_slt_evaluation_runs_tender_open_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_slt_evaluation_runs_tender_open_date ON public.slt_evaluation_runs USING btree (tender_open_date);


--
-- Name: ix_sor_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sor_active ON public.sor_rates USING btree (agency, is_active);


--
-- Name: ix_sor_agency_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sor_agency_code ON public.sor_rates USING btree (agency, code);


--
-- Name: ix_sor_normalized; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sor_normalized ON public.sor_rates USING btree (agency, normalized_code);


--
-- Name: ix_sor_rates_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sor_rates_agency ON public.sor_rates USING btree (agency);


--
-- Name: ix_sor_rates_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sor_rates_code ON public.sor_rates USING btree (code);


--
-- Name: ix_sor_rates_normalized_code; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sor_rates_normalized_code ON public.sor_rates USING btree (normalized_code);


--
-- Name: ix_sso_sessions_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sso_sessions_expires ON public.sso_sessions USING btree (expires_at);


--
-- Name: ix_sso_sessions_user_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sso_sessions_user_tenant ON public.sso_sessions USING btree (user_id, tenant_id);


--
-- Name: ix_staging_app_packages_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_staging_app_packages_agency ON public.staging_app_packages USING btree (agency_code);


--
-- Name: ix_staging_app_packages_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_staging_app_packages_package ON public.staging_app_packages USING btree (normalized_package_no);


--
-- Name: ix_staging_app_packages_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_staging_app_packages_tender ON public.staging_app_packages USING btree (tender_id);


--
-- Name: ix_staging_awards_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_staging_awards_agency ON public.staging_awards USING btree (agency_code);


--
-- Name: ix_staging_awards_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_staging_awards_package ON public.staging_awards USING btree (normalized_package_no);


--
-- Name: ix_staging_awards_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_staging_awards_tender ON public.staging_awards USING btree (tender_id);


--
-- Name: ix_staging_ecms_ongoing_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_staging_ecms_ongoing_agency ON public.staging_ecms_ongoing USING btree (agency_code);


--
-- Name: ix_staging_ecms_ongoing_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_staging_ecms_ongoing_package ON public.staging_ecms_ongoing USING btree (normalized_package_no);


--
-- Name: ix_staging_ecms_ongoing_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_staging_ecms_ongoing_tender ON public.staging_ecms_ongoing USING btree (tender_id);


--
-- Name: ix_staging_econtracts_agency; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_staging_econtracts_agency ON public.staging_econtracts USING btree (agency_code);


--
-- Name: ix_staging_econtracts_package; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_staging_econtracts_package ON public.staging_econtracts USING btree (normalized_package_no);


--
-- Name: ix_staging_econtracts_tender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_staging_econtracts_tender ON public.staging_econtracts USING btree (tender_id);


--
-- Name: ix_tenant_members_role_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_members_role_id ON public.tenant_members USING btree (role_id);


--
-- Name: ix_tenant_members_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_members_tenant_id ON public.tenant_members USING btree (tenant_id);


--
-- Name: ix_tenant_members_tenant_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_members_tenant_role ON public.tenant_members USING btree (tenant_id, role_id);


--
-- Name: ix_tenant_members_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_members_user_id ON public.tenant_members USING btree (user_id);


--
-- Name: ix_tenant_members_user_tenant; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenant_members_user_tenant ON public.tenant_members USING btree (user_id, tenant_id);


--
-- Name: ix_tenants_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenants_name ON public.tenants USING btree (name);


--
-- Name: ix_tender_data_pool_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tender_data_pool_tender_id ON public.tender_data_pool USING btree (tender_id);


--
-- Name: ix_tender_docs_tender_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tender_docs_tender_type ON public.tender_documents USING btree (tender_id, doc_type);


--
-- Name: ix_tender_documents_doc_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tender_documents_doc_type ON public.tender_documents USING btree (doc_type);


--
-- Name: ix_tender_documents_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tender_documents_tender_id ON public.tender_documents USING btree (tender_id);


--
-- Name: ix_tender_preparations_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tender_preparations_tender_id ON public.tender_preparations USING btree (tender_id);


--
-- Name: ix_tender_reports_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tender_reports_tender_id ON public.tender_reports USING btree (tender_id);


--
-- Name: ix_tenders_app_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenders_app_id ON public.tenders USING btree (app_id);


--
-- Name: ix_tenders_owner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenders_owner_id ON public.tenders USING btree (owner_id);


--
-- Name: ix_tenders_owner_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenders_owner_status ON public.tenders USING btree (owner_id, status);


--
-- Name: ix_tenders_package_no; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenders_package_no ON public.tenders USING btree (package_no);


--
-- Name: ix_tenders_regime; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tenders_regime ON public.tenders USING btree (regime);


--
-- Name: ix_tenders_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_tenders_tender_id ON public.tenders USING btree (tender_id);


--
-- Name: ix_tpm_deployed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tpm_deployed_at ON public.tender_price_models USING btree (deployed_at);


--
-- Name: ix_tpm_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_tpm_is_active ON public.tender_price_models USING btree (is_active);


--
-- Name: ix_user_queries_tender_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_queries_tender_id ON public.user_queries USING btree (tender_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_tenant_id ON public.users USING btree (tenant_id);


--
-- Name: ix_vw_contractor_perf_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_vw_contractor_perf_id ON public.vw_contractor_performance USING btree (contractor_id);


--
-- Name: ix_vw_market_agency_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_vw_market_agency_id ON public.vw_market_by_agency USING btree (agency_id);


--
-- Name: ix_webhook_delivery_logs_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_delivery_logs_event_type ON public.webhook_delivery_logs USING btree (event_type);


--
-- Name: ix_webhook_delivery_logs_subscription_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_delivery_logs_subscription_id ON public.webhook_delivery_logs USING btree (subscription_id);


--
-- Name: ix_webhook_logs_event; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_logs_event ON public.webhook_delivery_logs USING btree (event_type, created_at);


--
-- Name: ix_webhook_logs_sub_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_logs_sub_created ON public.webhook_delivery_logs USING btree (subscription_id, created_at);


--
-- Name: ix_webhook_subs_tenant_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_subs_tenant_active ON public.webhook_subscriptions USING btree (tenant_id, is_active);


--
-- Name: ix_webhook_subs_verified; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_subs_verified ON public.webhook_subscriptions USING btree (is_verified, is_active);


--
-- Name: ix_webhook_subscriptions_tenant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_webhook_subscriptions_tenant_id ON public.webhook_subscriptions USING btree (tenant_id);


--
-- Name: ix_zone_intelligence_zone_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_zone_intelligence_zone_name ON public.zone_intelligence USING btree (zone_name);


--
-- Name: ix_zones_zone_name; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_zones_zone_name ON public.zones USING btree (zone_name);


--
-- Name: uq_pf_awards_no_package; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pf_awards_no_package ON public.pf_awards USING btree (tender_id, company_id) WHERE ((tender_id IS NOT NULL) AND (company_id IS NOT NULL) AND (package_no IS NULL) AND (NOT is_deleted));


--
-- Name: uq_pf_awards_with_package; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pf_awards_with_package ON public.pf_awards USING btree (tender_id, package_no, company_id) WHERE ((tender_id IS NOT NULL) AND (company_id IS NOT NULL) AND (package_no IS NOT NULL) AND (NOT is_deleted));


--
-- Name: uq_pf_debarments_natural_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pf_debarments_natural_key ON public.pf_debarments USING btree (company_id, company_name) WHERE ((company_id IS NOT NULL) AND (company_name IS NOT NULL) AND (NOT is_deleted));


--
-- Name: uq_pf_documents_natural_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pf_documents_natural_key ON public.pf_documents USING btree (tender_id, doc_type, filename) WHERE (NOT is_deleted);


--
-- Name: uq_pf_emb_entity_doc; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pf_emb_entity_doc ON public.pf_document_embeddings USING btree (entity_type, entity_id, doc_type);


--
-- Name: uq_pf_experience_natural_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pf_experience_natural_key ON public.pf_experience USING btree (company_id, project_name) WHERE ((company_id IS NOT NULL) AND (project_name IS NOT NULL) AND (NOT is_deleted));


--
-- Name: uq_pf_rel_edge; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pf_rel_edge ON public.pf_relationships USING btree (source_type, source_id, target_type, target_id, relationship_type);


--
-- Name: idx_bid_rec_opportunity; Type: INDEX; Schema: tender; Owner: -
--

CREATE INDEX idx_bid_rec_opportunity ON tender.bid_recommendations USING btree (opportunity_id);


--
-- Name: idx_compliance_opportunity; Type: INDEX; Schema: tender; Owner: -
--

CREATE INDEX idx_compliance_opportunity ON tender.compliance_results USING btree (opportunity_id);


--
-- Name: idx_opportunities_egp_ref; Type: INDEX; Schema: tender; Owner: -
--

CREATE INDEX idx_opportunities_egp_ref ON tender.opportunities USING btree (egp_reference);


--
-- Name: idx_opportunities_status; Type: INDEX; Schema: tender; Owner: -
--

CREATE INDEX idx_opportunities_status ON tender.opportunities USING btree (status);


--
-- Name: idx_qual_opportunity; Type: INDEX; Schema: tender; Owner: -
--

CREATE INDEX idx_qual_opportunity ON tender.qualification_results USING btree (opportunity_id);


--
-- Name: idx_win_pred_opportunity; Type: INDEX; Schema: tender; Owner: -
--

CREATE INDEX idx_win_pred_opportunity ON tender.win_predictions USING btree (opportunity_id);


--
-- Name: idx_workspaces_opportunity; Type: INDEX; Schema: tender; Owner: -
--

CREATE INDEX idx_workspaces_opportunity ON tender.workspaces USING btree (opportunity_id);


--
-- Name: idx_workspaces_phase; Type: INDEX; Schema: tender; Owner: -
--

CREATE INDEX idx_workspaces_phase ON tender.workspaces USING btree (current_phase);


--
-- Name: audit_logs audit_logs_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_logs_append_only BEFORE DELETE OR UPDATE ON public.audit_logs FOR EACH ROW EXECUTE FUNCTION public.reject_audit_mutate();


--
-- Name: pf_relationships tgr_pf_relationships_updated; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER tgr_pf_relationships_updated BEFORE UPDATE ON public.pf_relationships FOR EACH ROW EXECUTE FUNCTION public.trg_pf_relationships_updated();


--
-- Name: app_records trg_app_records_extract_agency; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_app_records_extract_agency BEFORE INSERT ON public.app_records FOR EACH ROW EXECUTE FUNCTION public.app_records_agency_trigger();


--
-- Name: award_records_v2 trg_award_records_extract_agency; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_award_records_extract_agency BEFORE INSERT ON public.award_records_v2 FOR EACH ROW EXECUTE FUNCTION public.award_records_agency_trigger();


--
-- Name: amendments fk_amend_doc; Type: FK CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.amendments
    ADD CONSTRAINT fk_amend_doc FOREIGN KEY (document_id) REFERENCES commercial.regulation_documents(id);


--
-- Name: clauses fk_clause_ver; Type: FK CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.clauses
    ADD CONSTRAINT fk_clause_ver FOREIGN KEY (version_id) REFERENCES commercial.regulation_versions(id);


--
-- Name: rule_definitions fk_rule_ver; Type: FK CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.rule_definitions
    ADD CONSTRAINT fk_rule_ver FOREIGN KEY (authority_version_id) REFERENCES commercial.regulation_versions(id);


--
-- Name: slt_assessments fk_slt_calc; Type: FK CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.slt_assessments
    ADD CONSTRAINT fk_slt_calc FOREIGN KEY (calculation_id) REFERENCES commercial.weighted_average_calculations(id);


--
-- Name: regulation_versions fk_ver_doc; Type: FK CONSTRAINT; Schema: commercial; Owner: -
--

ALTER TABLE ONLY commercial.regulation_versions
    ADD CONSTRAINT fk_ver_doc FOREIGN KEY (document_id) REFERENCES commercial.regulation_documents(id);


--
-- Name: agent_jobs agent_jobs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_jobs
    ADD CONSTRAINT agent_jobs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: agent_logs agent_logs_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_logs
    ADD CONSTRAINT agent_logs_result_id_fkey FOREIGN KEY (result_id) REFERENCES public.agent_results(id);


--
-- Name: agent_results agent_results_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.agent_results
    ADD CONSTRAINT agent_results_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: awards awards_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.awards
    ADD CONSTRAINT awards_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: canonical_awards canonical_awards_canonical_contract_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_awards
    ADD CONSTRAINT canonical_awards_canonical_contract_id_fkey FOREIGN KEY (canonical_contract_id) REFERENCES public.canonical_contracts(canonical_contract_id) ON DELETE CASCADE;


--
-- Name: canonical_contractor_aliases canonical_contractor_aliases_canonical_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_contractor_aliases
    ADD CONSTRAINT canonical_contractor_aliases_canonical_contractor_id_fkey FOREIGN KEY (canonical_contractor_id) REFERENCES public.canonical_contractors(canonical_contractor_id) ON DELETE CASCADE;


--
-- Name: canonical_contractor_dna canonical_contractor_dna_canonical_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_contractor_dna
    ADD CONSTRAINT canonical_contractor_dna_canonical_contractor_id_fkey FOREIGN KEY (canonical_contractor_id) REFERENCES public.canonical_contractors(canonical_contractor_id) ON DELETE CASCADE;


--
-- Name: canonical_contractor_jv_members canonical_contractor_jv_membe_member_canonical_contractor__fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_contractor_jv_members
    ADD CONSTRAINT canonical_contractor_jv_membe_member_canonical_contractor__fkey FOREIGN KEY (member_canonical_contractor_id) REFERENCES public.canonical_contractors(canonical_contractor_id) ON DELETE CASCADE;


--
-- Name: canonical_contractor_jv_members canonical_contractor_jv_members_jv_canonical_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_contractor_jv_members
    ADD CONSTRAINT canonical_contractor_jv_members_jv_canonical_contractor_id_fkey FOREIGN KEY (jv_canonical_contractor_id) REFERENCES public.canonical_contractors(canonical_contractor_id) ON DELETE CASCADE;


--
-- Name: canonical_contracts canonical_contracts_canonical_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_contracts
    ADD CONSTRAINT canonical_contracts_canonical_contractor_id_fkey FOREIGN KEY (canonical_contractor_id) REFERENCES public.canonical_contractors(canonical_contractor_id) ON DELETE SET NULL;


--
-- Name: canonical_contracts canonical_contracts_canonical_package_key_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.canonical_contracts
    ADD CONSTRAINT canonical_contracts_canonical_package_key_fkey FOREIGN KEY (canonical_package_key) REFERENCES public.canonical_tenders(canonical_package_key) ON DELETE CASCADE;


--
-- Name: client_priority_states client_priority_states_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_priority_states
    ADD CONSTRAINT client_priority_states_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: client_subscriptions client_subscriptions_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_subscriptions
    ADD CONSTRAINT client_subscriptions_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.subscription_plans(id);


--
-- Name: client_subscriptions client_subscriptions_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.client_subscriptions
    ADD CONSTRAINT client_subscriptions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: compliance_checks compliance_checks_agent_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compliance_checks
    ADD CONSTRAINT compliance_checks_agent_result_id_fkey FOREIGN KEY (agent_result_id) REFERENCES public.agent_results(id);


--
-- Name: documents documents_tender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_tender_id_fkey FOREIGN KEY (tender_id) REFERENCES public.tenders(tender_id);


--
-- Name: fact_awards fact_awards_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_awards
    ADD CONSTRAINT fact_awards_contractor_id_fkey FOREIGN KEY (contractor_id) REFERENCES public.dim_contractors(contractor_id);


--
-- Name: fact_bids fact_bids_contractor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_bids
    ADD CONSTRAINT fact_bids_contractor_id_fkey FOREIGN KEY (contractor_id) REFERENCES public.dim_contractors(contractor_id);


--
-- Name: fact_tenders fact_tenders_agency_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_tenders
    ADD CONSTRAINT fact_tenders_agency_id_fkey FOREIGN KEY (agency_id) REFERENCES public.dim_agencies(agency_id);


--
-- Name: fact_tenders fact_tenders_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_tenders
    ADD CONSTRAINT fact_tenders_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.dim_categories(category_id);


--
-- Name: fact_tenders fact_tenders_zone_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fact_tenders
    ADD CONSTRAINT fact_tenders_zone_id_fkey FOREIGN KEY (zone_id) REFERENCES public.dim_zones(zone_id);


--
-- Name: feedback_labels feedback_labels_agent_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.feedback_labels
    ADD CONSTRAINT feedback_labels_agent_result_id_fkey FOREIGN KEY (agent_result_id) REFERENCES public.agent_results(id);


--
-- Name: amendments fk_amendments_clause_id_clauses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.amendments
    ADD CONSTRAINT fk_amendments_clause_id_clauses FOREIGN KEY (clause_id) REFERENCES public.clauses(id);


--
-- Name: amendments fk_amendments_regulation_version_id_regulation_versions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.amendments
    ADD CONSTRAINT fk_amendments_regulation_version_id_regulation_versions FOREIGN KEY (regulation_version_id) REFERENCES public.regulation_versions(id);


--
-- Name: boq_comparisons fk_boq_comparisons_tender_id_tenders; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.boq_comparisons
    ADD CONSTRAINT fk_boq_comparisons_tender_id_tenders FOREIGN KEY (tender_id) REFERENCES public.tenders(id);


--
-- Name: boq_comparisons fk_boq_comparisons_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.boq_comparisons
    ADD CONSTRAINT fk_boq_comparisons_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: boq_items fk_boq_items_tender_id_tenders; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.boq_items
    ADD CONSTRAINT fk_boq_items_tender_id_tenders FOREIGN KEY (tender_id) REFERENCES public.tenders(id);


--
-- Name: boq_jobs fk_boq_jobs_comparison_id_boq_comparisons; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.boq_jobs
    ADD CONSTRAINT fk_boq_jobs_comparison_id_boq_comparisons FOREIGN KEY (comparison_id) REFERENCES public.boq_comparisons(id);


--
-- Name: boq_jobs fk_boq_jobs_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.boq_jobs
    ADD CONSTRAINT fk_boq_jobs_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: clauses fk_clauses_regulation_version_id_regulation_versions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.clauses
    ADD CONSTRAINT fk_clauses_regulation_version_id_regulation_versions FOREIGN KEY (regulation_version_id) REFERENCES public.regulation_versions(id);


--
-- Name: competitor_awards fk_competitor_awards_award_id_award_records; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competitor_awards
    ADD CONSTRAINT fk_competitor_awards_award_id_award_records FOREIGN KEY (award_id) REFERENCES public.award_records(id);


--
-- Name: competitor_awards fk_competitor_awards_competitor_id_competitor_profiles; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.competitor_awards
    ADD CONSTRAINT fk_competitor_awards_competitor_id_competitor_profiles FOREIGN KEY (competitor_id) REFERENCES public.competitor_profiles(id);


--
-- Name: knowledge_edges fk_knowledge_edges_source_node_id_knowledge_nodes; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_edges
    ADD CONSTRAINT fk_knowledge_edges_source_node_id_knowledge_nodes FOREIGN KEY (source_node_id) REFERENCES public.knowledge_nodes(id) ON DELETE CASCADE;


--
-- Name: knowledge_edges fk_knowledge_edges_target_node_id_knowledge_nodes; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_edges
    ADD CONSTRAINT fk_knowledge_edges_target_node_id_knowledge_nodes FOREIGN KEY (target_node_id) REFERENCES public.knowledge_nodes(id) ON DELETE CASCADE;


--
-- Name: knowledge_embeddings fk_knowledge_embeddings_node_id_knowledge_nodes; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.knowledge_embeddings
    ADD CONSTRAINT fk_knowledge_embeddings_node_id_knowledge_nodes FOREIGN KEY (node_id) REFERENCES public.knowledge_nodes(id) ON DELETE CASCADE;


--
-- Name: phase2_documents fk_phase2_documents_created_by_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phase2_documents
    ADD CONSTRAINT fk_phase2_documents_created_by_users FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: phase2_team_members fk_phase2_team_members_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.phase2_team_members
    ADD CONSTRAINT fk_phase2_team_members_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: refresh_tokens fk_refresh_tokens_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT fk_refresh_tokens_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: regulation_versions fk_regulation_versions_document_id_regulation_documents; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regulation_versions
    ADD CONSTRAINT fk_regulation_versions_document_id_regulation_documents FOREIGN KEY (document_id) REFERENCES public.regulation_documents(id);


--
-- Name: roles fk_roles_tenant_id_tenants; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT fk_roles_tenant_id_tenants FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: rule_citations fk_rule_citations_circular_id_circulars; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rule_citations
    ADD CONSTRAINT fk_rule_citations_circular_id_circulars FOREIGN KEY (circular_id) REFERENCES public.circulars(id);


--
-- Name: rule_citations fk_rule_citations_clause_id_clauses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rule_citations
    ADD CONSTRAINT fk_rule_citations_clause_id_clauses FOREIGN KEY (clause_id) REFERENCES public.clauses(id);


--
-- Name: rule_citations fk_rule_citations_rule_version_id_rule_versions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rule_citations
    ADD CONSTRAINT fk_rule_citations_rule_version_id_rule_versions FOREIGN KEY (rule_version_id) REFERENCES public.rule_versions(id);


--
-- Name: rule_execution_logs fk_rule_execution_logs_rule_version_id_rule_versions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rule_execution_logs
    ADD CONSTRAINT fk_rule_execution_logs_rule_version_id_rule_versions FOREIGN KEY (rule_version_id) REFERENCES public.rule_versions(id);


--
-- Name: rule_versions fk_rule_versions_regulation_version_id_regulation_versions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rule_versions
    ADD CONSTRAINT fk_rule_versions_regulation_version_id_regulation_versions FOREIGN KEY (regulation_version_id) REFERENCES public.regulation_versions(id);


--
-- Name: rule_versions fk_rule_versions_rule_id_fk_rules; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rule_versions
    ADD CONSTRAINT fk_rule_versions_rule_id_fk_rules FOREIGN KEY (rule_id_fk) REFERENCES public.rules(id);


--
-- Name: slt_audit_logs fk_slt_audit_logs_evaluation_id_slt_evaluation_runs; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.slt_audit_logs
    ADD CONSTRAINT fk_slt_audit_logs_evaluation_id_slt_evaluation_runs FOREIGN KEY (evaluation_id) REFERENCES public.slt_evaluation_runs(id);


--
-- Name: slt_evaluation_bids fk_slt_evaluation_bids_evaluation_id_slt_evaluation_runs; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.slt_evaluation_bids
    ADD CONSTRAINT fk_slt_evaluation_bids_evaluation_id_slt_evaluation_runs FOREIGN KEY (evaluation_id) REFERENCES public.slt_evaluation_runs(id);


--
-- Name: tenant_members fk_tenant_members_role_id_roles; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_members
    ADD CONSTRAINT fk_tenant_members_role_id_roles FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- Name: tenant_members fk_tenant_members_tenant_id_tenants; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_members
    ADD CONSTRAINT fk_tenant_members_tenant_id_tenants FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: tenant_members fk_tenant_members_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenant_members
    ADD CONSTRAINT fk_tenant_members_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: tender_documents fk_tender_documents_tender_id_tenders; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tender_documents
    ADD CONSTRAINT fk_tender_documents_tender_id_tenders FOREIGN KEY (tender_id) REFERENCES public.tenders(id);


--
-- Name: tenders fk_tenders_owner_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tenders
    ADD CONSTRAINT fk_tenders_owner_id_users FOREIGN KEY (owner_id) REFERENCES public.users(id);


--
-- Name: idp_configs idp_configs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.idp_configs
    ADD CONSTRAINT idp_configs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: opening_reports opening_reports_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opening_reports
    ADD CONSTRAINT opening_reports_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: opening_reports opening_reports_tender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.opening_reports
    ADD CONSTRAINT opening_reports_tender_id_fkey FOREIGN KEY (tender_id) REFERENCES public.tenders(tender_id);


--
-- Name: organizations organizations_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: pf_awards pf_awards_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_awards
    ADD CONSTRAINT pf_awards_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.pf_companies(id);


--
-- Name: pf_awards pf_awards_procuring_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_awards
    ADD CONSTRAINT pf_awards_procuring_entity_id_fkey FOREIGN KEY (procuring_entity_id) REFERENCES public.pf_procuring_entities(id);


--
-- Name: pf_debarments pf_debarments_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_debarments
    ADD CONSTRAINT pf_debarments_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.pf_companies(id);


--
-- Name: pf_experience pf_experience_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_experience
    ADD CONSTRAINT pf_experience_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.pf_companies(id);


--
-- Name: pf_experience pf_experience_procuring_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_experience
    ADD CONSTRAINT pf_experience_procuring_entity_id_fkey FOREIGN KEY (procuring_entity_id) REFERENCES public.pf_procuring_entities(id);


--
-- Name: pf_tenders pf_tenders_procuring_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pf_tenders
    ADD CONSTRAINT pf_tenders_procuring_entity_id_fkey FOREIGN KEY (procuring_entity_id) REFERENCES public.pf_procuring_entities(id);


--
-- Name: ppr_schedules ppr_schedules_agent_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ppr_schedules
    ADD CONSTRAINT ppr_schedules_agent_result_id_fkey FOREIGN KEY (agent_result_id) REFERENCES public.agent_results(id);


--
-- Name: raw_json_documents raw_json_documents_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_json_documents
    ADD CONSTRAINT raw_json_documents_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.raw_import_batches(batch_id) ON DELETE SET NULL;


--
-- Name: rulesets rulesets_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rulesets
    ADD CONSTRAINT rulesets_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: sso_sessions sso_sessions_idp_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sso_sessions
    ADD CONSTRAINT sso_sessions_idp_config_id_fkey FOREIGN KEY (idp_config_id) REFERENCES public.idp_configs(id);


--
-- Name: sso_sessions sso_sessions_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sso_sessions
    ADD CONSTRAINT sso_sessions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: sso_sessions sso_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sso_sessions
    ADD CONSTRAINT sso_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: staging_app_packages staging_app_packages_raw_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staging_app_packages
    ADD CONSTRAINT staging_app_packages_raw_id_fkey FOREIGN KEY (raw_id) REFERENCES public.raw_json_documents(raw_id) ON DELETE SET NULL;


--
-- Name: staging_awards staging_awards_raw_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staging_awards
    ADD CONSTRAINT staging_awards_raw_id_fkey FOREIGN KEY (raw_id) REFERENCES public.raw_json_documents(raw_id) ON DELETE SET NULL;


--
-- Name: staging_ecms_ongoing staging_ecms_ongoing_raw_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staging_ecms_ongoing
    ADD CONSTRAINT staging_ecms_ongoing_raw_id_fkey FOREIGN KEY (raw_id) REFERENCES public.raw_json_documents(raw_id) ON DELETE SET NULL;


--
-- Name: staging_econtracts staging_econtracts_raw_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staging_econtracts
    ADD CONSTRAINT staging_econtracts_raw_id_fkey FOREIGN KEY (raw_id) REFERENCES public.raw_json_documents(raw_id) ON DELETE SET NULL;


--
-- Name: tender_preparations tender_preparations_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tender_preparations
    ADD CONSTRAINT tender_preparations_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: tender_preparations tender_preparations_tender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tender_preparations
    ADD CONSTRAINT tender_preparations_tender_id_fkey FOREIGN KEY (tender_id) REFERENCES public.tenders(tender_id);


--
-- Name: tender_usage_logs tender_usage_logs_tenant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tender_usage_logs
    ADD CONSTRAINT tender_usage_logs_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);


--
-- Name: agent_jobs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.agent_jobs ENABLE ROW LEVEL SECURITY;

--
-- Name: agent_results; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.agent_results ENABLE ROW LEVEL SECURITY;

--
-- Name: archived_records; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.archived_records ENABLE ROW LEVEL SECURITY;

--
-- Name: audit_logs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

--
-- Name: awards; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.awards ENABLE ROW LEVEL SECURITY;

--
-- Name: data_retention_policies; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.data_retention_policies ENABLE ROW LEVEL SECURITY;

--
-- Name: knowledge_edges; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.knowledge_edges ENABLE ROW LEVEL SECURITY;

--
-- Name: knowledge_edges knowledge_edges_tenant_isolation; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY knowledge_edges_tenant_isolation ON public.knowledge_edges USING (((tenant_id)::text = current_setting('app.tenant_id'::text, true))) WITH CHECK (((tenant_id)::text = current_setting('app.tenant_id'::text, true)));


--
-- Name: knowledge_embeddings; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.knowledge_embeddings ENABLE ROW LEVEL SECURITY;

--
-- Name: knowledge_embeddings knowledge_embeddings_tenant_isolation; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY knowledge_embeddings_tenant_isolation ON public.knowledge_embeddings USING (((tenant_id)::text = current_setting('app.tenant_id'::text, true))) WITH CHECK (((tenant_id)::text = current_setting('app.tenant_id'::text, true)));


--
-- Name: knowledge_entries; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.knowledge_entries ENABLE ROW LEVEL SECURITY;

--
-- Name: knowledge_nodes; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.knowledge_nodes ENABLE ROW LEVEL SECURITY;

--
-- Name: knowledge_nodes knowledge_nodes_tenant_isolation; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY knowledge_nodes_tenant_isolation ON public.knowledge_nodes USING (((tenant_id)::text = current_setting('app.tenant_id'::text, true))) WITH CHECK (((tenant_id)::text = current_setting('app.tenant_id'::text, true)));


--
-- Name: opening_reports; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.opening_reports ENABLE ROW LEVEL SECURITY;

--
-- Name: agent_jobs tenant_isolation_agent_jobs; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_agent_jobs ON public.agent_jobs USING (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true)))) WITH CHECK (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true))));


--
-- Name: agent_results tenant_isolation_agent_results; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_agent_results ON public.agent_results USING (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true)))) WITH CHECK (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true))));


--
-- Name: archived_records tenant_isolation_archived_records; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_archived_records ON public.archived_records USING (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true)))) WITH CHECK (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true))));


--
-- Name: audit_logs tenant_isolation_audit_logs; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_audit_logs ON public.audit_logs USING (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true)))) WITH CHECK (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true))));


--
-- Name: awards tenant_isolation_awards; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_awards ON public.awards USING (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true)))) WITH CHECK (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true))));


--
-- Name: data_retention_policies tenant_isolation_data_retention_policies; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_data_retention_policies ON public.data_retention_policies USING (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true)))) WITH CHECK (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true))));


--
-- Name: knowledge_entries tenant_isolation_knowledge_entries; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_knowledge_entries ON public.knowledge_entries USING (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true)))) WITH CHECK (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true))));


--
-- Name: opening_reports tenant_isolation_opening_reports; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_opening_reports ON public.opening_reports USING (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true)))) WITH CHECK (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true))));


--
-- Name: users tenant_isolation_users; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_users ON public.users USING (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true)))) WITH CHECK (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true))));


--
-- Name: webhook_subscriptions tenant_isolation_webhook_subscriptions; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY tenant_isolation_webhook_subscriptions ON public.webhook_subscriptions USING (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true)))) WITH CHECK (((tenant_id IS NULL) OR (current_setting('app.is_superuser'::text, true) = 'true'::text) OR ((tenant_id)::text = current_setting('app.tenant_id'::text, true))));


--
-- Name: users; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

--
-- Name: webhook_subscriptions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.webhook_subscriptions ENABLE ROW LEVEL SECURITY;

--
-- PostgreSQL database dump complete
--
-- Add an indexed pgvector representation without removing the legacy
-- JSON/text embedding column still consumed by the application.
ALTER TABLE public.knowledge_embeddings
    ADD COLUMN embedding_vector vector(384);
CREATE INDEX ix_knowledge_embeddings_vector_hnsw
    ON public.knowledge_embeddings
    USING hnsw (embedding_vector vector_cosine_ops);

