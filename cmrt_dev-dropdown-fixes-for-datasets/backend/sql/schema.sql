COMMENT ON DATABASE cmrt_dev IS 'CMRT DB for Development';

--
-- TOC entry 941 (class 1247 OID 25872)
-- Name: area_class; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.area_class AS ENUM (
    'METROPOLITAN',
    'REGIONAL',
    'REMOTE'
);


ALTER TYPE public.area_class OWNER TO psqladmin;

--
-- TOC entry 944 (class 1247 OID 25880)
-- Name: org_role; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.org_role AS ENUM (
    'PROPONENT',
    'DESIGNER',
    'DELIVERY'
);


ALTER TYPE public.org_role OWNER TO psqladmin;

--
-- TOC entry 935 (class 1247 OID 26046)
-- Name: organization_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.organization_type AS ENUM (
    'DESIGNERS',
    'CONTRACTORS'
);


ALTER TYPE public.organization_type OWNER TO psqladmin;

--
-- TOC entry 938 (class 1247 OID 25864)
-- Name: project_class; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.project_class AS ENUM (
    'SMALL',
    'LARGE',
    'RECURRING'
);


ALTER TYPE public.project_class OWNER TO psqladmin;

--
-- TOC entry 947 (class 1247 OID 25888)
-- Name: project_stage; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.project_stage AS ENUM (
    'BUSINESS_CASE',
    'DESIGN',
    'CONSTRUCTION'
);


ALTER TYPE public.project_stage OWNER TO psqladmin;

--
-- TOC entry 950 (class 1247 OID 25896)
-- Name: report_frequency; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.report_frequency AS ENUM (
    'MONTHLY',
    'QUARTERLY',
    'BI_MONTHLY',
    'ANNUAL'
);


ALTER TYPE public.report_frequency OWNER TO psqladmin;

--
-- TOC entry 884 (class 1247 OID 24812)
-- Name: report_frequency_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.report_frequency_type AS ENUM (
    'MONTHLY',
    'QUARTERLY',
    'FINANCIAL_YEAR',
    'CALENDAR_YEAR',
    'SIX_MONTHLY',
    'AS_BUILT'
);


ALTER TYPE public.report_frequency_type OWNER TO psqladmin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 232 (class 1259 OID 25029)
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO psqladmin;

--
-- TOC entry 217 (class 1259 OID 24825)
-- Name: emission_entry; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.emission_entry (
    emission_entry_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    project_reporting_submission_id uuid NOT NULL,
    emissions_sub_category_id uuid NOT NULL,
    emission_source_id uuid NOT NULL,
    measurement_unit_id uuid NOT NULL,
    emission_factor_id uuid NOT NULL,
    data_quality character varying(50) NOT NULL,
    quantity numeric(18,6) NOT NULL,
    notes character varying(100),
    emissions_tco2e numeric(18,6) NOT NULL,
    submitted_by_user_id uuid NOT NULL,
    submitted_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone
);


ALTER TABLE public.emission_entry OWNER TO psqladmin;

--
-- TOC entry 218 (class 1259 OID 24830)
-- Name: emission_entry_summary; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.emission_entry_summary (
    emission_entry_summary_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    project_reporting_submission_id uuid NOT NULL,
    summary character varying(1000),
    submitted_by_user_id uuid NOT NULL,
    submitted_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone
);


ALTER TABLE public.emission_entry_summary OWNER TO psqladmin;

--
-- TOC entry 219 (class 1259 OID 24837)
-- Name: emission_factor; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.emission_factor (
    emission_factor_id uuid DEFAULT gen_random_uuid() NOT NULL,
    emission_source_id uuid NOT NULL,
    measurement_unit_id uuid NOT NULL,
    is_active boolean DEFAULT true,
    created_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone
);


ALTER TABLE public.emission_factor OWNER TO psqladmin;

--
-- TOC entry 220 (class 1259 OID 24843)
-- Name: emission_factor_value; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.emission_factor_value (
    emission_factor_value_id uuid DEFAULT gen_random_uuid() NOT NULL,
    emission_factor_id uuid NOT NULL,
    stage_code character varying(100) NOT NULL,
    gwp_kgco2e_per_unit numeric(18,6) NOT NULL,
    created_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone
);


ALTER TABLE public.emission_factor_value OWNER TO psqladmin;

--
-- TOC entry 221 (class 1259 OID 24848)
-- Name: emission_source; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.emission_source (
    emission_source_id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(200) NOT NULL,
    emissions_sub_category_id uuid,
    measurement_unit_id uuid,
    is_active boolean DEFAULT true,
    created_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone
);


ALTER TABLE public.emission_source OWNER TO psqladmin;

--
-- TOC entry 222 (class 1259 OID 24854)
-- Name: emissions_category; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.emissions_category (
    emissions_category_id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(200) NOT NULL,
    is_active boolean DEFAULT true,
    created_on timestamp without time zone,
    updated_on timestamp without time zone
);


ALTER TABLE public.emissions_category OWNER TO psqladmin;

--
-- TOC entry 223 (class 1259 OID 24859)
-- Name: emissions_sub_category; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.emissions_sub_category (
    emissions_sub_category_id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(200) NOT NULL,
    emissions_category_id uuid,
    is_active boolean DEFAULT true,
    created_on timestamp without time zone,
    updated_on timestamp without time zone
);


ALTER TABLE public.emissions_sub_category OWNER TO psqladmin;

--
-- TOC entry 224 (class 1259 OID 24864)
-- Name: measurement_unit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.measurement_unit (
    measurement_unit_id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(100),
    is_active boolean DEFAULT true,
    created_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone
);


ALTER TABLE public.measurement_unit OWNER TO psqladmin;

--
-- TOC entry 233 (class 1259 OID 25905)
-- Name: organization; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.organization (
    organization_id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    is_active boolean,
    created_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone,
    organization_type public.organization_type DEFAULT 'DESIGNERS'::public.organization_type NOT NULL
);


ALTER TABLE public.organization OWNER TO psqladmin;

--
-- TOC entry 234 (class 1259 OID 25914)
-- Name: postcode_reference; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.postcode_reference (
    postcode_reference_id uuid DEFAULT gen_random_uuid() NOT NULL,
    postcode character varying(10) NOT NULL,
    area_class public.area_class NOT NULL,
    created_on timestamp without time zone DEFAULT now()
);


ALTER TABLE public.postcode_reference OWNER TO psqladmin;

--
-- TOC entry 225 (class 1259 OID 24870)
-- Name: project; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project (
    project_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_name character varying(200) NOT NULL,
    project_type character varying(200) NOT NULL,
    description character varying(1000),
    is_active boolean DEFAULT true,
    created_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone,
    project_class public.project_class DEFAULT 'SMALL'::public.project_class NOT NULL,
    simple_carbon_assessment boolean,
    contract_number character varying(100) DEFAULT ''::character varying NOT NULL,
    program_name character varying(255),
    location_text character varying(255),
    construction_start_date date,
    construction_end_date date,
    commencement_of_operations date,
    operational_life_years integer,
    project_capex_million numeric(18,2),
    project_opex numeric(18,2),
    first_submission_month date,
    maintenance_region character varying(255),
    proponent_org_id uuid NOT NULL,
    created_by_user_id uuid NOT NULL,
    last_updated_by_user_id uuid
);


