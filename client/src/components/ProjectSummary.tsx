import React, { useState, useEffect, useRef } from "react";
import InfoTooltip from "./common/InfoTooltip";
import  LookupsService from "../services/Lookups.service";
import { SelectListbox } from "./common/Select";
import FieldError from "./common/FieldError";
import PostcodesService from "../services/postcodes.service";
import { NumericInput } from "./common/NumericInput";
import { useUser } from "../context/UserContext";
import OrganizationService from "@/services/organization.service";

export type ProjectSummaryState = {
  projectName: string;
  programName: string; // optional
  projectType: string;
  projectTypecast: string;
  projectLocation: string;
  projectDescription: string; // optional
};


export type PostcodeRow = {
  postcode: string;
  area_class: string;
  postcode_reference_id?: string;
  suburb?: string;            // committed value
  suburbDraft?: string;       // in-progress value during editing
  isEditingSuburb?: boolean;  // editing state
};


type ProjectSummaryProps = {
  value: ProjectSummaryState;
  onChange: (patch: Partial<ProjectSummaryState>) => void;

  errors?: {
    projectName?: string | null;
    projectType?: string | null;
    projectTypecast?: string | null;
    projectLocation?: string | null;
  };

  postcodeRows: PostcodeRow[];
  setPostcodeRows: React.Dispatch<React.SetStateAction<PostcodeRow[]>>;
  postcodeInput: string;
  setPostcodeInput: (val: string) => void;
};

const MAX_POSTCODES = 20;

