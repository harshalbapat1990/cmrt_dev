import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import http from '@/http';
import { extractApiError } from '@/utils/utils';
import { useUser } from '@/context/UserContext';
import { SelectListbox } from '@/components/common/Select';
import PaginationBar from '@/components/PaginationBar';

import type {
  PageTab, DatasetRevision, DatasetScope,
  RecycledContentRow, TransportRow, WasteRateRow, AuditLogRow, BgmRow,
  G1Filter, G234Filter, RcFilter, TrFilter, DecarbFilter, DecarbRow, DensityFilter, FugitiveFilter,
  EvUptakeRow, VepmRow, FreightRailRow, EvUptakeFilter,
  G1Row, G2Row, G34Row,
  NamedOption, DensityRow, UnitConversionRow, FugitiveRow, EnergyDensityConversionRow,
  MaintenanceReplacementRow,
  OperationalEquipmentRow,
  VehicleClassOption,
  VehicleMassRow, InterruptedVehicleRow, UninterruptedVehicleRow, VehicleEnergyConversionRow,
  CarbonValueRow, CarbonValueFilter, WastageRateRow, WastageRateFilter,
  ContentRecycledRow, ContentRecycledFilter, ContentRecycledEditableField,
  ConcreteMixAssumption, ConcreteMixDesignRow, ConcreteMixBundle, ConcreteMixStrengthField,
  DirectSubstitutionRow,
  ElectricityRecyclingAssumptionRow,
  RenewableEnergyRow,

} from './types';
import {
  GRADE_OPTIONS, TABS, TAB_GROUPS, INIT_G1, INIT_G234, INIT_RC, INIT_TR, INIT_DECARB, INIT_CARBON_VALUES, INIT_EV_UPTAKE, INIT_DENSITY, INIT_FUGITIVE, INIT_WASTAGE_RATES, INIT_CONTENT_RECYCLED,
} from './constants';
import { distinct, LABEL_TO_METRIC_CODE } from './utils';
import { pivotGrade1, pivotGrade2, pivotGrade34 } from './pivot';
import { StatusBadge } from './components/Badges';
import { MultiSelect, TextFilter } from './components/FilterControls';
import Grade1Table from './components/Grade1Table';
import Grade2Table from './components/Grade2Table';
import Grade34Table from './components/Grade34Table';
import RecycledContentTable from './components/RecycledContentTable';
import TransportTable from './components/TransportTable';
import WasteRateTable from './components/WasteRateTable';
import AuditTrailTable from './components/AuditTrailTable';
import ElectricDecarbTable from './components/ElectricDecarbTable';
import EvUptakeTable from './components/EvUptakeTable';
import VepmTable from './components/VepmTable';
import FreightRailTable from './components/FreightRailTable';
import MaintenanceReplacementTable from './components/MaintenanceReplacementTable';
import OperationalEquipmentTable from './components/OperationalEquipmentTable';
import DensitiesTable from './components/DensitiesTable';
import UnitConversionsTable from './components/UnitConversionsTable';
import FugitivesTable from './components/FugitivesTable';
import EnergyDensityConversionsTable from './components/EnergyDensityConversionsTable';
import WastageRatesTable from './components/WastageRatesTable';
import ContentRecycledTable from './components/ContentRecycledTable';
import RenewableEnergyTable from './components/RenewableEnergyTable';
import VehicleMassesTable from './components/VehicleMassesTable';
import InterruptedVehiclesTable from './components/InterruptedVehiclesTable';
import UninterruptedVehiclesTable from './components/UninterruptedVehiclesTable';
import VehicleEnergyConversionTable from './components/VehicleEnergyConversionTable';
import CarbonValuesTable from './components/CarbonValuesTable';
import NewRevisionModal from './components/NewRevisionModal';
import DatasetBulkBar from './components/DatasetBulkBar';
import { UploadModal } from '../dummy-table/UploadModal';
import { downloadCsv } from '@/utils/downloadCsv';
import {
  RECYCLED_CONTENT_COLS, TRANSPORT_COLS, WASTE_COLS, DECARB_COLS, EV_UPTAKE_COLS,
  VEPM_COLS, FREIGHT_RAIL_COLS, MAINTENANCE_REPLACEMENT_COLS, OPERATIONAL_EQUIPMENT_COLS,
  DENSITIES_COLS, UNIT_CONVERSIONS_COLS, FUGITIVES_COLS, ENERGY_DENSITY_COLS,
  VEHICLE_MASSES_COLS, INTERRUPTED_VEHICLES_COLS, UNINTERRUPTED_VEHICLES_COLS,
  VEHICLE_ENERGY_COLS, CARBON_VALUES_COLS, WASTAGE_RATES_COLS, CONTENT_RECYCLED_COLS,
  GRADE1_COLS, GRADE2_COLS, GRADE34_COLS, CONCRETE_MIX_DESIGN_COLS, DIRECT_SUBSTITUTION_COLS,
  ELECTRICITY_RECYCLING_ASSUMPTION_COLS, RENEWABLE_ENERGY_COLS,
  eraRowsForCsvExport,
  parseEraUploadRow,
  isEraCalculatedMetric,
  parseContentRecycledUploadRow,
  parseContentRecycledPctUpload,
} from './csvColumns';
import ConcreteMixDesignTable from './components/ConcreteMixDesignTable';
import DirectSubstitutionsTable from './components/DirectSubstitutionsTable';
import ElectricityRecyclingAssumptionsTable from './components/ElectricityRecyclingAssumptionsTable';

const DECARB_FT_OPTS = [
  { code: 'scope2_location', label: 'Scope 2 Location',  hasRegion: true  },
  { code: 'scope2_market',   label: 'Scope 2 Market',    hasRegion: false },
  { code: 'scope3_location', label: 'Scope 3 Location',  hasRegion: true  },
  { code: 'scope3_market',   label: 'Scope 3 Market',    hasRegion: false },
  { code: 'renewable_pct',   label: 'Renewable Power Percentage',       hasRegion: false },
] as const;

const TAB_ENDPOINT: Partial<Record<PageTab, string>> = {
  recycled:                   '/api/material-recycled-content',
  content_recycled:           '/api/recycled-content-factors',
  transport:                  '/api/default-transport-distances',
  waste:                      '/api/default-waste-rates',
  decarb:                     '/api/electric-decarb-factors',
  carbon_values:              '/api/carbon-values',
  ev_uptake:                  '/api/ev-uptake-factors',
  vepm:                       '/api/vepm-factors',
  freight_rail:               '/api/freight-rail-factors',
  maintenance_replacement:    '/api/maintenance-replacement-factors',
  operational_equipment:      '/api/operational-equipment',
  densities:                  '/api/densities',
  unit_conversions:           '/api/unit-conversions',
  fugitives:                  '/api/fugitives',
  energy_density_conversions: '/api/energy-density-conversions',
  vehicle_masses:             '/api/vehicle-masses',
  interrupted_vehicles:       '/api/interrupted-vehicles',
  uninterrupted_vehicles:     '/api/uninterrupted-vehicles',
  vehicle_energy:             '/api/vehicle-energy-conversion-rates',
  wastage_rates:              '/api/wastage-rates',
  renewable_energy:           '/api/renewable-energy-classifications',
  concrete_mix_designs:       '/api/concrete-mix-designs',
  direct_substitutions:       '/api/direct-substitutions',
  electricity_recycling_assumptions: '/api/electricity-recycling-assumptions',
};

const SUPERADMIN_ONLY_TABS: PageTab[] = [
  'densities',
  'decarb',
  'unit_conversions',
  'energy_density_conversions',
  'renewable_energy',
  'interrupted_vehicles',
  'uninterrupted_vehicles',
];

const ORG_ONLY_TABS: PageTab[] = [
  'maintenance_replacement',
  'wastage_rates',
  'concrete_mix_designs',
  'carbon_values',
  'operational_equipment',
  'freight_rail',
  'ev_uptake',
  'vehicle_energy',
  'direct_substitutions',
  'electricity_recycling_assumptions',
];

function isScopeAllowedForTab(tab: PageTab, scopeType: string): boolean {
  if (tab === 'audit') return false;
  if (SUPERADMIN_ONLY_TABS.includes(tab)) return scopeType === 'DEFAULT';
  if (ORG_ONLY_TABS.includes(tab)) return scopeType === 'DEFAULT' || scopeType === 'ORG';
  return true;
}

