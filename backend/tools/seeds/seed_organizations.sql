-- =============================================================================
-- Seed: Organizations & email domains
-- Source: tools/seeds/data/Organizations_list.csv
--
-- Idempotent: safe to re-run against dev / staging / prod.
--   - Organizations matched by lower(name); skipped if already present.
--   - Domains matched by (organization_id, domain); skipped if already present.
--
-- Tables: organization, organization_domains
-- =============================================================================

DO $$
DECLARE
    _id UUID;
BEGIN

    -- =========================================================================
    -- DESIGNERS
    -- =========================================================================

    -- AECOM
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'AECOM', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'aecom');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'aecom';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'aecom.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'aecom.com');

    -- Arcadis
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Arcadis', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'arcadis');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'arcadis';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'arcadis.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'arcadis.com');

    -- Architectus
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Architectus', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'architectus');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'architectus';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'architectus.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'architectus.com.au');

    -- Arup
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Arup', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'arup');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'arup';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'arup.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'arup.com');

    -- Aurecon
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Aurecon', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'aurecon');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'aurecon';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'aurecongroup.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'aurecongroup.com');

    -- BG&E
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'BG&E', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'bg&e');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'bg&e';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'bge.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'bge.com.au');

    -- Beca
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Beca', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'beca');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'beca';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'beca.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'beca.com');

    -- GHD
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'GHD', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'ghd');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'ghd';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'ghd.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'ghd.com');

    -- Jacobs
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Jacobs', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'jacobs');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'jacobs';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'jacobs.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'jacobs.com');

    -- Mott MacDonald
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Mott MacDonald', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'mott macdonald');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'mott macdonald';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'mottmac.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'mottmac.com');

    -- Robert Bird Group
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Robert Bird Group', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'robert bird group');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'robert bird group';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'robertbird.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'robertbird.com.au');

    -- SMEC
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'SMEC', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'smec');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'smec';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'smec.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'smec.com');

    -- WSP
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'WSP', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'wsp');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'wsp';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'wsp.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'wsp.com');

    -- Worley
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Worley', 'DESIGNERS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'worley');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'worley';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'worley.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'worley.com');

    -- =========================================================================
    -- CONTRACTORS
    -- =========================================================================

    -- ADCO Constructions
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'ADCO Constructions', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'adco constructions');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'adco constructions';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'adcoconstructions.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'adcoconstructions.com.au');

    -- AJ Lucas Group
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'AJ Lucas Group', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'aj lucas group');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'aj lucas group';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'lucas.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'lucas.com.au');

    -- AW Edwards
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'AW Edwards', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'aw edwards');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'aw edwards';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'awedwards.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'awedwards.com.au');

    -- Abergeldie Complex Infrastructure
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Abergeldie Complex Infrastructure', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'abergeldie complex infrastructure');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'abergeldie complex infrastructure';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'abergeldie.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'abergeldie.com');

    -- Acciona
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Acciona', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'acciona');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'acciona';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'acciona.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'acciona.com.au');

    -- BESIX / Watpac
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'BESIX / Watpac', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'besix / watpac');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'besix / watpac';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'besixwatpac.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'besixwatpac.com');

    -- BMD
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'BMD', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'bmd');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'bmd';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'bmd.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'bmd.com.au');

    -- Bechtel Australia
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Bechtel Australia', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'bechtel australia');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'bechtel australia';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'bechtel.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'bechtel.com');

    -- Bielby Holdings
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Bielby Holdings', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'bielby holdings');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'bielby holdings';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'bielby.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'bielby.com.au');

    -- Bouygues
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Bouygues', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'bouygues');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'bouygues';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'bouygues-construction.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'bouygues-construction.com');

    -- Buildcorp
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Buildcorp', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'buildcorp');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'buildcorp';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'buildcorp.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'buildcorp.com.au');

    -- Built
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Built', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'built');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'built';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'built.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'built.com.au');

    -- CMC Pty Ltd
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'CMC Pty Ltd', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'cmc pty ltd');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'cmc pty ltd';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'cmc.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'cmc.com.au');

    -- CPB Contractors
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'CPB Contractors', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'cpb contractors');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'cpb contractors';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'cpbcon.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'cpbcon.com.au');

    -- Degnan
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Degnan', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'degnan');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'degnan';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'degnan.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'degnan.com.au');

    -- Downer
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Downer', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'downer');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'downer';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'downergroup.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'downergroup.com');

    -- Fulton Hogan
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Fulton Hogan', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'fulton hogan');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'fulton hogan';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'fultonhogan.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'fultonhogan.com');

    -- Hansen Yuncken
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Hansen Yuncken', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'hansen yuncken');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'hansen yuncken';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'hansenyuncken.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'hansenyuncken.com.au');

    -- Hutchinson Builders
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Hutchinson Builders', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'hutchinson builders');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'hutchinson builders';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'hutchinsonbuilders.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'hutchinsonbuilders.com.au');

    -- John Holland
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'John Holland', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'john holland');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'john holland';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'johnholland.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'johnholland.com.au');

    -- Laing O'Rourke
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Laing O''Rourke', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'laing o''rourke');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'laing o''rourke';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'laingorourke.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'laingorourke.com');

    -- Lendlease
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Lendlease', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'lendlease');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'lendlease';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'lendlease.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'lendlease.com');

    -- McConnell Dowell
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'McConnell Dowell', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'mcconnell dowell');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'mcconnell dowell';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'mcconnelldowell.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'mcconnelldowell.com');

    -- Monadelphous
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Monadelphous', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'monadelphous');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'monadelphous';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'monadelphous.com.au', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'monadelphous.com.au');

    -- Multiplex
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Multiplex', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'multiplex');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'multiplex';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'multiplex.global', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'multiplex.global');

    -- Thiess
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Thiess', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'thiess');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'thiess';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'thiess.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'thiess.com');

    -- Webuild
    INSERT INTO organization (id, name, type, country, is_active, is_proponent, created_on)
    SELECT gen_random_uuid(), 'Webuild', 'CONTRACTORS', 'AU', true, true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization WHERE lower(name) = 'webuild');
    SELECT id INTO _id FROM organization WHERE lower(name) = 'webuild';
    INSERT INTO organization_domains (id, organization_id, domain, is_active, created_on)
    SELECT gen_random_uuid(), _id, 'webuildgroup.com', true, now()
    WHERE NOT EXISTS (SELECT 1 FROM organization_domains WHERE organization_id = _id AND domain = 'webuildgroup.com');

END $$;