const ProjectSummary: React.FC<ProjectSummaryProps> = ({ value, onChange, errors, postcodeInput, setPostcodeInput, postcodeRows, setPostcodeRows }) => {
  const [expanded, setExpanded] = useState(true);

  const {
    projectName,
    programName,
    projectType,
    projectTypecast,
    projectLocation,
    projectDescription,
  } = value;
  const [projectTypes, setProjectTypes] = useState<any[]>([]);

  const [typecasts, setTypecasts] = useState<any[]>([]);


  const [postcodeAll, setPostcodeAll] = useState<any[]>([]);
  const [postcodeLoading, setPostcodeLoading] = useState(false);
  const [postcodeLookupMessage, setPostcodeLookupMessage] = useState<string | null>(null);
  const [postcodeInd, setPostcodeInd] = useState<Map<string, any>>(new Map());



  // Guard against race conditions when user switches projectType quickly
  const typecastReqIdRef = useRef(0);
  const { user } = useUser();
 
  useEffect(() => {
    if (errors && Object.keys(errors).length > 0) {
      setExpanded(true);
    }
  }, [errors]);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setPostcodeLoading(true);
        const organisationId = user?.organisation_id;
        if (!organisationId) {
          return;
        }
        const orgDetails = await OrganizationService.fetchOrganizationById(organisationId);
        if (orgDetails.jurisdiction_id) {
          const all = await PostcodesService.fetchPostcodes(orgDetails.jurisdiction_id);
          if (!cancelled && Array.isArray(all)) {
            setPostcodeAll(all);
          }
        }
      } catch (e: any) {
        // optional: show a soft error. We can still lookup by Enter.
        console.warn("Failed to fetch all postcodes on mount:", e?.message || e);
      } finally {
        if (!cancelled) setPostcodeLoading(false);
      }

    })();
    return () => { cancelled = true; };
  }, [user?.organisation_id]);

  useEffect(() => {
    const idx = new Map<string, any>();
    for (const rec of postcodeAll) {
      const key = String(rec?.postcode ?? "").trim().toLowerCase();
      if (key) idx.set(key, rec);
    }
    setPostcodeInd(idx);
  }, [postcodeAll]);


  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const response = await LookupsService.fetchMasterTypes();
        const mapped = (Array.isArray(response) ? response : [])
          .map((t: any) => {
            const label = String(t?.name ?? "").trim();
            if (!label) return null;
            const id = t?.id ?? t?.code ?? label;
            return { label, value: String(id) };
          })
          .filter(Boolean) as { label: string; value: string }[];

        if (!cancelled) {
          setProjectTypes(mapped);
        }
      } catch (e: any) {
        if (!cancelled) {
          setProjectTypes([]); // keep UI usable
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const reqId = ++typecastReqIdRef.current;

    if (!projectType) {
      setTypecasts([]);
      return;
    }

    (async () => {
      try {
        const response = await LookupsService.fetchTypecasts(projectType);
        const mapped = (Array.isArray(response) ? response : [])
          .map((t: any) => {
            const label = String(t?.name ?? "").trim();
            if (!label) return null;
            const id = t?.project_typecast_id ?? t?.id ?? t?.code ?? label;
            return { label, value: String(id) };
          })
          .filter(Boolean) as { label: string; value: string }[];

        // Only update if this is the latest request
        if (typecastReqIdRef.current === reqId) {
          setTypecasts(mapped);

          const stillValid = mapped.some(opt => opt.value === projectTypecast);
          if (!stillValid) {
            onChange({ projectTypecast: "" });
          }
        }
      } catch (e) {
        if (typecastReqIdRef.current === reqId) {
          setTypecasts([]);
        }
      }
    })();
  }, [projectType]);


  // Validate input lightly (numbers only; allow leading zeros if needed)

  const tokenizePostcodes = (raw: string): string[] =>
    raw
      .split(",") // if no comma, returns [raw]
      .map((s) => s.trim())
      .filter(Boolean);

  const handlePostcodeEnter = () => {
    setPostcodeLookupMessage(null);

    const raw = postcodeInput.trim();
    if (!raw) return;

    if (postcodeLoading) {
      setPostcodeLookupMessage("Postcodes are still loading. Please try again in a moment.");
      return;
    }
    if (postcodeAll.length === 0) {
      setPostcodeLookupMessage("Postcodes are not available yet.");
      return;
    }

    const tokens = tokenizePostcodes(raw);
    if (tokens.length === 0) return;

    const existingCount = postcodeRows.length;
    const remainingCapacity = Math.max(0, MAX_POSTCODES - existingCount);

    if (remainingCapacity === 0) {
      setPostcodeLookupMessage(`You can enter up to ${MAX_POSTCODES} postcodes.`);
      setPostcodeInput("");
      return;
    }

    // Build existing keys set (reference_id preferred, else postcode)
    const existingKeys = new Set<string>(
      postcodeRows.map((r) => String(r.postcode_reference_id ?? r.postcode))
    );
    const addedKeysThisBatch = new Set<string>();

    const notFound: string[] = [];
    const duplicates: string[] = [];
    let skippedForLimit = 0;

    const rowsToAdd: { postcode: string; area_class: string; postcode_reference_id?: string }[] = [];

    for (const token of tokens) {
      if (rowsToAdd.length >= remainingCapacity) {
        // Remaining tokens beyond capacity are considered skipped
        skippedForLimit = tokens.length - (rowsToAdd.length + notFound.length + duplicates.length);
        break;
      }

      const rec = postcodeInd.get(token.toLowerCase());
      if (!rec) {
        notFound.push(token);
        continue;
      }

      const row = {
        postcode: String(rec.postcode ?? token),
        area_class: String(rec.area_class ?? "OTHER"),
        postcode_reference_id: rec.id,
        suburb: "",
        suburbDraft: "",
        isEditingSuburb: false,
      };
      const uniqueKey = String(row.postcode_reference_id ?? row.postcode);

      if (existingKeys.has(uniqueKey) || addedKeysThisBatch.has(uniqueKey)) {
        duplicates.push(token);
        continue;
      }

      rowsToAdd.push(row);
      addedKeysThisBatch.add(uniqueKey);
    }

    if (rowsToAdd.length > 0) {
      setPostcodeRows((prev) => [...prev, ...rowsToAdd]);
      // Optional: keep projectLocation in sync with last added postcode
      onChange({ projectLocation: rowsToAdd[rowsToAdd.length - 1].postcode });
    }

    const messages: string[] = [];
    if (notFound.length > 0) messages.push(`Please enter a valid postcode for ${user?.organisation_name}`);
    if (duplicates.length > 0) messages.push(`${duplicates.join(", ")} is already added.`);
    if (skippedForLimit > 0 || postcodeRows.length + rowsToAdd.length >= MAX_POSTCODES) {
      messages.push(`You can enter up to ${MAX_POSTCODES} postcodes.`);
    }
    if (messages.length > 0) setPostcodeLookupMessage(messages.join(" "));

    // Clear input after processing
    setPostcodeInput("");
  };

  const deletePostcode = (key: string) => {
    setPostcodeRows((prev) => prev.filter(r => String(r.postcode_reference_id ?? r.postcode) !== key));
  };

  // const handlePostcodeKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
  //   if (e.key === "Enter") {
  //     e.preventDefault();
  //     handlePostcodeEnter();
  //   }
  // };

  const getRowKey = (r: PostcodeRow) =>
    String(r.postcode_reference_id ?? r.postcode);

  const startEditSuburb = (key: string) => {
    setPostcodeRows(prev =>
      prev.map(r =>
        getRowKey(r) === key ? { ...r, isEditingSuburb: true, suburbDraft: r.suburb } : r
      )
    )
  }


  const changeSuburbDraft = (key: string, value: string) => {
    setPostcodeRows(prev =>
      prev.map(r =>
        getRowKey(r) === key
          ? { ...r, suburbDraft: value, isEditingSuburb: true }
          : r
      )
    );
  };

  const commitSuburb = (key: string) => {
    setPostcodeRows(prev =>
      prev.map(r => {
        if (getRowKey(r) !== key) return r;
        const committed = (r.suburbDraft ?? "").trim();
        return {
          ...r,
          suburb: committed,
          suburbDraft: committed,
          isEditingSuburb: false
        };
      })
    );
  };

  const clearSuburb = (key: string) => {
    setPostcodeRows(prev =>
      prev.map(r =>
        getRowKey(r) === key
          ? { ...r, suburb: "", suburbDraft: "", isEditingSuburb: false }
          : r
      )
    );
  };

  // Required fields rule
  const isComplete =
    projectName.trim().length > 0 &&
    projectType.trim().length > 0 &&
    projectTypecast.trim().length > 0 &&
    projectLocation.trim().length > 0;

  const handleAccordion = () => setExpanded((v) => !v);

  // --- Icon selection (all in grey)
  const getStatusIcon = () => {
    if (isComplete) return "check_circle";
    if (expanded) return "radio_button_partial"; // fallback: "adjust"
    return "radio_button_unchecked";
  };

  const typecastDisabled = !projectType || typecasts.length === 0;
  return (
    <div className="p-4 border-t border-light-grey">
      {/* Header row — aligned with CostAndSchedule */}
      <div className="flex items-center justify-between gap-2">
        
      <button
        type="button"
        onClick={handleAccordion}
        className="w-full flex items-center justify-between gap-2 text-left cursor-pointer"
        aria-expanded={expanded}
        aria-controls="project-summary-panel"
      >
         <div className="flex min-w-0 items-center text-text-dark">
          <span
            className="material-symbols-rounded mr-2 shrink-0"
            aria-hidden="true"
          >
            {getStatusIcon()}
          </span>
          <span className="truncate">
            Project summary
          </span>
        </div>
      </button>
        <span
          className="material-symbols-rounded shrink-0 cursor-pointer "
          onClick={handleAccordion}>
          {expanded ? "keyboard_arrow_up" : "keyboard_arrow_down"}
        </span>
      </div>

      {expanded && (
        <div id="project-summary-panel" className="space-y-4">
          {/* Project Name */}
          <div className="flex flex-col mb-8">
            <label className="mb-1 mt-8 text-sm text-text-base">Project name</label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => onChange({ projectName: e.target.value })}
              aria-invalid={!!errors?.projectName}
              className="rounded-[var(--radius-3)] border border-border-input bg-white p-3 focus:ring-1 h-10"
            />
            {errors?.projectName && <FieldError message={errors.projectName} />}
          </div>

          {/* Program Name (Optional) */}
          <div className="flex flex-col  mb-8">
            <label className="mb-1 text-sm text-text-base">
              Program name (optional)
            </label>
            <input
              type="text"
              value={programName}
              onChange={(e) => onChange({ programName: e.target.value })}
              className="rounded-[var(--radius-3)] border border-border-input bg-white p-3 focus:ring-1 h-10"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="flex flex-col">
              <SelectListbox
                value={projectType}
                onChange={(v: string) => onChange({ projectType: v })}
                options={projectTypes/* .filter((p)=> p.label.includes("Road") || p.label.includes("Rail")) */}
                label="Project type"
                aria-label="Project type"
                placeholder=""
              />
              {errors?.projectType && <FieldError message={errors.projectType} />}
            </div>

            {/* Project Typecast */}
            <div className="flex flex-col mb-4">
              <SelectListbox
                value={projectTypecast}
                onChange={(v: string) => onChange({ projectTypecast: v })}
                options={typecasts}
                label="Project typecast"
                aria-label="Project typecast"
                placeholder=""
                disabled={typecastDisabled}
              />

              {!typecastDisabled && errors?.projectTypecast && (
                <FieldError message={errors.projectTypecast} />
              )}

            </div>
          </div>

          {/* Project Location */}
          <div className="flex flex-col mb-6">
            <label className="mb-1 flex items-center gap-2 text-sm text-text-base">
              Project location
              <InfoTooltip
                text="You can enter up to 20 postcodes"
                iconSize={20}
                trigger="auto"
                placement="top"
                offset={10}
                arrowOffset={23}
              />
            </label>
            <div className="flex flex-col">
              <div className="flex gap-2 items-start">
              <NumericInput
                value={postcodeInput}
                onChange={(val) => {
                  setPostcodeInput(val === null ? "" : String(val));
                }}
                allowCommaSeparated
                min={0}
                prefix="Postcode"
                ariaLabel="postcode"
                className="w-full"
              />

              <button
              type="button"
              onClick={handlePostcodeEnter}
              disabled={!postcodeInput.trim() || postcodeLoading}
              className={`h-10 px-4 border rounded-[var(--radius-3)] text-sm text-text-base transition cursor-pointer
                ${!postcodeInput.trim() || postcodeLoading
                  ? " bg-white text-neutral-800 border-neutral-300 cursor-not-allowed"
                  : " bg-neutral-20 text-border-neutral border-neutral-400 hover:bg-neutral-300"
                }`}
            >
              Add
            </button>

            </div>

              {errors?.projectLocation && <FieldError message={errors.projectLocation} />}
              {/* </div> */}

              {postcodeLookupMessage && (
                <div className="mt-1 text-xs text-danger">{postcodeLookupMessage}</div>
              )}
              {postcodeRows.length > 0 && (
                <div className="mt-4 rounded-[var(--radius-3)] border border-neutral-90 overflow-hidden mb-8">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-neutral-95 text-xs text-text-dark">
                      <tr>
                        <th className="p-4">Postcode</th>
                        <th className="p-4">Area</th>
                        <th className="p-4">Suburb <span className="font-normal"> (OPTIONAL)</span></th>
                        <th className="p-4"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {postcodeRows.slice(0, MAX_POSTCODES).map((row) => {
                        const key = row.postcode_reference_id ?? row.postcode;
                        const isEditing = !!row.isEditingSuburb;
                        return (
                          <tr key={row.postcode_reference_id ?? row.postcode} className="border-t border-neutral-90 bg-white">
                            <td className="p-4 align-middle">{row.postcode}</td>
                            <td className="p-4 align-middle">{row.area_class}</td>

                            <td className={`align-middle ${row.isEditingSuburb ? "px-3 py-2" : "p-4"}`}>
                              {isEditing ? (
                                <div className="flex items-center gap-2">
                                  <input
                                    type="text"
                                    value={row.suburbDraft ?? ""}
                                    onChange={(e) => changeSuburbDraft(key, e.target.value)}
                                    onKeyDown={(e) => {
                                      if (e.key === "Enter") {
                                        e.preventDefault();
                                        commitSuburb(key);
                                      }
                                      if (e.key === "Escape") {
                                        e.preventDefault();
                                        clearSuburb(key);
                                      }
                                    }}
                                    autoFocus
                                    className="w-full rounded-[var(--radius-3)] border border-border-input bg-white p-2 h-10 focus-visible:ring-1 focus-visible:ring-border-input"
                                    aria-label="Suburb"
                                  />
                                </div>
                              ) : (
                                <div className="cursor-text select-none rounded-[var(--radius-3)]"
                                  onDoubleClick={() => startEditSuburb(key)}
                                  role="button" tabIndex={0}
                                  onKeyDown={(e) => {
                                    if (e.key === "Enter" || e.key === " ") {
                                      e.preventDefault();
                                      startEditSuburb(key);
                                    }
                                  }}
                                  aria-label={(row.suburb && row.suburb.trim()) ?
                                    `Suburb: ${row.suburb}. Double click to edit.`
                                    : "Add suburb. Double click to edit."
                                  }>
                                  {row.suburb && row.suburb.trim().length
                                    ? row.suburb
                                    : <span className="text-neutral-400">Add suburb</span>}
                                </div>
                              )}
                            </td>
                            <td className="p-4 align-middle">
                              {isEditing ? (
                                <div className="flex items-center gap-3">
                                  <button
                                    type="button"
                                    className="text-sm text-success hover:underline cursor-pointer"
                                    onClick={() => commitSuburb(key)}
                                    title="Save suburb"
                                    aria-label="Save suburb"
                                    disabled={!((row.suburbDraft ?? "").trim().length)}
                                  >
                                    <span className="material-symbols-rounded text-success">
                                      check
                                    </span>
                                  </button>
                                  <button
                                    type="button"
                                    className="text-sm text-neutral-600 hover:underline cursor-pointer"
                                    onClick={() => clearSuburb(key)}
                                    title="Clear suburb"
                                    aria-label="Clear suburb"
                                  >
                                    <span className="material-symbols-rounded text-border-neutral">
                                      close
                                    </span>
                                  </button>
                                </div>
                              ) : <button
                                    type="button"
                                    className="text-sm text-neutral-600 hover:underline cursor-pointer"
                                    onClick={() => deletePostcode(key)}
                                    title="delete postcode"
                                    aria-label="Delete postcode"
                                  >
                                    <span className="material-symbols-rounded text-danger">
                                      delete
                                    </span>
                                  </button>}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
          {/* Project Description */}
          <div className="flex flex-col mb-6">
            <label className="mb-1 text-sm text-text-base">
              Project description (optional)
            </label>
            <textarea
              rows={4}
              value={projectDescription}
              onChange={(e) => onChange({ projectDescription: e.target.value })}
              className="resize-none rounded-[var(--radius-3)] border border-border-input bg-white p-3 focus:ring-1"
            />
          </div>

        </div>
      )}
    </div>)
}

export default ProjectSummary;