ALTER TABLE public.project OWNER TO psqladmin;

--
-- TOC entry 237 (class 1259 OID 25939)
-- Name: project_organizations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_organizations (
    project_organization_link_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    organization_id uuid NOT NULL,
    role public.org_role NOT NULL,
    created_on timestamp without time zone DEFAULT now()
);


ALTER TABLE public.project_organizations OWNER TO psqladmin;

--
-- TOC entry 238 (class 1259 OID 25956)
-- Name: project_postcode; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_postcode (
    project_postcode_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    postcode character varying(10) NOT NULL,
    area_class public.area_class NOT NULL,
    created_on timestamp without time zone DEFAULT now()
);


ALTER TABLE public.project_postcode OWNER TO psqladmin;

--
-- TOC entry 226 (class 1259 OID 24878)
-- Name: project_reporting_submission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_reporting_submission (
    project_reporting_submission_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    frequency character varying(50) NOT NULL,
    period_label character varying(100) NOT NULL,
    period_start_date date NOT NULL,
    period_end_date date NOT NULL,
    due_date date,
    is_open boolean DEFAULT true,
    created_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone
);


ALTER TABLE public.project_reporting_submission OWNER TO psqladmin;

--
-- TOC entry 239 (class 1259 OID 25968)
-- Name: project_stage_config; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_stage_config (
    project_stage_config_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id uuid NOT NULL,
    stage public.project_stage NOT NULL,
    enabled boolean,
    num_reports_required integer,
    frequency public.report_frequency,
    min_requirements jsonb,
    created_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone
);


ALTER TABLE public.project_stage_config OWNER TO psqladmin;

--
-- TOC entry 235 (class 1259 OID 25923)
-- Name: project_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_type (
    project_type_id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(50) NOT NULL,
    is_active boolean,
    created_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone
);


ALTER TABLE public.project_type OWNER TO psqladmin;

--
-- TOC entry 236 (class 1259 OID 25932)
-- Name: project_typecast; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.project_typecast (
    project_typecast_id uuid DEFAULT gen_random_uuid() NOT NULL,
    project_type_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    is_maintenance boolean,
    is_active boolean,
    created_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone
);


ALTER TABLE public.project_typecast OWNER TO psqladmin;

--
-- TOC entry 227 (class 1259 OID 24884)
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    role_id uuid DEFAULT gen_random_uuid() NOT NULL,
    role_name character varying(255) NOT NULL,
    description character varying(255),
    is_active boolean DEFAULT true,
    created_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone
);


ALTER TABLE public.roles OWNER TO psqladmin;

--
-- TOC entry 228 (class 1259 OID 24892)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    user_id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_name character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role_id uuid NOT NULL,
    is_active boolean DEFAULT true,
    created_on timestamp without time zone DEFAULT now(),
    updated_on timestamp without time zone,
    organization_id uuid
);


ALTER TABLE public.users OWNER TO psqladmin;

--
-- TOC entry 229 (class 1259 OID 24900)
-- Name: v_emission_factor_values_pivot; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_emission_factor_values_pivot AS
 SELECT ef.emission_factor_id,
    ef.emission_source_id,
    es.name AS emission_source_name,
    ef.measurement_unit_id,
    mu.name AS measurement_unit_name,
    esc.emissions_sub_category_id,
    esc.name AS emissions_sub_category_name,
    ec.emissions_category_id,
    ec.name AS emissions_category_name,
    max(
        CASE
            WHEN ((ev.stage_code)::text = 'A1-3'::text) THEN ev.gwp_kgco2e_per_unit
            ELSE NULL::numeric
        END) AS a1_3,
    max(
        CASE
            WHEN ((ev.stage_code)::text = 'A4'::text) THEN ev.gwp_kgco2e_per_unit
            ELSE NULL::numeric
        END) AS a4,
    max(
        CASE
            WHEN ((ev.stage_code)::text = 'A5'::text) THEN ev.gwp_kgco2e_per_unit
            ELSE NULL::numeric
        END) AS a5,
    max(
        CASE
            WHEN ((ev.stage_code)::text = 'B2-5'::text) THEN ev.gwp_kgco2e_per_unit
            ELSE NULL::numeric
        END) AS b2_5,
    max(
        CASE
            WHEN ((ev.stage_code)::text = 'C2'::text) THEN ev.gwp_kgco2e_per_unit
            ELSE NULL::numeric
        END) AS c2,
    max(
        CASE
            WHEN ((ev.stage_code)::text = 'C3-4'::text) THEN ev.gwp_kgco2e_per_unit
            ELSE NULL::numeric
        END) AS c3_4
   FROM (((((public.emission_factor ef
     JOIN public.emission_source es ON ((es.emission_source_id = ef.emission_source_id)))
     LEFT JOIN public.emissions_sub_category esc ON ((esc.emissions_sub_category_id = es.emissions_sub_category_id)))
     LEFT JOIN public.emissions_category ec ON ((ec.emissions_category_id = esc.emissions_category_id)))
     JOIN public.measurement_unit mu ON ((mu.measurement_unit_id = ef.measurement_unit_id)))
     LEFT JOIN public.emission_factor_value ev ON ((ev.emission_factor_id = ef.emission_factor_id)))
  GROUP BY ef.emission_factor_id, ef.emission_source_id, es.name, ef.measurement_unit_id, mu.name, esc.emissions_sub_category_id, esc.name, ec.emissions_category_id, ec.name;


ALTER VIEW public.v_emission_factor_values_pivot OWNER TO psqladmin;

--
-- TOC entry 230 (class 1259 OID 24905)
-- Name: view_emission_factor_values; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.view_emission_factor_values AS
 SELECT ev.emission_factor_value_id,
    ev.emission_factor_id,
    ev.stage_code,
    ev.gwp_kgco2e_per_unit,
    ev.created_on,
    ev.updated_on,
    ef.emission_source_id,
    ef.measurement_unit_id,
    ef.is_active AS factor_is_active,
    es.name AS emission_source_name,
    mu.name AS measurement_unit_name,
    esc.emissions_sub_category_id,
    esc.name AS emissions_sub_category_name,
    ec.emissions_category_id,
    ec.name AS emissions_category_name
   FROM (((((public.emission_factor_value ev
     JOIN public.emission_factor ef ON ((ef.emission_factor_id = ev.emission_factor_id)))
     JOIN public.emission_source es ON ((es.emission_source_id = ef.emission_source_id)))
     JOIN public.measurement_unit mu ON ((mu.measurement_unit_id = ef.measurement_unit_id)))
     LEFT JOIN public.emissions_sub_category esc ON ((esc.emissions_sub_category_id = es.emissions_sub_category_id)))
     LEFT JOIN public.emissions_category ec ON ((ec.emissions_category_id = esc.emissions_category_id)));


