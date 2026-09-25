import React, { useState } from "react";
import InfoTooltip from "./common/InfoTooltip";
import OrganizationService, {type OrganizationDto} from "../services/organization.service";
import AutoComplete, {type  AutocompleteOption } from "./common/AutoComplete";


export type ProjectCategoryValue = 'small' | 'large' | 'contractor';

type DeliveryPartnersProps = {
  category: ProjectCategoryValue;

  designContract: string;
  setDesignContract: (v: string) => void;

  designerOrg: string;
  setDesignerOrg: (v: string) => void;

  constructionContract: string;
  setConstructionContract: (v: string) => void;

  constructionOrg: string;
  setConstructionOrg: (v: string) => void;

  onDesignerOrgSelect?: (id: string) => void;
  onConstructionOrgSelect?: (id: string) => void;

  defaultExpanded?: boolean;
  className?: string;
};

const DeliveryPartners: React.FC<DeliveryPartnersProps> = ({
  category,
  designContract,
  setDesignContract,
  designerOrg,
  setDesignerOrg,
  constructionContract,
  setConstructionContract,
  constructionOrg,
  setConstructionOrg,
  onDesignerOrgSelect,
  onConstructionOrgSelect,
  defaultExpanded = false,
  className,
}) => {
  const [expanded, setExpanded] = useState<boolean>(defaultExpanded);

  const isContractor = category === "contractor";
  const showAllFields = !isContractor;

  const isComplete = showAllFields
    ? Boolean(
        designContract.trim() ||
          designerOrg.trim() ||
          constructionContract.trim() ||
          constructionOrg.trim()
      )
    : Boolean(constructionContract.trim() || constructionOrg.trim());

  const getStatusIcon = () => {
    if (isComplete) return "check_circle";
    if (expanded) return "radio_button_partial";
    return "radio_button_unchecked";
  };

  
  const toOption = (o: OrganizationDto): AutocompleteOption => ({
    id: o.id ?? o.code ?? o.name,
    label: o.name,
    ...o,
  });

  const loadDesignerOptions = async () => {
    const list = await OrganizationService.fetchOrganizations("DESIGNERS");
    return list.map(toOption);
  };
  const loadConstructionOptions = async () => {
    const list = await OrganizationService.fetchOrganizations("CONTRACTORS");
    return list.map(toOption);
  };

  const optionFilter = (opt: AutocompleteOption, input: string) => {
    const q = input.trim().toLowerCase();
    if (!q) return true;
    const name = (opt.label || "").toLowerCase();
    const shortName = (opt as any).shortName?.toLowerCase?.() || "";
    const code = (opt as any).code?.toLowerCase?.() || "";
    const aliases: string[] = (opt as any).aliases || [];
    return (
      name.includes(q) ||
      shortName.includes(q) ||
      code.includes(q) ||
      aliases.some((a) => a.toLowerCase().includes(q))
    );
  };


  return (
    <div className={["border-t border-neutral-200 p-4", className || ""].join(" ")}>
      <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="w-full flex items-center justify-between gap-8 text-left cursor-pointer"
          aria-expanded={expanded}
          aria-controls="delivery-partners-unified-panel"
          title={expanded ? "Collapse" : "Expand"}
        >
          <div className="flex min-w-0 items-center text-text-dark">
            <span
              className="material-symbols-rounded mr-2 shrink-0 text-lg text-gray-600"
              aria-hidden="true"
            >
              {getStatusIcon()}
            </span>

            <span className="truncate">
              Delivery partners (optional)
            </span>

            <span className="ml-2">
              <InfoTooltip
                text="Information about delivery partners"
                iconSize={16}
                trigger="auto"
                placement="top"
                offset={10}
                arrowOffset={23}
              />
            </span>
          </div>

          <span className="material-symbols-rounded shrink-0">
            {expanded ? "keyboard_arrow_up" : "keyboard_arrow_down"}
          </span>
        </button>

      {expanded && (
        <div id="delivery-partners-unified-panel" className="space-y-4 mt-8">
          {showAllFields ? (
            <div className="grid grid-cols-1 gap-8">
              <div className="flex flex-col mt-8">
                <label className="mb-1 text-sm text-text-base">Contract number (design)</label>
                <input
                  type="text"
                  value={designContract}
                  onChange={(e) => setDesignContract(e.target.value)}
                  className="rounded-[var(--radius-3)] border border-border-input bg-white p-3 h-10"
                />
              </div>
              
              <AutoComplete
                label="Designer organisation"
                value={designerOrg}
                onChange={(v) => { setDesignerOrg(v.toUpperCase()); onDesignerOrgSelect?.(""); }}
                onSelect={(opt) => {
                  setDesignerOrg(opt.label.toUpperCase());
                  onDesignerOrgSelect?.(String(opt.id));
                }}
                loadOptions={loadDesignerOptions}
                filterFn={optionFilter}
                id="designer-org"
                className="w-full"
                minLength={1}
                enableInlineCompletion
              />
              <div className="flex flex-col">
                <label className="mb-1 text-sm text-text-base">Contract number (construction)</label>
                <input
                  type="text"
                  value={constructionContract}
                  onChange={(e) => setConstructionContract(e.target.value)}
                  className="rounded-[var(--radius-3)] border border-border-input bg-white p-3 h-10"
                />
              </div>
              <AutoComplete
                label="Construction delivery organisation"
                value={constructionOrg}
                onChange={(v) => { setConstructionOrg(v.toUpperCase()); onConstructionOrgSelect?.(""); }}
                onSelect={(opt) => {
                  setConstructionOrg(opt.label.toUpperCase());
                  onConstructionOrgSelect?.(String(opt.id));
                }}
                loadOptions={loadConstructionOptions}
                filterFn={optionFilter}
                id="construction-org"
                className="w-full mb-8"
                minLength={1}
                enableInlineCompletion
              />
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-8">
              <div className="flex flex-col">
                <label className="mb-1 text-sm text-text-base">Contract number (supply/maintenance contract)</label>
                <input
                  type="text"
                  value={constructionContract}
                  onChange={(e) => setConstructionContract(e.target.value)}
                  className="rounded-[var(--radius-3)] border border-border-input bg-white p-3 h-10"
                />
              </div>
              
              <AutoComplete
                label="Supply & maintenance delivery organisation"
                value={constructionOrg}
                onChange={(v) => { setConstructionOrg(v.toUpperCase()); onConstructionOrgSelect?.(""); }}
                onSelect={(opt) => {
                  setConstructionOrg(opt.label.toUpperCase());
                  onConstructionOrgSelect?.(String(opt.id));
                }}
                loadOptions={loadConstructionOptions}
                filterFn={optionFilter}
                id="supply-maintenance-org"
                className="w-full"
                minLength={1}
                enableInlineCompletion
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DeliveryPartners;