import { Modal } from "../../components/common/Modal";
import AutoComplete, { type AutocompleteOption } from "../../components/common/AutoComplete";
import AustroadsLogo from "../../assets/icons/Austroads-logo.png";
import { useEffect, useState } from "react";
import FieldError from "../../components/common/FieldError";
import { SelectListbox } from "../../components/common/Select";
import CheckCircle from "../../assets/icons/check-circle-green.svg";
import InfoTooltip from "../../components/common/InfoTooltip";
import Info from "../../assets/icons/info.svg";
import { useUser } from "../../context/UserContext";
import http from "@/http";
import OrganizationService from "../../services/organization.service";
import { extractApiError } from "@/utils/utils";

type Step = "register" | "success";

type RegisterErrors = {
    name?: string | null;
    organisation?: string | null;
    location?: string | null;
    region?: string | null;
    terms?: string | null;
};

type Jurisdiction = {
    id: string;
    name: string;
    code: string;
    type: string;
    parent_id: string | null;
};

const noop = () => {};

// Fetches the currently active version of a legal document and renders its PDF inline.
const LegalDocumentModal = ({ isOpen, onClose, title, documentType }: { isOpen: boolean; onClose: () => void; title: string; documentType: "PICS" | "TERMS_OF_USE" }) => {
    const [doc, setDoc] = useState<{ id: string; filename: string } | null>(null);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!isOpen) return;
        setLoading(true);
        setLoadError(null);
        setDoc(null);
        http.get(`/api/terms-documents/${documentType}`)
            .then((res) => setDoc({ id: res.data.id, filename: res.data.filename }))
            .catch((err) => {
                setLoadError(err?.response?.status === 404
                    ? 'No document has been uploaded yet.'
                    : extractApiError(err, 'Unable to load document.'));
            })
            .finally(() => setLoading(false));
    }, [isOpen, documentType]);

    return (
        <Modal isOpen={isOpen} onClose={onClose} className="max-w-3xl p-8">
            <h2 className="text-xl font-semibold mb-4">{title}</h2>
            <div className="h-[70vh]">
                {loading && <p className="text-sm text-text-faint">Loading…</p>}
                {!loading && loadError && <p className="text-sm text-red-600">{loadError}</p>}
                {!loading && !loadError && doc && (
                    <iframe
                        src={`/api/terms-documents/${documentType}/${doc.id}/file`}
                        title={title}
                        className="w-full h-full border border-border-input rounded-[var(--radius-3)]"
                    />
                )}
            </div>
            <div className="mt-6 flex justify-end">
                <button className="bg-primary text-white px-4 py-2 rounded" onClick={onClose}>Close</button>
            </div>
        </Modal>
    );
};

const PersonalInformationCollectionStatementModal = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => (
    <LegalDocumentModal isOpen={isOpen} onClose={onClose} title="Personal Information Collection Statement" documentType="PICS" />
);

const TermsOfUseModal = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => (
    <LegalDocumentModal isOpen={isOpen} onClose={onClose} title="CMRT Terms of Use" documentType="TERMS_OF_USE" />
);