ALTER VIEW public.view_emission_factor_values OWNER TO psqladmin;

--
-- TOC entry 231 (class 1259 OID 24910)
-- Name: view_emission_factors; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.view_emission_factors AS
 SELECT ef.emission_factor_id,
    ef.is_active,
    ef.created_on,
    ef.updated_on,
    ef.emission_source_id,
    ef.measurement_unit_id,
    es.name AS emission_source_name,
    mu.name AS measurement_unit_name,
    esc.emissions_sub_category_id,
    esc.name AS emissions_sub_category_name,
    ec.emissions_category_id,
    ec.name AS emissions_category_name
   FROM ((((public.emission_factor ef
     JOIN public.emission_source es ON ((es.emission_source_id = ef.emission_source_id)))
     JOIN public.measurement_unit mu ON ((mu.measurement_unit_id = ef.measurement_unit_id)))
     LEFT JOIN public.emissions_sub_category esc ON ((esc.emissions_sub_category_id = es.emissions_sub_category_id)))
     LEFT JOIN public.emissions_category ec ON ((ec.emissions_category_id = esc.emissions_category_id)));


ALTER VIEW public.view_emission_factors OWNER TO psqladmin;

--
-- TOC entry 4340 (class 0 OID 25029)
-- Dependencies: 232
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.alembic_version VALUES ('a224bbfcb0aa');


--
-- TOC entry 4328 (class 0 OID 24825)
-- Dependencies: 217
-- Data for Name: emission_entry; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.emission_entry VALUES ('11f4c117-1286-4e22-87ea-e8df670ac839', '55555555-5555-5555-5555-555555555555', '77777777-7777-7777-7777-777777777777', '37ab3940-ecd4-45cc-887c-1a093bdbfa2a', 'f0610ed5-fdee-4306-ba46-98618b65eace', '6b461ae3-c0e5-408b-9f73-52aa6142feef', '1e7c6b68-46ea-4e5c-bee9-189080e5ff7b', 'Estimated', 20.000000, 'Test', 200.000000, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '2026-01-28 12:39:42.268196', NULL);
INSERT INTO public.emission_entry VALUES ('18147351-f9e8-4bde-a593-db498b6116d4', '44444444-4444-4444-4444-444444444444', '66666666-6666-6666-6666-666666666666', '37ab3940-ecd4-45cc-887c-1a093bdbfa2a', 'f0610ed5-fdee-4306-ba46-98618b65eace', '6b461ae3-c0e5-408b-9f73-52aa6142feef', '1e7c6b68-46ea-4e5c-bee9-189080e5ff7b', 'Estimated', 10.000000, 'string', 10000.000000, 'cccccccc-cccc-cccc-cccc-cccccccccccc', '2026-01-28 12:31:43.645222', NULL);
INSERT INTO public.emission_entry VALUES ('ef18b47c-5f6a-4178-a45d-e75f510e05d8', '44444444-4444-4444-4444-444444444444', '66666666-6666-6666-6666-666666666666', '37ab3940-ecd4-45cc-887c-1a093bdbfa2a', 'f0610ed5-fdee-4306-ba46-98618b65eace', '6b461ae3-c0e5-408b-9f73-52aa6142feef', '1e7c6b68-46ea-4e5c-bee9-189080e5ff7b', 'Estimated', 10.000000, 'string', 5000.000000, 'cccccccc-cccc-cccc-cccc-cccccccccccc', '2026-01-28 12:39:02.419056', NULL);


--
-- TOC entry 4329 (class 0 OID 24830)
-- Dependencies: 218
-- Data for Name: emission_entry_summary; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.emission_entry_summary VALUES ('c5d0980f-7682-491f-a391-30778c865603', '44444444-4444-4444-4444-444444444444', '66666666-6666-6666-6666-666666666666', 'New Submissions', 'cccccccc-cccc-cccc-cccc-cccccccccccc', '2026-01-28 12:40:10.160516', NULL);
INSERT INTO public.emission_entry_summary VALUES ('96710526-2aa9-4387-a6cb-d3a28b55d6a7', '55555555-5555-5555-5555-555555555555', '66666666-6666-6666-6666-666666666666', 'New Test', 'cccccccc-cccc-cccc-cccc-cccccccccccc', '2026-01-28 12:40:24.200915', NULL);


--
-- TOC entry 4330 (class 0 OID 24837)
-- Dependencies: 219
-- Data for Name: emission_factor; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.emission_factor VALUES ('1e7c6b68-46ea-4e5c-bee9-189080e5ff7b', 'f0610ed5-fdee-4306-ba46-98618b65eace', '6b461ae3-c0e5-408b-9f73-52aa6142feef', true, '2026-01-23 05:15:34.925913', NULL);
INSERT INTO public.emission_factor VALUES ('45bedfb5-9f2b-4a41-b792-94e14c3c6f40', '219fb05a-f73a-497f-991e-b1ec09cebf23', '6b461ae3-c0e5-408b-9f73-52aa6142feef', true, '2026-01-23 05:16:15.710759', NULL);
INSERT INTO public.emission_factor VALUES ('df0dfb86-3d58-453a-b3d4-7c9f64b7f96a', 'e7c1612c-fea0-4f15-9d1b-baaf26e4a9e9', '6b461ae3-c0e5-408b-9f73-52aa6142feef', true, '2026-01-23 05:16:31.864631', NULL);