export default function DatasetsPage({ scope = { type: 'DEFAULT' } }: { scope?: DatasetScope }) {
  const today = new Date().toISOString().slice(0, 10);
  const { roles } = useUser();
  // Derive edit rights based on the tier being managed
  const canEditScope =
    scope.type === 'DEFAULT' ? roles.includes('SUPER_ADMIN') :
    scope.type === 'ORG'     ? roles.includes('ORG_ADMIN') :
    /* PROJECT */              (roles.includes('PROJECT_ADMIN') || roles.includes('PROJECT_EDITOR'));
  const canArchiveScope = canEditScope;
  const [revisions, setRevisions]             = useState<DatasetRevision[]>([]);
  const [branchableRevisions, setBranchableRevisions] = useState<DatasetRevision[]>([]);
  const [loadingMeta, setLoadingMeta]     = useState(true);
  const [selectedRevisionId,  setSelectedRevisionId]  = useState('');
  const [selectedGrade,       setSelectedGrade]       = useState('');
  const [baseData,    setBaseData]    = useState<G1Row[] | G2Row[] | G34Row[]>([]);
  const [displayData, setDisplayData] = useState<G1Row[] | G2Row[] | G34Row[]>([]);
  const [activeGrade, setActiveGrade] = useState<string>('');
  const [fetching,       setFetching]       = useState(false);
  const [filterFetching, setFilterFetching] = useState(false);
  const [fetchError, setFetchError] = useState('');
  const [page,     setPage]     = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [g1Filter,   setG1Filter]   = useState<G1Filter>(INIT_G1);
  const [g234Filter, setG234Filter] = useState<G234Filter>(INIT_G234);
  const [activeTab, setActiveTab] = useState<PageTab>('factors');
  const selectedRevision = revisions.find(r => r.id === selectedRevisionId);
  const ownsSelectedRevision = !!selectedRevision && (
    selectedRevision.scope_type === scope.type &&
    (scope.type === 'DEFAULT' || selectedRevision.scope_id === (scope.type === 'ORG' ? scope.orgId : scope.projectId))
  );
  const canEdit = canEditScope && ownsSelectedRevision && selectedRevision?.status === 'draft';
  const canArchive = canArchiveScope && ownsSelectedRevision;
  const canEditTab = canEdit && isScopeAllowedForTab(activeTab, scope.type);
  const [activeGroup, setActiveGroup] = useState<string>(TAB_GROUPS[0].label);
  const [rcAsOfDate, setRcAsOfDate] = useState(today);
  const [rcRows, setRcRows]         = useState<RecycledContentRow[]>([]);
  const [rcFetching, setRcFetching] = useState(false);
  const [rcError, setRcError]       = useState('');
  const [rcFilter, setRcFilter]     = useState<RcFilter>(INIT_RC);
  const [rcPage, setRcPage]         = useState(1);
  const [trAsOfDate, setTrAsOfDate] = useState(today);
  const [trRows, setTrRows]         = useState<TransportRow[]>([]);
  const [trFetching, setTrFetching] = useState(false);
  const [trError, setTrError]       = useState('');
  const [trFilter, setTrFilter]     = useState<TrFilter>(INIT_TR);
  const [trPage, setTrPage]         = useState(1);
  const [wrAsOfDate, setWrAsOfDate] = useState(today);
  const [wrRows, setWrRows]         = useState<WasteRateRow[]>([]);
  const [wrFetching, setWrFetching] = useState(false);
  const [wrError, setWrError]       = useState('');
  const [matOpts, setMatOpts] = useState<NamedOption[]>([]);
  const [jurOpts, setJurOpts] = useState<NamedOption[]>([]);
  const [wtOpts,  setWtOpts]  = useState<NamedOption[]>([]);
  const [ecOpts,  setEcOpts]  = useState<NamedOption[]>([]);
  const [unitOpts,       setUnitOpts]       = useState<NamedOption[]>([]);
  const [metricTypeOpts, setMetricTypeOpts] = useState<NamedOption[]>([]);
  const [mastertypeOpts,    setMastertypeOpts]    = useState<NamedOption[]>([]);
  const [allTypecastsRaw,   setAllTypecastsRaw]   = useState<Array<{id: string; name: string; mastertype_id: string}>>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<Record<string, string>>({});
  const [addingTab, setAddingTab] = useState<PageTab | null>(null);
  const [addDraft,  setAddDraft]  = useState<Record<string, string>>({});
  const [savingOp,  setSavingOp]  = useState(false);
  const [saveError, setSaveError] = useState('');
  const [bgmEditKey,   setBgmEditKey]   = useState<string | null>(null);
  const [bgmEditDraft, setBgmEditDraft] = useState<Record<string, string>>({});
  const [bgmAdding,    setBgmAdding]    = useState(false);
  const [bgmAddDraft,  setBgmAddDraft]  = useState<Record<string, string>>({});
  const [bgmSaving,    setBgmSaving]    = useState(false);
  const [bgmSaveError, setBgmSaveError] = useState('');
  const [bgmRawRows,   setBgmRawRows]   = useState<BgmRow[]>([]);
  const [auditRows, setAuditRows]           = useState<AuditLogRow[]>([]);
  const [auditFetching, setAuditFetching]   = useState(false);
  const [auditError, setAuditError]         = useState('');
  const [decarbRows, setDecarbRows]         = useState<DecarbRow[]>([]);
  const [decarbFetching, setDecarbFetching] = useState(false);
  const [decarbError, setDecarbError]       = useState('');
  const [decarbFilter, setDecarbFilter]         = useState<DecarbFilter>(INIT_DECARB);
  const [decarbActiveFt,    setDecarbActiveFt]  = useState('scope2_location');
  const [decarbYearFrom,    setDecarbYearFrom]  = useState(2026);
  const [decarbYearTo,      setDecarbYearTo]    = useState(2045);
  const [decarbEditCellId,  setDecarbEditCellId] = useState<string | null>(null);
  const [decarbCellDraft,   setDecarbCellDraft]  = useState('');
  const [decarbCellSaving,  setDecarbCellSaving] = useState(false);
  const [decarbCellError,   setDecarbCellError]  = useState('');
  const [decarbAdding,      setDecarbAdding]     = useState(false);
  const [decarbSeriesDraft, setDecarbSeriesDraft] = useState({ jurisdictionId: '', regionId: '' });
  const [decarbAddSaving,   setDecarbAddSaving]  = useState(false);
  const [decarbAddError,    setDecarbAddError]   = useState('');
  const [evUptakeRows, setEvUptakeRows]               = useState<EvUptakeRow[]>([]);
  const [evUptakeFetching, setEvUptakeFetching]       = useState(false);
  const [evUptakeError, setEvUptakeError]             = useState('');
  const [evUptakeFilter, setEvUptakeFilter]           = useState<EvUptakeFilter>(INIT_EV_UPTAKE);
  const [evUptakeYearFrom, setEvUptakeYearFrom]       = useState(2026);
  const [evUptakeYearTo,   setEvUptakeYearTo]         = useState(2045);
  const [evUptakeEditCellId,  setEvUptakeEditCellId]  = useState<string | null>(null);
  const [evUptakeCellDraft,   setEvUptakeCellDraft]   = useState('');
  const [evUptakeCellSaving,  setEvUptakeCellSaving]  = useState(false);
  const [evUptakeCellError,   setEvUptakeCellError]   = useState('');
  const [evUptakeAdding,      setEvUptakeAdding]      = useState(false);
  const [evUptakeSeriesDraft, setEvUptakeSeriesDraft] = useState({ jurisdictionId: '', scenarioCode: '', vehicleCategoryCode: '', energyTypeCode: '' });
  const [evUptakeAddSaving,   setEvUptakeAddSaving]   = useState(false);
  const [evUptakeAddError,    setEvUptakeAddError]    = useState('');
  const [vepmRows, setVepmRows]         = useState<VepmRow[]>([]);
  const [vepmFetching, setVepmFetching] = useState(false);
  const [vepmError, setVepmError]       = useState('');
  const [vepmEditingId,  setVepmEditingId]  = useState<string | null>(null);
  const [vepmEditDraft,  setVepmEditDraft]  = useState<Record<string, string>>({});
  const [vepmSaving,     setVepmSaving]     = useState(false);
  const [vepmSaveError,  setVepmSaveError]  = useState('');
  const [vepmYearFilter, setVepmYearFilter] = useState('');
  const [frRows, setFrRows]         = useState<FreightRailRow[]>([]);
  const [frFetching, setFrFetching] = useState(false);
  const [frError, setFrError]       = useState('');
  const [frEditingId,  setFrEditingId]  = useState<string | null>(null);
  const [frEditDraft,  setFrEditDraft]  = useState<Record<string, string>>({});
  const [frSaving,     setFrSaving]     = useState(false);
  const [frSaveError,  setFrSaveError]  = useState('');
  const [mrRows, setMrRows]         = useState<MaintenanceReplacementRow[]>([]);
  const [mrFetching, setMrFetching] = useState(false);
  const [mrError, setMrError]       = useState('');
  const [mrEditingId,  setMrEditingId]  = useState<string | null>(null);
  const [mrEditDraft,  setMrEditDraft]  = useState<Record<string, string>>({});
  const [mrSaving,     setMrSaving]     = useState(false);
  const [mrSaveError,  setMrSaveError]  = useState('');

  const [wgRows,      setWgRows]      = useState<WastageRateRow[]>([]);
  const [wgFiltered,  setWgFiltered]  = useState<WastageRateRow[]>([]);
  const [wgFetching,  setWgFetching]  = useState(false);
  const [wgError,     setWgError]     = useState('');
  const [wgEditingId, setWgEditingId] = useState<string | null>(null);
  const [wgEditDraft, setWgEditDraft] = useState<Record<string, string>>({});
  const [wgSaving,    setWgSaving]    = useState(false);
  const [wgSaveError, setWgSaveError] = useState('');
  const [wgFilter,    setWgFilter]    = useState<WastageRateFilter>(INIT_WASTAGE_RATES);

  const [recRows,      setRecRows]      = useState<RenewableEnergyRow[]>([]);
  const [recFetching,  setRecFetching]  = useState(false);
  const [recError,     setRecError]     = useState('');
  const [recEditingId, setRecEditingId] = useState<string | null>(null);
  const [recEditDraft, setRecEditDraft] = useState<Record<string, string>>({});
  const [recSaving,    setRecSaving]    = useState(false);
  const [recSaveError, setRecSaveError] = useState('');

  const [crfRows,      setCrfRows]      = useState<ContentRecycledRow[]>([]);
  const [crfFiltered,  setCrfFiltered]  = useState<ContentRecycledRow[]>([]);
  const [crfFetching,  setCrfFetching]  = useState(false);
  const [crfError,     setCrfError]     = useState('');
  const [crfEditCellKey, setCrfEditCellKey] = useState<string | null>(null);
  const [crfCellDraft, setCrfCellDraft] = useState('');
  const [crfSaving,    setCrfSaving]    = useState(false);
  const [crfSaveError, setCrfSaveError] = useState('');
  const [crfAdding,    setCrfAdding]    = useState(false);
  const [crfAddDraft,  setCrfAddDraft]  = useState<Record<string, string>>({});
  const [crfFilter,    setCrfFilter]    = useState<ContentRecycledFilter>(INIT_CONTENT_RECYCLED);

  const [densityData,    setDensityData]    = useState<DensityRow[]>([]);
  const [densityFiltered, setDensityFiltered] = useState<DensityRow[]>([]);
  const [densityFetching, setDensityFetching] = useState(false);
  const [densityError,    setDensityError]    = useState('');
  
  const [densityEditingId, setDensityEditingId] = useState<string | null>(null);
  const [densityEditDraft, setDensityEditDraft] = useState<Record<string, string>>({});
  const [densitySaving,    setDensitySaving]    = useState(false);
  const [densitySaveError, setDensitySaveError] = useState('');
  
  const [densityFilter, setDensityFilter] = useState<DensityFilter>(INIT_DENSITY);
  
  const [ucRows,      setUcRows]      = useState<UnitConversionRow[]>([]);
  const [ucFetching,  setUcFetching]  = useState(false);
  const [ucError,     setUcError]     = useState('');
  
  const [ucEditingId,  setUcEditingId]  = useState<string | null>(null);
  const [ucEditDraft,  setUcEditDraft]  = useState<Record<string, string>>({});
  const [ucSaving,     setUcSaving]     = useState(false);
  const [ucSaveError,  setUcSaveError]  = useState('');

  const [fcRows,      setFcRows]      = useState<FugitiveRow[]>([]);
  const [fcFiltered,  setFcFiltered]  = useState<FugitiveRow[]>([]);
  const [fcFetching,  setFcFetching]  = useState(false);
  const [fcError,     setFcError]     = useState('');
  
  const [fcEditingId,  setFcEditingId]  = useState<string | null>(null);
  const [fcEditDraft,  setFcEditDraft]  = useState<Record<string, string>>({});
  const [fcSaving,     setFcSaving]     = useState(false);
  const [fcSaveError,  setFcSaveError]  = useState('');
  
  const [fcFilter, setFcFilter] = useState<FugitiveFilter>(INIT_FUGITIVE);

  const [edcRows,     setEdcRows]     = useState<EnergyDensityConversionRow[]>([]);
  const [edcFetching, setEdcFetching] = useState(false);
  const [edcError,    setEdcError]    = useState('');
  
  const [edcEditingId,  setEdcEditingId]  = useState<string | null>(null);
  const [edcEditDraft,  setEdcEditDraft]  = useState<Record<string, string>>({});
  const [edcSaving,     setEdcSaving]     = useState(false);
  const [edcSaveError,  setEdcSaveError]  = useState('');

  const [vehicleClassOpts,    setVehicleClassOpts]    = useState<VehicleClassOption[]>([]);
  const [vmRows,      setVmRows]      = useState<VehicleMassRow[]>([]);
  const [vmFetching,  setVmFetching]  = useState(false);
  const [vmError,     setVmError]     = useState('');
  const [vmEditingId, setVmEditingId] = useState<string | null>(null);
  const [vmEditDraft, setVmEditDraft] = useState<Record<string, string>>({});
  const [vmAdding,    setVmAdding]    = useState(false);
  const [vmAddDraft,  setVmAddDraft]  = useState<Record<string, string>>({});
  const [vmSaving,    setVmSaving]    = useState(false);
  const [vmSaveError, setVmSaveError] = useState('');
  const [ivRows,      setIvRows]      = useState<InterruptedVehicleRow[]>([]);
  const [ivFetching,  setIvFetching]  = useState(false);
  const [ivError,     setIvError]     = useState('');
  const [ivEditingId, setIvEditingId] = useState<string | null>(null);
  const [ivEditDraft, setIvEditDraft] = useState<Record<string, string>>({});
  const [ivAdding,    setIvAdding]    = useState(false);
  const [ivAddDraft,  setIvAddDraft]  = useState<Record<string, string>>({});
  const [ivSaving,    setIvSaving]    = useState(false);
  const [ivSaveError, setIvSaveError] = useState('');
  const [uvRows,      setUvRows]      = useState<UninterruptedVehicleRow[]>([]);
  const [uvFetching,  setUvFetching]  = useState(false);
  const [uvError,     setUvError]     = useState('');
  const [uvEditingId, setUvEditingId] = useState<string | null>(null);
  const [uvEditDraft, setUvEditDraft] = useState<Record<string, string>>({});
  const [uvAdding,    setUvAdding]    = useState(false);
  const [uvAddDraft,  setUvAddDraft]  = useState<Record<string, string>>({});
  const [uvSaving,    setUvSaving]    = useState(false);
  const [uvSaveError, setUvSaveError] = useState('');
  const [veRows,      setVeRows]      = useState<VehicleEnergyConversionRow[]>([]);
  const [veFetching,  setVeFetching]  = useState(false);
  const [veError,     setVeError]     = useState('');
  const [veEditingId, setVeEditingId] = useState<string | null>(null);
  const [veEditDraft, setVeEditDraft] = useState<Record<string, string>>({});
  const [veAdding,    setVeAdding]    = useState(false);
  const [veAddDraft,  setVeAddDraft]  = useState<Record<string, string>>({});
  const [veSaving,    setVeSaving]    = useState(false);
  const [veSaveError, setVeSaveError] = useState('');
  const [opEqRows,      setOpEqRows]      = useState<OperationalEquipmentRow[]>([]);
  const [opEqFetching,  setOpEqFetching]  = useState(false);
  const [opEqError,     setOpEqError]     = useState('');
  const [opEqEditingId, setOpEqEditingId] = useState<string | null>(null);
  const [opEqEditDraft, setOpEqEditDraft] = useState<Record<string, string>>({});
  const [opEqSaving,    setOpEqSaving]    = useState(false);
  const [opEqSaveError, setOpEqSaveError] = useState('');
  const [uploadTarget, setUploadTarget]   = useState<PageTab | null>(null);
  const [uploadRunning, setUploadRunning] = useState(false);

  // Business-as-usual Assumptions: Default concrete mix designs
  const [cmAssumptions, setCmAssumptions]     = useState<ConcreteMixAssumption | null>(null);
  const [cmRows,        setCmRows]            = useState<ConcreteMixDesignRow[]>([]);
  const [cmLoaded,      setCmLoaded]          = useState(false);
  const [cmFetching,    setCmFetching]        = useState(false);
  const [cmError,       setCmError]           = useState('');
  const [cmEditCellKey, setCmEditCellKey]     = useState<string | null>(null);
  const [cmCellDraft,   setCmCellDraft]       = useState('');
  const [cmAssumptionField,
         setCmAssumptionField]                 = useState<'bau_scm_content_pct' | 'default_max_fly_ash_pct' | null>(null);
  const [cmAssumptionDraft, setCmAssumptionDraft] = useState('');
  const [cmSaving,      setCmSaving]          = useState(false);
  const [cmSaveError,   setCmSaveError]       = useState('');

  const [directSubRows, setDirectSubRows]         = useState<DirectSubstitutionRow[]>([]);
  const [directSubTotal, setDirectSubTotal]       = useState(0);
  const [directSubFetching, setDirectSubFetching] = useState(false);
  const [directSubError, setDirectSubError]       = useState('');
  const [directSubJurisdictionId, setDirectSubJurisdictionId] = useState('');
  const [directSubPage, setDirectSubPage]         = useState(1);
  const [directSubExporting, setDirectSubExporting] = useState(false);

const [eraRows, setEraRows] = useState<ElectricityRecyclingAssumptionRow[]>([]);
  const [eraTotal, setEraTotal] = useState(0);
  const [eraFetching, setEraFetching] = useState(false);
  const [eraError, setEraError] = useState('');
  const [eraJurisdictionId, setEraJurisdictionId] = useState('');
  const [eraPage, setEraPage] = useState(1);
  const [eraExporting, setEraExporting] = useState(false);
  const [eraEditRowId, setEraEditRowId] = useState<string | null>(null);
  const [eraCellDraft, setEraCellDraft] = useState('');
  const [eraSaving, setEraSaving] = useState(false);
  const [eraSaveError, setEraSaveError] = useState('');


  // Carbon Values
  const [cvRows, setCvRows]                 = useState<CarbonValueRow[]>([]);
  const [cvFetching, setCvFetching]         = useState(false);
  const [cvError, setCvError]               = useState('');
  const [cvFilter, setCvFilter]             = useState<CarbonValueFilter>(INIT_CARBON_VALUES);
  const [cvYearFrom, setCvYearFrom]         = useState(2025);
  const [cvYearTo, setCvYearTo]             = useState(2050);
  const [cvEditCellId, setCvEditCellId]     = useState<string | null>(null);
  const [cvCellDraft, setCvCellDraft]       = useState('');
  const [cvCellSaving, setCvCellSaving]     = useState(false);
  const [cvCellError, setCvCellError]       = useState('');
  const [cvAdding, setCvAdding]             = useState(false);
  const [cvSeriesDraft, setCvSeriesDraft]   = useState({ jurisdictionId: '', rangeCode: '' });
  const [cvAddSaving, setCvAddSaving]       = useState(false);
  const [cvAddError, setCvAddError]         = useState('');
  const [_rangeOpts, setRangeOpts]           = useState<NamedOption[]>([]);

  const activeGradeRef    = useRef(activeGrade);
  const gradeRef          = useRef(selectedGrade);
  const g1FilterRef       = useRef(g1Filter);
  const g234FilterRef     = useRef(g234Filter);
  useEffect(() => { activeGradeRef.current    = activeGrade;        }, [activeGrade]);
  useEffect(() => { gradeRef.current          = selectedGrade;       }, [selectedGrade]);
  useEffect(() => { g1FilterRef.current       = g1Filter;            }, [g1Filter]);
  useEffect(() => { g234FilterRef.current     = g234Filter;          }, [g234Filter]);

  useEffect(() => {
    const revUrl = (() => {
      if (scope.type === 'DEFAULT') return '/api/dataset-revisions?scope_type=DEFAULT&limit=200';
      if (scope.type === 'ORG')     return `/api/dataset-revisions?scope_type=ORG&scope_id=${scope.orgId}&limit=200`;
      return `/api/dataset-revisions?scope_type=PROJECT&scope_id=${scope.projectId}&limit=200`;
    })();

    const branchUrls: string[] = (() => {
      if (scope.type === 'DEFAULT') return [];
      if (scope.type === 'ORG')     return ['/api/dataset-revisions?scope_type=DEFAULT&status=published&limit=200'];
      return [
        `/api/dataset-revisions?scope_type=ORG&scope_id=${scope.orgId}&status=published&limit=200`,
        '/api/dataset-revisions?scope_type=DEFAULT&status=published&limit=200',
        `/api/dataset-revisions?scope_type=PROJECT&scope_id=${scope.projectId}&status=published&limit=200`,
      ];
    })();

    Promise.all([
      http.get<DatasetRevision[]>(revUrl),
      ...branchUrls.map(u => http.get<DatasetRevision[]>(u)),
      http.get<NamedOption[]>('/api/materials?limit=2000'),
      http.get<NamedOption[]>('/api/jurisdictions?limit=500'),
      http.get<NamedOption[]>('/api/waste-treatments?limit=500'),
      http.get<NamedOption[]>('/api/emissions-categories?limit=500'),
      http.get<{ id: string; code: string }[]>('/api/units?limit=500'),
      http.get<{ id: string; code: string; name: string }[]>('/api/metric-types'),
      http.get<{ id: string; code: string; name: string }[]>('/api/benchmark-mastertypes'),
      http.get<{ id: string; code: string; name: string; mastertype_id: string }[]>('/api/benchmark-typecasts'),
    ])
      .then(responses => {
        const [rRes, ...rest] = responses;
        const branchResponses = rest.slice(0, branchUrls.length);
        const [matRes, jurRes, wtRes, ecRes, unitRes, mtRes, bmtRes, tcRes] = rest.slice(branchUrls.length);
        const ownRevisions = (rRes as { data: DatasetRevision[] }).data;
        const inheritedRevisions = (branchResponses as Array<{ data: DatasetRevision[] }>).flatMap(r => r.data);
        setRevisions([...ownRevisions, ...inheritedRevisions]);
        if (scope.type === 'DEFAULT') {
          setBranchableRevisions(ownRevisions.filter(r => r.status === 'published'));
        } else {
          setBranchableRevisions(inheritedRevisions.filter(r => r.status === 'published'));
        }
        setMatOpts((matRes as { data: NamedOption[] }).data);
        setJurOpts((jurRes as { data: NamedOption[] }).data);
        setWtOpts((wtRes as { data: NamedOption[] }).data);
        setEcOpts((ecRes as { data: NamedOption[] }).data);
        setUnitOpts((unitRes as unknown as { data: { id: string; code: string; label: string | null }[] }).data.map(u => ({ id: u.id, name: u.label ?? u.code })));
        setMetricTypeOpts((mtRes as { data: { id: string; code: string; name: string }[] }).data.map(m => ({ id: m.id, name: `${m.code} — ${m.name}` })));
        setMastertypeOpts((bmtRes as { data: { id: string; code: string; name: string }[] }).data.map(m => ({ id: m.id, name: m.name })));
        setAllTypecastsRaw((tcRes as { data: { id: string; code: string; name: string; mastertype_id: string }[] }).data.map(t => ({ id: t.id, name: t.name, mastertype_id: t.mastertype_id })));
        // Initialize range options for carbon values
        setRangeOpts([
          { id: 'low', name: 'Low' },
          { id: 'central', name: 'Central' },
          { id: 'high', name: 'High' },
        ]);
      })
      .catch((err) => console.error('[DatasetsPage] Failed to load reference metadata:', err))
      .finally(() => setLoadingMeta(false));
  }, []);

  const handleRevisionChange = (id: string) => {
    setSelectedRevisionId(id);
    setBaseData([]);
    setDisplayData([]);
    setActiveGrade('');
    setPage(1);
  };

  const handleGradeChange = (g: string) => {
    setSelectedGrade(g);
    setBaseData([]);
    setDisplayData([]);
    setActiveGrade('');
    setPage(1);
  };

  const canFetch = !!(selectedRevisionId && selectedGrade);

  const buildFilterParams = useCallback((
    revisionId: string,
    grade: string,
    g1f: G1Filter,
    g234f: G234Filter,
  ): URLSearchParams => {
    const p = new URLSearchParams();
    p.set('grade_id', grade);
    p.set('limit', '20000');
    p.set('skip', '0');
    p.set('dataset_revision_id', revisionId);

    if (grade === '1') {
      if (g1f.mastertype_id) p.set('mastertype_id', g1f.mastertype_id);
      if (g1f.typecast_id)   p.set('typecast_id', g1f.typecast_id);
      for (const u of g1f.units) p.append('unit_codes', u);
      for (const m of g1f.metrics) {
        const code = LABEL_TO_METRIC_CODE[m];
        if (code) p.append('metric_type_codes', code);
      }
      for (const j of g1f.jurisdictions) p.append('jurisdiction_names', j);
    } else {
      for (const c of g234f.categories)    p.append('emissions_category', c);
      for (const s of g234f.subcategories) p.append('emissions_subcategory', s);
      if (g234f.emissionsSource) p.set('emissions_source', g234f.emissionsSource);
      for (const u of g234f.units) p.append('unit_codes', u);
      for (const j of g234f.jurisdictions) p.append('jurisdiction_names', j);
    }
    return p;
  }, []);

  const pivotRows = (rawRows: BgmRow[], grade: string) => {
    if (grade === '1') return pivotGrade1(rawRows);
    if (grade === '2') return pivotGrade2(rawRows);
    return pivotGrade34(rawRows);
  };

  const fetchData = useCallback(async () => {
    if (!canFetch) return;
    setFetching(true);
    setFetchError('');
    setBaseData([]);
    setDisplayData([]);
    setActiveGrade('');
    setG1Filter(INIT_G1);
    setG234Filter(INIT_G234);
    setPage(1);
    try {
      const p = new URLSearchParams({
        grade_id: selectedGrade,
        limit: '20000',
        skip: '0',
        dataset_revision_id: selectedRevisionId,
      });
      const res = await http.get<BgmRow[]>(`/api/background-grade-metrics?${p.toString()}`);
      const pivoted = pivotRows(res.data, selectedGrade) as G1Row[];
      setBgmRawRows(res.data);
      setBgmEditKey(null); setBgmEditDraft({});
      setBgmAdding(false); setBgmAddDraft({});
      setBaseData(pivoted);
      setDisplayData(pivoted);
      setActiveGrade(selectedGrade);
      setPage(1);
    } catch {
      setFetchError('Failed to load data. Please try again.');
    } finally {      setFetching(false);
    }
  }, [canFetch, selectedGrade, selectedRevisionId]);

  const doFilterFetch = useCallback(async (
    revisionId: string,
    grade: string,
    g1f: G1Filter,
    g234f: G234Filter,
  ) => {
    setFilterFetching(true);
    setPage(1);
    try {
      const p = buildFilterParams(revisionId, grade, g1f, g234f);
      const res = await http.get<BgmRow[]>(`/api/background-grade-metrics?${p.toString()}`);
      setDisplayData(pivotRows(res.data, grade) as G1Row[]);
    } catch {
    } finally {
      setFilterFetching(false);
    }
  }, [buildFilterParams]);

  const isFirstFilterRender = useRef(true);
  useEffect(() => {
    if (isFirstFilterRender.current) { isFirstFilterRender.current = false; return; }
    if (!activeGrade || !selectedRevisionId) return;

    const hasText =
      (activeGrade === '1' && (g1Filter.mastertype_id !== '' || g1Filter.typecast_id !== '')) ||
      (activeGrade !== '1' && g234Filter.emissionsSource !== '');

    const delay = hasText ? 400 : 0;
    const id = setTimeout(() => {
      doFilterFetch(selectedRevisionId, activeGrade, g1Filter, g234Filter);
    }, delay);
    return () => clearTimeout(id);
  }, [g1Filter, g234Filter]);

  const fetchRecycledContent = useCallback(async (resetFilter = true) => {
    if (!selectedRevisionId) return;
    setRcFetching(true); setRcError('');
    if (resetFilter) { setRcFilter(INIT_RC); setRcPage(1); }
    try {
      const p = new URLSearchParams({ limit: '5000', skip: '0' });
      if (rcAsOfDate) p.set('as_of_date', rcAsOfDate);
      if (selectedRevisionId) p.set('dataset_revision_id', selectedRevisionId);
      const res = await http.get<RecycledContentRow[]>(`/api/material-recycled-content?${p}`);
      setRcRows(res.data);
    } catch { setRcError('Failed to load recycled content data.'); }
    finally { setRcFetching(false); }
  }, [rcAsOfDate, selectedRevisionId]);

  const fetchTransport = useCallback(async (resetFilter = true) => {
    if (!selectedRevisionId) return;
    setTrFetching(true); setTrError('');
    if (resetFilter) { setTrFilter(INIT_TR); setTrPage(1); }
    try {
      const p = new URLSearchParams({ limit: '5000', skip: '0' });
      if (trAsOfDate) p.set('as_of_date', trAsOfDate);
      if (selectedRevisionId) p.set('dataset_revision_id', selectedRevisionId);
      const res = await http.get<TransportRow[]>(`/api/default-transport-distances?${p}`);
      setTrRows(res.data);
    } catch { setTrError('Failed to load transport distance data.'); }
    finally { setTrFetching(false); }
  }, [trAsOfDate, selectedRevisionId]);

  const fetchWasteRates = useCallback(async (_resetFilter = true) => {
    if (!selectedRevisionId) return;
    setWrFetching(true); setWrError('');
    try {
      const p = new URLSearchParams({ limit: '5000', skip: '0' });
      if (wrAsOfDate) p.set('as_of_date', wrAsOfDate);
      if (selectedRevisionId) p.set('dataset_revision_id', selectedRevisionId);
      const res = await http.get<WasteRateRow[]>(`/api/default-waste-rates?${p}`);
      setWrRows(res.data);
    } catch { setWrError('Failed to load waste rate data.'); }
    finally { setWrFetching(false); }
  }, [wrAsOfDate, selectedRevisionId]);

  const fetchAuditLogs = useCallback(async (revisionId: string) => {
    if (!revisionId) return;
    setAuditFetching(true); setAuditError('');
    try {
      const p = new URLSearchParams({ entity_type: 'dataset_revision', entity_id: revisionId, limit: '500', skip: '0' });
      const res = await http.get<AuditLogRow[]>(`/api/audit-logs?${p}`);
      setAuditRows(res.data);
    } catch { setAuditError('Failed to load audit logs.'); }
    finally { setAuditFetching(false); }
  }, []);

  useEffect(() => {
    if (activeTab === 'audit' && selectedRevisionId) {
      fetchAuditLogs(selectedRevisionId);
    }
  }, [activeTab, selectedRevisionId]);

  const fetchDecarbFactors = useCallback(async (resetFilter = true) => {
    if (!selectedRevisionId) return;
    setDecarbFetching(true); setDecarbError('');
    if (resetFilter) { setDecarbFilter(INIT_DECARB); }
    try {
      const p = new URLSearchParams({ limit: '10000', skip: '0', dataset_revision_id: selectedRevisionId });
      const res = await http.get<DecarbRow[]>(`/api/electric-decarb-factors?${p}`);
      setDecarbRows(res.data);
    } catch { setDecarbError('Failed to load electricity decarbonisation factors.'); }
    finally { setDecarbFetching(false); }
  }, [selectedRevisionId, scope]);

  const fetchCarbonValues = useCallback(async () => {
    if (!selectedRevisionId) return;
    setCvFetching(true);
    setCvError('');
    try {
      const params = new URLSearchParams({ dataset_revision_id: selectedRevisionId, limit: '10000' });
      const res = await http.get<CarbonValueRow[]>(`/api/carbon-values?${params}`);
      setCvRows(res.data);
    } catch (err) {
      setCvError('Failed to load carbon values');
      console.error(err);
    } finally {
      setCvFetching(false);
    }
  }, [selectedRevisionId]);

  useEffect(() => {
    if (activeTab === 'decarb' && selectedRevisionId) {
      fetchDecarbFactors();
    }
  }, [activeTab, selectedRevisionId]);

  useEffect(() => {
    if (activeTab === 'carbon_values' && selectedRevisionId) {
      fetchCarbonValues();
    }
  }, [activeTab, selectedRevisionId, fetchCarbonValues]);

  const decarbRevisionLocked = !!(selectedRevisionId &&
    revisions.find(r => r.id === selectedRevisionId)?.status !== 'draft');
  const activeFtHasRegion = DECARB_FT_OPTS.find(o => o.code === decarbActiveFt)?.hasRegion ?? false;

  const doSaveDecarbCell = useCallback(async () => {
    if (!decarbEditCellId) return;
    setDecarbCellSaving(true); setDecarbCellError('');
    let value: number | null = null;
    let qualifier: string | null = null;
    const draft = decarbCellDraft.trim();
    if (draft.toUpperCase() === 'D') { qualifier = 'D'; }
    else if (draft === '' || draft === '—') { value = null; }
    else {
      const num = parseFloat(draft);
      if (isNaN(num)) { setDecarbCellError('Invalid value'); setDecarbCellSaving(false); return; }
      const activeRow = decarbRows.find(r => r.id === decarbEditCellId);
      value = activeRow?.unit?.code === '%' ? num / 100 : num;
    }
    try {
      await http.put(`/api/electric-decarb-factors/${decarbEditCellId}`, { value, value_qualifier: qualifier });
      setDecarbRows(prev => prev.map(r =>
        r.id === decarbEditCellId ? { ...r, value, value_qualifier: qualifier } : r,
      ));
      setDecarbEditCellId(null); setDecarbCellDraft('');
    } catch (e: any) {
      setDecarbCellError(extractApiError(e, 'Save failed'));
    } finally { setDecarbCellSaving(false); }
  }, [decarbEditCellId, decarbCellDraft, decarbRows]);

  const doAddDecarbSeries = useCallback(async () => {
    if (!selectedRevisionId || !decarbSeriesDraft.jurisdictionId) {
      setDecarbAddError('Please select a jurisdiction'); return;
    }
    setDecarbAddSaving(true); setDecarbAddError('');
    try {
      const res = await http.post<DecarbRow[]>('/api/electric-decarb-factors/bulk', {
        dataset_revision_id: selectedRevisionId,
        factor_type_code:    decarbActiveFt,
        jurisdiction_id:     decarbSeriesDraft.jurisdictionId,
        region_id:           decarbSeriesDraft.regionId || null,
        year_from:           decarbYearFrom,
        year_to:             decarbYearTo,
      });
      setDecarbRows(prev => {
        const existing = new Set(prev.map(r => r.id));
        const newRows = res.data.filter(r => !existing.has(r.id));
        return [...prev, ...newRows];
      });
      setDecarbAdding(false);
      setDecarbSeriesDraft({ jurisdictionId: '', regionId: '' });
    } catch (e: any) {
      setDecarbAddError(extractApiError(e, 'Save failed'));
    } finally { setDecarbAddSaving(false); }
  }, [selectedRevisionId, decarbActiveFt, decarbSeriesDraft, decarbYearFrom, decarbYearTo]);

  const doSaveCvCell = useCallback(async () => {
    if (!cvEditCellId) return;
    setCvCellSaving(true);
    setCvCellError('');
    let value: number | null = null;
    const draft = cvCellDraft.trim();
    if (draft === '' || draft === '—') { value = null; }
    else {
      const num = parseFloat(draft);
      if (isNaN(num)) { setCvCellError('Invalid value'); setCvCellSaving(false); return; }
      value = num;
    }
    try {
      await http.put(`/api/carbon-values/${cvEditCellId}`, { value, currency: null, source_comments: null });
      setCvRows(prev => prev.map(r =>
        r.id === cvEditCellId ? { ...r, value } : r,
      ));
      setCvEditCellId(null);
      setCvCellDraft('');
    } catch (e: any) {
      setCvCellError(extractApiError(e, 'Save failed'));
    } finally { setCvCellSaving(false); }
  }, [cvEditCellId, cvCellDraft]);

  const doAddCvSeries = useCallback(async () => {
    if (!selectedRevisionId || !cvSeriesDraft.jurisdictionId || !cvSeriesDraft.rangeCode) {
      setCvAddError('Please select a jurisdiction and range'); return;
    }
    setCvAddSaving(true);
    setCvAddError('');
    try {
      await http.post('/api/carbon-values/bulk', {
        dataset_revision_id: selectedRevisionId,
        jurisdiction_id: cvSeriesDraft.jurisdictionId,
        range_code: cvSeriesDraft.rangeCode,
        year_from: cvYearFrom,
        year_to: cvYearTo,
      });
      setCvAdding(false);
      setCvSeriesDraft({ jurisdictionId: '', rangeCode: '' });
      // Reload the full dataset to ensure consistency
      await fetchCarbonValues();
    } catch (e: any) {
      setCvAddError(extractApiError(e, 'Save failed'));
    } finally { setCvAddSaving(false); }
  }, [selectedRevisionId, cvSeriesDraft, cvYearFrom, cvYearTo, fetchCarbonValues]);

  const fetchEvUptakeFactors = useCallback(async (resetFilter = true) => {
    if (!selectedRevisionId) return;
    setEvUptakeFetching(true); setEvUptakeError('');
    if (resetFilter) { setEvUptakeFilter(INIT_EV_UPTAKE); }
    try {
      const p = new URLSearchParams({ limit: '100000', skip: '0', dataset_revision_id: selectedRevisionId });
      const res = await http.get<EvUptakeRow[]>(`/api/ev-uptake-factors?${p}`);
      setEvUptakeRows(res.data);
    } catch { setEvUptakeError('Failed to load EV uptake factors.'); }
    finally { setEvUptakeFetching(false); }
  }, [selectedRevisionId]);

  useEffect(() => {
    if (activeTab === 'ev_uptake' && selectedRevisionId) {
      fetchEvUptakeFactors();
    }
  }, [activeTab, selectedRevisionId]);

  const fetchVepmFactors = useCallback(async () => {
    if (!selectedRevisionId) return;
    setVepmFetching(true); setVepmError('');
    try {
      const p = new URLSearchParams({ limit: '10000', skip: '0', dataset_revision_id: selectedRevisionId });
      const res = await http.get<VepmRow[]>(`/api/vepm-factors?${p}`);
      setVepmRows(res.data);
    } catch { setVepmError('Failed to load VEPM factors.'); }
    finally { setVepmFetching(false); }
  }, [selectedRevisionId]);

  useEffect(() => {
    if (activeTab === 'vepm' && selectedRevisionId) {
      fetchVepmFactors();
    }
  }, [activeTab, selectedRevisionId]);

  const fetchFreightRailFactors = useCallback(async () => {
    if (!selectedRevisionId) return;
    setFrFetching(true); setFrError('');
    try {
      const p = new URLSearchParams({ limit: '500', skip: '0', dataset_revision_id: selectedRevisionId });
      const res = await http.get<FreightRailRow[]>(`/api/freight-rail-factors?${p}`);
      setFrRows(res.data);
    } catch { setFrError('Failed to load freight rail factors.'); }
    finally { setFrFetching(false); }
  }, [selectedRevisionId]);

  useEffect(() => {
    if (activeTab === 'freight_rail' && selectedRevisionId) {
      fetchFreightRailFactors();
    }
  }, [activeTab, selectedRevisionId]);

  const fetchMaintenanceReplacementFactors = useCallback(async () => {
    if (!selectedRevisionId) return;
    setMrFetching(true); setMrError('');
    try {
      const p = new URLSearchParams({ limit: '500', skip: '0', dataset_revision_id: selectedRevisionId });
      const res = await http.get<MaintenanceReplacementRow[]>(`/api/maintenance-replacement-factors?${p}`);
      setMrRows(res.data);
    } catch { setMrError('Failed to load maintenance & replacement factors.'); }
    finally { setMrFetching(false); }
  }, [selectedRevisionId]);

  useEffect(() => {
    if (activeTab === 'maintenance_replacement' && selectedRevisionId) {
      fetchMaintenanceReplacementFactors();
    }
  }, [activeTab, selectedRevisionId]);

  const evUptakeRevisionLocked = !!(selectedRevisionId &&
    revisions.find(r => r.id === selectedRevisionId)?.status !== 'draft');

  const doSaveEvUptakeCell = useCallback(async () => {
    if (!evUptakeEditCellId) return;
    setEvUptakeCellSaving(true); setEvUptakeCellError('');
    const draft = evUptakeCellDraft.trim();
    let uptake_pct: number | null = null;
    if (draft !== '' && draft !== '—') {
      const num = parseFloat(draft);
      if (isNaN(num)) { setEvUptakeCellError('Invalid value'); setEvUptakeCellSaving(false); return; }
      uptake_pct = num / 100;
    }
    try {
      await http.put(`/api/ev-uptake-factors/${evUptakeEditCellId}`, { uptake_pct });
      setEvUptakeRows(prev => prev.map(r =>
        r.id === evUptakeEditCellId ? { ...r, uptake_pct } : r,
      ));
      setEvUptakeEditCellId(null); setEvUptakeCellDraft('');
    } catch (e: any) {
      setEvUptakeCellError(extractApiError(e, 'Save failed'));
    } finally { setEvUptakeCellSaving(false); }
  }, [evUptakeEditCellId, evUptakeCellDraft]);

  const doAddEvUptakeSeries = useCallback(async () => {
    if (!selectedRevisionId || !evUptakeSeriesDraft.jurisdictionId ||
        !evUptakeSeriesDraft.scenarioCode || !evUptakeSeriesDraft.vehicleCategoryCode ||
        !evUptakeSeriesDraft.energyTypeCode) {
      setEvUptakeAddError('Please fill in all fields'); return;
    }
    setEvUptakeAddSaving(true); setEvUptakeAddError('');
    try {
      const res = await http.post<EvUptakeRow[]>('/api/ev-uptake-factors/bulk', {
        dataset_revision_id:   selectedRevisionId,
        jurisdiction_id:       evUptakeSeriesDraft.jurisdictionId,
        scenario_code:         evUptakeSeriesDraft.scenarioCode,
        vehicle_category_code: evUptakeSeriesDraft.vehicleCategoryCode,
        energy_type_code:      evUptakeSeriesDraft.energyTypeCode,
        year_from:             evUptakeYearFrom,
        year_to:               evUptakeYearTo,
      });
      setEvUptakeRows(prev => {
        const existing = new Set(prev.map(r => r.id));
        const newRows = res.data.filter(r => !existing.has(r.id));
        return [...prev, ...newRows];
      });
      setEvUptakeAdding(false);
      setEvUptakeSeriesDraft({ jurisdictionId: '', scenarioCode: '', vehicleCategoryCode: '', energyTypeCode: '' });
    } catch (e: any) {
      setEvUptakeAddError(extractApiError(e, 'Save failed'));
    } finally { setEvUptakeAddSaving(false); }
  }, [selectedRevisionId, evUptakeSeriesDraft, evUptakeYearFrom, evUptakeYearTo]);

  const doSaveVepmRow = useCallback(async () => {
    if (!vepmEditingId) return;
    setVepmSaving(true); setVepmSaveError('');
    const toNum = (v: string) => v.trim() === '' ? null : parseFloat(v);
    const payload = {
      fleet_average_co2e_g_km: toNum(vepmEditDraft.fleet_average_co2e_g_km ?? ''),
      light_vehicle_co2e_g_km: toNum(vepmEditDraft.light_vehicle_co2e_g_km ?? ''),
      heavy_vehicle_co2e_g_km: toNum(vepmEditDraft.heavy_vehicle_co2e_g_km ?? ''),
      bus_co2e_g_km:           toNum(vepmEditDraft.bus_co2e_g_km ?? ''),
    };
    try {
      await http.put(`/api/vepm-factors/${vepmEditingId}`, payload);
      setVepmRows(prev => prev.map(r => r.id === vepmEditingId ? { ...r, ...payload } : r));
      setVepmEditingId(null); setVepmEditDraft({});
    } catch (e: any) {
      setVepmSaveError(extractApiError(e, 'Save failed'));
    } finally { setVepmSaving(false); }
  }, [vepmEditingId, vepmEditDraft]);

  const doSaveFrRow = useCallback(async () => {
    if (!frEditingId) return;
    setFrSaving(true); setFrSaveError('');
    const rawFuel = frEditDraft.fuel_consumption?.trim() ?? '';
    const fuelVal = rawFuel === '' ? null : parseFloat(rawFuel);
    if (rawFuel !== '' && isNaN(fuelVal as number)) {
      setFrSaveError('Invalid fuel consumption value'); setFrSaving(false); return;
    }
    const payload = {
      fuel_consumption_l_per_000_gtk: fuelVal,
      source_note: frEditDraft.source_note?.trim() || null,
    };
    try {
      await http.put(`/api/freight-rail-factors/${frEditingId}`, payload);
      setFrRows(prev => prev.map(r => r.id === frEditingId ? { ...r, ...payload } : r));
      setFrEditingId(null); setFrEditDraft({});
    } catch (e: any) {
      setFrSaveError(extractApiError(e, 'Save failed'));
    } finally { setFrSaving(false); }
  }, [frEditingId, frEditDraft]);

  const doSaveMrRow = useCallback(async () => {
    if (!mrEditingId) return;
    setMrSaving(true); setMrSaveError('');
    const rawIntensity = mrEditDraft.emissions_intensity?.trim() ?? '';
    const intensityVal = rawIntensity === '' ? null : parseFloat(rawIntensity);
    if (rawIntensity !== '' && isNaN(intensityVal as number)) {
      setMrSaveError('Invalid emissions intensity value'); setMrSaving(false); return;
    }
    const rawFreq = mrEditDraft.default_frequency?.trim() ?? '';
    const freqVal = rawFreq === '' ? null : parseInt(rawFreq, 10);
    if (rawFreq !== '' && isNaN(freqVal as number)) {
      setMrSaveError('Invalid frequency value'); setMrSaving(false); return;
    }
    const payload = {
      emissions_intensity_tco2e: intensityVal,
      default_frequency_years: freqVal,
      source_note: mrEditDraft.source_note?.trim() || null,
    };
    try {
      await http.put(`/api/maintenance-replacement-factors/${mrEditingId}`, payload);
      setMrRows(prev => prev.map(r => r.id === mrEditingId ? { ...r, ...payload } : r));
      setMrEditingId(null); setMrEditDraft({});
    } catch (e: any) {
      setMrSaveError(extractApiError(e, 'Save failed'));
    } finally { setMrSaving(false); }
  }, [mrEditingId, mrEditDraft]);

  const doSaveUcRow = useCallback(async () => {
    if (!ucEditingId) return;
    setUcSaving(true);
    setUcSaveError('');
    const rawFactor = ucEditDraft.factor?.trim() ?? '';
    const factorVal = rawFactor === '' ? null : parseFloat(rawFactor);
    if (rawFactor !== '' && isNaN(factorVal as number)) {
      setUcSaveError('Invalid factor value');
      setUcSaving(false);
      return;
    }
    const payload = { factor: factorVal };
    try {
      await http.patch(`/api/unit-conversions/${ucEditingId}`, payload);
      setUcRows(prev => prev.map(r => r.id === ucEditingId ? { ...r, factor: factorVal?.toString() ?? '' } : r));
      setUcEditingId(null);
      setUcEditDraft({});
    } catch (e: any) {
      setUcSaveError(extractApiError(e, 'Save failed'));
    } finally {
      setUcSaving(false);
    }
  }, [ucEditingId, ucEditDraft]);

  const doSaveFugitiveRow = useCallback(async () => {
    if (!fcEditingId) return;
    setFcSaving(true);
    setFcSaveError('');
    try {
      const rawRate = fcEditDraft.default_annual_leakage_rate?.trim() ?? '';
      const rateVal = rawRate === '' ? null : parseFloat(rawRate);
      if (rawRate !== '' && isNaN(rateVal as number)) {
        setFcSaveError('Invalid leakage rate value');
        setFcSaving(false);
        return;
      }

      const payload = {
        equipment_type: fcEditDraft.equipment_type || '',
        default_annual_leakage_rate: rateVal,
        source_comments: fcEditDraft.source_comments || '',
      };
      await http.patch(`/api/fugitives/${fcEditingId}`, payload);
      setFcRows(prev => prev.map(r =>
        r.id === fcEditingId ? { ...r, equipment_type: payload.equipment_type, default_annual_leakage_rate: payload.default_annual_leakage_rate, source_comments: payload.source_comments } : r
      ));
      setFcFiltered(prev => prev.map(r =>
        r.id === fcEditingId ? { ...r, equipment_type: payload.equipment_type, default_annual_leakage_rate: payload.default_annual_leakage_rate, source_comments: payload.source_comments } : r
      ));
      setFcEditingId(null);
      setFcEditDraft({});
    } catch (err: any) {
      setFcSaveError(extractApiError(err, 'Failed to save'));
    } finally {
      setFcSaving(false);
    }
  }, [fcEditingId, fcEditDraft]);

  const doSaveWastageRateRow = useCallback(async () => {
    if (!wgEditingId) return;
    setWgSaving(true);
    setWgSaveError('');
    try {
      const wastageVal = wgEditDraft.construction_wastage_rate?.trim() ?? '';
      const recyclingVal = wgEditDraft.recycling_rate?.trim() ?? '';
      const landfillVal = wgEditDraft.landfill_rate?.trim() ?? '';

      const wastageNum = wastageVal === '' ? null : parseFloat(wastageVal);
      const recyclingNum = recyclingVal === '' ? null : parseFloat(recyclingVal);
      const landfillNum = landfillVal === '' ? null : parseFloat(landfillVal);

      if ((wastageVal !== '' && isNaN(wastageNum as number)) || (recyclingVal !== '' && isNaN(recyclingNum as number)) || (landfillVal !== '' && isNaN(landfillNum as number))) {
        setWgSaveError('Invalid rate values');
        setWgSaving(false);
        return;
      }

      const payload = {
        construction_wastage_rate: wastageNum,
        recycling_rate: recyclingNum,
        landfill_rate: landfillNum,
        source: wgEditDraft.source || '',
      };
      await http.patch(`/api/wastage-rates/${wgEditingId}`, payload);
      setWgRows(prev => prev.map(r =>
        r.id === wgEditingId ? { ...r, construction_wastage_rate: payload.construction_wastage_rate, recycling_rate: payload.recycling_rate, landfill_rate: payload.landfill_rate, source: payload.source } : r
      ));
      setWgFiltered(prev => prev.map(r =>
        r.id === wgEditingId ? { ...r, construction_wastage_rate: payload.construction_wastage_rate, recycling_rate: payload.recycling_rate, landfill_rate: payload.landfill_rate, source: payload.source } : r
      ));
      setWgEditingId(null);
      setWgEditDraft({});
    } catch (err: any) {
      setWgSaveError(extractApiError(err, 'Failed to save'));
    } finally {
      setWgSaving(false);
    }
  }, [wgEditingId, wgEditDraft]);

const parseContentRecycledPct = (uiVal: string): number | null | undefined => {
    const trimmed = uiVal.trim();
    if (trimmed === '') return null;
    const n = parseFloat(trimmed);
    if (isNaN(n)) return undefined;
    return n / 100;
  };

  const doSaveContentRecycledCell = useCallback(async () => {
    if (!crfEditCellKey) return;
    const sep = crfEditCellKey.indexOf('::');
    if (sep < 0) return;
    const rowId = crfEditCellKey.slice(0, sep);
    const field = crfEditCellKey.slice(sep + 2) as ContentRecycledEditableField;

    setCrfSaving(true);
    setCrfSaveError('');
    try {
      let payload: Record<string, string | null> = {};
      if (field === 'notes') {
        payload = { notes: crfCellDraft.trim() || null };
      } else {
        const num = parseContentRecycledPct(crfCellDraft);
        if (num === undefined) {
          setCrfSaveError('Invalid percentage value');
          setCrfSaving(false);
          return;
        }
        payload = { [field]: num != null ? String(num) : null };
      }

      await http.patch(`/api/recycled-content-factors/${rowId}`, payload);
      setCrfRows(prev =>
        prev.map(r => {
          if (r.id !== rowId) return r;
          if (field === 'notes') return { ...r, notes: payload.notes as string | null };
          return { ...r, [field]: payload[field] as string | null };
        }),
      );
      setCrfEditCellKey(null);
      setCrfCellDraft('');
    } catch (err: any) {
      setCrfSaveError(extractApiError(err, 'Failed to save'));
    } finally {
      setCrfSaving(false);
    }
  }, [crfEditCellKey, crfCellDraft]);

  const doSaveEnergyDensityConversionRow = useCallback(async () => {
    if (!edcEditingId) return;
    setEdcSaving(true);
    setEdcSaveError('');
    try {
      const rawDensity = edcEditDraft.energy_density?.trim() ?? '';
      const densityVal = rawDensity === '' ? null : parseFloat(rawDensity);
      if (rawDensity !== '' && isNaN(densityVal as number)) {
        setEdcSaveError('Invalid energy density value');
        setEdcSaving(false);
        return;
      }

      const payload = {
        category: edcEditDraft.category || '',
        name: edcEditDraft.name || '',
        energy_density: densityVal,
        source_comments: edcEditDraft.source_comments || '',
      };
      await http.patch(`/api/energy-density-conversions/${edcEditingId}`, payload);
      setEdcRows(prev => prev.map(r =>
        r.id === edcEditingId ? { ...r, category: payload.category, name: payload.name, energy_density: payload.energy_density, source_comments: payload.source_comments } : r
      ));
      setEdcEditingId(null);
      setEdcEditDraft({});
    } catch (err: any) {
      setEdcSaveError(extractApiError(err, 'Failed to save'));
    } finally {
      setEdcSaving(false);
    }
  }, [edcEditingId, edcEditDraft]);

    
  const fetchDensities = useCallback(async () => {
    if (!selectedRevisionId) return;
    setDensityFetching(true);
    setDensityError('');
    try {
      const params = new URLSearchParams({ dataset_revision_id: selectedRevisionId, limit: '10000' });
      const res = await http.get(`/api/densities?${params}`);
      console.log(res.data);
      setDensityData(res.data || []);
      setDensityFiltered(res.data || []);
    } catch (err: any) {
      setDensityError(extractApiError(err, 'Failed to load densities'));
    } finally {
      setDensityFetching(false);
    }
  }, [selectedRevisionId]);

  const fetchUnitConversions = useCallback(async () => {
    if (!selectedRevisionId) return;
    setUcFetching(true);
    setUcError('');
    try {
      const params = new URLSearchParams({
        dataset_revision_id: selectedRevisionId,
        limit: '10000',
      });
      const res = await http.get(`/api/unit-conversions?${params}`);
      setUcRows(res.data || []);
    } catch (err: any) {
      setUcError(extractApiError(err, 'Failed to load unit conversions'));
    } finally {
      setUcFetching(false);
    }
  }, [selectedRevisionId]);

  const fetchFugitives = useCallback(async () => {
    if (!selectedRevisionId) return;
    setFcFetching(true);
    setFcError('');
    try {
      const params = new URLSearchParams({ dataset_revision_id: selectedRevisionId, limit: '10000' });
      const res = await http.get(`/api/fugitives?${params}`);
      setFcRows(res.data || []);
      setFcFiltered(res.data || []);
    } catch (err: any) {
      setFcError(extractApiError(err, 'Failed to load fugitives'));
    } finally {
      setFcFetching(false);
    }
  }, [selectedRevisionId]);

  const fetchEnergyDensityConversions = useCallback(async () => {
    setEdcFetching(true);
    setEdcError('');
    try {
      const params = new URLSearchParams({ dataset_revision_id: selectedRevisionId, limit: '10000' });
      const res = await http.get(`/api/energy-density-conversions?${params}`);
      setEdcRows(res.data || []);
    } catch (err: any) {
      setEdcError(extractApiError(err, 'Failed to load energy density conversions'));
    } finally {
      setEdcFetching(false);
    }
  }, [selectedRevisionId]);

  const fetchWastageRates = useCallback(async () => {
    if (!selectedRevisionId) return;
    setWgFetching(true);
    setWgError('');
    try {
      const params = new URLSearchParams({ dataset_revision_id: selectedRevisionId, limit: '10000' });
      const res = await http.get(`/api/wastage-rates?${params}`);
      setWgRows(res.data || []);
      setWgFiltered(res.data || []);
    } catch (err: any) {
      setWgError(extractApiError(err, 'Failed to load wastage rates'));
    } finally {
      setWgFetching(false);
    }
  }, [selectedRevisionId]);

  const fetchRenewableEnergy = useCallback(async () => {
    if (!selectedRevisionId) return;
    setRecFetching(true);
    setRecError('');
    try {
      const params = new URLSearchParams({ dataset_revision_id: selectedRevisionId, limit: '1000' });
      const res = await http.get<RenewableEnergyRow[]>(`/api/renewable-energy-classifications?${params}`);
      setRecRows(res.data || []);
    } catch (err: any) {
      setRecError(extractApiError(err, 'Failed to load renewable energy classifications'));
    } finally {
      setRecFetching(false);
    }
  }, [selectedRevisionId]);

const enrichContentRecycledRows = useCallback((rows: ContentRecycledRow[]): ContentRecycledRow[] => {
    return rows
      .map(r => ({
        ...r,
        jurisdiction_name: jurOpts.find(j => j.id === r.jurisdiction_id)?.name ?? '',
        category_name: ecOpts.find(c => c.id === r.emissions_sub_category_id)?.name ?? '',
      }))
      .sort((a, b) => {
        const ca = (a.category_name ?? '').localeCompare(b.category_name ?? '');
        if (ca !== 0) return ca;
        return (a.emissions_source ?? '').localeCompare(b.emissions_source ?? '');
      });
  }, [jurOpts, ecOpts]);

  const fetchContentRecycled = useCallback(async () => {
    if (!selectedRevisionId) return;
    setCrfFetching(true);
    setCrfError('');
    try {
      const params = new URLSearchParams({ dataset_revision_id: selectedRevisionId, limit: '10000' });
      const res = await http.get<ContentRecycledRow[]>(`/api/recycled-content-factors?${params}`);
      const enriched = enrichContentRecycledRows(res.data || []);
      setCrfRows(enriched);
      const allJurs = Array.from(new Set(enriched.map(r => r.jurisdiction_name).filter(Boolean))) as string[];
      setCrfFilter(prev => {
        if (prev.jurisdictions.length > 0) return prev;
        return { jurisdictions: allJurs };
      });
    } catch (err: any) {
      setCrfError(extractApiError(err, 'Failed to load content recycled data'));
    } finally {
      setCrfFetching(false);
    }
  }, [selectedRevisionId, enrichContentRecycledRows]);

  const doAddContentRecycled = useCallback(async () => {
    if (!selectedRevisionId) return;
    setCrfSaving(true);
    setCrfSaveError('');
    try {
      const source = crfAddDraft.emissions_source?.trim();
      if (!source) {
        setCrfSaveError('Emission source is required');
        setCrfSaving(false);
        return;
      }
      let jurisdictionId = crfAddDraft.jurisdiction_id?.trim() || '';
      if (!jurisdictionId && crfFilter.jurisdictions.length === 1) {
        jurisdictionId = jurOpts.find(j => j.name === crfFilter.jurisdictions[0])?.id ?? '';
      }
      if (!jurisdictionId) {
        setCrfSaveError('Jurisdiction is required');
        setCrfSaving(false);
        return;
      }
      const recycledVal = crfAddDraft.recycled_content_pct?.trim() ?? '';
      const reusedVal = crfAddDraft.reused_content_pct?.trim() ?? '';
      const recycledNum = parseContentRecycledPct(recycledVal);
      const reusedNum = parseContentRecycledPct(reusedVal);
      if (recycledNum === undefined || reusedNum === undefined) {
        setCrfSaveError('Invalid percentage values');
        setCrfSaving(false);
        return;
      }
      const payload = {
        dataset_revision_id: selectedRevisionId,
        jurisdiction_id: jurisdictionId,
        emissions_sub_category_id: crfAddDraft.emissions_sub_category_id?.trim() || null,
        emissions_source: source,
        recycled_content_pct: recycledNum,
        reused_content_pct: reusedNum,
        notes: crfAddDraft.notes?.trim() || null,
      };
      await http.post('/api/recycled-content-factors', payload);
      setCrfAdding(false);
      setCrfAddDraft({});
      await fetchContentRecycled();
    } catch (err: any) {
      setCrfSaveError(extractApiError(err, 'Failed to add row'));
    } finally {
      setCrfSaving(false);
    }
  }, [selectedRevisionId, crfAddDraft, crfFilter.jurisdictions, jurOpts, fetchContentRecycled]);

    useEffect(() => {
    if (activeTab === 'densities') {
      fetchDensities();
    } else if (activeTab === 'unit_conversions') {
      fetchUnitConversions();
    } else if (activeTab === 'fugitives') {
      fetchFugitives();
    } else if (activeTab === 'energy_density_conversions') {
      fetchEnergyDensityConversions();
    } else if (activeTab === 'wastage_rates') {
      fetchWastageRates();
      } else if (activeTab === 'content_recycled') {
      fetchContentRecycled();
    } else if (activeTab === 'renewable_energy') {
      fetchRenewableEnergy();
    }
  }, [activeTab, selectedRevisionId, fetchDensities, fetchUnitConversions, fetchFugitives, fetchEnergyDensityConversions, fetchWastageRates, fetchContentRecycled, fetchRenewableEnergy]);

  const fetchVehicleClasses = useCallback(async () => {
    try {
      const res = await http.get<VehicleClassOption[]>('/api/vehicle-classes');
      setVehicleClassOpts(res.data || []);
    } catch (e) {
      console.warn('[DatasetsPage] fetchVehicleClasses failed:', e);
    }
  }, []);

  const fetchVehicleMasses = useCallback(async () => {
    setVmFetching(true); setVmError('');
    try {
      const res = await http.get<VehicleMassRow[]>('/api/vehicle-masses', { params: { dataset_revision_id: selectedRevisionId } });
      setVmRows(res.data || []);
    } catch (e: any) {
      setVmError(extractApiError(e, 'Failed to load vehicle masses'));
    } finally { setVmFetching(false); }
  }, [selectedRevisionId]);

  const fetchInterruptedVehicles = useCallback(async () => {
    setIvFetching(true); setIvError('');
    try {
      const res = await http.get<InterruptedVehicleRow[]>('/api/interrupted-vehicles', { params: { dataset_revision_id: selectedRevisionId } });
      setIvRows(res.data || []);
    } catch (e: any) {
      setIvError(extractApiError(e, 'Failed to load fuel use variables - stop-start'));
    } finally { setIvFetching(false); }
  }, [selectedRevisionId]);

  const fetchUninterruptedVehicles = useCallback(async () => {
    setUvFetching(true); setUvError('');
    try {
      const res = await http.get<UninterruptedVehicleRow[]>('/api/uninterrupted-vehicles', { params: { dataset_revision_id: selectedRevisionId } });
      setUvRows(res.data || []);
    } catch (e: any) {
      setUvError(extractApiError(e, 'Failed to load fuel use variables - free flow'));
    } finally { setUvFetching(false); }
  }, [selectedRevisionId]);

  const fetchVehicleEnergy = useCallback(async () => {
    setVeFetching(true); setVeError('');
    try {
      const res = await http.get<VehicleEnergyConversionRow[]>('/api/vehicle-energy-conversion-rates', { params: { dataset_revision_id: selectedRevisionId } });
      setVeRows(res.data || []);
    } catch (e: any) {
      setVeError(extractApiError(e, 'Failed to load vehicle energy rates'));
    } finally { setVeFetching(false); }
  }, [selectedRevisionId]);

  useEffect(() => {
    const vehicleTabs: PageTab[] = ['vehicle_masses', 'interrupted_vehicles', 'uninterrupted_vehicles', 'vehicle_energy'];
    if (!selectedRevisionId || !vehicleTabs.includes(activeTab)) return;
    if (vehicleClassOpts.length === 0) fetchVehicleClasses();
    if (activeTab === 'vehicle_masses') fetchVehicleMasses();
    if (activeTab === 'interrupted_vehicles') fetchInterruptedVehicles();
    if (activeTab === 'uninterrupted_vehicles') fetchUninterruptedVehicles();
    if (activeTab === 'vehicle_energy') fetchVehicleEnergy();
  }, [activeTab, selectedRevisionId, vehicleClassOpts.length, fetchVehicleClasses, fetchVehicleMasses, fetchInterruptedVehicles, fetchUninterruptedVehicles, fetchVehicleEnergy]);

  const fetchOpEq = useCallback(async () => {
    setOpEqFetching(true); setOpEqError('');
    try {
      const params: Record<string, string | number> = { limit: 500 };
      if (selectedRevisionId) {
        params.dataset_revision_id = selectedRevisionId;
      }
      const res = await http.get<OperationalEquipmentRow[]>('/api/operational-equipment', { params });
      setOpEqRows(res.data);
    } catch { setOpEqError('Failed to load operational equipment data.'); }
    finally { setOpEqFetching(false); }
  }, [selectedRevisionId]);

  useEffect(() => {
    if (activeTab === 'operational_equipment' && opEqRows.length === 0) fetchOpEq();
  }, [activeTab, opEqRows.length, fetchOpEq]);

  
  // ── Default concrete mix designs (BAU Assumptions) ────────────────────────
  const fetchConcreteMix = useCallback(async () => {
    if (!selectedRevisionId) return;
    setCmFetching(true); setCmError('');
    try {
      const params = new URLSearchParams({ dataset_revision_id: selectedRevisionId });
      const res = await http.get<ConcreteMixBundle>(`/api/concrete-mix-designs?${params}`);
      setCmAssumptions(res.data?.assumptions ?? null);
      setCmRows(res.data?.rows ?? []);
      setCmLoaded(true);
    } catch { setCmError('Failed to load concrete mix designs.'); }
    finally { setCmFetching(false); }
  }, [selectedRevisionId]);

  useEffect(() => {
    if (activeTab !== 'concrete_mix_designs') return;
    setCmAssumptions(null);
    setCmRows([]);
    setCmLoaded(false);
    setCmError('');
    if (selectedRevisionId) {
      fetchConcreteMix();
    }
  }, [activeTab, selectedRevisionId, fetchConcreteMix]);

  const auNzDirectSubJurOpts = useMemo(
    () => jurOpts.filter(j => j.name === 'Australia' || j.name === 'New Zealand'),
    [jurOpts],
  );

  useEffect(() => {
    setDirectSubPage(1);
  }, [directSubJurisdictionId]);

  const fetchDirectSubstitutions = useCallback(async () => {
    setDirectSubFetching(true);
    setDirectSubError('');
    try {
      const p = new URLSearchParams();
      p.set('skip', String((directSubPage - 1) * pageSize));
      p.set('limit', String(pageSize));
      if (selectedRevisionId) p.set('dataset_revision_id', selectedRevisionId);
      if (directSubJurisdictionId) p.set('jurisdiction_id', directSubJurisdictionId);
      const res = await http.get<{ items: DirectSubstitutionRow[]; total: number }>(`/api/direct-substitutions?${p}`);
      setDirectSubRows(res.data.items ?? []);
      setDirectSubTotal(typeof res.data.total === 'number' ? res.data.total : 0);
    } catch {
      setDirectSubError('Failed to load direct substitutions.');
    } finally {
      setDirectSubFetching(false);
    }
  }, [directSubPage, pageSize, directSubJurisdictionId, selectedRevisionId]);

  useEffect(() => {
    if (activeTab !== 'direct_substitutions') return;
    void fetchDirectSubstitutions();
  }, [activeTab, fetchDirectSubstitutions]);

  useEffect(() => {
    if (activeTab !== 'direct_substitutions') return;
    if (directSubTotal === 0) return;
    const pages = Math.max(1, Math.ceil(directSubTotal / pageSize));
    if (directSubPage > pages) setDirectSubPage(pages);
  }, [activeTab, directSubTotal, pageSize, directSubPage]);

  const downloadAllDirectSubstitutionsCsv = useCallback(async () => {
    setDirectSubExporting(true);
    setDirectSubError('');
    try {
      const all: DirectSubstitutionRow[] = [];
      let skip = 0;
      const limit = 500;
      while (true) {
        const p = new URLSearchParams();
        p.set('skip', String(skip));
        p.set('limit', String(limit));
        if (selectedRevisionId) p.set('dataset_revision_id', selectedRevisionId);
        if (directSubJurisdictionId) p.set('jurisdiction_id', directSubJurisdictionId);
        const res = await http.get<{ items: DirectSubstitutionRow[]; total: number }>(`/api/direct-substitutions?${p}`);
        const batch = res.data.items ?? [];
        all.push(...batch);
        const total = res.data.total ?? 0;
        if (all.length >= total || batch.length === 0) break;
        skip += limit;
      }
      const fname = `direct_substitutions_${(revisions.find(r => r.id === selectedRevisionId)?.name ?? 'data').replace(/\s+/g, '_')}.csv`;
      downloadCsv(DIRECT_SUBSTITUTION_COLS, all as unknown[], fname);
    } catch {
      setDirectSubError('Failed to export CSV.');
    } finally {
      setDirectSubExporting(false);
    }
  }, [directSubJurisdictionId, revisions, selectedRevisionId]);

  useEffect(() => {
    setEraPage(1);
  }, [eraJurisdictionId, selectedRevisionId]);

  const fetchElectricityRecyclingAssumptions = useCallback(async () => {
    if (!selectedRevisionId) return;
    setEraFetching(true);
    setEraError('');
    try {
      const p = new URLSearchParams({
        dataset_revision_id: selectedRevisionId,
        skip: String((eraPage - 1) * pageSize),
        limit: String(pageSize),
      });
      if (eraJurisdictionId) p.set('jurisdiction_id', eraJurisdictionId);
      const res = await http.get<{ items: ElectricityRecyclingAssumptionRow[]; total: number }>(
        `/api/electricity-recycling-assumptions?${p}`,
      );
      setEraRows(res.data.items ?? []);
      setEraTotal(typeof res.data.total === 'number' ? res.data.total : 0);
    } catch {
      setEraError('Failed to load electricity and recycling assumptions.');
    } finally {
      setEraFetching(false);
    }
  }, [selectedRevisionId, eraPage, pageSize, eraJurisdictionId]);

  useEffect(() => {
    if (activeTab !== 'electricity_recycling_assumptions') return;
    setEraRows([]);
    setEraTotal(0);
    setEraError('');
    setEraEditRowId(null);
    setEraCellDraft('');
    if (selectedRevisionId) {
      void fetchElectricityRecyclingAssumptions();
    }
  }, [activeTab, selectedRevisionId, fetchElectricityRecyclingAssumptions]);

  useEffect(() => {
    if (activeTab !== 'electricity_recycling_assumptions') return;
    if (eraTotal === 0) return;
    const pages = Math.max(1, Math.ceil(eraTotal / pageSize));
    if (eraPage > pages) setEraPage(pages);
  }, [activeTab, eraTotal, pageSize, eraPage]);

  const downloadAllElectricityRecyclingAssumptionsCsv = useCallback(async () => {
    if (!selectedRevisionId) return;
    setEraExporting(true);
    setEraError('');
    try {
      const all: ElectricityRecyclingAssumptionRow[] = [];
      let skip = 0;
      const limit = 500;
      while (true) {
        const p = new URLSearchParams({
          dataset_revision_id: selectedRevisionId,
          skip: String(skip),
          limit: String(limit),
        });
        if (eraJurisdictionId) p.set('jurisdiction_id', eraJurisdictionId);
        const res = await http.get<{ items: ElectricityRecyclingAssumptionRow[]; total: number }>(
          `/api/electricity-recycling-assumptions?${p}`,
        );
        const batch = res.data.items ?? [];
        all.push(...batch);
        const total = res.data.total ?? 0;
        if (all.length >= total || batch.length === 0) break;
        skip += limit;
      }
      const fname = `electricity_recycling_assumptions_${(revisions.find(r => r.id === selectedRevisionId)?.name ?? 'data').replace(/\s+/g, '_')}.csv`;
      downloadCsv(ELECTRICITY_RECYCLING_ASSUMPTION_COLS, eraRowsForCsvExport(all) as unknown[], fname);
    } catch {
      setEraError('Failed to export CSV.');
    } finally {
      setEraExporting(false);
    }
  }, [selectedRevisionId, eraJurisdictionId, revisions]);

  const doSaveEraCell = useCallback(async () => {
    if (!eraEditRowId) return;
    setEraSaving(true);
    setEraSaveError('');
    try {
      const trimmed = eraCellDraft.trim();
      if (trimmed === '') {
        setEraSaveError('Enter a percentage value');
        setEraSaving(false);
        return;
      }
      const pct = parseFloat(trimmed);
      if (!Number.isFinite(pct) || pct < 0 || pct > 100) {
        setEraSaveError('Enter a value between 0 and 100');
        setEraSaving(false);
        return;
      }
      const res = await http.patch<{
        row: ElectricityRecyclingAssumptionRow;
        recalculated_rows: ElectricityRecyclingAssumptionRow[];
      }>(`/api/electricity-recycling-assumptions/${eraEditRowId}`, {
        default_bau_pct: pct / 100,
      });
      const updated = res.data.row;
      const recalcIds = new Set((res.data.recalculated_rows ?? []).map(r => r.id));
      setEraRows(prev => prev.map(r => {
        if (r.id === updated.id) return updated;
        const recalc = (res.data.recalculated_rows ?? []).find(x => x.id === r.id);
        if (recalc) return recalc;
        if (recalcIds.has(r.id)) {
          return (res.data.recalculated_rows ?? []).find(x => x.id === r.id) ?? r;
        }
        return r;
      }));
      setEraEditRowId(null);
      setEraCellDraft('');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setEraSaveError(typeof msg === 'string' ? msg : 'Failed to save value.');
    } finally {
      setEraSaving(false);
    }
  }, [eraEditRowId, eraCellDraft]);

  const doSaveCmCell = useCallback(async () => {
    if (!cmEditCellKey) return;
    if (!selectedRevisionId) { setCmSaveError('Select a revision first'); return; }
    const [rowId, field] = cmEditCellKey.split('::') as [string, ConcreteMixStrengthField];
    if (!rowId || !field) return;
    setCmSaving(true); setCmSaveError('');
    try {
      const trimmed = cmCellDraft.trim();
      const numeric = trimmed === '' ? null : parseFloat(trimmed);
      if (numeric !== null && (!Number.isFinite(numeric) || numeric < 0)) {
        setCmSaveError('Enter a non-negative number');
        setCmSaving(false);
        return;
      }
      const payload: Record<string, number | null> = {};
      payload[field] = numeric;
      const res = await http.patch<{
        row: ConcreteMixDesignRow;
        recalculated_rows: ConcreteMixDesignRow[];
      }>(`/api/concrete-mix-designs/${rowId}`, payload);
      const recalcMap = new Map(res.data.recalculated_rows.map(r => [r.id, r]));
      setCmRows(prev => prev.map(r =>
        r.id === res.data.row.id ? res.data.row :
        recalcMap.get(r.id) ?? r
      ));
      setCmEditCellKey(null); setCmCellDraft('');
    } catch (err: any) {
      setCmSaveError(extractApiError(err, 'Save failed'));
    } finally {
      setCmSaving(false);
    }
  }, [cmEditCellKey, cmCellDraft, selectedRevisionId]);

  const doSaveCmAssumption = useCallback(async () => {
    if (!cmAssumptionField) return;
    if (!selectedRevisionId) { setCmSaveError('Select a revision first'); return; }
    setCmSaving(true); setCmSaveError('');
    try {
      const trimmed = cmAssumptionDraft.trim();
      const asPercent = trimmed === '' ? 0 : parseFloat(trimmed);
      if (!Number.isFinite(asPercent) || asPercent < 0 || asPercent > 100) {
        setCmSaveError('Enter a percentage between 0 and 100');
        setCmSaving(false);
        return;
      }
      const fraction = asPercent / 100;
      const payload: Record<string, number> = {};
      payload[cmAssumptionField] = fraction;
      const params = new URLSearchParams({ dataset_revision_id: selectedRevisionId });
      const res = await http.patch<{
        assumptions: ConcreteMixAssumption;
        recalculated_rows: ConcreteMixDesignRow[];
     }>(`/api/concrete-mix-designs/assumptions?${params}`, payload);
      setCmAssumptions(res.data.assumptions);
      if (res.data.recalculated_rows?.length) {
        const recalcMap = new Map(res.data.recalculated_rows.map(r => [r.id, r]));
        setCmRows(prev => prev.map(r => recalcMap.get(r.id) ?? r));
      }
      setCmAssumptionField(null); setCmAssumptionDraft('');
    } catch (err: any) {
      setCmSaveError(extractApiError(err, 'Save failed'));
    } finally {
      setCmSaving(false);
    }
 }, [cmAssumptionField, cmAssumptionDraft, selectedRevisionId]);

    
  const doSaveDensityRow = useCallback(async () => {
    if (!densityEditingId) return;
    setDensitySaving(true);
    setDensitySaveError('');
    try {
      const row = densityData.find(r => r.id === densityEditingId);
      if (!row) return;
      
      await http.patch(`/api/densities/${densityEditingId}`, {
        density: densityEditDraft.density ? parseFloat(densityEditDraft.density) : null,
        source: densityEditDraft.source || null,
      });
      
      setDensityData(prev => prev.map(r =>
        r.id === densityEditingId
          ? {
              ...r,
              density: densityEditDraft.density || null,
              source: densityEditDraft.source || null,
            }
          : r
      ));
      setDensityFiltered(prev => prev.map(r =>
        r.id === densityEditingId
          ? {
              ...r,
              density: densityEditDraft.density || null,
              source: densityEditDraft.source || null,
            }
          : r
      ));
      setDensityEditingId(null);
      setDensityEditDraft({});
    } catch (err: any) {
      setDensitySaveError(extractApiError(err, 'Failed to save'));
    } finally {
      setDensitySaving(false);
    }
  }, [densityEditingId, densityEditDraft, densityData]);

  const doSaveOpEqRow = useCallback(async () => {
    if (!opEqEditingId) return;
    setOpEqSaving(true); setOpEqSaveError('');
    try {
      const payload: Record<string, unknown> = {};
      if (opEqEditDraft.group_name  !== undefined) payload.group_name   = opEqEditDraft.group_name;
      if (opEqEditDraft.item        !== undefined) payload.item          = opEqEditDraft.item;
      if (opEqEditDraft.power_kw    !== undefined) payload.power_kw      = parseFloat(opEqEditDraft.power_kw);
      if (opEqEditDraft.hours_per_day !== undefined) payload.hours_per_day = parseFloat(opEqEditDraft.hours_per_day);
      if (opEqEditDraft.days_per_year !== undefined) payload.days_per_year = parseFloat(opEqEditDraft.days_per_year);
      if (opEqEditDraft.source      !== undefined) payload.source        = opEqEditDraft.source || null;
      const res = await http.post<OperationalEquipmentRow>(`/api/operational-equipment/${opEqEditingId}/supersede`, payload);
      setOpEqRows(prev => prev.map(r => r.id === opEqEditingId ? res.data : r));
      setOpEqEditingId(null); setOpEqEditDraft({});
    } catch (err: any) { setOpEqSaveError(extractApiError(err, 'Save failed')); }
    finally { setOpEqSaving(false); }
  }, [opEqEditingId, opEqEditDraft]);

  useMemo(() => {
    let filtered = densityData;

    if (densityFilter.jurisdictions.length > 0) {
      filtered = filtered.filter(r => densityFilter.jurisdictions.includes(r.jurisdiction?.name ?? ''));
    }
    if (densityFilter.datasets.length > 0) {
      filtered = filtered.filter(r => densityFilter.datasets.includes(r.dataset ?? ''));
    }
    if (densityFilter.categories.length > 0) {
      filtered = filtered.filter(r => densityFilter.categories.includes(r.emissions_category?.name ?? ''));
    }
    if (densityFilter.subcategories.length > 0) {
      filtered = filtered.filter(r => densityFilter.subcategories.includes(r.emissions_sub_category?.name ?? ''));
    }
    if (densityFilter.emissionsSource.trim()) {
      const search = densityFilter.emissionsSource.toLowerCase();
      filtered = filtered.filter(r =>
        (r.emissions_source ?? '').toLowerCase().includes(search)
      );
    }
    if (densityFilter.units.length > 0) {
      filtered = filtered.filter(r => densityFilter.units.includes(r.unit?.code ?? ''));
    }

    setDensityFiltered(filtered);
  }, [densityData, densityFilter]);

  useMemo(() => {
    let filtered = fcRows;

    if (fcFilter.jurisdictions.length > 0) {
      filtered = filtered.filter(r => fcFilter.jurisdictions.includes(r.jurisdiction?.name ?? ''));
    }

    setFcFiltered(filtered);
  }, [fcRows, fcFilter]);

  useMemo(() => {
    let filtered = wgRows;

    if (wgFilter.jurisdictions.length > 0) {
      filtered = filtered.filter(r => wgFilter.jurisdictions.includes(r.jurisdiction?.name ?? ''));
    }

    if (wgFilter.materials.length > 0) {
      filtered = filtered.filter(r => wgFilter.materials.includes(r.material?.name ?? ''));
    }

    setWgFiltered(filtered);
  }, [wgRows, wgFilter]);

useMemo(() => {
    const allJurOptions = Array.from(new Set(crfRows.map(r => r.jurisdiction_name).filter(Boolean))) as string[];
    let filtered = crfRows;
    const sel = crfFilter.jurisdictions;
    if (sel.length > 0 && sel.length < allJurOptions.length) {
      filtered = filtered.filter(r => sel.includes(r.jurisdiction_name ?? ''));
    }
    setCrfFiltered(filtered);
  }, [crfRows, crfFilter]);

  const crfJurOptions = useMemo(
    () => Array.from(new Set(crfRows.map(r => r.jurisdiction_name).filter(Boolean))).sort() as string[],
    [crfRows],
  );

  const doSaveVmEdit = useCallback(async () => {
    if (!vmEditingId) return;
    setVmSaving(true); setVmSaveError('');
    try {
      await http.patch(`/api/vehicle-masses/${vmEditingId}`, {
        reference_gcm_tonnes: vmEditDraft.reference_gcm_tonnes || null,
        max_payload_tonnes:   vmEditDraft.max_payload_tonnes   || null,
        gvm_tonnes:           vmEditDraft.gvm_tonnes           || null,
        assumed_payload_pct:  vmEditDraft.assumed_payload_pct  || null,
      });
      const r = await http.get<VehicleMassRow[]>('/api/vehicle-masses', { params: { dataset_revision_id: selectedRevisionId } });
      setVmRows(r.data || []);
      setVmEditingId(null); setVmEditDraft({});
    } catch (e: any) { setVmSaveError(extractApiError(e, 'Save failed')); }
    finally { setVmSaving(false); }
  }, [vmEditingId, vmEditDraft, selectedRevisionId]);

  const doAddVm = useCallback(async () => {
    setVmSaving(true); setVmSaveError('');
    try {
      await http.post('/api/vehicle-masses', {
        dataset_revision_id: selectedRevisionId,
        vehicle_class_id:     vmAddDraft.vehicle_class_id,
        reference_gcm_tonnes: vmAddDraft.reference_gcm_tonnes || null,
        max_payload_tonnes:   vmAddDraft.max_payload_tonnes   || null,
        gvm_tonnes:           vmAddDraft.gvm_tonnes           || null,
        assumed_payload_pct:  vmAddDraft.assumed_payload_pct  || null,
      });
      const r = await http.get<VehicleMassRow[]>('/api/vehicle-masses', { params: { dataset_revision_id: selectedRevisionId } });
      setVmRows(r.data || []);
      setVmAdding(false); setVmAddDraft({});
    } catch (e: any) { setVmSaveError(extractApiError(e, 'Save failed')); }
    finally { setVmSaving(false); }
  }, [vmAddDraft, selectedRevisionId]);

  const doSaveIvEdit = useCallback(async () => {
    if (!ivEditingId) return;
    setIvSaving(true); setIvSaveError('');
    try {
      await http.patch(`/api/interrupted-vehicles/${ivEditingId}`, {
        coefficient_a: ivEditDraft.coefficient_a || null,
        coefficient_b: ivEditDraft.coefficient_b || null,
      });
      const r = await http.get<InterruptedVehicleRow[]>('/api/interrupted-vehicles', { params: { dataset_revision_id: selectedRevisionId } });
      setIvRows(r.data || []);
      setIvEditingId(null); setIvEditDraft({});
    } catch (e: any) { setIvSaveError(extractApiError(e, 'Save failed')); }
    finally { setIvSaving(false); }
  }, [ivEditingId, ivEditDraft, selectedRevisionId]);

  const doAddIv = useCallback(async () => {
    setIvSaving(true); setIvSaveError('');
    try {
      await http.post('/api/interrupted-vehicles', {
        dataset_revision_id: selectedRevisionId,
        vehicle_class_id: ivAddDraft.vehicle_class_id,
        coefficient_a: ivAddDraft.coefficient_a,
        coefficient_b: ivAddDraft.coefficient_b,
      });
      const r = await http.get<InterruptedVehicleRow[]>('/api/interrupted-vehicles', { params: { dataset_revision_id: selectedRevisionId } });
      setIvRows(r.data || []);
      setIvAdding(false); setIvAddDraft({});
    } catch (e: any) { setIvSaveError(extractApiError(e, 'Save failed')); }
    finally { setIvSaving(false); }
  }, [ivAddDraft, selectedRevisionId]);

  const doSaveUvEdit = useCallback(async () => {
    if (!uvEditingId) return;
    setUvSaving(true); setUvSaveError('');
    try {
      await http.patch(`/api/uninterrupted-vehicles/${uvEditingId}`, {
        gradient_m_per_km:     uvEditDraft.gradient_m_per_km     || null,
        curvature_deg_per_km:  uvEditDraft.curvature_deg_per_km  || null,
        base_fuel_l_per_100km: uvEditDraft.base_fuel_l_per_100km || null,
        k1: uvEditDraft.k1 || null, k2: uvEditDraft.k2 || null,
        k3: uvEditDraft.k3 || null, k4: uvEditDraft.k4 || null, k5: uvEditDraft.k5 || null,
      });
      const r = await http.get<UninterruptedVehicleRow[]>('/api/uninterrupted-vehicles', { params: { dataset_revision_id: selectedRevisionId } });
      setUvRows(r.data || []);
      setUvEditingId(null); setUvEditDraft({});
    } catch (e: any) { setUvSaveError(extractApiError(e, 'Save failed')); }
    finally { setUvSaving(false); }
  }, [uvEditingId, uvEditDraft, selectedRevisionId]);

  const doAddUv = useCallback(async () => {
    setUvSaving(true); setUvSaveError('');
    try {
      await http.post('/api/uninterrupted-vehicles', {
        dataset_revision_id: selectedRevisionId,
        vehicle_class_id:      uvAddDraft.vehicle_class_id,
        gradient_m_per_km:     uvAddDraft.gradient_m_per_km    || '0',
        curvature_deg_per_km:  uvAddDraft.curvature_deg_per_km,
        base_fuel_l_per_100km: uvAddDraft.base_fuel_l_per_100km,
        k1: uvAddDraft.k1, k2: uvAddDraft.k2, k3: uvAddDraft.k3,
        k4: uvAddDraft.k4, k5: uvAddDraft.k5,
      });
      const r = await http.get<UninterruptedVehicleRow[]>('/api/uninterrupted-vehicles', { params: { dataset_revision_id: selectedRevisionId } });
      setUvRows(r.data || []);
      setUvAdding(false); setUvAddDraft({});
    } catch (e: any) { setUvSaveError(extractApiError(e, 'Save failed')); }
    finally { setUvSaving(false); }
  }, [uvAddDraft, selectedRevisionId]);

  const doSaveVeEdit = useCallback(async () => {
    if (!veEditingId) return;
    setVeSaving(true); setVeSaveError('');
    try {
      await http.patch(`/api/vehicle-energy-conversion-rates/${veEditingId}`, {
        ev_projection_category:               veEditDraft.ev_projection_category               || null,
        primary_ice_fuel:                     veEditDraft.primary_ice_fuel                     || null,
        hybrid_fuel_savings_pct:              veEditDraft.hybrid_fuel_savings_pct              || null,
        phev_fuel_savings_pct:                veEditDraft.phev_fuel_savings_pct                || null,
        bev_energy_shift_kwh_per_l:           veEditDraft.bev_energy_shift_kwh_per_l           || null,
        fcev_hydrogen_consumption_kwh_per_l:  veEditDraft.fcev_hydrogen_consumption_kwh_per_l  || null,
        source_comments:                      veEditDraft.source_comments                      || null,
      });
      const r = await http.get<VehicleEnergyConversionRow[]>('/api/vehicle-energy-conversion-rates', { params: { dataset_revision_id: selectedRevisionId } });
      setVeRows(r.data || []);
      setVeEditingId(null); setVeEditDraft({});
    } catch (e: any) { setVeSaveError(extractApiError(e, 'Save failed')); }
    finally { setVeSaving(false); }
  }, [veEditingId, veEditDraft, selectedRevisionId]);

  const doAddVe = useCallback(async () => {
    setVeSaving(true); setVeSaveError('');
    try {
      await http.post('/api/vehicle-energy-conversion-rates', {
        dataset_revision_id: selectedRevisionId,
        vehicle_class_id:                     veAddDraft.vehicle_class_id,
        ev_projection_category:               veAddDraft.ev_projection_category,
        primary_ice_fuel:                     veAddDraft.primary_ice_fuel,
        hybrid_fuel_savings_pct:              veAddDraft.hybrid_fuel_savings_pct              || null,
        phev_fuel_savings_pct:                veAddDraft.phev_fuel_savings_pct                || null,
        bev_energy_shift_kwh_per_l:           veAddDraft.bev_energy_shift_kwh_per_l           || null,
        fcev_hydrogen_consumption_kwh_per_l:  veAddDraft.fcev_hydrogen_consumption_kwh_per_l  || null,
        source_comments:                      veAddDraft.source_comments                      || null,
      });
      const r = await http.get<VehicleEnergyConversionRow[]>('/api/vehicle-energy-conversion-rates', { params: { dataset_revision_id: selectedRevisionId } });
      setVeRows(r.data || []);
      setVeAdding(false); setVeAddDraft({});
    } catch (e: any) { setVeSaveError(extractApiError(e, 'Save failed')); }
    finally { setVeSaving(false); }
  }, [veAddDraft, selectedRevisionId]);

  // ——— Row delete helpers ———
  const doDeleteFugitive = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/fugitives/${id}`);
      setFcRows(prev => prev.filter(r => r.id !== id));
      setFcFiltered(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteDensity = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/densities/${id}`);
      setDensityData(prev => prev.filter(r => r.id !== id));
      setDensityFiltered(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteUnitConversion = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/unit-conversions/${id}`);
      setUcRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteEnergyDensityConversion = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/energy-density-conversions/${id}`);
      setEdcRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteWastageRate = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/wastage-rates/${id}`);
      setWgRows(prev => prev.filter(r => r.id !== id));
      setWgFiltered(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doSaveRenewableEnergyRow = useCallback(async () => {
    if (!recEditingId) return;
    setRecSaving(true);
    setRecSaveError('');
    try {
      const payload = {
        classification: recEditDraft.classification?.trim() || '',
        notes: recEditDraft.notes?.trim() || null,
      };
      await http.patch(`/api/renewable-energy-classifications/${recEditingId}`, payload);
      setRecRows(prev => prev.map(r =>
        r.id === recEditingId ? { ...r, classification: payload.classification, notes: payload.notes } : r
      ));
      setRecEditingId(null);
      setRecEditDraft({});
    } catch (err: any) {
      setRecSaveError(extractApiError(err, 'Failed to save'));
    } finally {
      setRecSaving(false);
    }
  }, [recEditingId, recEditDraft]);

  const doDeleteRenewableEnergy = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/renewable-energy-classifications/${id}`);
      setRecRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteContentRecycled = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/recycled-content-factors/${id}`);
      setCrfRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteVepm = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/vepm-factors/${id}`);
      setVepmRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteFreightRail = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/freight-rail-factors/${id}`);
      setFrRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteMaintenanceReplacement = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/maintenance-replacement-factors/${id}`);
      setMrRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteOperationalEquipment = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/operational-equipment/${id}`);
      setOpEqRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteRecycledContent = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/material-recycled-content/${id}`);
      setRcRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteTransport = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/default-transport-distances/${id}`);
      setTrRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteWasteRate = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/default-waste-rates/${id}`);
      setWrRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteVehicleMass = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/vehicle-masses/${id}`);
      setVmRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteInterruptedVehicle = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/interrupted-vehicles/${id}`);
      setIvRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteUninterruptedVehicle = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/uninterrupted-vehicles/${id}`);
      setUvRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const doDeleteVehicleEnergy = useCallback(async (id: string) => {
    if (!window.confirm('Delete this row? This cannot be undone.')) return;
    try {
      await http.delete(`/api/vehicle-energy-conversion-rates/${id}`);
      setVeRows(prev => prev.filter(r => r.id !== id));
    } catch { /* silent */ }
  }, []);

  const [lifecycleLoading, setLifecycleLoading] = useState(false);  const [lifecycleError, setLifecycleError]     = useState('');
  const [deleteRevLoading, setDeleteRevLoading] = useState(false);
  const [deleteRevError,   setDeleteRevError]   = useState('');

  const [showNewRevision,   setShowNewRevision]   = useState(false);

  const doCreateRevision = useCallback(async (
    name: string,
    notes: string,
    sourceId: string | null,
  ) => {
    const scopePayload =
      scope.type === 'DEFAULT'  ? { scope_type: 'DEFAULT', scope_id: null } : scope.type === 'ORG'      ? { scope_type: 'ORG',     scope_id: scope.orgId } : { scope_type: 'PROJECT',  scope_id: scope.projectId };

    let newRev: DatasetRevision;
    if (sourceId) {
      const res = await http.post<DatasetRevision>(
        `/api/dataset-revisions/${sourceId}/branch`,
        { name, notes: notes || null, ...scopePayload },
      );
      newRev = res.data;
    } else {
      const res = await http.post<DatasetRevision>(
        '/api/dataset-revisions',
        { name, notes: notes || null, ...scopePayload },
      );
      newRev = res.data;
    }
    setRevisions(prev => [...prev, newRev]);
    setSelectedRevisionId(newRev.id);
    setBaseData([]); setDisplayData([]); setActiveGrade('');
  }, [scope]);

  const doLifecycleAction = useCallback(async (
    action: 'publish' | 'unpublish' | 'deprecate' | 'archive',
  ) => {
    if (!selectedRevisionId) return;
    const confirmMsg: Record<string, string> = {
      deprecate: 'Mark this revision as deprecated? Existing project bindings remain intact.',
      archive:   'Archive this revision? This is a terminal state — it cannot be undone.',
    };
    if (confirmMsg[action] && !window.confirm(confirmMsg[action])) return;
    setLifecycleLoading(true);
    setLifecycleError('');
    try {
      await http.post(`/api/dataset-revisions/${selectedRevisionId}/${action}`);
      const revUrl =
        scope.type === 'DEFAULT' ? '/api/dataset-revisions?scope_type=DEFAULT&limit=200' :
        scope.type === 'ORG'     ? `/api/dataset-revisions?scope_type=ORG&scope_id=${scope.orgId}&limit=200` :
        `/api/dataset-revisions?scope_type=PROJECT&scope_id=${scope.projectId}&limit=200`;
      const res = await http.get<DatasetRevision[]>(revUrl);
      setRevisions(res.data);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      setLifecycleError(typeof detail === 'string' ? detail : `Failed to ${action} revision.`);
    } finally {
      setLifecycleLoading(false);
    }
  }, [selectedRevisionId]);

  const doDeleteRevision = useCallback(async () => {
    if (!selectedRevisionId) return;
    const rev = revisions.find(r => r.id === selectedRevisionId);
    if (!window.confirm(`Delete revision "${rev?.name ?? selectedRevisionId}"? This cannot be undone.`)) return;
    setDeleteRevLoading(true);
    setDeleteRevError('');
    try {
      await http.delete(`/api/dataset-revisions/${selectedRevisionId}`);
      setSelectedRevisionId('');
      setBaseData([]); setDisplayData([]); setActiveGrade('');
      const revUrl =
        scope.type === 'DEFAULT' ? '/api/dataset-revisions?scope_type=DEFAULT&limit=200' :
        scope.type === 'ORG'     ? `/api/dataset-revisions?scope_type=ORG&scope_id=${scope.orgId}&limit=200` :
        `/api/dataset-revisions?scope_type=PROJECT&scope_id=${scope.projectId}&limit=200`;
      const res = await http.get<DatasetRevision[]>(revUrl);
      setRevisions(res.data);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      setDeleteRevError(typeof detail === 'string' ? detail : 'Cannot delete this revision.');
    } finally {
      setDeleteRevLoading(false);
    }
  }, [selectedRevisionId, revisions, scope]);

  const doStartEdit = useCallback((id: string, draft: Record<string, string>) => {
    setEditingId(id); setEditDraft(draft);
    setAddingTab(null); setAddDraft({});
    setSaveError('');
  }, []);

  const doCancelEdit = useCallback(() => {
    setEditingId(null); setEditDraft({}); setSaveError('');
  }, []);

  const doStartAdd = useCallback((tab: PageTab) => {
    setAddingTab(tab); setAddDraft({ effective_from: today });
    setEditingId(null); setEditDraft({});
    setSaveError('');
  }, [today]);

  const doCancelAdd = useCallback(() => {
    setAddingTab(null); setAddDraft({}); setSaveError('');
  }, []);

  const doSaveEdit = useCallback(async () => {
    if (!editingId) return;
    setSavingOp(true); setSaveError('');
    try {
      let endpoint = '';
      if (activeTab === 'recycled')   endpoint = `/api/material-recycled-content/${editingId}/supersede`;
      else if (activeTab === 'transport') endpoint = `/api/default-transport-distances/${editingId}/supersede`;
      else if (activeTab === 'waste') endpoint = `/api/default-waste-rates/${editingId}/supersede`;
      else return;

      const payload: Record<string, unknown> = { ...editDraft };
      if (activeTab === 'recycled' && editDraft.percent !== undefined) {
        payload.percent = editDraft.percent !== '' ? String(parseFloat(editDraft.percent) / 100) : null;
      }
      Object.keys(payload).forEach(k => { if (payload[k] === '') payload[k] = null; });

      await http.post(endpoint, payload);
      setEditingId(null); setEditDraft({});
      if (activeTab === 'recycled')        await fetchRecycledContent(false);
      else if (activeTab === 'transport')  await fetchTransport(false);
      else if (activeTab === 'waste')      await fetchWasteRates(false);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      setSaveError(typeof detail === 'string' ? detail : 'Failed to save changes.');
    } finally { setSavingOp(false); }
  }, [editingId, editDraft, activeTab, fetchRecycledContent, fetchTransport, fetchWasteRates]);

  const doSaveAdd = useCallback(async () => {
    setSavingOp(true); setSaveError('');
    try {
      let endpoint = '';
      if (addingTab === 'recycled')        endpoint = '/api/material-recycled-content';
      else if (addingTab === 'transport')  endpoint = '/api/default-transport-distances';
      else if (addingTab === 'waste')      endpoint = '/api/default-waste-rates';
      else return;

      const payload: Record<string, unknown> = { ...addDraft };
      if (addingTab === 'recycled' && addDraft.percent !== undefined) {
        payload.percent = addDraft.percent !== '' ? String(parseFloat(addDraft.percent) / 100) : null;
      }
      // Auto-inject jurisdiction from filter when no jurisdiction was selected in the (hidden) column
      if (addingTab === 'recycled' && !payload.jurisdiction_id && rcFilter.jurisdictions.length === 1) {
        const autoJur = jurOpts.find(j => j.name === rcFilter.jurisdictions[0]);
        if (autoJur) payload.jurisdiction_id = autoJur.id;
      }
      if (addingTab === 'transport') {
        const keyType = addDraft.__tr_key_type ?? 'material';
        if (!addDraft.jurisdiction_id) {
          setSaveError('Jurisdiction is required.'); setSavingOp(false); return;
        }
        if (keyType === 'material' && !addDraft.material_id) {
          setSaveError('Material is required.'); setSavingOp(false); return;
        }
        if (keyType === 'category' && !addDraft.emissions_category_id) {
          setSaveError('Emissions category is required.'); setSavingOp(false); return;
        }
        if (keyType === 'material') delete payload.emissions_category_id;
        else delete payload.material_id;
        delete payload.__tr_key_type;
      }
      Object.keys(payload).forEach(k => { if (payload[k] === '') payload[k] = null; });

      await http.post(endpoint, payload);
      setAddingTab(null); setAddDraft({});
      if (addingTab === 'recycled')        await fetchRecycledContent(false);
      else if (addingTab === 'transport')  await fetchTransport(false);
      else if (addingTab === 'waste')      await fetchWasteRates(false);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      setSaveError(typeof detail === 'string' ? detail : 'Failed to create record.');
    } finally { setSavingOp(false); }
  }, [addingTab, addDraft, fetchRecycledContent, fetchTransport, fetchWasteRates]);

  const doStartBgmEdit = useCallback((key: string, draft: Record<string, string>) => {
    setBgmEditKey(key); setBgmEditDraft(draft);
    setBgmAdding(false); setBgmAddDraft({});
    setBgmSaveError('');
  }, []);

  const doCancelBgmEdit = useCallback(() => {
    setBgmEditKey(null); setBgmEditDraft({}); setBgmSaveError('');
  }, []);

  const doStartBgmAdd = useCallback(() => {
    setBgmAdding(true); setBgmAddDraft({});
    setBgmEditKey(null); setBgmEditDraft({});
    setBgmSaveError('');
  }, []);

  const doCancelBgmAdd = useCallback(() => {
    setBgmAdding(false); setBgmAddDraft({}); setBgmSaveError('');
  }, []);

  const doSaveBgmEdit = useCallback(async () => {
    if (!bgmEditKey) return;
    setBgmSaving(true); setBgmSaveError('');
    try {
      const grade = activeGrade;
      const patches: Promise<unknown>[] = [];

      if (grade === '1') {
        const row = (displayData as G1Row[]).find(r =>
          `${r._jurisdiction_id ?? ''}||${r._mastertype_id ?? ''}||${r._typecast_id ?? ''}||${r._metric_type_code}` === bgmEditKey
        );
        if (!row) throw new Error('Row not found');
        const source = bgmEditDraft.source !== '' ? bgmEditDraft.source : null;

        const bands = [
          ['Low', 'low', '_low_id'],
          ['Mid', 'mid', '_mid_id'],
          ['High', 'high', '_high_id'],
        ] as [string, string, keyof G1Row][];

        for (const [band, field, idField] of bands) {
          const val = bgmEditDraft[field];
          const id = row[idField] as string | null;
          if (id) {
            patches.push(http.patch(`/api/background-grade-metrics/${id}`, {
              value: val !== '' ? val : null,
              source,
              band_code: band,
            }));
          } else if (val && val !== '') {
            patches.push(http.post('/api/background-grade-metrics', {
              dataset_revision_id: selectedRevisionId,
              grade_id: row._grade_id,
              metric_type_id: row._metric_type_id,
              unit_id: row._unit_id,
              mastertype_id: row._mastertype_id || null,
              typecast_id: row._typecast_id || null,
              band_code: band,
              value: val,
              source,
            }));
          }
        }
      } else if (grade === '2') {
        const row = (displayData as G2Row[]).find(r =>
          `${r._jurisdiction_id ?? ''}||${r.emissions_category}||${r.emissions_subcategory}||${r.emissions_source}||${r.unit}` === bgmEditKey
        );
        if (!row) throw new Error('Row not found');
        const source = bgmEditDraft.source !== '' ? bgmEditDraft.source : null;
        const qty = bgmEditDraft.quantity !== '' ? bgmEditDraft.quantity : null;
        const metricTypeMap = new Map(bgmRawRows.map(r => [r.metric_type_code, r.metric_type_id]));

        const g2Specs: [string, string, string | null][] = [
          ['carbon_storage',          'carbon_storage', row._cs_id],
          ['emission_intensity_a1_a3','a1_a3',          row._a1a3_id],
          ['emission_intensity_a4',   'a4',             row._a4_id],
          ['emission_intensity_a5',   'a5',             row._a5_id],
        ];
        for (const [mtCode, draftKey, existingId] of g2Specs) {
          const val = bgmEditDraft[draftKey];
          if (existingId) {
            patches.push(http.patch(`/api/background-grade-metrics/${existingId}`, {
              value: val !== '' ? val : null,
              assumed_quantity_default: qty,
              source,
            }));
          } else if (val && val !== '') {
            patches.push(http.post('/api/background-grade-metrics', {
              dataset_revision_id: selectedRevisionId,
              grade_id: row._grade_id,
              emissions_category_id: row._cat_id,
              emissions_subcategory_id: row._subcat_id,
              emissions_source: row.emissions_source || null,
              unit_id: row._unit_id,
              metric_type_id: metricTypeMap.get(mtCode),
              value: val,
              assumed_quantity_default: qty,
              source,
            }));
          }
        }
      } else {
        const row = (displayData as G34Row[]).find(r =>
          `${r._jurisdiction_id ?? ''}||${r.emissions_category}||${r.emissions_subcategory}||${r.emissions_source}||${r.unit}` === bgmEditKey
        );
        if (!row) throw new Error('Row not found');
        const source = bgmEditDraft.source !== '' ? bgmEditDraft.source : null;
        const metricTypeMap = new Map(bgmRawRows.map(r => [r.metric_type_code, r.metric_type_id]));

        const g34Specs: [string, string, string | null][] = [
          ['carbon_storage',         'carbon_storage', row._cs_id],
          ['emission_factor_scope1', 'scope1',         row._s1_id],
          ['emission_factor_scope2', 'scope2',         row._s2_id],
          ['emission_factor_scope3', 'scope3',         row._s3_id],
        ];
        for (const [mtCode, draftKey, existingId] of g34Specs) {
          const val = bgmEditDraft[draftKey];
          if (existingId) {
            patches.push(http.patch(`/api/background-grade-metrics/${existingId}`, {
              value: val !== '' ? val : null,
              source,
            }));
          } else if (val && val !== '') {
            patches.push(http.post('/api/background-grade-metrics', {
              dataset_revision_id: selectedRevisionId,
              grade_id: row._grade_id,
              emissions_category_id: row._cat_id,
              emissions_subcategory_id: row._subcat_id,
              emissions_source: row.emissions_source || null,
              unit_id: row._unit_id,
              metric_type_id: metricTypeMap.get(mtCode),
              value: val,
              source,
            }));
          }
        }
      }

      await Promise.all(patches);
      setBgmEditKey(null); setBgmEditDraft({});
      await fetchData();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      setBgmSaveError(typeof detail === 'string' ? detail : 'Failed to save changes.');
    } finally { setBgmSaving(false); }
  }, [bgmEditKey, bgmEditDraft, activeGrade, displayData, bgmRawRows, fetchData]);

  const doSaveBgmAdd = useCallback(async () => {
    setBgmSaving(true); setBgmSaveError('');
    try {
      const grade = activeGrade;
      const base = {
        dataset_revision_id: selectedRevisionId,
        grade_id: parseInt(grade, 10),
      };
      const posts: Promise<unknown>[] = [];

      if (grade === '1') {
        for (const [band, draftKey] of [['Low','low'],['Mid','mid'],['High','high']] as [string,string][]) {
          const val = bgmAddDraft[draftKey];
          if (!val || val === '') continue;
          posts.push(http.post('/api/background-grade-metrics', {
            ...base,
            jurisdiction_id: bgmAddDraft.jurisdiction_id || null,
            metric_type_id: bgmAddDraft.metric_type_id || undefined,
            unit_id: bgmAddDraft.unit_id || undefined,
            mastertype_id: bgmAddDraft.mastertype_id || null,
            typecast_id: bgmAddDraft.typecast_id || null,
            band_code: band,
            value: val,
            source: bgmAddDraft.source || null,
          }));
        }
        if (posts.length === 0) {
          setBgmSaveError('Enter at least one value (Low/Mid/High).');
          setBgmSaving(false); return;
        }
      } else if (grade === '2') {
        const metricTypeMap = new Map(bgmRawRows.map(r => [r.metric_type_code, r.metric_type_id]));
        const g2MetricCodes: [string, string][] = [
          ['carbon_storage',           'carbon_storage'],
          ['emission_intensity_a1_a3', 'a1_a3'],
          ['emission_intensity_a4',    'a4'],
          ['emission_intensity_a5',    'a5'],
        ];
        for (const [mtCode, draftKey] of g2MetricCodes) {
          const val = bgmAddDraft[draftKey];
          if (!val || val === '') continue;
          const mtId = metricTypeMap.get(mtCode) ?? metricTypeOpts.find(m => m.name.startsWith(mtCode))?.id;
          posts.push(http.post('/api/background-grade-metrics', {
            ...base,
            jurisdiction_id: bgmAddDraft.jurisdiction_id || null,
            emissions_category_id: bgmAddDraft.emissions_category_id || null,
            emissions_subcategory_id: bgmAddDraft.emissions_subcategory_id || null,
            emissions_source: bgmAddDraft.emissions_source || null,
            unit_id: bgmAddDraft.unit_id || null,
            metric_type_id: mtId,
            assumed_quantity_default: bgmAddDraft.assumed_quantity_default || null,
            value: val,
            source: bgmAddDraft.source || null,
          }));
        }
        if (posts.length === 0) {
          setBgmSaveError('Enter at least one emission factor value.');
          setBgmSaving(false); return;
        }
      } else {
        const metricTypeMap = new Map(bgmRawRows.map(r => [r.metric_type_code, r.metric_type_id]));
        const g34MetricCodes: [string, string][] = [
          ['carbon_storage',         'carbon_storage'],
          ['emission_factor_scope1', 'scope1'],
          ['emission_factor_scope2', 'scope2'],
          ['emission_factor_scope3', 'scope3'],
        ];
        for (const [mtCode, draftKey] of g34MetricCodes) {
          const val = bgmAddDraft[draftKey];
          if (!val || val === '') continue;
          const mtId = metricTypeMap.get(mtCode) ?? metricTypeOpts.find(m => m.name.startsWith(mtCode))?.id;
          posts.push(http.post('/api/background-grade-metrics', {
            ...base,
            jurisdiction_id: bgmAddDraft.jurisdiction_id || null,
            emissions_category_id: bgmAddDraft.emissions_category_id || null,
            emissions_subcategory_id: bgmAddDraft.emissions_subcategory_id || null,
            emissions_source: bgmAddDraft.emissions_source || null,
            unit_id: bgmAddDraft.unit_id || null,
            metric_type_id: mtId,
            value: val,
            source: bgmAddDraft.source || null,
          }));
        }
        if (posts.length === 0) {
          setBgmSaveError('Enter at least one emission factor value.');
          setBgmSaving(false); return;
        }
      }

      await Promise.all(posts);
      setBgmAdding(false); setBgmAddDraft({});
      await fetchData();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      setBgmSaveError(typeof detail === 'string' ? detail : 'Failed to create record.');
    } finally { setBgmSaving(false); }
  }, [bgmAddDraft, activeGrade, selectedRevisionId, bgmRawRows, metricTypeOpts, fetchData]);

  const revisionOptions  = revisions.map(r  => ({ label: r.name, value: r.id }));

  const g1Opts = useMemo(() => {
    if (activeGrade !== '1') return null;
    const rows = baseData as G1Row[];
    return {
      metrics:      distinct(rows.map(r => r.metric)),
      units:        distinct(rows.map(r => r.unit)),
      jurisdictions: distinct(rows.map(r => r.jurisdiction).filter(Boolean)),
    };
  }, [baseData, activeGrade]);

  const g234Opts = useMemo(() => {
    if (activeGrade === '1' || activeGrade === '') return null;
    const rows = baseData as (G2Row | G34Row)[];
    const catRows = g234Filter.categories.length > 0
      ? rows.filter(r => g234Filter.categories.includes(r.emissions_category))
      : rows;
    return {
      categories:    distinct(rows.map(r => r.emissions_category)),
      subcategories: distinct(catRows.map(r => r.emissions_subcategory)),
      units:         distinct(rows.map(r => r.unit)),
      jurisdictions: distinct(rows.map(r => r.jurisdiction).filter(Boolean)),
    };
  }, [baseData, activeGrade, g234Filter.categories]);

  const totalBase   = (baseData as unknown[]).length;
  const displayRows = (displayData as unknown[]).slice((page - 1) * pageSize, page * pageSize);

  const hasG1Active   = g1Filter.mastertype_id !== '' || g1Filter.typecast_id !== '' ||
    g1Filter.metrics.length > 0 || g1Filter.units.length > 0 ||
    g1Filter.jurisdictions.length > 0;
  const hasG234Active = g234Filter.categories.length > 0 || g234Filter.subcategories.length > 0 ||
    g234Filter.emissionsSource !== '' || g234Filter.units.length > 0 ||
    g234Filter.jurisdictions.length > 0;
  const hasActiveFilters = activeGrade === '1' ? hasG1Active : hasG234Active;

  const rcOpts = useMemo(() => ({
    jurisdictions: distinct(rcRows.map(r => r.jurisdiction_name ?? r.jurisdiction_id ?? '').filter(Boolean)),
  }), [rcRows]);

  const rcFiltered = useMemo(() => {
    let rows = rcRows;
    if (rcFilter.material) {
      const q = rcFilter.material.toLowerCase();
      rows = rows.filter(r => (r.material_name ?? r.material_id ?? '').toLowerCase().includes(q));
    }
    if (rcFilter.jurisdictions.length > 0)
      rows = rows.filter(r => rcFilter.jurisdictions.includes(r.jurisdiction_name ?? r.jurisdiction_id ?? ''));
    if (rcFilter.percentMin !== '') {
      const min = parseFloat(rcFilter.percentMin) / 100;
      rows = rows.filter(r => r.percent != null && parseFloat(r.percent) >= min);
    }
    if (rcFilter.percentMax !== '') {
      const max = parseFloat(rcFilter.percentMax) / 100;
      rows = rows.filter(r => r.percent != null && parseFloat(r.percent) <= max);
    }
    return rows;
  }, [rcRows, rcFilter]);

  const rcDisplayRows = rcFiltered.slice((rcPage - 1) * pageSize, rcPage * pageSize);

  const trOpts = useMemo(() => ({
    jurisdictions: distinct(trRows.map(r => r.jurisdiction_name ?? r.jurisdiction_id ?? '').filter(Boolean)),
  }), [trRows]);

  const trFiltered = useMemo(() => {
    let rows = trRows;
    if (trFilter.materialCategory) {
      const q = trFilter.materialCategory.toLowerCase();
      rows = rows.filter(r =>
        (r.material_name ?? r.emissions_category_name ?? r.material_id ?? r.emissions_category_id ?? '').toLowerCase().includes(q)
      );
    }
    if (trFilter.jurisdictions.length > 0)
      rows = rows.filter(r => trFilter.jurisdictions.includes(r.jurisdiction_name ?? r.jurisdiction_id ?? ''));
    if (trFilter.transportMode) {
      const q = trFilter.transportMode.toLowerCase();
      rows = rows.filter(r =>
        (r.truck_transport_mode ?? '').toLowerCase().includes(q) ||
        (r.rail_transport_mode ?? '').toLowerCase().includes(q) ||
        (r.sea_transport_mode ?? '').toLowerCase().includes(q)
      );
    }
    return rows;
  }, [trRows, trFilter]);

  const trDisplayRows = trFiltered.slice((trPage - 1) * pageSize, trPage * pageSize);

  const decarbOpts = useMemo(() => {
    const jurSeen = new Set<string>();
    const jurOpts: NamedOption[] = [];
    const jurisdictions: string[] = [];
    const regionSeen = new Set<string>();
    const allRegions: Array<{ id: string; name: string; jurisdictionId: string }> = [];
    for (const r of decarbRows) {
      if (!jurSeen.has(r.jurisdiction_id)) {
        jurSeen.add(r.jurisdiction_id);
        const name = r.jurisdiction_name ?? r.jurisdiction_id;
        jurOpts.push({ id: r.jurisdiction_id, name });
        jurisdictions.push(name);
      }
      if (r.region_id && !regionSeen.has(r.region_id)) {
        regionSeen.add(r.region_id);
        allRegions.push({ id: r.region_id, name: r.region_name ?? r.region_id, jurisdictionId: r.jurisdiction_id });
      }
    }
    return { jurisdictions, jurOpts, allRegions };
  }, [decarbRows]);

  const decarbFiltered = useMemo(() => {
    return decarbRows.filter(r => {
      if (r.factor_type_code !== decarbActiveFt) return false;
      if (decarbFilter.jurisdictions.length > 0 &&
          !decarbFilter.jurisdictions.includes(r.jurisdiction_name ?? r.jurisdiction_id ?? '')) return false;
      return true;
    });
  }, [decarbRows, decarbActiveFt, decarbFilter]);

  const evUptakeOpts = useMemo(() => {
    const jurSeen = new Set<string>();
    const jurOpts: NamedOption[] = [];
    const jurisdictions: string[] = [];
    const scenarios   = new Set<string>();
    const vehicles    = new Set<string>();
    const energyTypes = new Set<string>();
    for (const r of evUptakeRows) {
      if (!jurSeen.has(r.jurisdiction_id)) {
        jurSeen.add(r.jurisdiction_id);
        const name = r.jurisdiction_name ?? r.jurisdiction_id;
        jurOpts.push({ id: r.jurisdiction_id, name });
        jurisdictions.push(name);
      }
      scenarios.add(r.scenario_code);
      vehicles.add(r.vehicle_category_code);
      energyTypes.add(r.energy_type_code);
    }
    return {
      jurisdictions,
      jurOpts,
      scenarioCodes:        Array.from(scenarios).sort(),
      vehicleCategoryCodes: Array.from(vehicles).sort(),
      energyTypeCodes:      Array.from(energyTypes).sort(),
    };
  }, [evUptakeRows]);

  const evUptakeFiltered = useMemo(() => {
    return evUptakeRows.filter(r => {
      if (evUptakeFilter.jurisdictions.length > 0 &&
          !evUptakeFilter.jurisdictions.includes(r.jurisdiction_name ?? r.jurisdiction_id)) return false;
      if (evUptakeFilter.scenarioCodes.length > 0 &&
          !evUptakeFilter.scenarioCodes.includes(r.scenario_code)) return false;
      if (evUptakeFilter.vehicleCategoryCodes.length > 0 &&
          !evUptakeFilter.vehicleCategoryCodes.includes(r.vehicle_category_code)) return false;
      if (evUptakeFilter.energyTypeCodes.length > 0 &&
          !evUptakeFilter.energyTypeCodes.includes(r.energy_type_code)) return false;
      return true;
    });
  }, [evUptakeRows, evUptakeFilter]);

  const cvFiltered = useMemo(() => {
    return cvRows.filter(r => {
      if (cvFilter.jurisdictions.length > 0 &&
          !cvFilter.jurisdictions.includes(r.jurisdiction_name ?? r.jurisdiction_id ?? '')) return false;   
          
      if (cvFilter.rangeCodes.length > 0 &&
          !cvFilter.rangeCodes.some(code => code.toLowerCase() === (r.range_code ?? '').toLowerCase())) return false;
      return true;
    });
  }, [cvRows, cvFilter]);

  const cvOpts = useMemo(() => {
    const jurSeen = new Set<string>();
    const jurOpts: NamedOption[] = [];
    const jurisdictions: string[] = [];
    const rangeSeen = new Set<string>();
    const rangeOpts: NamedOption[] = [];
    const ranges: string[] = [];
    
    for (const r of cvRows) {
      // Jurisdictions
      if (!jurSeen.has(r.jurisdiction_id)) {
        jurSeen.add(r.jurisdiction_id);
        const name = r.jurisdiction_name ?? r.jurisdiction_id;
        jurOpts.push({ id: r.jurisdiction_id, name });
        jurisdictions.push(name);
      }
      // Ranges
      if (!rangeSeen.has(r.range_code)) {
        rangeSeen.add(r.range_code);
        const name = r.range_name ?? r.range_code;
        rangeOpts.push({ id: r.range_code, name });
        ranges.push(name);
      }
    }
    
    return { jurisdictions, jurOpts, ranges, rangeOpts };
  }, [cvRows]);

  const vepmFiltered = useMemo(() => {
    if (!vepmYearFilter) return vepmRows;
    const y = parseInt(vepmYearFilter);
    if (isNaN(y)) return vepmRows;
    return vepmRows.filter(r => r.year === y);
  }, [vepmRows, vepmYearFilter]);

  const tabDownloadRows = useMemo((): any[] => {
    switch (activeTab) {
      case 'recycled':                   return rcFiltered;
      case 'transport':                  return trFiltered;
      case 'waste':                      return wrRows;
      case 'decarb':                     return decarbFiltered;
      case 'carbon_values':              return cvFiltered;
      case 'ev_uptake':                  return evUptakeFiltered;
      case 'vepm':                       return vepmFiltered;
      case 'freight_rail':               return frRows;
      case 'maintenance_replacement':    return mrRows;
      case 'operational_equipment':      return opEqRows;
      case 'densities':                  return densityFiltered;
      case 'unit_conversions':           return ucRows;
      case 'fugitives':                  return fcFiltered;
      case 'energy_density_conversions': return edcRows;
      case 'vehicle_masses':             return vmRows;
      case 'interrupted_vehicles':       return ivRows;
      case 'uninterrupted_vehicles':     return uvRows;
      case 'vehicle_energy':             return veRows;
      case 'wastage_rates':              return wgFiltered;
      case 'renewable_energy':            return recRows;
      case 'content_recycled':           return crfFiltered;
      case 'factors':                    return displayData as any[];
      case 'concrete_mix_designs':       return cmRows;
      case 'direct_substitutions':       return directSubRows;
      case 'electricity_recycling_assumptions': return eraRowsForCsvExport(eraRows);
      default:                           return [];
    }
  }, [activeTab, rcFiltered, trFiltered, wrRows, decarbFiltered, cvFiltered, evUptakeFiltered,
      vepmFiltered, frRows, mrRows, opEqRows, densityFiltered, ucRows, fcFiltered, edcRows,
     vmRows, ivRows, uvRows, veRows, wgFiltered, recRows, crfFiltered, cmRows, directSubRows, eraRows, displayData]);

  const tabCsvCols = useMemo(() => {
    switch (activeTab) {
      case 'recycled':                   return RECYCLED_CONTENT_COLS;
      case 'transport':                  return TRANSPORT_COLS;
      case 'waste':                      return WASTE_COLS;
      case 'decarb':                     return DECARB_COLS;
      case 'carbon_values':              return CARBON_VALUES_COLS;
      case 'ev_uptake':                  return EV_UPTAKE_COLS;
      case 'vepm':                       return VEPM_COLS;
      case 'freight_rail':               return FREIGHT_RAIL_COLS;
      case 'maintenance_replacement':    return MAINTENANCE_REPLACEMENT_COLS;
      case 'operational_equipment':      return OPERATIONAL_EQUIPMENT_COLS;
      case 'densities':                  return DENSITIES_COLS;
      case 'unit_conversions':           return UNIT_CONVERSIONS_COLS;
      case 'fugitives':                  return FUGITIVES_COLS;
      case 'energy_density_conversions': return ENERGY_DENSITY_COLS;
      case 'vehicle_masses':             return VEHICLE_MASSES_COLS;
      case 'interrupted_vehicles':       return INTERRUPTED_VEHICLES_COLS;
      case 'uninterrupted_vehicles':     return UNINTERRUPTED_VEHICLES_COLS;
      case 'vehicle_energy':             return VEHICLE_ENERGY_COLS;
      case 'wastage_rates':              return WASTAGE_RATES_COLS;
      case 'renewable_energy':            return RENEWABLE_ENERGY_COLS;
       case 'content_recycled':           return CONTENT_RECYCLED_COLS;
      case 'factors':
        return activeGrade === '1' ? GRADE1_COLS : activeGrade === '2' ? GRADE2_COLS : GRADE34_COLS;
      case 'concrete_mix_designs':       return CONCRETE_MIX_DESIGN_COLS;
      case 'direct_substitutions':       return DIRECT_SUBSTITUTION_COLS;
      case 'electricity_recycling_assumptions': return ELECTRICITY_RECYCLING_ASSUMPTION_COLS;
      default: return [];
    }
  }, [activeTab, activeGrade]);

  const tabFilename = `${activeTab}_${(revisions.find(r => r.id === selectedRevisionId)?.name ?? 'data').replace(/\s+/g, '_')}.csv`;

  const handleCategoryChange = (cats: string[]) => {
    setG234Filter(prev => {
      const validSubs = new Set(
        (baseData as (G2Row | G34Row)[])
          .filter(r => cats.length === 0 || cats.includes(r.emissions_category))
          .map(r => r.emissions_subcategory)
      );
      return { ...prev, categories: cats, subcategories: prev.subcategories.filter(s => validSubs.has(s)) };
    });
  };

  return (
    <div className="flex flex-col h-full">
      {showNewRevision && (
        <NewRevisionModal
          scopeType={scope.type}
          revisions={revisions}
          sourceRevisions={branchableRevisions}
          onClose={() => setShowNewRevision(false)}
          onCreate={doCreateRevision}
        />
      )}
      <div className="px-6 pt-6 pb-4 border-b border-neutral-90 bg-white">
        <h1 className="text-xl font-semibold text-text-dark">
          {scope.type === 'DEFAULT'  ? 'Datasets' :
           scope.type === 'ORG'      ? 'Organisation Datasets' :
           'Project Datasets'}
        </h1>
        <p className="text-sm text-text-base mt-0.5">
          {scope.type === 'DEFAULT'  ? 'View and manage platform-default background datasets' :
           scope.type === 'ORG'      ? 'View and manage organisation-scoped dataset customisations' :
           'View and manage project-scoped dataset customisations'}
        </p>
      </div>

      <div className="px-6 py-3 bg-neutral-98 border-b border-neutral-90">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <SelectListbox
              value={selectedRevisionId}
              placeholder="Datasets"
              options={revisionOptions}
              onChange={handleRevisionChange}
              loading={loadingMeta}
              className="w-56"
            />
          </div>

          <div className="ml-auto flex items-center gap-1.5 flex-wrap justify-end">
            {canEditScope && (
              <button
                type="button"
                onClick={() => setShowNewRevision(true)}
                title="Create a new revision or branch from an existing one"
                className="rounded border border-primary px-2.5 py-1 text-xs font-medium text-primary hover:bg-primary/10 whitespace-nowrap cursor-pointer"
              >
                + New
              </button>
            )}
            {selectedRevisionId && (() => {
              const rev = revisions.find(r => r.id === selectedRevisionId);
              if (!rev) return null;
              return (
                <>
                  <StatusBadge status={rev.status} />
                  {(canEdit || canArchive) && (
                    <div className="flex items-center gap-1">
                      {rev.status === 'draft' && canEdit && (
                        <>
                          <button
                            type="button"
                            onClick={() => doLifecycleAction('publish')}
                            disabled={lifecycleLoading}
                            className="rounded  cursor-pointer border border-green-600 bg-green-50 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-100 disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            {lifecycleLoading ? '…' : 'Publish'}
                          </button>
                          <button
                            type="button"
                            onClick={doDeleteRevision}
                            disabled={deleteRevLoading}
                            className="rounded cursor-pointer border border-red-300 bg-red-50 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-100 disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            {deleteRevLoading ? '…' : 'Delete'}
                          </button>
                        </>
                      )}
                      {rev.status === 'published' && (
                        <>
                          {canEdit && (
                            <>
                              <button
                                type="button"
                                onClick={() => doLifecycleAction('unpublish')}
                                disabled={lifecycleLoading}
                                className="rounded cursor-pointer border border-neutral-400 bg-white px-2 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-98 disabled:opacity-40 disabled:cursor-not-allowed"
                              >
                                {lifecycleLoading ? '…' : 'Unpublish'}
                              </button>
                              <button
                                type="button"
                                onClick={() => doLifecycleAction('deprecate')}
                                disabled={lifecycleLoading}
                                className="rounded cursor-pointer border border-yellow-500 bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-700 hover:bg-yellow-100 disabled:opacity-40 disabled:cursor-not-allowed"
                              >
                                {lifecycleLoading ? '…' : 'Deprecate'}
                              </button>
                            </>
                          )}
                          {canArchive && (
                            <button
                              type="button"
                              onClick={() => doLifecycleAction('archive')}
                              disabled={lifecycleLoading}
                              className="rounded border cursor-pointer border-red-400 bg-red-50 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-100 disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              {lifecycleLoading ? '…' : 'Archive'}
                            </button>
                          )}
                        </>
                      )}
                      {rev.status === 'deprecated' && (
                        <>
                          {canArchive && (
                            <button
                              type="button"
                              onClick={() => doLifecycleAction('archive')}
                              disabled={lifecycleLoading}
                              className="rounded border border-red-400 bg-red-50 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-100 disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                              {lifecycleLoading ? '…' : 'Archive'}
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  )}
                  {(lifecycleError || deleteRevError) && (
                    <span className="text-xs text-red-600">{lifecycleError || deleteRevError}</span>
                  )}
                </>
              );
            })()}
          </div>
        </div>
        <div className="flex items-center gap-2 mt-3 -mx-6 px-6 border-t border-neutral-90 pt-2">
          {TAB_GROUPS.map((group) => (
            <button
              key={group.label}
              type="button"
              onClick={() => { setActiveGroup(group.label); setActiveTab(group.ids[0]); }}
              className={[
                'rounded-full px-3 py-1 text-xs font-medium transition-colors cursor-pointer',
                activeGroup === group.label
                  ? 'bg-primary text-white'
                  : 'bg-white border border-neutral-80 text-text-base hover:border-primary hover:text-primary',
              ].join(' ')}
            >
              {group.label}
            </button>
          ))}
        </div>
        {(() => {
          const activeGroupDef = TAB_GROUPS.find(g => g.label === activeGroup) ?? TAB_GROUPS[0];
          const activeGroupTabs = TABS.filter(t => (activeGroupDef.ids as readonly string[]).includes(t.id));
          /////if (activeGroupTabs.length <= 1) return null;
          const minToShow = activeGroupDef.alwaysShowSubTabs ? 1 : 2;
          if (activeGroupTabs.length < minToShow) return null;

          return (
            <div className="flex items-center gap-0 -mx-6 px-6 border-t border-neutral-90 mt-1 flex-wrap">
              {activeGroupTabs.map(tab => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  className={[
                    'px-4 py-2 text-xs font-medium border-b-2 transition-colors cursor-pointer',
                    activeTab === tab.id
                      ? 'border-primary text-primary'
                      : 'border-transparent text-text-base hover:text-text-dark',
                  ].join(' ')}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          );
        })()}
        <div className="flex items-center gap-3 mt-2">
          {activeTab === 'factors' && (
            <>
              <div className="h-4 w-px bg-neutral-80 mx-1" />
              <SelectListbox
                value={selectedGrade}
                placeholder="Grade"
                options={GRADE_OPTIONS}
                onChange={handleGradeChange}
                disabled={!selectedRevisionId}
                className="w-40"
              />
              <button
                onClick={fetchData}
                disabled={!canFetch || fetching}
                className="rounded bg-primary cursor-pointer px-4 py-2 text-sm font-medium text-white disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {fetching ? 'Loading…' : 'Load'}
              </button>
              {activeGrade !== '' && !fetching && totalBase > 0 && (
                <span className="text-xs text-text-base">
                  {(displayData as unknown[]).length} rows
                  {hasActiveFilters && ` (filtered from ${totalBase})`}
                </span>
              )}
              {filterFetching && (
                <span className="flex items-center gap-1 text-xs text-text-base">
                  <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Filtering…
                </span>
              )}
            </>
          )}
          {(activeTab === 'recycled' || activeTab === 'transport' || activeTab === 'waste') && (
            <>
              <label className="text-xs text-text-base">As of date:</label>
              <input
                type="date"
                value={activeTab === 'recycled' ? rcAsOfDate : activeTab === 'transport' ? trAsOfDate : wrAsOfDate}
                onChange={e => {
                  if (activeTab === 'recycled') setRcAsOfDate(e.target.value);
                  else if (activeTab === 'transport') setTrAsOfDate(e.target.value);
                  else setWrAsOfDate(e.target.value);
                }}
                className="rounded border border-neutral-80 px-2 py-1 text-xs focus:outline-none focus:border-primary"
              />
              <button
                onClick={() => {
                  if (activeTab === 'recycled') fetchRecycledContent();
                  else if (activeTab === 'transport') fetchTransport();
                  else fetchWasteRates();
                }}
                disabled={!selectedRevisionId || (activeTab === 'recycled' ? rcFetching : activeTab === 'transport' ? trFetching : wrFetching)}
                className="rounded bg-primary px-4 py-2 text-sm font-medium cursor-pointer text-white disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {(activeTab === 'recycled' ? rcFetching : activeTab === 'transport' ? trFetching : wrFetching) ? 'Loading…' : 'Load'}
              </button>
              {activeTab === 'recycled' && rcRows.length > 0 && (
                <span className="text-xs text-text-base">
                  {rcFiltered.length} rows
                  {(rcFilter.material || rcFilter.jurisdictions.length > 0 || rcFilter.percentMin !== '' || rcFilter.percentMax !== '') ? ` (filtered from ${rcRows.length})` : ''}
                </span>
              )}
              {activeTab === 'transport' && trRows.length > 0 && (
                <span className="text-xs text-text-base">
                  {trFiltered.length} rows
                  {(trFilter.materialCategory || trFilter.jurisdictions.length > 0 || trFilter.transportMode !== '') ? ` (filtered from ${trRows.length})` : ''}
                </span>
              )}
              {activeTab === 'waste' && wrRows.length > 0 && (
                <span className="text-xs text-text-base">{wrRows.length} rows</span>
              )}
            </>
          )}
          {activeTab === 'audit' && (
            <>
              <span className="text-xs text-text-base">
                {selectedRevisionId ? 'Showing audit events for selected revision' : 'Select a revision to view its audit trail'}
              </span>
              {selectedRevisionId && (
                <button
                  onClick={() => fetchAuditLogs(selectedRevisionId)}
                  disabled={auditFetching}
                  className="rounded bg-primary cursor-pointer px-4 py-2 text-sm font-medium text-white disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {auditFetching ? 'Loading…' : 'Refresh'}
                </button>
              )}
              {auditRows.length > 0 && <span className="text-xs text-text-base">{auditRows.length} events</span>}
            </>
          )}
          {activeTab === 'direct_substitutions' && (
            <>
              <label htmlFor="direct-sub-jurisdiction" className="text-xs text-text-base">Jurisdiction</label>
              <select
                id="direct-sub-jurisdiction"
                value={directSubJurisdictionId}
                onChange={(e) => setDirectSubJurisdictionId(e.target.value)}
                className="rounded border border-neutral-80 px-2 py-1 text-xs focus:outline-none focus:border-primary min-w-[10rem]"
              >
                <option value="">All</option>
                {auNzDirectSubJurOpts.map(j => (
                  <option key={j.id} value={j.id}>{j.name}</option>
                ))}
              </select>
              {!directSubFetching && directSubTotal > 0 && (
                <span className="text-xs text-text-base">
                  {directSubTotal} row{directSubTotal === 1 ? '' : 's'}
                </span>
              )}
            </>
          )}
{activeTab === 'electricity_recycling_assumptions' && (
            <>
              <label htmlFor="era-jurisdiction" className="text-xs text-text-base">Jurisdiction</label>
              <select
                id="era-jurisdiction"
                value={eraJurisdictionId}
                onChange={(e) => setEraJurisdictionId(e.target.value)}
                className="rounded border border-neutral-80 px-2 py-1 text-xs focus:outline-none focus:border-primary min-w-[10rem]"
              >
                <option value="">All</option>
                {auNzDirectSubJurOpts.map(j => (
                  <option key={j.id} value={j.id}>{j.name}</option>
                ))}
              </select>
              {!eraFetching && eraTotal > 0 && (
                <span className="text-xs text-text-base">
                  {eraTotal} row{eraTotal === 1 ? '' : 's'}
                </span>
              )}
            </>
          )}
          {activeTab !== 'audit' && (
            <div className="ml-auto">
              <DatasetBulkBar
                onDownload={() => {
                  if (activeTab === 'direct_substitutions') {
                    void downloadAllDirectSubstitutionsCsv();
                    return;
                  }
                  if (activeTab === 'electricity_recycling_assumptions') {
                    void downloadAllElectricityRecyclingAssumptionsCsv();
                    return;
                  }
                  downloadCsv(tabCsvCols, tabDownloadRows, tabFilename);
                }}
                onDownloadTemplate={() => downloadCsv(tabCsvCols, [], `${activeTab}_template.csv`, true)}
                onUpload={
                  activeTab !== 'factors'
                  && activeTab !== 'concrete_mix_designs'
                    ? () => setUploadTarget(activeTab)
                    : undefined
                }
                canEdit={canEditTab}
                loading={uploadRunning || (activeTab === 'direct_substitutions' && directSubExporting) || (activeTab === 'electricity_recycling_assumptions' && eraExporting)}
              />
            </div>
          )}
        </div>
      </div>

      {activeTab === 'factors' && activeGrade !== '' && !fetching && (
        <div className={`flex flex-wrap items-center gap-2 px-6 py-2 border-b border-neutral-90 ${hasActiveFilters ? 'bg-primary/5' : 'bg-white'}`}>
          <span className="text-xs font-medium text-text-base">Filters:</span>

          {activeGrade === '1' && g1Opts && (
            <>
              <MultiSelect
                label="Jurisdiction"
                options={g1Opts.jurisdictions}
                selected={g1Filter.jurisdictions}
                onChange={v => setG1Filter(p => ({ ...p, jurisdictions: v }))}
              />
              <SelectListbox
                placeholder="All Mastertypes"
                value={g1Filter.mastertype_id}
                onChange={(v) =>
                  setG1Filter(p => ({ ...p, mastertype_id: v, typecast_id: '' }))
                }
                options={mastertypeOpts.map((m: any) => ({
                  label: m.name,
                  value: m.id,
                }))}
                className="rounded-3 h-8!"
              />
              {/* <select
                value={g1Filter.typecast_id}
                onChange={e => setG1Filter(p => ({ ...p, typecast_id: e.target.value }))}
                className="rounded border border-neutral-80 px-2 py-1 text-xs focus:outline-none focus:border-primary"
              >
                <option value="">All Typecasts</option>
                {allTypecastsRaw
                  .filter(t => !g1Filter.mastertype_id || t.mastertype_id === g1Filter.mastertype_id)
                  .map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select> */}
              <SelectListbox 
                value={g1Filter.typecast_id}
                onChange={(v) => setG1Filter(p => ({ ...p, typecast_id: v }))}
                placeholder="All Typecasts"
                options={allTypecastsRaw
                  .filter(t => !g1Filter.mastertype_id || t.mastertype_id === g1Filter.mastertype_id)
                  .map(t => ({ label: t.name, value: t.id }))}
                className="rounded-3 h-8!"
              />
              <MultiSelect
                label="Metric"
                options={g1Opts.metrics}
                selected={g1Filter.metrics}
                onChange={v => setG1Filter(p => ({ ...p, metrics: v }))}
              />
              <MultiSelect
                label="Unit"
                options={g1Opts.units}
                selected={g1Filter.units}
                onChange={v => setG1Filter(p => ({ ...p, units: v }))}
              />
            </>
          )}

          {(activeGrade === '2' || activeGrade === '3') && g234Opts && (
            <>
              <MultiSelect
                label="Jurisdiction"
                options={g234Opts.jurisdictions}
                selected={g234Filter.jurisdictions}
                onChange={v => setG234Filter(p => ({ ...p, jurisdictions: v }))}
              />
              <MultiSelect
                label="Category"
                options={g234Opts.categories}
                selected={g234Filter.categories}
                onChange={handleCategoryChange}
              />
              <MultiSelect
                label="Sub-Category"
                options={g234Opts.subcategories}
                selected={g234Filter.subcategories}
                onChange={v => setG234Filter(p => ({ ...p, subcategories: v }))}
              />
              <TextFilter
                placeholder="Emissions Source"
                value={g234Filter.emissionsSource}
                onChange={v => setG234Filter(p => ({ ...p, emissionsSource: v }))}
              />
              <MultiSelect
                label="UoM"
                options={g234Opts.units}
                selected={g234Filter.units}
                onChange={v => setG234Filter(p => ({ ...p, units: v }))}
              />
            </>
          )}

          {hasActiveFilters && (
            <button
              type="button"
              onClick={() => { setG1Filter(INIT_G1); setG234Filter(INIT_G234); }}
              className="ml-auto cursor-pointer text-xs text-primary hover:underline"
            >
              Clear all filters
            </button>
          )}
        </div>
      )}

      {activeTab === 'recycled' && rcRows.length > 0 && (
            <div className={`flex flex-wrap items-center gap-2 px-6 py-2 border-b border-neutral-90 ${
              (rcFilter.material || rcFilter.jurisdictions.length > 0 || rcFilter.percentMin !== '' || rcFilter.percentMax !== '') ? 'bg-primary/5' : 'bg-white'
            }`}>
              <span className="text-xs font-medium text-text-base">Filters:</span>
              <TextFilter
                placeholder="Material"
                value={rcFilter.material}
                onChange={v => { setRcFilter(p => ({ ...p, material: v })); setRcPage(1); }}
              />
              <MultiSelect
                label="Jurisdiction"
                options={rcOpts.jurisdictions}
                selected={rcFilter.jurisdictions}
                onChange={v => { setRcFilter(p => ({ ...p, jurisdictions: v })); setRcPage(1); }}
              />
              <div className="flex items-center gap-1">
                <span className="text-xs text-text-base">% from</span>
                <input
                  type="number" min="0" max="100" step="1"
                  value={rcFilter.percentMin}
                  onChange={e => { setRcFilter(p => ({ ...p, percentMin: e.target.value })); setRcPage(1); }}
                  placeholder="0"
                  className="w-14 rounded border border-neutral-80 px-2 py-1.5 text-xs focus:outline-none focus:border-primary"
                />
                <span className="text-xs text-text-base">to</span>
                <input
                  type="number" min="0" max="100" step="1"
                  value={rcFilter.percentMax}
                  onChange={e => { setRcFilter(p => ({ ...p, percentMax: e.target.value })); setRcPage(1); }}
                  placeholder="100"
                  className="w-14 rounded border border-neutral-80 px-2 py-1.5 text-xs focus:outline-none focus:border-primary"
                />
              </div>
              {(rcFilter.material || rcFilter.jurisdictions.length > 0 || rcFilter.percentMin !== '' || rcFilter.percentMax !== '') && (
                <button type="button" onClick={() => { setRcFilter(INIT_RC); setRcPage(1); }}
                  className="ml-auto cursor-pointer text-xs text-primary hover:underline">Clear all filters</button>
              )}
              {canEditTab && !addingTab && !editingId && (
                <button type="button" onClick={() => doStartAdd('recycled')}
                  className="ml-auto  cursor-pointer rounded border border-primary px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10">+ Add Row</button>
              )}
            </div>
      )}
      {activeTab === 'transport' && trRows.length > 0 && (
            <div className={`flex flex-wrap items-center gap-2 px-6 py-2 border-b border-neutral-90 ${
              (trFilter.materialCategory || trFilter.jurisdictions.length > 0 || trFilter.transportMode !== '') ? 'bg-primary/5' : 'bg-white'
            }`}>
              <span className="text-xs font-medium text-text-base">Filters:</span>
              <TextFilter
                placeholder="Material / Category"
                value={trFilter.materialCategory}
                onChange={v => { setTrFilter(p => ({ ...p, materialCategory: v })); setTrPage(1); }}
              />
              <MultiSelect
                label="Jurisdiction"
                options={trOpts.jurisdictions}
                selected={trFilter.jurisdictions}
                onChange={v => { setTrFilter(p => ({ ...p, jurisdictions: v })); setTrPage(1); }}
              />
              <TextFilter
                placeholder="Transport mode"
                value={trFilter.transportMode}
                onChange={v => { setTrFilter(p => ({ ...p, transportMode: v })); setTrPage(1); }}
              />
              {(trFilter.materialCategory || trFilter.jurisdictions.length > 0 || trFilter.transportMode !== '') && (
                <button type="button" onClick={() => { setTrFilter(INIT_TR); setTrPage(1); }}
                  className="ml-auto cursor-pointer text-xs text-primary hover:underline">Clear all filters</button>
              )}
              {canEditTab && !addingTab && !editingId && (
                <button type="button" onClick={() => doStartAdd('transport')}
                  className="ml-auto cursor-pointer rounded border border-primary px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10">+ Add Row</button>
              )}
            </div>
      )}

      {activeTab === 'waste' && canEditTab && !addingTab && !editingId && (
        <div className="flex items-center gap-2 px-6 py-2 border-b border-neutral-90 bg-white">
          <button type="button" onClick={() => doStartAdd('waste')}
            className="cursor-pointer rounded border border-primary px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10">+ Add Row</button>
        </div>
      )}

      {activeTab === 'vehicle_masses' && canEditTab && !vmEditingId && (
        <div className="flex items-center gap-2 px-6 py-2 border-b border-neutral-90 bg-white">
          {!vmAdding && (
            <button type="button" onClick={() => { setVmAdding(true); setVmAddDraft({}); setVmSaveError(''); }}
              className="rounded cursor-pointer border border-primary px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10">+ Add Row</button>
          )}
        </div>
      )}

      {activeTab === 'interrupted_vehicles' && canEditTab && !ivEditingId && (
        <div className="flex items-center gap-2 px-6 py-2 border-b border-neutral-90 bg-white">
          {!ivAdding && (
            <button type="button" onClick={() => { setIvAdding(true); setIvAddDraft({}); setIvSaveError(''); }}
              className="cursor-pointer rounded border border-primary px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10">+ Add Row</button>
          )}
        </div>
      )}

      {activeTab === 'uninterrupted_vehicles' && canEditTab && !uvEditingId && (
        <div className="flex items-center gap-2 px-6 py-2 border-b border-neutral-90 bg-white">
          {!uvAdding && (
            <button type="button" onClick={() => { setUvAdding(true); setUvAddDraft({}); setUvSaveError(''); }}
              className="cursor-pointer rounded border border-primary px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10">+ Add Row</button>
          )}
        </div>
      )}

      {activeTab === 'vehicle_energy' && canEditTab && !veEditingId && (
        <div className="flex items-center gap-2 px-6 py-2 border-b border-neutral-90 bg-white">
          {!veAdding && (
            <button type="button" onClick={() => { setVeAdding(true); setVeAddDraft({}); setVeSaveError(''); }}
              className="cursor-pointer rounded border border-primary px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10">+ Add Row</button>
          )}
        </div>
      )}

      {activeTab === 'decarb' && (
        <div className="border-b border-neutral-90">
          <div className="flex items-center gap-1 px-4 py-2 bg-neutral-90/40 flex-wrap">
            {DECARB_FT_OPTS.map(opt => (
              <button
                key={opt.code}
                type="button"
                onClick={() => {
                  setDecarbActiveFt(opt.code);
                  setDecarbFilter(INIT_DECARB);
                  setDecarbAdding(false);
                  setDecarbEditCellId(null);
                  setDecarbCellError('');
                }}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors cursor-pointer ${
                  decarbActiveFt === opt.code
                    ? 'bg-primary text-white'
                    : 'bg-white text-text-base hover:bg-neutral-200 border border-neutral-80'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {decarbRows.length > 0 && (
            <div className={`flex flex-wrap items-center gap-2 px-6 py-2 ${
              decarbFilter.jurisdictions.length > 0 ? 'bg-primary/5' : 'bg-white'
            }`}>
              <label className="text-xs text-text-base">Year:</label>
              <input
                type="number" min={2026} max={2100}
                value={decarbYearFrom}
                onChange={e => setDecarbYearFrom(Number(e.target.value))}
                className="w-16 rounded border border-neutral-80 px-2 py-1 text-xs focus:outline-none focus:border-primary"
              />
              <span className="text-xs text-text-base">–</span>
              <input
                type="number" min={2026} max={2100}
                value={decarbYearTo}
                onChange={e => setDecarbYearTo(Number(e.target.value))}
                className="w-16 rounded border border-neutral-80 px-2 py-1 text-xs focus:outline-none focus:border-primary"
              />
              <MultiSelect
                label="Jurisdiction"
                options={decarbOpts.jurisdictions}
                selected={decarbFilter.jurisdictions}
                onChange={v => setDecarbFilter(p => ({ ...p, jurisdictions: v }))}
              />
              {decarbFilter.jurisdictions.length > 0 && (
                <button type="button" onClick={() => setDecarbFilter(INIT_DECARB)}
                  className="text-xs text-primary cursor-pointer hover:underline">Clear filters</button>
              )}
              <span className="text-xs text-text-base ml-auto">{decarbFiltered.length} rows</span>
              {canEditTab && !decarbRevisionLocked && !decarbAdding && !decarbEditCellId && (
                <button
                  type="button"
                  onClick={() => { setDecarbAdding(true); setDecarbSeriesDraft({ jurisdictionId: '', regionId: '' }); setDecarbAddError(''); }}
                  className=" cursor-pointer rounded border border-primary px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10"
                >
                  + Add Series
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'carbon_values' && selectedRevisionId && (
        <div className="border-b border-neutral-90 bg-white">
          {cvRows.length > 0 && (
            <div className={`flex flex-wrap items-center gap-2 px-6 py-2 ${
              cvFilter.jurisdictions.length > 0 || cvFilter.rangeCodes.length > 0
                ? 'bg-primary/5' : 'bg-white'
            }`}>
              <label className="text-xs text-text-base">Year:</label>
              <input
                type="number" min={2025} max={2100}
                value={cvYearFrom}
                onChange={e => setCvYearFrom(Number(e.target.value))}
                className="w-16 rounded border border-neutral-80 px-2 py-1 text-xs focus:outline-none focus:border-primary"
              />
              <span className="text-xs text-text-base">–</span>
              <input
                type="number" min={2025} max={2100}
                value={cvYearTo}
                onChange={e => setCvYearTo(Number(e.target.value))}
                className="w-16 rounded border border-neutral-80 px-2 py-1 text-xs focus:outline-none focus:border-primary"
              />
              <MultiSelect
                label="Jurisdiction"
                options={cvOpts.jurisdictions}
                selected={cvFilter.jurisdictions}
                onChange={v => setCvFilter(p => ({ ...p, jurisdictions: v }))}
              />
              <MultiSelect
                label="Range"
                options={cvOpts.ranges}
                selected={cvFilter.rangeCodes}
                onChange={v => setCvFilter(p => ({ ...p, rangeCodes: v }))}
              />
              {(cvFilter.jurisdictions.length > 0 || cvFilter.rangeCodes.length > 0) && (
                <button type="button" onClick={() => setCvFilter(INIT_CARBON_VALUES)}
                  className="text-xs cursor-pointer text-primary hover:underline">Clear filters</button>
              )}
              {canEditTab && !cvAdding && !cvEditCellId && (
                <button
                  type="button"
                  onClick={() => { setCvAdding(true); setCvSeriesDraft({ jurisdictionId: '', rangeCode: '' }); setCvAddError(''); }}
                  className="rounded border cursor-pointer border-primary px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10"
                >
                  + Add Series
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'ev_uptake' && selectedRevisionId && (
        <div className="border-b border-neutral-90 bg-white">
          {evUptakeRows.length > 0 && (
            <div className={`flex flex-wrap items-center gap-2 px-6 py-2 ${
              evUptakeFilter.jurisdictions.length > 0 || evUptakeFilter.scenarioCodes.length > 0 ||
              evUptakeFilter.vehicleCategoryCodes.length > 0 || evUptakeFilter.energyTypeCodes.length > 0
                ? 'bg-primary/5' : 'bg-white'
            }`}>
              <label className="text-xs text-text-base">Year:</label>
              <input
                type="number" min={2026} max={2100}
                value={evUptakeYearFrom}
                onChange={e => setEvUptakeYearFrom(Number(e.target.value))}
                className="w-16 rounded border border-neutral-80 px-2 py-1 text-xs focus:outline-none focus:border-primary"
              />
              <span className="text-xs text-text-base">–</span>
              <input
                type="number" min={2026} max={2100}
                value={evUptakeYearTo}
                onChange={e => setEvUptakeYearTo(Number(e.target.value))}
                className="w-16 rounded border border-neutral-80 px-2 py-1 text-xs focus:outline-none focus:border-primary"
              />
              <MultiSelect
                label="Jurisdiction"
                options={evUptakeOpts.jurisdictions}
                selected={evUptakeFilter.jurisdictions}
                onChange={v => setEvUptakeFilter(p => ({ ...p, jurisdictions: v }))}
              />
              <MultiSelect
                label="Scenario"
                options={evUptakeOpts.scenarioCodes}
                selected={evUptakeFilter.scenarioCodes}
                onChange={v => setEvUptakeFilter(p => ({ ...p, scenarioCodes: v }))}
              />
              <MultiSelect
                label="Vehicle Category"
                options={evUptakeOpts.vehicleCategoryCodes}
                selected={evUptakeFilter.vehicleCategoryCodes}
                onChange={v => setEvUptakeFilter(p => ({ ...p, vehicleCategoryCodes: v }))}
              />
              <MultiSelect
                label="Energy Type"
                options={evUptakeOpts.energyTypeCodes}
                selected={evUptakeFilter.energyTypeCodes}
                onChange={v => setEvUptakeFilter(p => ({ ...p, energyTypeCodes: v }))}
              />
              {(evUptakeFilter.jurisdictions.length > 0 || evUptakeFilter.scenarioCodes.length > 0 ||
                evUptakeFilter.vehicleCategoryCodes.length > 0 || evUptakeFilter.energyTypeCodes.length > 0) && (
                <button type="button" onClick={() => setEvUptakeFilter(INIT_EV_UPTAKE)}
                  className="text-xs text-primary cursor-pointer hover:underline">Clear filters</button>
              )}
              <span className="text-xs text-text-base ml-auto">{evUptakeFiltered.length} rows</span>
              {canEditTab && !evUptakeRevisionLocked && !evUptakeAdding && !evUptakeEditCellId && (
                <button
                  type="button"
                  onClick={() => { setEvUptakeAdding(true); setEvUptakeSeriesDraft({ jurisdictionId: '', scenarioCode: '', vehicleCategoryCode: '', energyTypeCode: '' }); setEvUptakeAddError(''); }}
                  className="rounded cursor-pointer border border-primary px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10"
                >
                  + Add Series
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {activeTab === 'vepm' && selectedRevisionId && vepmRows.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 px-6 py-2 border-b border-neutral-90 bg-white">
          <label className="text-xs text-text-base">Filter year:</label>
          <input
            type="number"
            value={vepmYearFilter}
            onChange={e => setVepmYearFilter(e.target.value)}
            placeholder="e.g. 2030"
            className="w-24 rounded border border-neutral-80 px-2 py-1 text-xs focus:outline-none focus:border-primary"
          />
          {vepmYearFilter && (
            <button type="button" onClick={() => setVepmYearFilter('')}
              className="text-xs cursor-pointer text-primary hover:underline">Clear</button>
          )}
          <span className="text-xs text-text-base ml-auto">{vepmFiltered.length} rows</span>
        </div>
      )}

      {activeTab === 'factors' && activeGrade !== '' && !fetching && canEditTab && (
        <div className="flex items-center gap-2 px-6 py-2 border-b border-neutral-90 bg-white">
          {!bgmAdding && !bgmEditKey && (
            <button type="button" onClick={doStartBgmAdd}
              className="rounded  cursor-pointer border border-primary px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10">
              + Add Row
            </button>
          )}
          {bgmSaveError && !bgmAdding && !bgmEditKey && (
            <span className="text-xs text-red-600">{bgmSaveError}</span>
          )}
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden bg-bg-content">
        <div className="flex-1 overflow-auto">

          {activeTab === 'factors' && (
            fetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading dataset…
              </div>
            ) : fetchError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{fetchError}</div>
            ) : activeGrade === '' ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No datasets loaded</p>
                <p className="text-sm text-text-base">Select a version and grade, then click Fetch</p>
              </div>
            ) : (displayData as unknown[]).length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-sm font-medium text-text-dark">No rows match the current filters</p>
                <button type="button" onClick={() => { setG1Filter(INIT_G1); setG234Filter(INIT_G234); }}
                  className="text-xs cursor-pointer text-primary hover:underline mt-1">Clear filters</button>
              </div>
            ) : activeGrade === '1' ? (
              <Grade1Table rows={displayRows as unknown as G1Row[]} ec={canEditTab ? {
                unitOpts, metricTypeOpts, ecOpts, jurOpts,
                mastertypeOpts,
                typecasts: allTypecastsRaw,
                editKey: bgmEditKey,
                editDraft: bgmEditDraft,
                adding: bgmAdding,
                addDraft: bgmAddDraft,
                onStartEdit: doStartBgmEdit,
                onEditField: (f, v) => setBgmEditDraft(p => ({ ...p, [f]: v })),
                onSaveEdit: doSaveBgmEdit,
                onCancelEdit: doCancelBgmEdit,
                onAddField: (f, v) => setBgmAddDraft(p => ({ ...p, [f]: v })),
                onSaveAdd: doSaveBgmAdd,
                onCancelAdd: doCancelBgmAdd,
                saving: bgmSaving,
                saveError: bgmSaveError,
              } : undefined} />
            ) : activeGrade === '2' ? (
              <Grade2Table rows={displayRows as unknown as G2Row[]} ec={canEditTab ? {
                unitOpts, metricTypeOpts, ecOpts, jurOpts,
                mastertypeOpts,
                typecasts: allTypecastsRaw,
                editKey: bgmEditKey,
                editDraft: bgmEditDraft,
                adding: bgmAdding,
                addDraft: bgmAddDraft,
                onStartEdit: doStartBgmEdit,
                onEditField: (f, v) => setBgmEditDraft(p => ({ ...p, [f]: v })),
                onSaveEdit: doSaveBgmEdit,
                onCancelEdit: doCancelBgmEdit,
                onAddField: (f, v) => setBgmAddDraft(p => ({ ...p, [f]: v })),
                onSaveAdd: doSaveBgmAdd,
                onCancelAdd: doCancelBgmAdd,
                saving: bgmSaving,
                saveError: bgmSaveError,
              } : undefined} />
            ) : (
              <Grade34Table rows={displayRows as unknown as G34Row[]} ec={canEditTab ? {
                unitOpts, metricTypeOpts, ecOpts, jurOpts,
                mastertypeOpts,
                typecasts: allTypecastsRaw,
                editKey: bgmEditKey,
                editDraft: bgmEditDraft,
                adding: bgmAdding,
                addDraft: bgmAddDraft,
                onStartEdit: doStartBgmEdit,
                onEditField: (f, v) => setBgmEditDraft(p => ({ ...p, [f]: v })),
                onSaveEdit: doSaveBgmEdit,
                onCancelEdit: doCancelBgmEdit,
                onAddField: (f, v) => setBgmAddDraft(p => ({ ...p, [f]: v })),
                onSaveAdd: doSaveBgmAdd,
                onCancelAdd: doCancelBgmAdd,
                saving: bgmSaving,
                saveError: bgmSaveError,
              } : undefined} />
            )
          )}

          {activeTab === 'recycled' && (
            rcFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading…
              </div>
            ) : rcError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{rcError}</div>
            ) : rcRows.length === 0 && addingTab !== 'recycled' ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No recycled content data loaded</p>
                <p className="text-sm text-text-base">Optionally set an effective date, then click Load</p>
              </div>
            ) : rcFiltered.length === 0 && addingTab !== 'recycled' ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-sm font-medium text-text-dark">No rows match the current filters</p>
                <button type="button" onClick={() => { setRcFilter(INIT_RC); setRcPage(1); }}
                  className="text-xs cursor-pointer text-primary hover:underline mt-1">Clear filters</button>
              </div>
            ) : (
              <RecycledContentTable rows={rcDisplayRows} editCtx={canEditTab ? {
                matOpts, jurOpts, wtOpts, ecOpts,
                editingId, editDraft, adding: addingTab === 'recycled', addDraft,
                onStartEdit: doStartEdit,
                onEditField: (f, v) => setEditDraft(p => ({ ...p, [f]: v })),
                onSaveEdit: doSaveEdit, onCancelEdit: doCancelEdit,
                onAddField: (f, v) => setAddDraft(p => ({ ...p, [f]: v })),
                onSaveAdd: doSaveAdd, onCancelAdd: doCancelAdd,
                saving: savingOp, saveError,
                onDelete: doDeleteRecycledContent,
              } : undefined} />
            )
          )}

          {activeTab === 'transport' && (
            trFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading…
              </div>
            ) : trError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{trError}</div>
            ) : trRows.length === 0 && addingTab !== 'transport' ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No transport distance data loaded</p>
                <p className="text-sm text-text-base">Optionally set an effective date, then click Load</p>
              </div>
            ) : trFiltered.length === 0 && addingTab !== 'transport' ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-sm font-medium text-text-dark">No rows match the current filters</p>
                <button type="button" onClick={() => { setTrFilter(INIT_TR); setTrPage(1); }}
                  className="text-xs text-primary cursor-pointer hover:underline mt-1">Clear filters</button>
              </div>
            ) : (
              <TransportTable rows={trDisplayRows} editCtx={canEditTab ? {
                matOpts, jurOpts, wtOpts, ecOpts,
                editingId, editDraft, adding: addingTab === 'transport', addDraft,
                onStartEdit: doStartEdit,
                onEditField: (f, v) => setEditDraft(p => ({ ...p, [f]: v })),
                onSaveEdit: doSaveEdit, onCancelEdit: doCancelEdit,
                onAddField: (f, v) => setAddDraft(p => ({ ...p, [f]: v })),
                onSaveAdd: doSaveAdd, onCancelAdd: doCancelAdd,
                saving: savingOp, saveError,
                onDelete: doDeleteTransport,
              } : undefined} />
            )
          )}

          {activeTab === 'waste' && (
            wrFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading…
              </div>
            ) : wrError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{wrError}</div>
            ) : wrRows.length === 0 && addingTab !== 'waste' ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No waste rate data loaded</p>
                <p className="text-sm text-text-base">Optionally set an effective date, then click Load</p>
              </div>
            ) : (
              <WasteRateTable rows={wrRows} editCtx={canEditTab ? {
                matOpts, jurOpts, wtOpts, ecOpts,
                editingId, editDraft, adding: addingTab === 'waste', addDraft,
                onStartEdit: doStartEdit,
                onEditField: (f, v) => setEditDraft(p => ({ ...p, [f]: v })),
                onSaveEdit: doSaveEdit, onCancelEdit: doCancelEdit,
                onAddField: (f, v) => setAddDraft(p => ({ ...p, [f]: v })),
                onSaveAdd: doSaveAdd, onCancelAdd: doCancelAdd,
                saving: savingOp, saveError,
                onDelete: doDeleteWasteRate,
              } : undefined} />
            )
          )}

          {activeTab === 'audit' && (
            auditFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading…
              </div>
            ) : auditError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{auditError}</div>
            ) : !selectedRevisionId ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">Select a dataset revision</p>
                <p className="text-sm text-text-base">The audit trail will load automatically</p>
              </div>
            ) : auditRows.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No audit events found for this revision</p>
              </div>
            ) : (
              <AuditTrailTable rows={auditRows} />
            )
          )}

          {activeTab === 'decarb' && (
            decarbFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading…
              </div>
            ) : decarbError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{decarbError}</div>
            ) : !selectedRevisionId ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">Select a dataset revision</p>
                <p className="text-sm text-text-base">The electricity decarbonisation factors will load automatically</p>
              </div>
            ) : decarbRows.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No electricity decarbonisation factors for this revision</p>
              </div>
            ) : decarbFiltered.length === 0 && !decarbAdding ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-sm font-medium text-text-dark">No rows match the current filters</p>
                <button type="button" onClick={() => setDecarbFilter(INIT_DECARB)}
                  className="text-xs text-primary cursor-pointer hover:underline mt-1">Clear filters</button>
              </div>
            ) : (
              <ElectricDecarbTable
                rows={decarbFiltered}
                yearFrom={decarbYearFrom}
                yearTo={decarbYearTo}
                editCtx={canEditTab ? {
                  editCellId: decarbEditCellId,
                  cellDraft: decarbCellDraft,
                  adding: decarbAdding,
                  addDraft: decarbSeriesDraft,
                  jurOpts: decarbOpts.jurOpts,
                  allRegions: decarbOpts.allRegions,
                  activeFtHasRegion,
                  onEditCell: (rowId) => {
                    const row = decarbRows.find(r => r.id === rowId);
                    if (!row) return;
                    let init = '';
                    if (row.value_qualifier === 'D') init = 'D';
                    else if (row.value != null) init = row.unit?.code === '%' ? (row.value * 100).toFixed(2) : String(row.value);
                    setDecarbEditCellId(rowId);
                    setDecarbCellDraft(init);
                    setDecarbCellError('');
                  },
                  onCellChange: setDecarbCellDraft,
                  onSaveCell: doSaveDecarbCell,
                  onCancelCell: () => { setDecarbEditCellId(null); setDecarbCellDraft(''); setDecarbCellError(''); },
                  onAddField: (f, v) => setDecarbSeriesDraft(prev => ({ ...prev, [f]: v })),
                  onSaveAdd: doAddDecarbSeries,
                  onCancelAdd: () => { setDecarbAdding(false); setDecarbSeriesDraft({ jurisdictionId: '', regionId: '' }); setDecarbAddError(''); },
                  saving: decarbCellSaving || decarbAddSaving,
                  saveError: decarbCellError || decarbAddError,
                } : undefined}
              />
            )
          )}

          {activeTab === 'carbon_values' && (
            cvFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading…
              </div>
            ) : cvError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{cvError}</div>
            ) : !selectedRevisionId ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">Select a dataset revision</p>
                <p className="text-sm text-text-base">The carbon values will load automatically</p>
              </div>
            ) : cvRows.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No carbon values for this revision</p>
              </div>
            ) : cvFiltered.length === 0 && !cvAdding ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-sm font-medium text-text-dark">No rows match the current filters</p>
                <button type="button" onClick={() => setCvFilter(INIT_CARBON_VALUES)}
                  className="text-xs cursor-pointer text-primary hover:underline mt-1">Clear filters</button>
              </div>
            ) : (
              <CarbonValuesTable
                rows={cvFiltered}
                yearFrom={cvYearFrom}
                yearTo={cvYearTo}
                editCtx={canEditTab ? {
                  editCellId: cvEditCellId,
                  cellDraft: cvCellDraft,
                  adding: cvAdding,
                  addDraft: cvSeriesDraft,
                  jurOpts: cvOpts.jurOpts,
                  rangeOpts: cvOpts.rangeOpts,
                  onEditCell: (rowId) => {
                    const row = cvRows.find(r => r.id === rowId);
                    if (!row) return;
                    setCvEditCellId(rowId);
                    setCvCellDraft(row.value?.toString() ?? '');
                    setCvCellError('');
                  },
                  onCellChange: setCvCellDraft,
                  onSaveCell: doSaveCvCell,
                  onCancelCell: () => { setCvEditCellId(null); setCvCellDraft(''); setCvCellError(''); },
                  onAddField: (f, v) => setCvSeriesDraft(prev => ({ ...prev, [f]: v })),
                  onSaveAdd: doAddCvSeries,
                  onCancelAdd: () => { setCvAdding(false); setCvSeriesDraft({ jurisdictionId: '', rangeCode: '' }); setCvAddError(''); },
                  saving: cvCellSaving || cvAddSaving,
                  saveError: cvCellError || cvAddError,
                } : undefined}
              />
            )
          )}

          {activeTab === 'ev_uptake' && (
            evUptakeFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading EV uptake data…
              </div>
            ) : evUptakeError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{evUptakeError}</div>
            ) : !selectedRevisionId ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No revision selected</p>
                <p className="text-sm text-text-base">Select a dataset revision above</p>
              </div>
            ) : evUptakeFiltered.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-sm font-medium text-text-dark">No data found</p>
                {(evUptakeFilter.jurisdictions.length > 0 || evUptakeFilter.scenarioCodes.length > 0 ||
                  evUptakeFilter.vehicleCategoryCodes.length > 0 || evUptakeFilter.energyTypeCodes.length > 0) && (
                  <button type="button" onClick={() => setEvUptakeFilter(INIT_EV_UPTAKE)}
                    className="text-xs cursor-pointer text-primary hover:underline mt-1">Clear filters</button>
                )}
              </div>
            ) : (
              <EvUptakeTable
                rows={evUptakeFiltered}
                yearFrom={evUptakeYearFrom}
                yearTo={evUptakeYearTo}
                editCtx={canEditTab ? {
                  editCellId: evUptakeEditCellId,
                  cellDraft:  evUptakeCellDraft,
                  adding:     evUptakeAdding,
                  addDraft:   evUptakeSeriesDraft,
                  jurOpts: evUptakeOpts.jurOpts,
                  scenarioOpts: evUptakeOpts.scenarioCodes.map(code => ({ id: code, name: code })),
                  vehicleCategoryOpts: evUptakeOpts.vehicleCategoryCodes.map(code => ({ id: code, name: code })),
                  energyTypeOpts: evUptakeOpts.energyTypeCodes.map(code => ({ id: code, name: code })),
                  onEditCell: (rowId) => {
                    const row = evUptakeRows.find(r => r.id === rowId);
                    if (!row) return;
                    const init = row.uptake_pct != null ? (row.uptake_pct * 100).toFixed(4) : '';
                    setEvUptakeEditCellId(rowId);
                    setEvUptakeCellDraft(init);
                    setEvUptakeCellError('');
                  },
                  onCellChange: setEvUptakeCellDraft,
                  onSaveCell:   doSaveEvUptakeCell,
                  onCancelCell: () => { setEvUptakeEditCellId(null); setEvUptakeCellDraft(''); setEvUptakeCellError(''); },
                  onAddField: (f, v) => setEvUptakeSeriesDraft(prev => ({ ...prev, [f]: v })),
                  onSaveAdd:    doAddEvUptakeSeries,
                  onCancelAdd:  () => { setEvUptakeAdding(false); setEvUptakeSeriesDraft({ jurisdictionId: '', scenarioCode: '', vehicleCategoryCode: '', energyTypeCode: '' }); setEvUptakeAddError(''); },
                  saving:    evUptakeCellSaving || evUptakeAddSaving,
                  saveError: evUptakeCellError || evUptakeAddError,
                } : undefined}
              />
            )
          )}

          {activeTab === 'vepm' && (
            vepmFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading VEPM data…
              </div>
            ) : vepmError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{vepmError}</div>
            ) : !selectedRevisionId ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No revision selected</p>
                <p className="text-sm text-text-base">Select a dataset revision above</p>
              </div>
            ) : (
              <VepmTable
                rows={vepmFiltered}
                editCtx={canEditTab ? {
                  editingId: vepmEditingId,
                  editDraft: vepmEditDraft,
                  onStartEdit: (id, draft) => { setVepmEditingId(id); setVepmEditDraft(draft); setVepmSaveError(''); },
                  onEditField: (f, v) => setVepmEditDraft(prev => ({ ...prev, [f]: v })),
                  onSaveEdit:   doSaveVepmRow,
                  onCancelEdit: () => { setVepmEditingId(null); setVepmEditDraft({}); setVepmSaveError(''); },
                  saving:    vepmSaving,
                  saveError: vepmSaveError,
                  onDelete: doDeleteVepm,
                } : undefined}
              />
            )
          )}

          {activeTab === 'freight_rail' && (
            frFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading freight rail data…
              </div>
            ) : frError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{frError}</div>
            ) : !selectedRevisionId ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No revision selected</p>
                <p className="text-sm text-text-base">Select a dataset revision above</p>
              </div>
            ) : (
              <FreightRailTable
                rows={frRows}
                editCtx={canEditTab ? {
                  editingId: frEditingId,
                  editDraft: frEditDraft,
                  onStartEdit: (id, draft) => { setFrEditingId(id); setFrEditDraft(draft); setFrSaveError(''); },
                  onEditField: (f, v) => setFrEditDraft(prev => ({ ...prev, [f]: v })),
                  onSaveEdit:   doSaveFrRow,
                  onCancelEdit: () => { setFrEditingId(null); setFrEditDraft({}); setFrSaveError(''); },
                  saving:    frSaving,
                  saveError: frSaveError,
                  onDelete: doDeleteFreightRail,
                } : undefined}
              />
            )
          )}

          {activeTab === 'maintenance_replacement' && (
            mrFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Loading maintenance &amp; replacement data…
              </div>
            ) : mrError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{mrError}</div>
            ) : !selectedRevisionId ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No revision selected</p>
                <p className="text-sm text-text-base">Select a dataset revision above</p>
              </div>
            ) : (
              <MaintenanceReplacementTable
                rows={mrRows}
                editCtx={canEditTab ? {
                  editingId: mrEditingId,
                  editDraft: mrEditDraft,
                  onStartEdit: (id, draft) => { setMrEditingId(id); setMrEditDraft(draft); setMrSaveError(''); },
                  onEditField: (f, v) => setMrEditDraft(prev => ({ ...prev, [f]: v })),
                  onSaveEdit:   doSaveMrRow,
                  onCancelEdit: () => { setMrEditingId(null); setMrEditDraft({}); setMrSaveError(''); },
                  saving:    mrSaving,
                  saveError: mrSaveError,
                  onDelete: doDeleteMaintenanceReplacement,
                } : undefined}
              />
            )
          )}

          {activeTab === 'densities' && (
            densityFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading densities...</span>
              </div>
            ) : densityError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{densityError}</div>
            ) : !selectedRevisionId ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No revision selected</p>
                <p className="text-sm text-text-base">Select a dataset revision above</p>
              </div>
            ) : (
              <>
                <div className="mb-2 flex gap-2 flex-wrap">
                  <MultiSelect
                    label="Jurisdiction"
                    options={Array.from(new Set(densityData.map(r => r.jurisdiction?.name).filter(Boolean))).sort() as string[]}
                    selected={densityFilter.jurisdictions}
                    onChange={(sel) => setDensityFilter(prev => ({ ...prev, jurisdictions: sel }))}
                  />
                  <MultiSelect
                    label="Dataset"
                    options={['Component Level', 'Detailed Level']}
                    selected={densityFilter.datasets.map(d => d === 'component' ? 'Component Level' : 'Detailed Level')}
                    onChange={(sel) => {
                      const codes = sel.map(s => s === 'Component Level' ? 'component' : 'detailed') as ('component' | 'detailed')[];
                      setDensityFilter(prev => ({ ...prev, datasets: codes }));
                    }}
                  />
                  <MultiSelect
                    label="Category"
                    options={Array.from(new Set(densityFiltered.map(r => r.emissions_category?.name).filter(Boolean))).sort() as string[]}
                    selected={densityFilter.categories}
                    onChange={(sel) => setDensityFilter(prev => ({ ...prev, categories: sel }))}
                  />
                  <MultiSelect
                    label="Sub-Category"
                    options={Array.from(new Set(densityFiltered.map(r => r.emissions_sub_category?.name).filter(Boolean))).sort() as string[]}
                    selected={densityFilter.subcategories}
                    onChange={(sel) => setDensityFilter(prev => ({ ...prev, subcategories: sel }))}
                  />
                  <MultiSelect
                    label="Unit"
                    options={Array.from(new Set(densityFiltered.map(r => r.unit?.code).filter(Boolean))).sort() as string[]}
                    selected={densityFilter.units}
                    onChange={(sel) => setDensityFilter(prev => ({ ...prev, units: sel }))}
                  />
                  <TextFilter
                    placeholder="Emissions Source"
                    value={densityFilter.emissionsSource}
                    onChange={(val) => setDensityFilter(prev => ({ ...prev, emissionsSource: val }))}
                  />
                  {(densityFilter.jurisdictions.length > 0 || densityFilter.datasets.length > 0 || densityFilter.categories.length > 0 || densityFilter.subcategories.length > 0 || densityFilter.emissionsSource.trim() || densityFilter.units.length > 0) && (
                    <button type="button" onClick={() => setDensityFilter(INIT_DENSITY)} className="text-xs text-primary cursor-pointer hover:underline mt-1">Clear filters</button>
                  )}
                </div>
                <DensitiesTable
                  rows={densityFiltered}
                  editCtx={canEditTab ? {
                    editingId: densityEditingId,
                    editDraft: densityEditDraft,
                    onStartEdit: (id, draft) => { setDensityEditingId(id); setDensityEditDraft(draft); setDensitySaveError(''); },
                    onEditField: (f, v) => setDensityEditDraft(prev => ({ ...prev, [f]: v })),
                    onSaveEdit: doSaveDensityRow,
                    onCancelEdit: () => { setDensityEditingId(null); setDensityEditDraft({}); setDensitySaveError(''); },
                    saving: densitySaving,
                    saveError: densitySaveError,
                    onDelete: doDeleteDensity,
                  } : undefined}
                />
              </>
            )
          )}

          {activeTab === 'unit_conversions' && (
            ucFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading unit conversions...</span>
              </div>
            ) : ucError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{ucError}</div>
            ) : (
              <UnitConversionsTable
                rows={ucRows}
                editCtx={canEditTab ? {
                  editingId: ucEditingId,
                  editDraft: ucEditDraft,
                  onStartEdit: (id, draft) => { setUcEditingId(id); setUcEditDraft(draft); setUcSaveError(''); },
                  onEditField: (f, v) => setUcEditDraft(prev => ({ ...prev, [f]: v })),
                  onSaveEdit: doSaveUcRow,
                  onCancelEdit: () => { setUcEditingId(null); setUcEditDraft({}); setUcSaveError(''); },
                  saving: ucSaving,
                  saveError: ucSaveError,
                  onDelete: doDeleteUnitConversion,
                } : undefined}
              />
            )
          )}

          {activeTab === 'fugitives' && (
            fcFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading fugitives...</span>
              </div>
            ) : fcError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{fcError}</div>
            ) : (
              <>
                <div className="mb-2 flex gap-2 flex-wrap">
                  <MultiSelect
                    label="Jurisdiction"
                    options={Array.from(new Set(fcRows.map(r => r.jurisdiction?.name).filter(Boolean))).sort() as string[]}
                    selected={fcFilter.jurisdictions}
                    onChange={(sel) => setFcFilter(prev => ({ ...prev, jurisdictions: sel }))}
                  />
                  {fcFilter.jurisdictions.length > 0 && (
                    <button type="button" onClick={() => setFcFilter(INIT_FUGITIVE)} className="text-xs text-primary cursor-pointer hover:underline mt-1">Clear filters</button>
                  )}
                </div>
                <FugitivesTable
                  rows={fcFiltered}
                  editCtx={canEditTab ? {
                    editingId: fcEditingId,
                    editDraft: fcEditDraft,
                    onStartEdit: (id, draft) => { setFcEditingId(id); setFcEditDraft(draft); setFcSaveError(''); },
                    onEditField: (f, v) => setFcEditDraft(prev => ({ ...prev, [f]: v })),
                    onSaveEdit: doSaveFugitiveRow,
                    onCancelEdit: () => { setFcEditingId(null); setFcEditDraft({}); setFcSaveError(''); },
                    saving: fcSaving,
                    saveError: fcSaveError,
                    onDelete: doDeleteFugitive,
                  } : undefined}
                />
              </>
            )
          )}

          {activeTab === 'energy_density_conversions' && (
            edcFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading energy density conversions...</span>
              </div>
            ) : edcError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{edcError}</div>
            ) : (
              <EnergyDensityConversionsTable
                rows={edcRows}
                editCtx={canEditTab ? {
                  editingId: edcEditingId,
                  editDraft: edcEditDraft,
                  onStartEdit: (id, draft) => { setEdcEditingId(id); setEdcEditDraft(draft); setEdcSaveError(''); },
                  onEditField: (f, v) => setEdcEditDraft(prev => ({ ...prev, [f]: v })),
                  onSaveEdit: doSaveEnergyDensityConversionRow,
                  onCancelEdit: () => { setEdcEditingId(null); setEdcEditDraft({}); setEdcSaveError(''); },
                  saving: edcSaving,
                  saveError: edcSaveError,
                  onDelete: doDeleteEnergyDensityConversion,
                } : undefined}
              />
            )
          )}

          {activeTab === 'wastage_rates' && (
            wgFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading wastage rates...</span>
              </div>
            ) : wgError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{wgError}</div>
            ) : !selectedRevisionId ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No revision selected</p>
                <p className="text-sm text-text-base">Select a dataset revision above</p>
              </div>
            ) : (
              <>
                <div className="mb-2 flex gap-2 flex-wrap">
                  <MultiSelect
                    label="Jurisdiction"
                    options={Array.from(new Set(wgRows.map(r => r.jurisdiction?.name).filter(Boolean))).sort() as string[]}
                    selected={wgFilter.jurisdictions}
                    onChange={(sel) => setWgFilter(prev => ({ ...prev, jurisdictions: sel }))}
                  />
                  <MultiSelect
                    label="Material"
                    options={Array.from(new Set(wgFiltered.map(r => r.material?.name).filter(Boolean))).sort() as string[]}
                    selected={wgFilter.materials}
                    onChange={(sel) => setWgFilter(prev => ({ ...prev, materials: sel }))}
                  />
                  {(wgFilter.jurisdictions.length > 0 || wgFilter.materials.length > 0) && (
                    <button type="button" onClick={() => setWgFilter(INIT_WASTAGE_RATES)} className="text-xs text-primary cursor-pointer hover:underline mt-1">Clear filters</button>
                  )}
                </div>
                <WastageRatesTable
                  rows={wgFiltered}
                  editCtx={canEditTab ? {
                    editingId: wgEditingId,
                    editDraft: wgEditDraft,
                    onStartEdit: (id, draft) => { setWgEditingId(id); setWgEditDraft(draft); setWgSaveError(''); },
                    onEditField: (f, v) => setWgEditDraft(prev => ({ ...prev, [f]: v })),
                    onSaveEdit: doSaveWastageRateRow,
                    onCancelEdit: () => { setWgEditingId(null); setWgEditDraft({}); setWgSaveError(''); },
                    saving: wgSaving,
                    saveError: wgSaveError,
                    onDelete: doDeleteWastageRate,
                  } : undefined}
                />
              </>
            )
          )}

          {activeTab === 'renewable_energy' && (
            recFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading renewable energy classifications...</span>
              </div>
            ) : recError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{recError}</div>
            ) : !selectedRevisionId ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No revision selected</p>
                <p className="text-sm text-text-base">Select a dataset revision above</p>
              </div>
            ) : (
              <RenewableEnergyTable
                rows={recRows}
                editCtx={canEditTab ? {
                  editingId: recEditingId,
                  editDraft: recEditDraft,
                  onStartEdit: (id, draft) => { setRecEditingId(id); setRecEditDraft(draft); setRecSaveError(''); },
                  onEditField: (f, v) => setRecEditDraft(prev => ({ ...prev, [f]: v })),
                  onSaveEdit: doSaveRenewableEnergyRow,
                  onCancelEdit: () => { setRecEditingId(null); setRecEditDraft({}); setRecSaveError(''); },
                  saving: recSaving,
                  saveError: recSaveError,
                  onDelete: doDeleteRenewableEnergy,
                } : undefined}
              />
            )
          )}

{activeTab === 'content_recycled' && (
            crfFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading content recycled...</span>
              </div>
            ) : crfError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{crfError}</div>
            ) : !selectedRevisionId ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No revision selected</p>
                <p className="text-sm text-text-base">Select a dataset revision above</p>
              </div>
            ) : (
              <>
                <div className="mb-2 flex gap-2 flex-wrap items-center">
                  <MultiSelect
                    label="Jurisdiction"
                    options={crfJurOptions}
                    selected={crfFilter.jurisdictions}
                    onChange={(sel) => setCrfFilter(prev => ({ ...prev, jurisdictions: sel }))}
                  />
                  {crfFilter.jurisdictions.length > 0 && crfFilter.jurisdictions.length < crfJurOptions.length && (
                    <button
                      type="button"
                      onClick={() => setCrfFilter({ jurisdictions: crfJurOptions })}
                      className="text-xs text-primary hover:underline mt-1 cursor-pointer"
                    >
                      Select all jurisdictions
                    </button>
                  )}
                  {canEditTab && !crfAdding && !crfEditCellKey && (
                    <button
                      type="button"
                      onClick={() => {
                        setCrfAdding(true);
                        const draft: Record<string, string> = {};
                        if (crfFilter.jurisdictions.length === 1) {
                          const j = jurOpts.find(x => x.name === crfFilter.jurisdictions[0]);
                          if (j) draft.jurisdiction_id = j.id;
                        }
                        setCrfAddDraft(draft);
                        setCrfSaveError('');
                      }}
                      className="ml-auto cursor-pointer rounded border border-primary px-3 py-1 text-xs font-medium text-primary hover:bg-primary/10"
                    >
                      + Add Row
                    </button>
                  )}
                </div>
                <ContentRecycledTable
                  rows={crfFiltered}
                  editCtx={canEditTab ? {
                    editCellKey: crfEditCellKey,
                    cellDraft: crfCellDraft,
                    adding: crfAdding,
                    addDraft: crfAddDraft,
                    jurOpts,
                    catOpts: ecOpts,
                    onEditCell: (rowId, field, initial) => {
                      setCrfEditCellKey(`${rowId}::${field}`);
                      setCrfCellDraft(initial);
                      setCrfSaveError('');
                    },
                    onCellChange: setCrfCellDraft,
                    onSaveCell: doSaveContentRecycledCell,
                    onCancelCell: () => { setCrfEditCellKey(null); setCrfCellDraft(''); setCrfSaveError(''); },
                    onStartAdd: () => { setCrfAdding(true); setCrfAddDraft({}); setCrfSaveError(''); },
                    onAddField: (f, v) => setCrfAddDraft(prev => ({ ...prev, [f]: v })),
                    onSaveAdd: doAddContentRecycled,
                    onCancelAdd: () => { setCrfAdding(false); setCrfAddDraft({}); setCrfSaveError(''); },
                    saving: crfSaving,
                    saveError: crfSaveError,
                    onDelete: doDeleteContentRecycled,
                  } : undefined}
                />
              </>
            )
          )}

          {activeTab === 'vehicle_masses' && (
            vmFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading vehicle masses...</span>
              </div>
            ) : vmError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{vmError}</div>
            ) : (
              <VehicleMassesTable
                rows={vmRows}
                editCtx={canEditTab ? {
                  editingId: vmEditingId,
                  editDraft: vmEditDraft,
                  adding: vmAdding,
                  addDraft: vmAddDraft,
                  vehicleClassOpts,
                  onStartEdit: (id, draft) => { setVmEditingId(id); setVmEditDraft(draft); setVmSaveError(''); },
                  onEditField: (f, v) => setVmEditDraft(prev => ({ ...prev, [f]: v })),
                  onSaveEdit: doSaveVmEdit,
                  onCancelEdit: () => { setVmEditingId(null); setVmEditDraft({}); setVmSaveError(''); },
                  onStartAdd: () => { setVmAdding(true); setVmAddDraft({}); setVmSaveError(''); },
                  onAddField: (f, v) => setVmAddDraft(prev => ({ ...prev, [f]: v })),
                  onSaveAdd: doAddVm,
                  onCancelAdd: () => { setVmAdding(false); setVmAddDraft({}); setVmSaveError(''); },
                  saving: vmSaving,
                  saveError: vmSaveError,
                  onDelete: doDeleteVehicleMass,
                } : undefined}
              />
            )
          )}

          {activeTab === 'interrupted_vehicles' && (
            ivFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading fuel use variables - stop-start...</span>
              </div>
            ) : ivError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{ivError}</div>
            ) : (
              <InterruptedVehiclesTable
                rows={ivRows}
                editCtx={canEditTab ? {
                  editingId: ivEditingId,
                  editDraft: ivEditDraft,
                  adding: ivAdding,
                  addDraft: ivAddDraft,
                  vehicleClassOpts,
                  onStartEdit: (id, draft) => { setIvEditingId(id); setIvEditDraft(draft); setIvSaveError(''); },
                  onEditField: (f, v) => setIvEditDraft(prev => ({ ...prev, [f]: v })),
                  onSaveEdit: doSaveIvEdit,
                  onCancelEdit: () => { setIvEditingId(null); setIvEditDraft({}); setIvSaveError(''); },
                  onStartAdd: () => { setIvAdding(true); setIvAddDraft({}); setIvSaveError(''); },
                  onAddField: (f, v) => setIvAddDraft(prev => ({ ...prev, [f]: v })),
                  onSaveAdd: doAddIv,
                  onCancelAdd: () => { setIvAdding(false); setIvAddDraft({}); setIvSaveError(''); },
                  saving: ivSaving,
                  saveError: ivSaveError,
                  onDelete: doDeleteInterruptedVehicle,
                } : undefined}
              />
            )
          )}

          {activeTab === 'uninterrupted_vehicles' && (
            uvFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading fuel use variables - free flow...</span>
              </div>
            ) : uvError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{uvError}</div>
            ) : (
              <UninterruptedVehiclesTable
                rows={uvRows}
                editCtx={canEditTab ? {
                  editingId: uvEditingId,
                  editDraft: uvEditDraft,
                  adding: uvAdding,
                  addDraft: uvAddDraft,
                  vehicleClassOpts,
                  onStartEdit: (id, draft) => { setUvEditingId(id); setUvEditDraft(draft); setUvSaveError(''); },
                  onEditField: (f, v) => setUvEditDraft(prev => ({ ...prev, [f]: v })),
                  onSaveEdit: doSaveUvEdit,
                  onCancelEdit: () => { setUvEditingId(null); setUvEditDraft({}); setUvSaveError(''); },
                  onStartAdd: () => { setUvAdding(true); setUvAddDraft({}); setUvSaveError(''); },
                  onAddField: (f, v) => setUvAddDraft(prev => ({ ...prev, [f]: v })),
                  onSaveAdd: doAddUv,
                  onCancelAdd: () => { setUvAdding(false); setUvAddDraft({}); setUvSaveError(''); },
                  saving: uvSaving,
                  saveError: uvSaveError,
                  onDelete: doDeleteUninterruptedVehicle,
                } : undefined}
              />
            )
          )}

          {activeTab === 'vehicle_energy' && (
            veFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading vehicle energy rates...</span>
              </div>
            ) : veError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{veError}</div>
            ) : (
              <VehicleEnergyConversionTable
                rows={veRows}
                editCtx={canEditTab ? {
                  editingId: veEditingId,
                  editDraft: veEditDraft,
                  adding: veAdding,
                  addDraft: veAddDraft,
                  vehicleClassOpts,
                  onStartEdit: (id, draft) => { setVeEditingId(id); setVeEditDraft(draft); setVeSaveError(''); },
                  onEditField: (f, v) => setVeEditDraft(prev => ({ ...prev, [f]: v })),
                  onSaveEdit: doSaveVeEdit,
                  onCancelEdit: () => { setVeEditingId(null); setVeEditDraft({}); setVeSaveError(''); },
                  onStartAdd: () => { setVeAdding(true); setVeAddDraft({}); setVeSaveError(''); },
                  onAddField: (f, v) => setVeAddDraft(prev => ({ ...prev, [f]: v })),
                  onSaveAdd: doAddVe,
                  onCancelAdd: () => { setVeAdding(false); setVeAddDraft({}); setVeSaveError(''); },
                  saving: veSaving,
                  saveError: veSaveError,
                  onDelete: doDeleteVehicleEnergy,
                } : undefined}
              />
            )
          )}

          {activeTab === 'operational_equipment' && (
            opEqFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading operational equipment...</span>
              </div>
            ) : opEqError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{opEqError}</div>
            ) : (
              <OperationalEquipmentTable
                rows={opEqRows}
                editCtx={canEditTab ? {
                  editingId: opEqEditingId,
                  editDraft: opEqEditDraft,
                  onStartEdit: (id, draft) => { setOpEqEditingId(id); setOpEqEditDraft(draft); setOpEqSaveError(''); },
                  onEditField: (f, v) => setOpEqEditDraft(prev => ({ ...prev, [f]: v })),
                  onSaveEdit: doSaveOpEqRow,
                  onCancelEdit: () => { setOpEqEditingId(null); setOpEqEditDraft({}); setOpEqSaveError(''); },
                  saving: opEqSaving,
                  saveError: opEqSaveError,
                  onDelete: doDeleteOperationalEquipment,
                  } : undefined}
              />
            )
          )}

          {activeTab === 'concrete_mix_designs' && (
            !selectedRevisionId ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No revision selected</p>
                <p className="text-sm text-text-base">Select a dataset revision above</p>
              </div>
            ) : cmFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading concrete mix designs...</span>
              </div>
            ) : cmError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{cmError}</div>
               ) : cmLoaded && cmRows.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-sm font-medium text-text-dark">No data found</p>
                <p className="text-xs text-text-base">No concrete mix design rows for the selected revision</p>
              </div>
            ) : (
              <ConcreteMixDesignTable
                assumptions={cmAssumptions}
                rows={cmRows}
                editCtx={canEditTab ? {
                  editCellKey: cmEditCellKey,
                  cellDraft: cmCellDraft,
                  onEditCell: (rowId, field, current) => {
                    setCmEditCellKey(`${rowId}::${field}`);
                    setCmCellDraft(current);
                    setCmSaveError('');
                  },
                  onCellChange: setCmCellDraft,
                  onSaveCell: doSaveCmCell,
                  onCancelCell: () => { setCmEditCellKey(null); setCmCellDraft(''); setCmSaveError(''); },
                  assumptionField: cmAssumptionField,
                  assumptionDraft: cmAssumptionDraft,
                  onEditAssumption: (field, current) => {
                    setCmAssumptionField(field);
                    setCmAssumptionDraft(current);
                    setCmSaveError('');
                  },
                  onAssumptionChange: setCmAssumptionDraft,
                  onSaveAssumption: doSaveCmAssumption,
                  onCancelAssumption: () => { setCmAssumptionField(null); setCmAssumptionDraft(''); setCmSaveError(''); },
                  saving: cmSaving,
                  saveError: cmSaveError,
                  } : undefined}
              />
            )
          )}

          {activeTab === 'direct_substitutions' && (
            directSubFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading direct substitutions…</span>
              </div>
            ) : directSubError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{directSubError}</div>
            ) : (
              <DirectSubstitutionsTable
                rows={directSubRows}
                canEdit={canEditTab}
                revisionId={selectedRevisionId}
                jurisdictions={jurOpts}
                onSaved={() => { void fetchDirectSubstitutions(); }}
              />
            )
          )}

          {activeTab === 'electricity_recycling_assumptions' && (
            !selectedRevisionId ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-base font-medium text-text-dark">No revision selected</p>
                <p className="text-sm text-text-base">Select a dataset revision above</p>
              </div>
            ) : eraFetching ? (
              <div className="flex items-center justify-center h-full gap-2 text-text-base">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>Loading electricity and recycling assumptions…</span>
              </div>
            ) : eraError ? (
              <div className="flex items-center justify-center h-full text-red-600 text-sm">{eraError}</div>
            ) : eraRows.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-1">
                <p className="text-sm font-medium text-text-dark">No data found</p>
                <p className="text-xs text-text-base">No electricity and recycling assumptions match the current filters</p>
              </div>
            ) : (
              <div className="flex flex-col h-full">
                {eraSaveError && (
                  <div className="px-4 py-2 text-xs text-red-600 border-b border-red-100 bg-red-50">{eraSaveError}</div>
                )}
                <ElectricityRecyclingAssumptionsTable
                  rows={eraRows}
                  editCtx={canEditTab ? {
                    editRowId: eraEditRowId,
                    cellDraft: eraCellDraft,
                    onEditCell: (rowId, current) => {
                      setEraEditRowId(rowId);
                      setEraCellDraft(current);
                      setEraSaveError('');
                    },
                    onCellChange: setEraCellDraft,
                    onSaveCell: doSaveEraCell,
                    onCancelCell: () => { setEraEditRowId(null); setEraCellDraft(''); setEraSaveError(''); },
                    saving: eraSaving,
                    saveError: eraSaveError,
                  } : undefined}
                />
              </div>
            )
          )}
        </div>
        {activeTab === 'factors' && activeGrade !== '' && !fetching && (displayData as unknown[]).length > 0 && (
          <PaginationBar
            page={page}
            totalItems={(displayData as unknown[]).length}
            pageSize={pageSize}
            onChangePage={setPage}
            onChangePageSize={size => { setPageSize(size); setPage(1); }}
          />
        )}
        {activeTab === 'recycled' && rcFiltered.length > 0 && (
          <PaginationBar
            page={rcPage}
            totalItems={rcFiltered.length}
            pageSize={pageSize}
            onChangePage={setRcPage}
            onChangePageSize={size => { setPageSize(size); setRcPage(1); }}
          />
        )}
        {activeTab === 'transport' && trFiltered.length > 0 && (
          <PaginationBar
            page={trPage}
            totalItems={trFiltered.length}
            pageSize={pageSize}
            onChangePage={setTrPage}
            onChangePageSize={size => { setPageSize(size); setTrPage(1); }}
          />
        )}
        {activeTab === 'direct_substitutions' && directSubTotal > 0 && (
          <PaginationBar
            page={directSubPage}
            totalItems={directSubTotal}
            pageSize={pageSize}
            onChangePage={setDirectSubPage}
            onChangePageSize={size => { setPageSize(size); setDirectSubPage(1); }}
          />
        )}
        {activeTab === 'electricity_recycling_assumptions' && selectedRevisionId && eraTotal > 0 && (
          <PaginationBar
            page={eraPage}
            totalItems={eraTotal}
            pageSize={pageSize}
            onChangePage={setEraPage}
            onChangePageSize={size => { setPageSize(size); setEraPage(1); }}
          />
          )}

      </div>
      {uploadTarget && uploadTarget !== 'audit' && uploadTarget !== 'factors' && (
        <UploadModal<Record<string, string>>
          open={true}
          onClose={() => setUploadTarget(null)}
          title={`Upload ${uploadTarget.replace(/_/g, ' ')}`}
          parseFile={async (file) => {
            const XLSX = await import('xlsx');
            const ab = await file.arrayBuffer();
            const wb = XLSX.read(ab, { type: 'array' });
            const ws = wb.Sheets[wb.SheetNames[0]];
            return XLSX.utils.sheet_to_json<Record<string, string>>(ws, { defval: '' });
          }}
          validateRows={async (rows) => {
            if (!rows.length) return { validRows: [], errors: ['No data rows found.'] };
            if (uploadTarget === 'electricity_recycling_assumptions') {
              if (!selectedRevisionId) {
                return { validRows: [], errors: ['Select a dataset revision before uploading.'] };
              }
              const errors: string[] = [];
              const validRows: Record<string, string>[] = [];
              rows.forEach((row, idx) => {
                const r = row as Record<string, string>;
                const { jurisdiction, metric, pctRaw } = parseEraUploadRow(r);
                if (isEraCalculatedMetric(metric)) return;

                const pct = pctRaw === '' ? NaN : parseFloat(pctRaw);

                if (!jurisdiction) errors.push(`Row ${idx + 2}: Jurisdiction Name is required`);
                else if (!metric) errors.push(`Row ${idx + 2}: Metric is required`);
                else if (!Number.isFinite(pct) || pct < 0 || pct > 100) {
                  errors.push(`Row ${idx + 2}: Default BAU(%) must be a number between 0 and 100`);
                } else {
                  validRows.push(r);
                }
              });
              if (!validRows.length && !errors.length) {
                errors.push('No editable rows found (calculated grid electricity rows are skipped).');
              }
              return { validRows, errors };
            }
            if (uploadTarget === 'content_recycled') {
              if (!selectedRevisionId) {
                return { validRows: [], errors: ['Select a dataset revision before uploading.'] };
              }
              const errors: string[] = [];
              const validRows: Record<string, string>[] = [];
              rows.forEach((row, idx) => {
                const r = row as Record<string, string>;
                const parsed = parseContentRecycledUploadRow(r);
                if (!parsed.jurisdiction) {
                  errors.push(`Row ${idx + 2}: Jurisdiction is required`);
                  return;
                }
                if (!parsed.source) return;
                if (parsed.recycledRaw !== '') {
                  const rv = parseContentRecycledPctUpload(parsed.recycledRaw);
                  if (rv === undefined) errors.push(`Row ${idx + 2}: Invalid Recycled Content (%)`);
                }
                if (parsed.reusedRaw !== '') {
                  const uv = parseContentRecycledPctUpload(parsed.reusedRaw);
                  if (uv === undefined) errors.push(`Row ${idx + 2}: Invalid Reused Content (%)`);
                }
                if (!errors.some(e => e.startsWith(`Row ${idx + 2}:`))) {
                  validRows.push(r);
                }
              });
              if (!validRows.length && !errors.length) {
                errors.push('No data rows with an emissions source were found.');
              }
              return { validRows, errors };
            }
            return { validRows: rows, errors: [] };
          }}
          onSuccess={async (rows) => {
            const endpoint = TAB_ENDPOINT[uploadTarget];
            if (!endpoint) return;
            const tabAtStart = uploadTarget;
            setUploadRunning(true);
            try {
              if (tabAtStart === 'direct_substitutions') {
                if (!selectedRevisionId) return;
                for (const row of rows) {
                  const payload = { ...(row as Record<string, unknown>) };
                  delete payload.id;
                  await http.post('/api/direct-substitutions/upsert', { ...payload, dataset_revision_id: selectedRevisionId });
                }
                 } else if (tabAtStart === 'electricity_recycling_assumptions') {
                if (!selectedRevisionId) return;
                for (const row of rows) {
                  const r = row as Record<string, string>;
                  const { jurisdiction, metric, pctRaw } = parseEraUploadRow(r);
                  const pct = parseFloat(pctRaw) / 100;
                  await http.post('/api/electricity-recycling-assumptions/upsert', {
                    dataset_revision_id: selectedRevisionId,
                    jurisdiction_name: jurisdiction,
                    metric_label: metric,
                    default_bau_pct: pct,
                  });
                }
                 } else if (tabAtStart === 'content_recycled') {
                if (!selectedRevisionId) return;
                for (const row of rows) {
                  const r = row as Record<string, string>;
                  const parsed = parseContentRecycledUploadRow(r);
                  if (!parsed.source) continue;
                  const jurisdictionId = jurOpts.find(j => j.name === parsed.jurisdiction)?.id ?? null;
                  const subCategoryId = ecOpts.find(c => c.name === parsed.category)?.id ?? null;
                  const recycledNum = parseContentRecycledPctUpload(parsed.recycledRaw);
                  const reusedNum = parseContentRecycledPctUpload(parsed.reusedRaw);
                  await http.post('/api/recycled-content-factors/upsert', {
                    dataset_revision_id: selectedRevisionId,
                    jurisdiction_id: jurisdictionId,
                    emissions_sub_category_id: subCategoryId,
                    emissions_source: parsed.source,
                    recycled_content_pct: recycledNum ?? null,
                    reused_content_pct: reusedNum ?? null,
                    notes: parsed.notes || null,
                  });
                }
              } else {
                for (const row of rows) {
                  const { id, ...rest } = row as Record<string, string>;
                  if (id) {
                    await http.patch(`${endpoint}/${id}`, rest);
                  } else {
                    await http.post(endpoint, rest);
                  }
                }
              }
              if (tabAtStart === 'direct_substitutions') {
                await fetchDirectSubstitutions();
                 } else if (tabAtStart === 'electricity_recycling_assumptions') {
                await fetchElectricityRecyclingAssumptions();
                } else if (tabAtStart === 'content_recycled') {
                await fetchContentRecycled();
              }
            } finally {
              setUploadRunning(false);
              setUploadTarget(null);
            }
          }}
        />
      )}
    </div>
  );
}
