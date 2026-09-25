import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useToast } from "@/components/common/ToastProvider"
import { type AutocompleteOption } from "./common/AutoComplete";
import UsersService from "../services/Users.service";
import OrganizationService from "../services/organization.service";
import useDebounce from "../customHooks/useDebounce";
import FieldError from "./common/FieldError";
import CheckCircle from "../assets/icons/check-circle-green.svg";
import http from "@/http";

type AccessLevel = "Can view" | "Can edit";
type AccessByStage = Record<string, AccessLevel | "">;




export type AccessTableRow = {
  id: string;
  userId?: string;
  name: string;
  email?: string;
  stage: string;
  access: AccessLevel;
};

type ProjectAccessProps = {
  category?: string;
  editingRow?: AccessTableRow | null;
  onCloseRequestModal?: () => void;
  onOpenCancelModal?: () => void;
  onCloseAllModals?: () => void;
  onAddAccessRows?: (rows: AccessTableRow[]) => void;
  onUpdateAccessRow?: (row: AccessTableRow) => void;
  selectedReportingStage?: "business" | "design" | "construction";
};

const EMAIL_REGEX =
  /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i;

const ProjectAccess: React.FC<ProjectAccessProps> = ({
  category,
  editingRow,
  onCloseRequestModal,
  onOpenCancelModal,
  onCloseAllModals,
  onAddAccessRows,
  onUpdateAccessRow,
  selectedReportingStage,
}) => {
  const [selectedUser, setSelectedUser] = useState<AutocompleteOption | null>(null);

  const [projectName, setProjectName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [justification, setJustification] = useState("");
  const [accessType, setAccessType] = useState<AccessLevel | "">("");

  const [submitted, setSubmitted] = useState(false);

  const debouncedProjectName = useDebounce(projectName, 500);
  const debouncedOrgName = useDebounce(orgName, 500);

  const [email, setEmail] = useState("");
  const debouncedEmail = useDebounce(email, 400);
  const [isCheckingUser, setIsCheckingUser] = useState(false);
  const [isUserValid, setIsUserValid] = useState<boolean | null>(null);
  const [userLookupError, setUserLookupError] = useState<string | null>(null);
  const isEmailFormatValid = useMemo(() => EMAIL_REGEX.test(debouncedEmail.trim()), [debouncedEmail]);

  const stages = useMemo(() => ["Business case", "Design", "Construction"], []);
  const [accessByStage, setAccessByStage] = useState<AccessByStage>(() =>
    stages.reduce((acc, s) => ({ ...acc, [s]: "" }), {} as AccessByStage),
  );

  const [detectedCategory, setDetectedCategory] = useState<string | null>(null);

  const [matchedOrg, setMatchedOrg] = useState<{ id: string; name: string } | null>(null);
  const [matchedProject, setMatchedProject] = useState<{ id: string; name: string; project_class: string } | null>(null);
  const [isResolvingOrg, setIsResolvingOrg] = useState(false);
  const [isResolvingProject, setIsResolvingProject] = useState(false);
  const [orgLookupError, setOrgLookupError] = useState<string | null>(null);
  const [projectLookupError, setProjectLookupError] = useState<string | null>(null);

  const [isSubmittingRequest, setIsSubmittingRequest] = useState(false);
  const [submitRequestError, setSubmitRequestError] = useState<string | null>(null);
  const [, setSubmitRequestSuccess] = useState(false);
  const [requestedRole, setRequestedRole] = useState<"PROJECT_VIEWER" | "PROJECT_EDITOR" | "PROJECT_ADMIN" | "">("" );
  const [existingRoles, setExistingRoles] = useState<string[]>([]);
  const [isLoadingExistingAccess, setIsLoadingExistingAccess] = useState(false);

  const [showCancelModal, setShowCancelModal] = useState(false);
  const { success } = useToast();

  const isEditMode = Boolean(editingRow);
  const currentEditing = editingRow ?? null;

  
const ENABLED_STAGES_BY_REPORTING_STAGE: Record<
  string,
  Set<string>
> = {
  business: new Set(["Business case", "Design", "Construction"]),
  design: new Set(["Design", "Construction"]),
  construction: new Set(["Construction"]),
};


const reportingAllowedStages = useMemo(() => {
  if (!selectedReportingStage) return new Set<string>();
  return ENABLED_STAGES_BY_REPORTING_STAGE[selectedReportingStage] ?? new Set();
}, [selectedReportingStage]);


const enabledStages = useMemo(() => {
  // Editing mode → ONLY allow the stage being edited
  if (editingRow) {
    return new Set([editingRow.stage]);
  }

  // Add-mode → use reporting-stage rules
  return reportingAllowedStages;
}, [editingRow, reportingAllowedStages]);



  const hasAnyStageSelection = useMemo(() => {
    const values = Object.values(accessByStage);
    return values.some(v => v === "Can view" || v === "Can edit");
  }, [accessByStage]);


  const showStages: boolean = useMemo(() => {
    const effective = (category ?? detectedCategory ?? "").trim().toLowerCase();
    const stageBasedCategories = new Set(["small", "large"]);
    return stageBasedCategories.has(effective);
  }, [category, detectedCategory]);

  const projectEntered = projectName.trim().length > 0;
  const isValidOrgProjectPair = Boolean(matchedOrg && matchedProject);
  const showProjectValidTick = Boolean(projectEntered && matchedProject);

  const canShowAccessControls = useMemo(() => {
    if (isEditMode) return true;
    if (category) return Boolean(isUserValid);
    return isValidOrgProjectPair;
  }, [isEditMode, category, isUserValid, isValidOrgProjectPair]);

  const checkEmailExists = async (email: string): Promise<{ exists: boolean; user?: any }> => {
    const trimmed = (email || '').trim().toLowerCase();
    if (!trimmed) return { exists: false };

    const users = await UsersService.fetchUsers();
    const found = users.find((u: any) => (u.email || '').trim().toLowerCase() === trimmed);
    return { exists: Boolean(found), user: found };
  }

  useEffect(() => {
    if(isEditMode) return;
    if (!debouncedEmail.trim() || !isEmailFormatValid) {
      setIsCheckingUser(false);
      setIsUserValid(null);
      setUserLookupError(null);
      setSelectedUser(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        setIsCheckingUser(true);
        setUserLookupError(null);
        const res = await checkEmailExists(debouncedEmail.trim());
        if (cancelled) return;

        if (res.exists) {
          setIsUserValid(true);

          const opt = {
            id: res.user?.id ?? res.user?.user_id ?? debouncedEmail.trim(),
            label: res.user?.name ?? res.user?.user_name ?? debouncedEmail.trim(),
            email: res.user?.email ?? debouncedEmail.trim(),
            ...res.user,
          } as AutocompleteOption;
          setSelectedUser(opt);

        } else {
          setIsUserValid(false);
          setSelectedUser(null);
          setUserLookupError("Email not found in any organisation.");
        }
      } catch (e: any) {
        if (cancelled) return;
        setIsUserValid(null);
        setSelectedUser(null);
        setUserLookupError(e?.message || "Unable to verify email. Please try again.");
      } finally {
        if (!cancelled) setIsCheckingUser(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [debouncedEmail, isEmailFormatValid]);


  useEffect(() => {
    if (currentEditing) {
      setSelectedUser({
        id: currentEditing.id.split("-")[0],
        label: currentEditing.name,
        email: currentEditing.email,
      });
      if (showStages) {
        setAccessByStage(
          stages.reduce((acc, s) => {
            acc[s] = s === currentEditing.stage ? (currentEditing.access as AccessLevel) : "";
            return acc;
          }, {} as AccessByStage),
        );
      } else {
        setAccessType(currentEditing.access as AccessLevel);
      }
    }
  }, [currentEditing, showStages, stages]);

  const handleInputChange = useCallback((fieldName: string, value: string) => {
    if (fieldName === "project-name") setProjectName(value);
    else if (fieldName === "organisation-name") setOrgName(value);
    else if (fieldName === "justification") setJustification(value);
    else if (fieldName === "email") setEmail(value.trim());
  }, []);

  const handleStageChange = useCallback((stage: string, value: AccessLevel) => {
    if (!enabledStages.has(stage)) return;
    setAccessByStage(prev => ({ ...prev, [stage]: value }));
  }, [enabledStages]);

  const canAdd = Boolean(selectedUser && (showStages ? hasAnyStageSelection : accessType));

  const handleAddForSetup = useCallback(() => {
    if (!canAdd || !selectedUser) return;

    const rawUserId = String(selectedUser.id);
    let rows: AccessTableRow[] = [];
    if (showStages) {
      rows = stages
        .filter(s => accessByStage[s])
        .map(s => ({
          id: `${rawUserId}-${s}`,
          userId: rawUserId,
          name: selectedUser.label,
          email: (selectedUser as any)?.email,
          stage: s,
          access: accessByStage[s] as AccessLevel,
        }));
    } else {
      rows = [
        {
          id: `${rawUserId}-overall`,
          userId: rawUserId,
          name: selectedUser.label,
          email: (selectedUser as any)?.email,
          stage: "—",
          access: accessType as AccessLevel,
        },
      ];
    }
    onAddAccessRows?.(rows);
    setEmail("");
    setSelectedUser(null);
    setAccessByStage(stages.reduce((acc, s) => ({ ...acc, [s]: "" }), {} as AccessByStage));
    setAccessType("");
    onCloseRequestModal?.();
  }, [canAdd, selectedUser, showStages, stages, accessByStage, accessType, onAddAccessRows, onCloseRequestModal]);

  useEffect(() => {
    if (category) return;
    const q = debouncedOrgName.trim();
    if (!q) {
      setMatchedOrg(null);
      setOrgLookupError(null);
      setMatchedProject(null);
      setProjectLookupError(null);
      setDetectedCategory(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        setIsResolvingOrg(true);
        setOrgLookupError(null);
        const orgs = await OrganizationService.fetchAllOrganizations();
        if (cancelled) return;
        const match = orgs.find(o => o.name.toLowerCase().includes(q.toLowerCase()));
        if (match && match.id) {
          setMatchedOrg({ id: String(match.id), name: match.name });
        } else {
          setMatchedOrg(null);
          setOrgLookupError("Organisation not found.");
        }
      } catch {
        if (!cancelled) setOrgLookupError("Unable to look up organisation.");
      } finally {
        if (!cancelled) setIsResolvingOrg(false);
      }
    })();
    return () => { cancelled = true; };
  }, [category, debouncedOrgName]);

  useEffect(() => {
    if (category) return;
    const q = debouncedProjectName.trim();
    if (!q || !matchedOrg) {
      setMatchedProject(null);
      setProjectLookupError(null);
      setDetectedCategory(null);
      setExistingRoles([]);
      setRequestedRole("");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        setIsResolvingProject(true);
        setProjectLookupError(null);
        const res = await http.get<any[]>("/api/projects?limit=500");
        if (cancelled) return;
        const all: any[] = Array.isArray(res.data) ? res.data : [];
        const match = all.find(
          p =>
            String(p.proponent_org_id) === matchedOrg.id &&
            (p.project_name as string).toLowerCase() === q.toLowerCase(),
        );
        if (match) {
          setMatchedProject({ id: String(match.id), name: match.project_name, project_class: match.project_class });
          const classMap: Record<string, string> = { SMALL: "small", LARGE: "large", RECURRING: "contractor" };
          setDetectedCategory(classMap[match.project_class] ?? null);
          setIsLoadingExistingAccess(true);
          try {
            const accessRes = await http.get<{ effective_roles: string[] }>(`/api/me/access?project_id=${match.id}`);
            if (cancelled) return;
            const roles: string[] = accessRes.data?.effective_roles ?? [];
            setExistingRoles(roles);
            if (roles.includes("PROJECT_ADMIN")) setRequestedRole("PROJECT_ADMIN");
            else if (roles.includes("PROJECT_EDITOR")) setRequestedRole("PROJECT_EDITOR");
            else if (roles.includes("PROJECT_VIEWER")) setRequestedRole("PROJECT_VIEWER");
            else setRequestedRole("");
          } finally {
            if (!cancelled) setIsLoadingExistingAccess(false);
          }
        } else {
          setMatchedProject(null);
          setProjectLookupError("Project not found in that organisation. Check both names are exact.");
          setDetectedCategory(null);
          setExistingRoles([]);
          setRequestedRole("");
        }
      } catch {
        if (!cancelled) setProjectLookupError("Unable to look up project.");
      } finally {
        if (!cancelled) setIsResolvingProject(false);
      }
    })();
    return () => { cancelled = true; };
  }, [category, debouncedProjectName, matchedOrg]);

  const handleSubmit = useCallback(async () => {
    setSubmitted(true);
    setSubmitRequestError(null);

    const hasErrors =
      !orgName.trim() ||
      !projectName.trim() ||
      !isValidOrgProjectPair ||
      !requestedRole ||
      !justification.trim();

    if (hasErrors) return;

    try {
      setIsSubmittingRequest(true);
      await http.post("/api/access-requests", {
        request_type: requestedRole,
        scope_type: "PROJECT",
        scope_id: matchedProject!.id,
        project_id: matchedProject!.id,
        organisation_id: matchedOrg!.id,
        reason: justification.trim(),
        metadata: {
          requested_role: requestedRole,
          project_class: matchedProject!.project_class,
        },
      });
      success(`Your request to access ${matchedProject?.name} has been submitted`);
      setSubmitRequestSuccess(true);
      onCloseRequestModal?.();
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setSubmitRequestError(
        typeof detail === "string" ? detail : "Failed to submit request. Please try again.",
      );
    } finally {
      setIsSubmittingRequest(false);
    }
  }, [
    orgName,
    projectName,
    justification,
    isValidOrgProjectPair,
    requestedRole,
    matchedOrg,
    matchedProject,
    onCloseRequestModal,
  ]);

  const handleCancelClick = useCallback(() => {
    if (onOpenCancelModal) onOpenCancelModal();
    else setShowCancelModal(true);
  }, [onOpenCancelModal]);

  const handleDiscardChanges = useCallback(() => {
    if (onCloseAllModals) onCloseAllModals();
    else setShowCancelModal(false);
    setSubmitted(false);
    setAccessType("");
    setJustification("");
    setOrgName("");
    setProjectName("");
    setDetectedCategory(null);
    setAccessByStage(stages.reduce((acc, s) => ({ ...acc, [s]: "" }), {} as AccessByStage));
    setEmail("");
    setIsUserValid(null);
    setUserLookupError(null);
    setSelectedUser(null);
    setMatchedOrg(null);
    setMatchedProject(null);
    setOrgLookupError(null);
    setProjectLookupError(null);
    setRequestedRole("");
    setExistingRoles([]);
  }, [onCloseAllModals, stages]);

  const handleSaveEdit = useCallback(() => {
    if (!currentEditing) return;

    let updatedRow: AccessTableRow = { ...currentEditing };
    if (showStages) {
      const selectedStage = Object.keys(accessByStage).find(s => accessByStage[s]);
      if (!selectedStage) return;

      updatedRow = {
        ...currentEditing,
        stage: selectedStage,
        access: accessByStage[selectedStage] as AccessLevel,
        id: currentEditing.id,
      };
    } else {
      updatedRow = {
        ...currentEditing,
        access: accessType as AccessLevel,
        id: currentEditing.id,
      };
    }
    onUpdateAccessRow?.(updatedRow);
    onCloseRequestModal?.();
  }, [currentEditing, showStages, accessByStage, accessType, onUpdateAccessRow, onCloseRequestModal]);

  return (
    <>
      {category ? (
        <>
          <div className="mb-4 text-text-dark text-2xl">
            {isEditMode ? `Edit access for ${currentEditing?.name}` : "Search and add users"}
          </div>
          {!isEditMode && (
            <div className="mt-8 text-sm text-text-base">
            <label htmlFor="user-email">Search by email</label>
            <div className="relative">
              <input
                id="user-email"
                type="email"
                inputMode="email"
                autoComplete="email"
                value={email}
                onChange={e => setEmail(e.target.value.trim())}
                className="mt-1 h-10 block w-full p-2 rounded-[var(--radius-3)] border border-border-input focus:border-border-input focus:ring-border-input sm:text-sm text-text-table-cell"
              />
              {isUserValid && (
                <img
                  src={CheckCircle}
                  alt="Valid"
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-5 h-5"
                />
              )}
            </div>
            {submitted && !email.trim() && <FieldError message="User email is required" />}
            {!!email && !isEmailFormatValid && <FieldError message="Enter a valid email address" />}
            {isCheckingUser && <div className="text-xs text-text-faint mt-1">Checking user…</div>}
            {userLookupError && isEmailFormatValid && <FieldError message={userLookupError} />}
          </div>)}
          {canShowAccessControls && (showStages ? (
            <>
              <div className="mt-8 text-text-dark">Project stage access</div>
              <div className="mt-2 text-xs text-text-faint">Select the access type required for each project stage</div>
              <table className="w-full text-left border-collapse mt-6">
                <thead>
                  <tr className="border-b-2 border-neutral-90 text-text-dark text-sm h-10">
                    <th className="font-medium">PROJECT STAGES</th>
                    <th className="font-medium">VIEW</th>
                    <th className="px-3 py-2 font-medium">EDIT</th>
                  </tr>
                </thead>
                <tbody>
                  {stages.map(stage => {
                    const isDisabled = !enabledStages.has(stage);
                    return (
                    <tr key={stage} 
className={`border-b border-neutral-95 h-10 ${
        isDisabled ? "opacity-50 text-neutral-400" : ""
      }`}>
                      <td className="text-sm text-text-base">{stage}</td>
                      <td className="px-2 text-sm">
                        <input
                          type="radio"
                          name={`${stage}-access`}
                          value="Can view"
                          checked={accessByStage[stage] === "Can view"}
                          onChange={() => handleStageChange(stage, "Can view")}
disabled={isDisabled}
          className={`h-5 w-5 accent-primary ${
            isDisabled ? "cursor-not-allowed" : ""
          }`}
                        />
                      </td>
                      <td className="px-4 py-2 text-sm">
                        <input
                          type="radio"
                          name={`${stage}-access`}
                          value="Can edit"
                          checked={accessByStage[stage] === "Can edit"}
                          onChange={() => handleStageChange(stage, "Can edit")}
disabled={isDisabled}
          className={`h-5 w-5 accent-primary ${
            isDisabled ? "cursor-not-allowed" : ""
          }`}
                        />
                      </td>
                    </tr>
                  )})}
                </tbody>
              </table>
            </>
          ) : (
            <>
              <div className="mt-8 mb-1 text-sm text-text-base">Access</div>
              <div className="flex items-center gap-2 mb-4">
                <input
                  type="radio"
                  name="access"
                  value="Can view"
                  checked={accessType === "Can view"}
                  onChange={() => setAccessType("Can view")}
                  className="h-5 w-5 accent-primary"
                />
                <label className="text-sm text-text-table-cell">View</label>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="radio"
                  name="access"
                  value="Can edit"
                  checked={accessType === "Can edit"}
                  onChange={() => setAccessType("Can edit")}
                  className="h-5 w-5 accent-primary"
                />
                <label className="text-sm text-text-table-cell">Edit</label>
              </div>
            </>
          ))}

          <div className="mt-12 flex justify-end gap-3">
            <button
              className="cursor-pointer rounded-[var(--radius-3)] px-4 py-2.5 text-sm font-medium text-text-table-cell transition-colors hover:bg-neutral-95"
              type="button"
              onClick={handleCancelClick}
            >
              Cancel
            </button>
            <button
              className="cursor-pointer rounded-[var(--radius-3)] border bg-primary px-4 py-2.5 font-medium text-white hover:brightness-95 disabled:opacity-50 disabled:cursor-not-allowed"
              type="button"
              onClick={isEditMode ? handleSaveEdit : handleAddForSetup}
              disabled={
                isEditMode
                  ? showStages
                    ? !currentEditing || !accessByStage[currentEditing.stage]
                    : !accessType
                  : !canAdd
              }
            >
              {isEditMode ? "Save" : "Add user"}
            </button>
          </div>

          {showCancelModal && (
            <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
              <div className="bg-white p-6 rounded-[var(--radius-3)] w-full max-w-md">
                <div className="text-2xl text-text-dark">Discard changes?</div>
                <div className="mt-6 text-sm text-text-base">Are you sure you want to discard your changes?</div>
                <div className="mt-6 flex justify-end gap-3">
                  <button
                    className="cursor-pointer rounded-[var(--radius-3)] px-4 py-2.5 text-sm font-medium text-text-table-cell transition-colors hover:bg-neutral-95"
                    type="button"
                    onClick={() => setShowCancelModal(false)}
                  >
                    Keep editing
                  </button>
                  <button
                    className="cursor-pointer rounded-[var(--radius-3)] border bg-primary px-4 py-2.5 font-medium text-white hover:brightness-95"
                    type="button"
                    onClick={handleDiscardChanges}
                  >
                    Discard changes
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <>
          <div className="text-2xl font-medium text-text-dark">Request Project Access</div>
          <div className="mt-6 text-sm text-text-faint">All fields are required unless marked as optional.</div>
          <div className="mt-8 text-sm text-text-base">
            <label htmlFor="organisation-name">Organisation name</label>
            <input
              id="organisation-name"
              type="text"
              onChange={e => handleInputChange("organisation-name", e.target.value)}
              value={orgName}
              className="mt-1 h-10 block w-full p-2 rounded-[var(--radius-3)] border border-border-input focus:border-border-input focus:ring-border-input sm:text-sm text-text-table-cell"
            />
            {submitted && !orgName.trim() && <FieldError message="Organisation name is required" />}
            {isResolvingOrg && <div className="text-xs text-text-faint mt-1">Looking up organisation…</div>}
            {!isResolvingOrg && orgLookupError && orgName.trim() && <FieldError message={orgLookupError} />}
            {!isResolvingOrg && matchedOrg && <div className="text-xs text-text-faint mt-1">Matched: {matchedOrg.name}</div>}
          </div>

          <div className="mt-8 text-sm text-text-base">
            <label htmlFor="project-name">Project name</label>
            <div className="relative">
              <input
                id="project-name"
                type="text"
                value={projectName}
                onChange={e => handleInputChange("project-name", e.target.value)}
                disabled={!matchedOrg}
                placeholder={!matchedOrg ? "Enter organisation name first" : ""}
                className={`mt-1 h-10 block w-full p-2 rounded-[var(--radius-3)] border border-border-input focus:border-border-input focus:ring-border-input sm:text-sm ${!matchedOrg ? "bg-neutral-95 text-text-faint cursor-not-allowed" : "text-text-table-cell"}`}
              />
              {showProjectValidTick && (
                <img
                  src={CheckCircle}
                  alt="Valid"
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-5 h-5"
                />
              )}
            </div>
            {submitted && !projectName.trim() && <FieldError message="Project name is required" />}
            {isResolvingProject && <div className="text-xs text-text-faint mt-1">Looking up project…</div>}
            {!isResolvingProject && projectLookupError && orgName.trim() && projectName.trim() && (
              <FieldError message={projectLookupError} />
            )}
            {submitted && !isValidOrgProjectPair && orgName.trim() && projectName.trim() && !projectLookupError && (
              <FieldError message="Project could not be verified. Please check the names and try again." />
            )}
          </div>

          {isValidOrgProjectPair && (
            <>
              {isLoadingExistingAccess && (
                <div className="mt-6 text-xs text-text-faint">Checking your current access…</div>
              )}
              {!isLoadingExistingAccess && existingRoles.filter(r => r.startsWith("PROJECT_")).length > 0 && (
                <div className="mt-6 text-xs text-text-faint bg-neutral-98 border border-border-input rounded-[var(--radius-3)] px-3 py-2">
                  You currently have:{" "}
                  <strong>
                    {existingRoles
                      .filter(r => r.startsWith("PROJECT_"))
                      .map(r => r.replace("PROJECT_", "").toLowerCase())
                      .join(", ")}
                  </strong>
                  . Select a role below to request a change.
                </div>
              )}
              <div className="mt-8 text-sm font-medium text-text-dark">Requested access level</div>
              <div className="mt-2 text-xs text-text-faint">Select the access level you are requesting for this project</div>
              <div className="mt-4 flex flex-col gap-3">
                {([
                  { value: "PROJECT_VIEWER" as const, label: "View", desc: "Read-only access to project data" },
                  { value: "PROJECT_EDITOR" as const, label: "Edit", desc: "Can submit and update project reports" },
                  { value: "PROJECT_ADMIN" as const, label: "Project Admin", desc: "Can manage project members and settings" },
                ] as const).map(opt => (
                  <label
                    key={opt.value}
                    className={`flex items-start gap-3 p-3 rounded-[var(--radius-3)] border cursor-pointer transition-colors ${
                      requestedRole === opt.value
                        ? "border-primary bg-primary/5"
                        : "border-border-input hover:bg-neutral-98"
                    }`}
                  >
                    <input
                      type="radio"
                      name="requested-role"
                      value={opt.value}
                      checked={requestedRole === opt.value}
                      onChange={() => setRequestedRole(opt.value)}
                      className="mt-0.5 h-4 w-4 accent-primary"
                    />
                    <div>
                      <div className="text-sm font-medium text-text-dark">{opt.label}</div>
                      <div className="text-xs text-text-faint">{opt.desc}</div>
                    </div>
                  </label>
                ))}
              </div>
              {submitted && !requestedRole && <FieldError message="Select an access level" />}
            </>
          )}

          <div className="mt-8 text-sm text-text-base">
            <label htmlFor="justification">Justification</label>
            <textarea
              id="justification"
              onChange={e => handleInputChange("justification", e.target.value)}
              value={justification}
              className="mt-1 h-45 block w-full p-2 rounded-[var(--radius-3)] border border-border-input focus:border-border-input focus:ring-border-input sm:text-sm text-text-table-cell"
            />
            {submitted && !justification.trim() && <FieldError message="Justification is required" />}
          </div>

          {submitRequestError && (
            <div className="mt-4 text-sm text-danger">{submitRequestError}</div>
          )}

          <div className="mt-10 flex justify-end gap-3">
            <button
              className="cursor-pointer rounded-[var(--radius-3)] px-4 py-2.5 text-sm font-medium text-text-table-cell transition-colors hover:bg-neutral-95"
              type="button"
              onClick={handleCancelClick}
              disabled={isSubmittingRequest}
            >
              Cancel
            </button>
            <button
              className="cursor-pointer rounded-[var(--radius-3)] border bg-primary px-4 py-2.5 font-medium text-white hover:brightness-95 disabled:opacity-50 disabled:cursor-not-allowed"
              type="button"
              onClick={handleSubmit}
              disabled={isSubmittingRequest}
            >
              {isSubmittingRequest ? "Submitting…" : "Submit request"}
            </button>
          </div>
        </>
      )}
    </>
  );
};

export default ProjectAccess;