--
-- TOC entry 4331 (class 0 OID 24843)
-- Dependencies: 220
-- Data for Name: emission_factor_value; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.emission_factor_value VALUES ('dc64f873-dfef-4e16-976a-cb3ecb0812e0', '1e7c6b68-46ea-4e5c-bee9-189080e5ff7b', 'A1-3', 283.856227, '2026-01-23 05:30:00.793964', NULL);
INSERT INTO public.emission_factor_value VALUES ('d6dd6300-bee9-4b1c-a8c5-5f66d545f803', '1e7c6b68-46ea-4e5c-bee9-189080e5ff7b', 'A4', 6.455210, '2026-01-23 05:30:08.674798', NULL);
INSERT INTO public.emission_factor_value VALUES ('9e810bbf-04e4-44d5-a65f-5325d72af3d7', '1e7c6b68-46ea-4e5c-bee9-189080e5ff7b', 'A5', 15.126861, '2026-01-23 05:30:08.674798', NULL);
INSERT INTO public.emission_factor_value VALUES ('5dfb9375-dd5c-49cc-a062-69c285ffcbc9', '1e7c6b68-46ea-4e5c-bee9-189080e5ff7b', 'B2-5', 305.438297, '2026-01-23 05:30:08.674798', NULL);
INSERT INTO public.emission_factor_value VALUES ('6a6587e0-2cff-48a1-9ba1-1d251018ad39', '1e7c6b68-46ea-4e5c-bee9-189080e5ff7b', 'C2', 12.225776, '2026-01-23 05:30:08.674798', NULL);
INSERT INTO public.emission_factor_value VALUES ('afcaeab8-40b5-4162-8c07-aa2b53bff81c', '1e7c6b68-46ea-4e5c-bee9-189080e5ff7b', 'C3-4', 0.000000, '2026-01-23 05:30:08.674798', NULL);
INSERT INTO public.emission_factor_value VALUES ('56b7e805-9012-4a6a-8a58-64a11089f3ec', '45bedfb5-9f2b-4a41-b792-94e14c3c6f40', 'A1-3', 313.796145, '2026-01-23 05:32:52.509492', NULL);
INSERT INTO public.emission_factor_value VALUES ('ae6fa227-a943-4428-9676-c31ed59f5b8d', '45bedfb5-9f2b-4a41-b792-94e14c3c6f40', 'A4', 5.683832, '2026-01-23 05:32:52.509492', NULL);
INSERT INTO public.emission_factor_value VALUES ('1e5e6d38-3c21-4505-a99a-2d2367a5a566', '45bedfb5-9f2b-4a41-b792-94e14c3c6f40', 'A5', 16.512241, '2026-01-23 05:32:52.509492', NULL);
INSERT INTO public.emission_factor_value VALUES ('4b04562f-7fc2-43c1-beb4-4422b4bc452f', '45bedfb5-9f2b-4a41-b792-94e14c3c6f40', 'B2-5', 335.992218, '2026-01-23 05:32:52.509492', NULL);
INSERT INTO public.emission_factor_value VALUES ('22c9d5fd-36d6-440a-a638-68e7f9d409ae', '45bedfb5-9f2b-4a41-b792-94e14c3c6f40', 'C2', 10.764834, '2026-01-23 05:32:52.509492', NULL);
INSERT INTO public.emission_factor_value VALUES ('6bb2c4d0-aafe-4b7d-99b3-181c28200920', '45bedfb5-9f2b-4a41-b792-94e14c3c6f40', 'C3-4', 0.000000, '2026-01-23 05:32:52.509492', NULL);
INSERT INTO public.emission_factor_value VALUES ('4bb1f524-fb79-48f1-a8e9-e11990019389', 'df0dfb86-3d58-453a-b3d4-7c9f64b7f96a', 'A1-3', 313.796145, '2026-01-23 05:36:02.309074', NULL);
INSERT INTO public.emission_factor_value VALUES ('b16b4550-8b69-4c64-a49f-eb97b7d17d3e', 'df0dfb86-3d58-453a-b3d4-7c9f64b7f96a', 'A4', 5.683832, '2026-01-23 05:36:02.309074', NULL);
INSERT INTO public.emission_factor_value VALUES ('5608362b-3a0d-434f-981e-b0161767ab3b', 'df0dfb86-3d58-453a-b3d4-7c9f64b7f96a', 'A5', 12.384180, '2026-01-23 05:36:02.309074', NULL);
INSERT INTO public.emission_factor_value VALUES ('e4e9f363-bf0b-4240-a478-2bf2e351de4f', 'df0dfb86-3d58-453a-b3d4-7c9f64b7f96a', 'B2-5', 331.864158, '2026-01-23 05:36:02.309074', NULL);
INSERT INTO public.emission_factor_value VALUES ('8c1d4600-c771-43bb-be88-00182912479b', 'df0dfb86-3d58-453a-b3d4-7c9f64b7f96a', 'C2', 10.764834, '2026-01-23 05:36:02.309074', NULL);
INSERT INTO public.emission_factor_value VALUES ('60ac343b-4b71-4408-a271-e0ea98f32027', 'df0dfb86-3d58-453a-b3d4-7c9f64b7f96a', 'C3-4', 0.000000, '2026-01-23 05:36:02.309074', NULL);


--
-- TOC entry 4332 (class 0 OID 24848)
-- Dependencies: 221
-- Data for Name: emission_source; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.emission_source VALUES ('f0610ed5-fdee-4306-ba46-98618b65eace', 'C25/30 Grade readymix concrete', '37ab3940-ecd4-45cc-887c-1a093bdbfa2a', '6b461ae3-c0e5-408b-9f73-52aa6142feef', true, '2026-01-23 05:03:32.957205', NULL);
INSERT INTO public.emission_source VALUES ('219fb05a-f73a-497f-991e-b1ec09cebf23', 'Granolithic Concrete', '37ab3940-ecd4-45cc-887c-1a093bdbfa2a', '6b461ae3-c0e5-408b-9f73-52aa6142feef', true, '2026-01-23 05:03:32.957205', NULL);
INSERT INTO public.emission_source VALUES ('e7c1612c-fea0-4f15-9d1b-baaf26e4a9e9', 'Mortar', '37ab3940-ecd4-45cc-887c-1a093bdbfa2a', '6b461ae3-c0e5-408b-9f73-52aa6142feef', true, '2026-01-23 05:03:32.957205', NULL);


--
-- TOC entry 4333 (class 0 OID 24854)
-- Dependencies: 222
-- Data for Name: emissions_category; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.emissions_category VALUES ('fe321fdd-10a2-4475-8685-cb3cdf3b4185', 'Material', true, '2026-01-23 04:04:17.677932', NULL);


--
-- TOC entry 4334 (class 0 OID 24859)
-- Dependencies: 223
-- Data for Name: emissions_sub_category; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.emissions_sub_category VALUES ('37ab3940-ecd4-45cc-887c-1a093bdbfa2a', 'Concrete and Mortar', 'fe321fdd-10a2-4475-8685-cb3cdf3b4185', true, '2026-01-23 04:04:30.670709', NULL);


--
-- TOC entry 4335 (class 0 OID 24864)
-- Dependencies: 224
-- Data for Name: measurement_unit; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.measurement_unit VALUES ('6b461ae3-c0e5-408b-9f73-52aa6142feef', 'm3', true, '2026-01-23 04:04:35.367233', NULL);
INSERT INTO public.measurement_unit VALUES ('274f62c4-1152-47ec-80b6-8371558376e6', 'each', true, '2026-01-23 04:13:52.9247', NULL);


--
-- TOC entry 4341 (class 0 OID 25905)
-- Dependencies: 233
-- Data for Name: organization; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.organization VALUES ('98b650ef-c49f-4344-8bc8-fb22a78b5887', 'Proponent', true, '2026-01-29 06:19:12.157825', NULL, 'DESIGNERS');
INSERT INTO public.organization VALUES ('03d35975-04d0-4227-a74f-e17ae50d6b8d', 'Delivery', true, '2026-01-29 06:19:45.570572', NULL, 'DESIGNERS');
INSERT INTO public.organization VALUES ('a7f47223-dde5-40ef-a108-220a7ec28cf3', 'Designer', true, '2026-01-29 06:19:58.514559', NULL, 'DESIGNERS');
INSERT INTO public.organization VALUES ('c245994a-231f-42b2-a6b1-c7374b884197', 'AECOM', true, '2026-01-29 06:20:40.316387', NULL, 'DESIGNERS');
INSERT INTO public.organization VALUES ('609fe034-556a-40bc-8fa6-9b196deb3495', 'ADCO Constructions', true, '2026-01-29 06:20:21.058409', NULL, 'CONTRACTORS');


