import type { PageTab, G1Filter, G234Filter, RcFilter, TrFilter, DecarbFilter, EvUptakeFilter, DensityFilter, FugitiveFilter, CarbonValueFilter, WastageRateFilter, ContentRecycledFilter } from './types';

export const GRADE_OPTIONS = [
  { label: 'Grade 1', value: '1' },
  { label: 'Grade 2', value: '2' },
  { label: 'Grade 3/4', value: '3' },
];

export const TABS: Array<{ id: PageTab; label: string }> = [
  { id: 'factors',                label: 'Emission Factors'          },
/*   { id: 'recycled',               label: 'Recycled Content'          }, */
  { id: 'content_recycled',       label: 'Recycled Content'          },
  { id: 'transport',              label: 'Default Transport'         },
  { id: 'waste',                  label: 'Waste Rates'               },
  { id: 'decarb',                 label: 'Electricity'               },
  { id: 'carbon_values',          label: 'Carbon Values'             },
  { id: 'ev_uptake',              label: 'EV Uptake'                 },
  { id: 'vepm',                   label: 'VEPM'                      },
  { id: 'freight_rail',           label: 'Freight Rail'              },
  { id: 'maintenance_replacement', label: 'Maintenance & Replacement' },
  { id: 'operational_equipment',   label: 'Operational Equipment'     },
  { id: 'audit',                  label: 'Audit Trail'               },
  { id: 'densities',              label: 'Densities'                 },
  { id: 'unit_conversions',       label: 'Unit Conversions'          },
  { id: 'fugitives',              label: 'Fugitives'                 },
  { id: 'energy_density_conversions', label: 'Energy Density Conversions' },
  { id: 'vehicle_masses',         label: 'Vehicle Masses'            },
  { id: 'interrupted_vehicles',   label: 'Fuel use variables - stop-start'      },
  { id: 'uninterrupted_vehicles', label: 'Fuel use variables - free flow'    },
  { id: 'vehicle_energy',         label: 'Vehicle Energy Conversion'            },
  { id: 'wastage_rates',          label: 'Wastage Rates'             },
  { id: 'renewable_energy',        label: 'Renewable Energy'          },
  { id: 'concrete_mix_designs',   label: 'Default concrete mix designs' },
  { id: 'direct_substitutions',   label: 'Direct Substitutions' },
  { id: 'electricity_recycling_assumptions', label: 'Electricity and Recycling Assumptions' },

];

export const TAB_GROUPS: Array<{ label: string; ids: PageTab[];  alwaysShowSubTabs?: boolean; }> = [
  {
    label: 'Emission Factors',
    ids: [
          'factors', 
          'decarb', 
          'maintenance_replacement'
        ],
  },
  /* {
    label: 'Reference & Conversion Data',
    ids: [  
      
    ],
  }, */
   {
    label: 'Conversions',
    ids: [ 
      'densities', 
      'unit_conversions',
      'energy_density_conversions',    
    ],
  },
   {
    label: 'Default Assumptions',
    ids: [ 
   'fugitives', 
   'recycled', 
   'content_recycled',
   'transport', 
     'waste',
     'operational_equipment', 
      'carbon_values', 
         'wastage_rates',
         'renewable_energy'
    ],
  },
  {
    label: 'User emissions data',
    ids: [ 
    'vehicle_masses',
      'interrupted_vehicles', 
      'uninterrupted_vehicles', 
      'vehicle_energy',
      'vepm', 
      'freight_rail',
       'ev_uptake', 
    ],
  },
  /* {
    label: 'Assumptions & Scenarios',
    ids: [
         
        ],
  }, */
  {
    label: 'Business-as-usual Assumptions',
 ids: ['concrete_mix_designs', 'direct_substitutions', 'electricity_recycling_assumptions'],
    alwaysShowSubTabs: true,
  },
  {
    label: 'Audit Trail',
    ids: ['audit'],
  },
];

export const STATUS_STYLES: Record<string, string> = {
  draft:      'bg-neutral-200 text-neutral-700',
  published:  'bg-green-100 text-green-700',
  deprecated: 'bg-yellow-100 text-yellow-700',
  archived:   'bg-red-100 text-red-700',
};

export const INIT_G1: G1Filter     = { mastertype_id: '', typecast_id: '', metrics: [], units: [], jurisdictions: [] };
export const INIT_G234: G234Filter = { categories: [], subcategories: [], emissionsSource: '', units: [], jurisdictions: [] };
export const INIT_RC: RcFilter = { material: '', jurisdictions: [], percentMin: '', percentMax: '' };
export const INIT_TR: TrFilter = { materialCategory: '', jurisdictions: [], transportMode: '' };
export const INIT_DECARB: DecarbFilter = { jurisdictions: [] };
export const INIT_CARBON_VALUES: CarbonValueFilter = { jurisdictions: [], rangeCodes: [] };
export const INIT_EV_UPTAKE: EvUptakeFilter = { jurisdictions: [], scenarioCodes: [], vehicleCategoryCodes: [], energyTypeCodes: [] };
export const INIT_DENSITY: DensityFilter = { jurisdictions: [], datasets: [], categories: [], subcategories: [], emissionsSource: '', units: [] };
export const INIT_FUGITIVE: FugitiveFilter = { jurisdictions: [] };
export const INIT_WASTAGE_RATES: WastageRateFilter = { jurisdictions: [], materials: [] };
export const INIT_CONTENT_RECYCLED: ContentRecycledFilter = { jurisdictions: [] };

export const METRIC_LABEL: Record<string, string> = {
  material_share_capex:     'Material share of capex',
  emission_intensity_a1_a3: 'A1-A3 Emission intensity',
  emission_intensity_a4:    'A4 Transport intensity',
  emission_intensity_a5:    'A5 Construction intensity',
};

export const TODAY = new Date().toISOString().split('T')[0];
export const DEFAULT_EFFECTIVE_TO = '2100-12-31';