// Shown when Azure Easy Auth has authenticated a caller with no CMRT account yet.
// Blocks the rest of the app until registration completes.
const RegisterForm = () => {
    const { pendingEmail, refreshUser } = useUser();

    const [step, setStep] = useState<Step>("register");
    const [regName, setRegName] = useState("");
    const [organisation, setOrganisation] = useState("");
    const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
    const [location, setLocation] = useState<Jurisdiction | null>(null);
    const [region, setRegion] = useState<Jurisdiction | null>(null);
    const [isProponent, setIsProponent] = useState(false);
    const [regErrors, setRegErrors] = useState<RegisterErrors>({});
    const [regSubmitting, setRegSubmitting] = useState(false);
    const [successOrgName, setSuccessOrgName] = useState("");
    const [locationOptions, setLocationOptions] = useState<Jurisdiction[]>([]);
    const [regionOptions, setRegionOptions] = useState<Jurisdiction[]>([]);
    const [acceptLegalTerms, setAcceptLegalTerms] = useState(false);
    const [showPicsModal, setShowPicsModal] = useState(false);
    const [showTermsModal, setShowTermsModal] = useState(false);

    const isOrgInList = selectedOrgId !== null && organisation.trim().length > 0;
    const isNewOrg = !isOrgInList && organisation.trim().length > 0;

    useEffect(() => {
        if (!isProponent) {
            setLocation(null);
            setRegion(null);
            setLocationOptions([]);
            setRegionOptions([]);
            return;
        }

        const fetchLocations = async () => {
            try {
                const res = await http.get("/api/jurisdictions?type=Country");
                setLocationOptions(Array.isArray(res?.data) ? res.data : []);
            } catch (err) {
                console.error("Failed to fetch locations", err);
                setLocationOptions([]);
            }
        };

        fetchLocations();
    }, [isProponent]);

    useEffect(() => {
        if (!isProponent || !location?.id) {
            setRegion(null);
            setRegionOptions([]);
            return;
        }

        const fetchRegions = async () => {
            try {
                const res = await http.get(`/api/jurisdictions?parent_id=${location.id}`);
                setRegionOptions(Array.isArray(res?.data) ? res.data : []);
            } catch (err) {
                console.error("Failed to fetch regions", err);
                setRegionOptions([]);
            }
        };

        fetchRegions();
    }, [isProponent, location?.id]);

    const loadOrgOptions = async (): Promise<AutocompleteOption[]> => {
        try {
            const all = await OrganizationService.fetchAllOrganizations();
            return all.map((o) => ({ label: o.name, value: String(o.id ?? '') }));
        } catch { return []; }
    };

    const optionFilter = (opt: AutocompleteOption, input: string) => {
        const q = input.trim().toLowerCase();
        return !q || (opt.label || "").toLowerCase().includes(q);
    };

    const handleOrgSelect = (opt: AutocompleteOption) => {
        setOrganisation(opt.label);
        setSelectedOrgId(String(opt.value));
        setLocation(null);
        setIsProponent(false);
        if (regErrors.organisation) setRegErrors((p) => ({ ...p, organisation: null }));
    };

    const validateRegister = (): boolean => {
        const errs: RegisterErrors = {};
        if (!regName.trim()) errs.name = "Name is required";
        if (!organisation.trim()) errs.organisation = "Organisation is required";
        if (isNewOrg && isProponent && !location) errs.location = "Location is required";
        if (!acceptLegalTerms) {
            errs.terms =
                "You must acknowledge the Personal Information Collection Statement and CMRT Terms of Use";
        }
        setRegErrors(errs);
        return Object.keys(errs).length === 0;
    };

    const handleRegister = async () => {
        if (!validateRegister()) return;
        setRegSubmitting(true);
        setRegErrors({});
        const parts = regName.trim().split(/\s+/);
        const payload: Record<string, unknown> = {
            first_name: parts[0],
            last_name: parts.slice(1).join(' ') || undefined,
            accepted_pics: acceptLegalTerms,
            accepted_terms: acceptLegalTerms,
        };
        if (isOrgInList) {
            payload.organisation_id = selectedOrgId;
        } else {
            payload.org_name = organisation.trim();
            payload.org_type = isProponent ? 'DESIGNERS' : 'CONTRACTORS';
            payload.is_proponent = isProponent;
            payload.org_country = location?.name || undefined;
            if (isProponent && region) {
                payload.region = region.name;
                payload.region_id = region.id;
            }
        }
        try {
            await http.post('/api/identity/register', payload);
            if (isNewOrg && isProponent) {
                setSuccessOrgName(organisation.trim());
                setStep("success");
            } else {
                await refreshUser();
            }
        } catch (err: any) {
            const detail = extractApiError(err, 'Registration failed. Please try again.');
            if (err?.response?.status === 409) {
                setRegErrors({ organisation: 'This email is already registered.' });
            } else {
                setRegErrors({ organisation: detail });
            }
        } finally {
            setRegSubmitting(false);
        }
    };

    const GeneralAccessInfo = () => (
        <div className="bg-info-bg border border-info-border/35 rounded-[var(--radius-3)] flex items-start mt-3 p-3 text-sm text-info-border">
            <img src={Info} alt="Info" className="inline-block mr-2.5 mt-0.5 w-4.5 h-4.5 shrink-0" />
            <div>
                You'll be given general user access, which lets you request access to projects, complete project data for submission, and view project results.
            </div>
        </div>
    );

    const Header = () => (
        <>
            <img src={AustroadsLogo} alt="Austroads Logo" className="mx-auto h-28 w-auto mb-6" />
            <div className="text-[20px] font-light text-text-dark text-center mb-10">
                Carbon Measurement & Reporting Tool
            </div>
        </>
    );

    if (step === "success") {
        return (
            <Modal isOpen onClose={noop} className="max-w-150 p-10" disableBackdropClose disableEscClose>
                <Header />
                <div className="p-4 text-sm bg-light-green border border-success/35 rounded-[var(--radius-3)] flex">
                    <img src={CheckCircle} alt="Success" className="inline-block mr-2.5 mt-1 w-5 h-5 shrink-0" />
                    <div className="flex flex-col text-success">
                        <div className="font-bold mb-2">Your request to create {successOrgName} has been submitted</div>
                        <div>You'll be appointed as its administrator once Austroads confirms the organisation.</div>
                    </div>
                </div>
                <button
                    className="mt-12 w-full text-text-table-cell cursor-pointer text-base font-medium border border-text-table-cell py-3.25 rounded-[var(--radius-3)]"
                    onClick={() => refreshUser()}
                >
                    Continue
                </button>
            </Modal>
        );
    }

    const regBtnLabel = isNewOrg && isProponent ? "Create Organisation & Register" : "Register";
    const registerDisabled = regSubmitting || !acceptLegalTerms;

    return (
        <>
        <PersonalInformationCollectionStatementModal isOpen={showPicsModal} onClose={() => setShowPicsModal(false)} />
        <TermsOfUseModal isOpen={showTermsModal} onClose={() => setShowTermsModal(false)} />
        <Modal isOpen onClose={noop} className="max-w-150 p-10" disableBackdropClose disableEscClose>
            <Header />

            <div className="mb-6">
                <label className="block text-sm text-text-base mb-1">Full Name</label>
                <input
                    type="text"
                    className="h-10 w-full border border-border-input rounded-[var(--radius-3)] p-3"
                    value={regName}
                    onChange={(e) => { setRegName(e.target.value); if (regErrors.name) setRegErrors(p => ({ ...p, name: null })); }}
                />
                {regErrors.name && <FieldError message={regErrors.name} />}
            </div>

            <div className="mb-6">
                <label className="block text-sm text-text-base mb-1">Email</label>
                <input
                    type="email"
                    className="h-10 w-full border border-border-input rounded-[var(--radius-3)] p-3 bg-gray-50 cursor-not-allowed"
                    value={pendingEmail ?? ''}
                    disabled
                    readOnly
                />
                <p className="text-xs text-text-faint mt-1">Verified by Azure Easy Auth and cannot be changed.</p>
            </div>

            <div className="mb-6">
                <div className="relative">
                    <AutoComplete
                        label="Organisation"
                        value={organisation}
                        onChange={(val) => {
                            setOrganisation(val);
                            setSelectedOrgId(null);
                            setLocation(null);
                            setIsProponent(false);
                            if (regErrors.organisation) setRegErrors(p => ({ ...p, organisation: null }));
                        }}
                        onSelect={handleOrgSelect}
                        loadOptions={loadOrgOptions}
                        filterFn={optionFilter}
                        id="organisation"
                        className="w-full"
                        minLength={1}
                        enableInlineCompletion
                        materialIconName="Search"
                        isLoginPage={true}
                    />
                    {isOrgInList && (
                        <span className="absolute right-3 top-8 text-success">
                            <img src={CheckCircle} alt="Check" className="w-5 h-5" />
                        </span>
                    )}
                </div>
                {regErrors.organisation && <FieldError message={regErrors.organisation} />}
                {isOrgInList && <GeneralAccessInfo />}
            </div>

            {isNewOrg && (
                <>
                    <div className="mb-6">
                        <label className="inline-flex items-start gap-2 text-sm text-text-base cursor-pointer">
                            <input
                                type="checkbox"
                                className="form-checkbox h-5 w-5 mt-0.5 text-primary shrink-0"
                                checked={isProponent}
                                onChange={(e) => {
                                    setIsProponent(e.target.checked);
                                    if (!e.target.checked) setLocation(null);
                                }}
                            />
                            <span>
                                Is this organisation a Proponent or Local Government that will be creating and managing projects in the tool?
                            </span>
                            <InfoTooltip
                                text="This is intended only for proponents and Local Government Approvers"
                                iconSize={16}
                                trigger="auto"
                                placement="top"
                                offset={10}
                                arrowOffset={23}
                            />
                        </label>
                        {!isProponent && <GeneralAccessInfo />}
                    </div>

                    {isProponent && (
                        <>
                            <div className="mb-6">
                                <SelectListbox
                                    label="Location"
                                    placeholder="Select location"
                                    options={locationOptions.map(loc => ({ label: loc.name, value: loc.id, _data: loc }))}
                                    value={location?.id ?? ""}
                                    onChange={(id) => {
                                        const selected = locationOptions.find(l => l.id === id) ?? null;
                                        setLocation(selected);
                                        setRegion(null);
                                        setRegionOptions([]);
                                        if (regErrors.location) setRegErrors(p => ({ ...p, location: null }));
                                    }}
                                    className="w-full"
                                />
                                {regErrors.location && <FieldError message={regErrors.location} />}
                            </div>

                            {location && (
                                <div className="mb-6">
                                    <SelectListbox
                                        label="Region"
                                        placeholder="Select region"
                                        options={regionOptions.map(reg => ({ label: reg.name, value: reg.id }))}
                                        value={region?.id ?? ""}
                                        onChange={(id) => {
                                            const selected = regionOptions.find(r => r.id === id) ?? null;
                                            setRegion(selected);
                                            if (regErrors.region) setRegErrors(p => ({ ...p, region: null }));
                                        }}
                                        className="w-full"
                                    />
                                    {regErrors.region && <FieldError message={regErrors.region} />}
                                </div>
                            )}
                        </>
                    )}
                </>
            )}

            <div className="mb-4 mt-6 border-t border-border-input pt-6">
                <label className="flex items-start gap-2 text-sm text-text-base cursor-pointer mt-2">
                    <input
                        type="checkbox"
                        className="form-checkbox h-5 w-5 mt-0.5 text-primary shrink-0"
                        checked={acceptLegalTerms}
                        onChange={(e) => {
                            setAcceptLegalTerms(e.target.checked);
                            if (regErrors.terms) {
                                setRegErrors(p => ({
                                    ...p,
                                    terms: null,
                                }));
                            }
                        }}
                    />

                    <span>
                        I have read the{' '}
                        <button
                            type="button"
                            className="text-primary underline"
                            onClick={() => setShowPicsModal(true)}
                        >
                            Personal Information Collection Statement
                        </button>{' '}
                        and acknowledge that access to the CMRT is subject to the{' '}
                        <button
                            type="button"
                            className="text-primary underline"
                            onClick={() => setShowTermsModal(true)}
                        >
                            CMRT Terms of Use
                        </button>.
                        If I access the CMRT on behalf of an organisation, I confirm that I am
                        authorised to accept the Terms of Use on that organisation's behalf. If
                        I access the CMRT as a sole trader, I accept the Terms of Use on my own
                        behalf.
                    </span>
                </label>
                {regErrors.terms && <FieldError message={regErrors.terms} />}
            </div>
            <button
                className="w-full bg-primary text-white cursor-pointer py-3.25 rounded-[var(--radius-3)] hover:bg-primary-dark transition-colors mt-4 disabled:opacity-60"
                onClick={handleRegister}
                disabled={registerDisabled}
            >
                {regSubmitting ? 'Please wait…' : regBtnLabel}
            </button>
        </Modal>
        </>
    );
};

export default RegisterForm;