--
-- TOC entry 4342 (class 0 OID 25914)
-- Dependencies: 234
-- Data for Name: postcode_reference; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.postcode_reference VALUES ('84088592-2dfd-43e3-b244-d3afbb555217', '800', 'METROPOLITAN', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('d8aaed7e-b8b4-4acb-8ba3-a07bb93609e8', '810', 'METROPOLITAN', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('7f1429b1-a3f8-4059-9c54-69bfe3f4dd1b', '812', 'METROPOLITAN', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('24214bc1-1a68-40eb-89cc-7d3c0aa456be', '820', 'METROPOLITAN', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('1fe38a62-b1c0-48df-9ca3-596adf4c5b1e', '822', 'REGIONAL', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('48e2a9a6-828f-477a-be1a-015d28e6fc3c', '828', 'REGIONAL', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('ce3046c5-0532-42e1-828b-7c8c81324b90', '829', 'REGIONAL', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('98e597e4-e237-49a2-9c5f-85d37e5c025e', '830', 'REGIONAL', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('a9fe8af0-412b-4df0-bf26-6e5190f9d318', '832', 'REMOTE', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('261165ad-2479-43cd-983e-d549b698f4f3', '834', 'REMOTE', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('496a314e-dabe-44cc-94d7-45114757311b', '835', 'REMOTE', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('2f85fa17-2e1b-4620-b7e1-49e6d4329e66', '836', 'REMOTE', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('7cebe62e-85d5-4178-9ccd-991236b6afaa', '837', 'REMOTE', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('0a55c4d3-5eb0-4c05-b412-bf4c0e9aea67', '838', 'REMOTE', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('a9c54e7d-c563-41a7-812d-9da87a2f2fbb', '839', 'REMOTE', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('48390e1b-6dc6-4672-b626-b21fa6b14a28', '840', 'REMOTE', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('86bd583b-5029-4fea-9ef3-46398119ad4f', '841', 'REMOTE', '2026-01-29 05:59:05.343373');
INSERT INTO public.postcode_reference VALUES ('5c32cacf-5d05-457b-95e4-d37ac34c4244', '842', 'REMOTE', '2026-01-29 05:59:05.343373');


--
-- TOC entry 4336 (class 0 OID 24870)
-- Dependencies: 225
-- Data for Name: project; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.project VALUES ('44444444-4444-4444-4444-444444444444', 'Austroads Carbon Accounting POC', 'Infrastructure', 'POC project to validate emission entry workflow', true, '2026-01-23 04:38:41.383171', NULL, 'SMALL', NULL, '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '98b650ef-c49f-4344-8bc8-fb22a78b5887', 'ae544dd2-bd70-4aed-a0c0-b7a2891d60bf', NULL);
INSERT INTO public.project VALUES ('55555555-5555-5555-5555-555555555555', 'Urban Road Upgrade – Stage 2', 'Roadworks', 'Urban corridor upgrade with reporting periods', true, '2026-01-23 04:38:41.383171', NULL, 'SMALL', NULL, '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '98b650ef-c49f-4344-8bc8-fb22a78b5887', 'ae544dd2-bd70-4aed-a0c0-b7a2891d60bf', NULL);
INSERT INTO public.project VALUES ('bd5d5269-388a-44cd-a9c4-50c867261df1', 'New_Project_Test', 'small', 'small project CMRT', true, '2026-01-27 04:02:29.856007', NULL, 'SMALL', NULL, '', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, '98b650ef-c49f-4344-8bc8-fb22a78b5887', 'ae544dd2-bd70-4aed-a0c0-b7a2891d60bf', NULL);
INSERT INTO public.project VALUES ('e70dc2af-3e3a-4397-85b8-92adebb89395', 'Demo Project 001', 'Road', NULL, true, '2026-01-29 08:52:31.343492', NULL, 'SMALL', false, 'C-123', NULL, NULL, NULL, NULL, '2026-01-01', 25, 100.00, NULL, NULL, NULL, '98b650ef-c49f-4344-8bc8-fb22a78b5887', 'ae544dd2-bd70-4aed-a0c0-b7a2891d60bf', 'ae544dd2-bd70-4aed-a0c0-b7a2891d60bf');


--
-- TOC entry 4345 (class 0 OID 25939)
-- Dependencies: 237
-- Data for Name: project_organizations; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.project_organizations VALUES ('68a4a82a-8324-4ca4-92b5-b87c9342641c', 'e70dc2af-3e3a-4397-85b8-92adebb89395', '98b650ef-c49f-4344-8bc8-fb22a78b5887', 'DELIVERY', '2026-01-29 08:52:31.343492');


--
-- TOC entry 4346 (class 0 OID 25956)
-- Dependencies: 238
-- Data for Name: project_postcode; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.project_postcode VALUES ('ac9c0772-8f49-449f-8e17-df6ca2a0b0b1', 'e70dc2af-3e3a-4397-85b8-92adebb89395', '800', 'METROPOLITAN', '2026-01-29 08:52:31.343492');


--
-- TOC entry 4337 (class 0 OID 24878)
-- Dependencies: 226
-- Data for Name: project_reporting_submission; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.project_reporting_submission VALUES ('66666666-6666-6666-6666-666666666666', '44444444-4444-4444-4444-444444444444', 'MONTHLY', '2026-01', '2026-01-01', '2026-01-31', '2026-02-07', true, '2026-01-23 04:38:51.770591', NULL);
INSERT INTO public.project_reporting_submission VALUES ('77777777-7777-7777-7777-777777777777', '55555555-5555-5555-5555-555555555555', 'QUARTERLY', 'FY26-Q1', '2026-01-01', '2026-03-31', '2026-03-31', true, '2026-01-23 04:38:51.770591', NULL);
INSERT INTO public.project_reporting_submission VALUES ('b2f9b50e-1eec-4ce4-9f1f-cd610b22dbe6', 'bd5d5269-388a-44cd-a9c4-50c867261df1', 'MONTHLY', '2026-02', '2026-02-01', '2026-05-30', '2026-05-30', true, '2026-01-27 05:03:54.137356', NULL);
INSERT INTO public.project_reporting_submission VALUES ('06b1f903-c068-43b9-87ca-6e0189f95b7d', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'MONTHLY', 'Jan 2026', '2026-01-01', '2026-01-31', NULL, true, '2026-01-29 08:52:31.343492', NULL);
INSERT INTO public.project_reporting_submission VALUES ('3bbd2d7e-b304-4511-8a4c-49af0cbeefd5', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'MONTHLY', 'Feb 2026', '2026-02-01', '2026-02-28', NULL, true, '2026-01-29 08:52:31.343492', NULL);
INSERT INTO public.project_reporting_submission VALUES ('dd88b810-e1f2-4c23-bc96-2f4e4ae1b013', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'MONTHLY', 'Mar 2026', '2026-03-01', '2026-03-31', NULL, true, '2026-01-29 08:52:31.343492', NULL);
INSERT INTO public.project_reporting_submission VALUES ('00971fc2-6b16-411f-ba27-69cb892a5f16', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'MONTHLY', 'Apr 2026', '2026-04-01', '2026-04-30', NULL, true, '2026-01-29 08:52:31.343492', NULL);
INSERT INTO public.project_reporting_submission VALUES ('e840fc33-653c-48f5-a76d-ca2a09f04443', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'MONTHLY', 'May 2026', '2026-05-01', '2026-05-31', NULL, true, '2026-01-29 08:52:31.343492', NULL);
INSERT INTO public.project_reporting_submission VALUES ('a5417b73-2659-484d-a529-183c6e692487', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'MONTHLY', 'Jun 2026', '2026-06-01', '2026-06-30', NULL, true, '2026-01-29 08:52:31.343492', NULL);
INSERT INTO public.project_reporting_submission VALUES ('978fb05f-f8f0-4a23-9322-4867d0780092', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'MONTHLY', 'Jul 2026', '2026-07-01', '2026-07-31', NULL, true, '2026-01-29 08:52:31.343492', NULL);
INSERT INTO public.project_reporting_submission VALUES ('c1875231-d9c3-49d8-bfd4-2174d3d5c540', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'MONTHLY', 'Aug 2026', '2026-08-01', '2026-08-31', NULL, true, '2026-01-29 08:52:31.343492', NULL);
INSERT INTO public.project_reporting_submission VALUES ('8d00c14a-94b9-4f8a-85ee-65e747579fd1', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'MONTHLY', 'Sep 2026', '2026-09-01', '2026-09-30', NULL, true, '2026-01-29 08:52:31.343492', NULL);
INSERT INTO public.project_reporting_submission VALUES ('561587ae-3e0c-45e3-93c9-c1b0137a9f41', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'MONTHLY', 'Oct 2026', '2026-10-01', '2026-10-31', NULL, true, '2026-01-29 08:52:31.343492', NULL);
INSERT INTO public.project_reporting_submission VALUES ('4aad92a9-82d0-424b-8b81-571c41c440ec', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'MONTHLY', 'Nov 2026', '2026-11-01', '2026-11-30', NULL, true, '2026-01-29 08:52:31.343492', NULL);
INSERT INTO public.project_reporting_submission VALUES ('fca5e955-8fdd-4e42-b06a-33a93a1c5144', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'MONTHLY', 'Dec 2026', '2026-12-01', '2026-12-31', NULL, true, '2026-01-29 08:52:31.343492', NULL);


--
-- TOC entry 4347 (class 0 OID 25968)
-- Dependencies: 239
-- Data for Name: project_stage_config; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.project_stage_config VALUES ('f61b3c85-c9a3-4229-95cc-f56c41597097', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'DESIGN', true, NULL, NULL, 'null', '2026-01-29 08:52:31.343492', NULL);
INSERT INTO public.project_stage_config VALUES ('2a8e7343-36f1-42d4-a2bb-a88acc1674ac', 'e70dc2af-3e3a-4397-85b8-92adebb89395', 'CONSTRUCTION', true, NULL, 'MONTHLY', 'null', '2026-01-29 08:52:31.343492', NULL);


--
-- TOC entry 4343 (class 0 OID 25923)
-- Dependencies: 235
-- Data for Name: project_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.project_type VALUES ('bae70b84-7e1a-4a04-a1c6-0fc542d0f2d6', 'Rail', true, '2026-01-29 06:23:46.634103', NULL);
INSERT INTO public.project_type VALUES ('6f1ac7be-fb35-40e2-970f-277532b731e7', 'Road', true, '2026-01-29 06:23:59.514123', NULL);
INSERT INTO public.project_type VALUES ('84510d68-35dd-421e-835d-ea8bd99eaa7e', 'Road/Rail', true, '2026-01-29 06:24:16.285322', NULL);


--
-- TOC entry 4344 (class 0 OID 25932)
-- Dependencies: 236
-- Data for Name: project_typecast; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.project_typecast VALUES ('1b9af2cf-22fe-4cdb-a34c-8d4f4516c381', 'bae70b84-7e1a-4a04-a1c6-0fc542d0f2d6', 'Bridge(Rail)', false, true, '2026-01-29 06:29:29.229715', NULL);
INSERT INTO public.project_typecast VALUES ('67699d64-8ec7-4678-ab12-715b093e3b23', 'bae70b84-7e1a-4a04-a1c6-0fc542d0f2d6', 'Light Rail', true, true, '2026-01-29 06:30:00.11436', NULL);
INSERT INTO public.project_typecast VALUES ('641bfa9b-c6c7-4afe-9e9e-1c2f8a1f5f07', 'bae70b84-7e1a-4a04-a1c6-0fc542d0f2d6', 'Highway', false, true, '2026-01-29 06:31:00.804034', NULL);
INSERT INTO public.project_typecast VALUES ('c3c9d382-11fc-4af3-8d66-c26ba2e1c9d6', 'bae70b84-7e1a-4a04-a1c6-0fc542d0f2d6', 'State Highway', true, true, '2026-01-29 06:31:18.811473', NULL);
INSERT INTO public.project_typecast VALUES ('2f52bd56-0abd-4c9e-929e-cefd5a267950', 'bae70b84-7e1a-4a04-a1c6-0fc542d0f2d6', 'Railway Station and Overbridge', false, true, '2026-01-29 06:32:05.82246', NULL);
INSERT INTO public.project_typecast VALUES ('5df80c3c-08ee-4d84-880c-44d0ea76d264', 'bae70b84-7e1a-4a04-a1c6-0fc542d0f2d6', 'Railway Station and Overbridge2', true, true, '2026-01-29 06:32:18.52483', NULL);


--
-- TOC entry 4338 (class 0 OID 24884)
-- Dependencies: 227
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.roles VALUES ('11111111-1111-1111-1111-111111111111', 'Admin', 'Full Access on Projects', true, '2026-01-23 04:38:22.122401', NULL);
INSERT INTO public.roles VALUES ('22222222-2222-2222-2222-222222222222', 'Contributor', 'Create and submit emission entries', true, '2026-01-23 04:38:22.122401', NULL);
INSERT INTO public.roles VALUES ('33333333-3333-3333-3333-333333333333', 'SuperAdmin', 'Full Access', true, '2026-01-23 04:38:22.122401', NULL);
INSERT INTO public.roles VALUES ('9fb8607a-50c1-4925-98cd-9115ba16deca', 'Test_New_Role', 'Role Test Api Endpoint', true, '2026-01-27 05:06:24.461203', NULL);


--
-- TOC entry 4339 (class 0 OID 24892)
-- Dependencies: 228
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public.users VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'Phanindra', 'phani@example.com', '$2b$12$8uX4M1QyT.O8bq2sWmZ1dOqYz6o0h8aXq8vO8mLkS7G9HcUoQf6n6', '11111111-1111-1111-1111-111111111111', true, '2026-01-23 04:38:34.373941', NULL, NULL);
INSERT INTO public.users VALUES ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Jyothi', 'jyothi@example.com', '$2b$12$8uX4M1QyT.O8bq2sWmZ1dOqYz6o0h8aXq8vO8mLkS7G9HcUoQf6n6', '33333333-3333-3333-3333-333333333333', true, '2026-01-23 04:38:34.373941', NULL, NULL);
INSERT INTO public.users VALUES ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'Arjit', 'arjit@example.com', '$2b$12$8uX4M1QyT.O8bq2sWmZ1dOqYz6o0h8aXq8vO8mLkS7G9HcUoQf6n6', '22222222-2222-2222-2222-222222222222', true, '2026-01-23 04:38:34.373941', NULL, NULL);
INSERT INTO public.users VALUES ('ae544dd2-bd70-4aed-a0c0-b7a2891d60bf', 'new_user', 'newuser@example.com', '$bcrypt-sha256$v=2,t=2b,r=12$UQTz3jGQIr98Ns9C6U1fr.$MwRY24fIhFJyaO9v9lME.mnlALyUjEu', '9fb8607a-50c1-4925-98cd-9115ba16deca', true, '2026-01-27 05:53:26.785239', NULL, NULL);


--
-- TOC entry 4133 (class 2606 OID 25033)
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- TOC entry 4099 (class 2606 OID 24916)
-- Name: emission_entry emission_entry_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_entry
    ADD CONSTRAINT emission_entry_pkey PRIMARY KEY (emission_entry_id);


--
-- TOC entry 4101 (class 2606 OID 24918)
-- Name: emission_entry_summary emission_entry_summary_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_entry_summary
    ADD CONSTRAINT emission_entry_summary_pkey PRIMARY KEY (emission_entry_summary_id);


--
-- TOC entry 4103 (class 2606 OID 24920)
-- Name: emission_entry_summary emission_entry_summary_project_id_project_reporting_submiss_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_entry_summary
    ADD CONSTRAINT emission_entry_summary_project_id_project_reporting_submiss_key UNIQUE (project_id, project_reporting_submission_id);


--
-- TOC entry 4105 (class 2606 OID 24922)
-- Name: emission_factor emission_factor_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_factor
    ADD CONSTRAINT emission_factor_pkey PRIMARY KEY (emission_factor_id);


--
-- TOC entry 4107 (class 2606 OID 24924)
-- Name: emission_factor_value emission_factor_value_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_factor_value
    ADD CONSTRAINT emission_factor_value_pkey PRIMARY KEY (emission_factor_value_id);


--
-- TOC entry 4109 (class 2606 OID 24926)
-- Name: emission_source emission_source_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_source
    ADD CONSTRAINT emission_source_pkey PRIMARY KEY (emission_source_id);


--
-- TOC entry 4111 (class 2606 OID 24928)
-- Name: emissions_category emissions_category_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emissions_category
    ADD CONSTRAINT emissions_category_pkey PRIMARY KEY (emissions_category_id);


--
-- TOC entry 4113 (class 2606 OID 24930)
-- Name: emissions_sub_category emissions_sub_category_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emissions_sub_category
    ADD CONSTRAINT emissions_sub_category_pkey PRIMARY KEY (emissions_sub_category_id);


--
-- TOC entry 4115 (class 2606 OID 24932)
-- Name: measurement_unit measurement_unit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.measurement_unit
    ADD CONSTRAINT measurement_unit_pkey PRIMARY KEY (measurement_unit_id);


--
-- TOC entry 4135 (class 2606 OID 25911)
-- Name: organization pk__organization; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organization
    ADD CONSTRAINT pk__organization PRIMARY KEY (organization_id);


--
-- TOC entry 4139 (class 2606 OID 25920)
-- Name: postcode_reference pk__postcode_reference; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.postcode_reference
    ADD CONSTRAINT pk__postcode_reference PRIMARY KEY (postcode_reference_id);


--
-- TOC entry 4149 (class 2606 OID 25945)
-- Name: project_organizations pk__project_organizations; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_organizations
    ADD CONSTRAINT pk__project_organizations PRIMARY KEY (project_organization_link_id);


--
-- TOC entry 4151 (class 2606 OID 25962)
-- Name: project_postcode pk__project_postcode; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_postcode
    ADD CONSTRAINT pk__project_postcode PRIMARY KEY (project_postcode_id);


--
-- TOC entry 4153 (class 2606 OID 25976)
-- Name: project_stage_config pk__project_stage_config; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_stage_config
    ADD CONSTRAINT pk__project_stage_config PRIMARY KEY (project_stage_config_id);


--
-- TOC entry 4143 (class 2606 OID 25929)
-- Name: project_type pk__project_type; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_type
    ADD CONSTRAINT pk__project_type PRIMARY KEY (project_type_id);


--
-- TOC entry 4147 (class 2606 OID 25938)
-- Name: project_typecast pk__project_typecast; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_typecast
    ADD CONSTRAINT pk__project_typecast PRIMARY KEY (project_typecast_id);


--
-- TOC entry 4117 (class 2606 OID 24934)
-- Name: project project_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_pkey PRIMARY KEY (project_id);


--
-- TOC entry 4121 (class 2606 OID 24936)
-- Name: project_reporting_submission project_reporting_submission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_reporting_submission
    ADD CONSTRAINT project_reporting_submission_pkey PRIMARY KEY (project_reporting_submission_id);


--
-- TOC entry 4123 (class 2606 OID 24938)
-- Name: project_reporting_submission project_reporting_submission_project_id_period_label_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_reporting_submission
    ADD CONSTRAINT project_reporting_submission_project_id_period_label_key UNIQUE (project_id, period_label);


--
-- TOC entry 4125 (class 2606 OID 24940)
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (role_id);


--
-- TOC entry 4137 (class 2606 OID 25913)
-- Name: organization uq__organization__name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.organization
    ADD CONSTRAINT uq__organization__name UNIQUE (name);


--
-- TOC entry 4145 (class 2606 OID 25931)
-- Name: project_type uq__project_type__name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_type
    ADD CONSTRAINT uq__project_type__name UNIQUE (name);


--
-- TOC entry 4127 (class 2606 OID 26036)
-- Name: roles uq__roles__role_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT uq__roles__role_name UNIQUE (role_name);


--
-- TOC entry 4129 (class 2606 OID 26038)
-- Name: users uq__users__email; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq__users__email UNIQUE (email);


--
-- TOC entry 4141 (class 2606 OID 25922)
-- Name: postcode_reference uq_postcode_reference_postcode; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.postcode_reference
    ADD CONSTRAINT uq_postcode_reference_postcode UNIQUE (postcode);


--
-- TOC entry 4119 (class 2606 OID 26005)
-- Name: project uq_project_project_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT uq_project_project_name UNIQUE (project_name);


--
-- TOC entry 4131 (class 2606 OID 24942)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- TOC entry 4154 (class 2606 OID 24954)
-- Name: emission_entry emission_entry_emission_factor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_entry
    ADD CONSTRAINT emission_entry_emission_factor_id_fkey FOREIGN KEY (emission_factor_id) REFERENCES public.emission_factor(emission_factor_id);


--
-- TOC entry 4155 (class 2606 OID 24959)
-- Name: emission_entry emission_entry_emission_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_entry
    ADD CONSTRAINT emission_entry_emission_source_id_fkey FOREIGN KEY (emission_source_id) REFERENCES public.emission_source(emission_source_id);


--
-- TOC entry 4156 (class 2606 OID 24964)
-- Name: emission_entry emission_entry_emissions_sub_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_entry
    ADD CONSTRAINT emission_entry_emissions_sub_category_id_fkey FOREIGN KEY (emissions_sub_category_id) REFERENCES public.emissions_sub_category(emissions_sub_category_id);


--
-- TOC entry 4157 (class 2606 OID 24969)
-- Name: emission_entry emission_entry_measurement_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_entry
    ADD CONSTRAINT emission_entry_measurement_unit_id_fkey FOREIGN KEY (measurement_unit_id) REFERENCES public.measurement_unit(measurement_unit_id);


--
-- TOC entry 4158 (class 2606 OID 24974)
-- Name: emission_entry emission_entry_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_entry
    ADD CONSTRAINT emission_entry_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- TOC entry 4159 (class 2606 OID 24979)
-- Name: emission_entry emission_entry_project_reporting_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_entry
    ADD CONSTRAINT emission_entry_project_reporting_submission_id_fkey FOREIGN KEY (project_reporting_submission_id) REFERENCES public.project_reporting_submission(project_reporting_submission_id);


--
-- TOC entry 4160 (class 2606 OID 24984)
-- Name: emission_entry emission_entry_submitted_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_entry
    ADD CONSTRAINT emission_entry_submitted_by_user_id_fkey FOREIGN KEY (submitted_by_user_id) REFERENCES public.users(user_id);


--
-- TOC entry 4164 (class 2606 OID 24989)
-- Name: emission_factor emission_factor_emission_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_factor
    ADD CONSTRAINT emission_factor_emission_source_id_fkey FOREIGN KEY (emission_source_id) REFERENCES public.emission_source(emission_source_id);


--
-- TOC entry 4165 (class 2606 OID 24994)
-- Name: emission_factor emission_factor_measurement_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_factor
    ADD CONSTRAINT emission_factor_measurement_unit_id_fkey FOREIGN KEY (measurement_unit_id) REFERENCES public.measurement_unit(measurement_unit_id);


--
-- TOC entry 4167 (class 2606 OID 25004)
-- Name: emission_source emission_source_emissions_sub_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_source
    ADD CONSTRAINT emission_source_emissions_sub_category_id_fkey FOREIGN KEY (emissions_sub_category_id) REFERENCES public.emissions_sub_category(emissions_sub_category_id);


--
-- TOC entry 4168 (class 2606 OID 25009)
-- Name: emission_source emission_source_measurement_unit_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_source
    ADD CONSTRAINT emission_source_measurement_unit_id_fkey FOREIGN KEY (measurement_unit_id) REFERENCES public.measurement_unit(measurement_unit_id);


--
-- TOC entry 4169 (class 2606 OID 25014)
-- Name: emissions_sub_category emissions_sub_category_emissions_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emissions_sub_category
    ADD CONSTRAINT emissions_sub_category_emissions_category_id_fkey FOREIGN KEY (emissions_category_id) REFERENCES public.emissions_category(emissions_category_id);


--
-- TOC entry 4161 (class 2606 OID 25992)
-- Name: emission_entry_summary fk__emission_entry_summary__project_id__project; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_entry_summary
    ADD CONSTRAINT fk__emission_entry_summary__project_id__project FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- TOC entry 4162 (class 2606 OID 25982)
-- Name: emission_entry_summary fk__emission_entry_summary__project_reporting_submissio_ccf6; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_entry_summary
    ADD CONSTRAINT fk__emission_entry_summary__project_reporting_submissio_ccf6 FOREIGN KEY (project_reporting_submission_id) REFERENCES public.project_reporting_submission(project_reporting_submission_id);


--
-- TOC entry 4163 (class 2606 OID 25987)
-- Name: emission_entry_summary fk__emission_entry_summary__submitted_by_user_id__users; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_entry_summary
    ADD CONSTRAINT fk__emission_entry_summary__submitted_by_user_id__users FOREIGN KEY (submitted_by_user_id) REFERENCES public.users(user_id);


--
-- TOC entry 4166 (class 2606 OID 25997)
-- Name: emission_factor_value fk__emission_factor_value__emission_factor_id__emission_factor; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.emission_factor_value
    ADD CONSTRAINT fk__emission_factor_value__emission_factor_id__emission_factor FOREIGN KEY (emission_factor_id) REFERENCES public.emission_factor(emission_factor_id);


--
-- TOC entry 4170 (class 2606 OID 26006)
-- Name: project fk__project__created_by_user_id__users; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT fk__project__created_by_user_id__users FOREIGN KEY (created_by_user_id) REFERENCES public.users(user_id);


--
-- TOC entry 4171 (class 2606 OID 26011)
-- Name: project fk__project__last_updated_by_user_id__users; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT fk__project__last_updated_by_user_id__users FOREIGN KEY (last_updated_by_user_id) REFERENCES public.users(user_id);


--
-- TOC entry 4172 (class 2606 OID 26016)
-- Name: project fk__project__proponent_org_id__organization; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT fk__project__proponent_org_id__organization FOREIGN KEY (proponent_org_id) REFERENCES public.organization(organization_id);


--
-- TOC entry 4176 (class 2606 OID 25946)
-- Name: project_organizations fk__project_organizations__organization_id__organization; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_organizations
    ADD CONSTRAINT fk__project_organizations__organization_id__organization FOREIGN KEY (organization_id) REFERENCES public.organization(organization_id);


--
-- TOC entry 4177 (class 2606 OID 25951)
-- Name: project_organizations fk__project_organizations__project_id__project; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_organizations
    ADD CONSTRAINT fk__project_organizations__project_id__project FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- TOC entry 4178 (class 2606 OID 25963)
-- Name: project_postcode fk__project_postcode__project_id__project; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_postcode
    ADD CONSTRAINT fk__project_postcode__project_id__project FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- TOC entry 4179 (class 2606 OID 25977)
-- Name: project_stage_config fk__project_stage_config__project_id__project; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_stage_config
    ADD CONSTRAINT fk__project_stage_config__project_id__project FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- TOC entry 4174 (class 2606 OID 26039)
-- Name: users fk__users__organization_id__organization; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk__users__organization_id__organization FOREIGN KEY (organization_id) REFERENCES public.organization(organization_id);


--
-- TOC entry 4173 (class 2606 OID 25019)
-- Name: project_reporting_submission project_reporting_submission_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.project_reporting_submission
    ADD CONSTRAINT project_reporting_submission_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- TOC entry 4175 (class 2606 OID 25024)
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(role_id);


-- Completed on 2026-02-05 19:18:25

--
-- PostgreSQL database dump complete
--

