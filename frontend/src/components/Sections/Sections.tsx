import React, { useEffect, useMemo, useState, useCallback } from "react";
import { toast } from "react-hot-toast";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import type { Section } from "../../../types/types";
import "./Sections.css";

import { CircularProgress } from "@mui/material";
import { ArrowBackIosNew, AdsClickRounded } from '@mui/icons-material';
import SectionSummaryModal from "../../modals/SectionSummaryModal/SectionSummaryModal";
import PackageModal from "../../modals/PackageModal/PackageModal";
import LifecycleDonut from '../LifecycleDonut/LifecycleDonut';
import PDFViewer from "../../modals/PDFViewer/PDFViewer";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// ── Types ──────────────────────────────────────────────────────────────────────

type LifecycleStatus = "pending" | "in_progress" | "complete" | "excluded";

interface DivisionLifecycle {
    complete: number;
    total: number;
    excluded: number;
    score: number;
}

interface LifecycleSummary {
    spec_id: string;
    overall_score: number;
    divisions: Record<string, DivisionLifecycle>;
}

const LIFECYCLE_CYCLE: LifecycleStatus[] = ["pending", "in_progress", "complete", "excluded"];

function nextLifecycleStatus(current: LifecycleStatus): LifecycleStatus {
    const idx = LIFECYCLE_CYCLE.indexOf(current);
    return LIFECYCLE_CYCLE[(idx + 1) % LIFECYCLE_CYCLE.length];
}

// ── Division progress bar ──────────────────────────────────────────────────────

function DivisionProgressBar({ score }: { score: number }) {
    const fillClass =
        score >= 0.8 ? "division-progress-bar__fill--high" :
            score >= 0.5 ? "division-progress-bar__fill--mid" :
                score > 0 ? "division-progress-bar__fill--low" :
                    "division-progress-bar__fill--zero";

    return (
        <div className="division-progress-bar">
            <div
                className={`division-progress-bar__fill ${fillClass}`}
                style={{ width: `${Math.round(score * 100)}%` }}
            />
        </div>
    );
}

// ── Lifecycle pill ─────────────────────────────────────────────────────────────

const LIFECYCLE_LABELS: Record<LifecycleStatus, string> = {
    pending: "Pending",
    in_progress: "In Progress",
    complete: "Complete",
    excluded: "Excluded",
};

function LifecyclePill({
    status,
    updating,
    onClick,
}: {
    status: LifecycleStatus;
    updating: boolean;
    onClick: () => void;
}) {
    return (
        <button
            className={`lifecycle-pill lifecycle-pill--${status}`}
            onClick={(e) => { e.stopPropagation(); onClick(); }}
            disabled={updating}
            title="Click to advance lifecycle status"
        >
            {updating && <CircularProgress size={8} sx={{ color: "inherit" }} />}
            {LIFECYCLE_LABELS[status]}
        </button>
    );
}

// ── Main ───────────────────────────────────────────────────────────────────────

export default function Sections() {
    const [sections, setSections] = useState<Record<string, Section[]>>({});
    const [activeDivision, setActiveDivision] = useState<string>("");
    const [query, setQuery] = useState("");
    const [statusFilter, setStatusFilter] = useState<string>("all");

    const [sectionModalsOpen, setSectionModalsOpen] = useState<boolean>(false);
    const [sectionModalSectionNumber, setSectionModalSectionNumber] = useState<string>("");
    const [sectionModalSectionTitle, setSectionModalSectionTitle] = useState<string>("");
    const [sectionModalSectionId, setSectionModalSectionId] = useState<number>(0);

    const [packagesModalOpen, setPackagesModalOpen] = useState<boolean>(false);
    const [packagesModalSectionId, setPackagesModalSectionId] = useState<number>(0);
    const [packagesModalSectionNumber, setPackagesModalSectionNumber] = useState<string>("");
    const [packagesModalSectionTitle, setPackagesModalSectionTitle] = useState<string>("");

    const [generatingSummaries, setGeneratingSummaries] = useState<Set<string>>(new Set());
    const [updatingLifecycle, setUpdatingLifecycle] = useState<Set<number>>(new Set());
    const [lifecycle, setLifecycle] = useState<LifecycleSummary | null>(null);

    const [pdfViewerOpen, setPdfViewerOpen] = useState<boolean>(false);
    const [pdfViewerPages, setPdfViewerPages] = useState<{ bytes: string, media_type: string }[]>([]);
    const [pdfViewerLoading, setPdfViewerLoading] = useState<boolean>(false);

    const { spec_id } = useParams();
    const [searchParams] = useSearchParams();
    const project_name = searchParams.get("project_name");
    const navigate = useNavigate();

    const divisions = useMemo(() => Object.keys(sections).sort(), [sections]);

    // ── Division status helpers ────────────────────────────────────────────────

    const isDivisionClassificationComplete = (division: string) => {
        const list = sections[division] ?? [];
        if (list.length === 0) return false;
        return list.every((s) => ["complete", "failed"].includes((s.classification_status ?? "").toLowerCase()));
    };

    const isDivisionClassificationPending = (division: string) => {
        const list = sections[division] ?? [];
        return list.some((s) => ["pending", "error"].includes((s.classification_status ?? "").toLowerCase()));
    };

    const allDivisionsClassificationComplete = useMemo(() => {
        if (divisions.length === 0) return false;
        return divisions.every((d) => isDivisionClassificationComplete(d));
    }, [divisions, sections]);

    const isDivisionSummaryComplete = (division: string) => {
        const list = sections[division] ?? [];
        if (list.length === 0) return false;
        return list.every((s) => ["complete", "failed", "manual"].includes((s.summary_status ?? "").toLowerCase()));
    };

    const isDivisionSummaryPending = (division: string) => {
        const list = sections[division] ?? [];
        return list.some((s) => (s.summary_status ?? "").toLowerCase() === "pending");
    };

    const isDivisionSummaryError = (division: string) => {
        const list = sections[division] ?? [];
        return list.some((s) => (s.summary_status ?? "").toLowerCase() === "error");
    };

    const normalizeDivisions = (obj: Record<string, unknown>) =>
        Object.keys(obj).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));

    // ── Fetch ──────────────────────────────────────────────────────────────────

    const fetchSections = async () => {
        const response = await fetch(`${BACKEND_URL}/api/spec/spec_sections/${spec_id}`);
        const data = await response.json();
        const specSections = data.spec_sections ?? {};
        setSections(specSections);
        setActiveDivision((prev) => {
            const keys = normalizeDivisions(specSections);
            if (!prev) return keys[0] ?? "";
            if (prev === "all") return "all";
            if (specSections[prev]) return prev;
            return keys[0] ?? "";
        });
    };

    const fetchLifecycle = useCallback(async () => {
        if (!spec_id) return;
        const res = await fetch(`${BACKEND_URL}/api/spec/lifecycle/summary/${spec_id}`);
        const data = await res.json();
        if (data.success) setLifecycle(data.summary);
    }, [spec_id]);

    const fetchPdfViewerUrls = async (e: React.MouseEvent<HTMLDivElement>, section_number: string, page_type: "primary" | "reference") => {
        e.stopPropagation();
        e.preventDefault();
        setPdfViewerOpen(true);
        setPdfViewerLoading(true);
        const response = await fetch(`${BACKEND_URL}/api/spec/section_pdf_pages?spec_id=${spec_id}&section_number=${section_number}`);
        const data = await response.json();
        try {
            if (data.success) {
                if (page_type === "primary") {
                    setPdfViewerPages(data.primary_pdf_pages);
                } else {
                    setPdfViewerPages(data.reference_pdf_pages);
                }
            } else {
                toast.error("Failed to fetch PDF viewer URLs.");
            }
        } catch (error) {
            console.error(error);
            toast.error("Failed to fetch PDF viewer URLs.");
        }
        setPdfViewerLoading(false);
    };

    // ── Lifecycle update ───────────────────────────────────────────────────────

    const handleLifecycleClick = async (section: Section) => {
        const current = (section.lifecycle_status ?? "pending") as LifecycleStatus;
        const next = nextLifecycleStatus(current);

        setUpdatingLifecycle((prev) => new Set(prev).add(section.id));

        setSections((prev) => ({
            ...prev,
            [section.division]: prev[section.division].map((s) =>
                s.id === section.id ? { ...s, lifecycle_status: next } : s
            ),
        }));

        try {
            const res = await fetch(`${BACKEND_URL}/api/spec/lifecycle/${section.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ lifecycle_status: next, override: true }),
            });
            if (!res.ok) {
                toast.error("Failed to update lifecycle status.");
                setSections((prev) => ({
                    ...prev,
                    [section.division]: prev[section.division].map((s) =>
                        s.id === section.id ? { ...s, lifecycle_status: current } : s
                    ),
                }));
                return;
            }
            await fetchLifecycle();
        } catch {
            toast.error("Network error updating lifecycle.");
        } finally {
            setUpdatingLifecycle((prev) => {
                const n = new Set(prev);
                n.delete(section.id);
                return n;
            });
        }
    };

    // ── Active list ────────────────────────────────────────────────────────────

    const activeList = useMemo(() => {
        let list = sections[activeDivision] ?? [];
        if (activeDivision === "all") list = Object.values(sections).flat();
        const q = query.trim().toLowerCase();
        return list
            .filter((s) => {
                const matchesQuery =
                    !q ||
                    s.section_title?.toLowerCase().includes(q) ||
                    s.section_number?.toLowerCase().includes(q);
                const normalizedClassification = (s.classification_status ?? "none").toLowerCase();
                const normalizedSummary = (s.summary_status ?? "none").toLowerCase();
                const normalizedLifecycle = (s.lifecycle_status ?? "pending").toLowerCase();
                const matchesStatus =
                    statusFilter === "all" ||
                    normalizedClassification === statusFilter ||
                    normalizedSummary === statusFilter ||
                    normalizedLifecycle === statusFilter;
                return matchesQuery && matchesStatus;
            })
            .sort((a, b) => (a.section_number ?? "").localeCompare(b.section_number ?? ""));
    }, [sections, activeDivision, query, statusFilter]);

    const totalSections = useMemo(
        () => Object.values(sections).reduce((acc, arr) => acc + (arr?.length ?? 0), 0),
        [sections]
    );

    // ── Handlers ───────────────────────────────────────────────────────────────

    const openSectionModal = (section_number: string, section_title?: string) => {
        const section = activeList.find((s) => s.section_number === section_number);
        if (section?.summary_status === "manual") {
            toast.error("Summary for this section is manual. Please generate it first.");
            return;
        }
        setSectionModalSectionId(section?.id ?? 0);
        setSectionModalSectionNumber(section_number);
        setSectionModalSectionTitle(section_title ?? "Undocumented Section Number (MSF2020)");
        setSectionModalsOpen(true);
    };

    const openPackagesModal = (section_id: number, section_number: string, section_title?: string) => {
        setPackagesModalSectionId(section_id);
        setPackagesModalSectionNumber(section_number);
        setPackagesModalSectionTitle(section_title ?? "");
        setPackagesModalOpen(true);
    };

    function getStatusIcon(status: string) {
        const statusMap: Record<string, React.ReactNode> = {
            complete: '✓',
            pending: <CircularProgress size={10} sx={{ color: 'inherit' }} />,
            manual: <AdsClickRounded sx={{ fontSize: 15, color: 'inherit' }} />,
            error: '✕',
            unknown: '○',
            failed: '✕',
        };
        return statusMap[status] ?? <CircularProgress size={10} sx={{ color: 'inherit' }} />;
    }

    function getSummaryStatusText(status: string) {
        const statusTextMap: Record<string, string> = {
            manual: "MANUAL", complete: "SUMMARIZED", pending: "SUMMARIZING...",
            error: "ERROR SUMMARIZING", unknown: "SUMMARY UNKNOWN", failed: "SUMMARY FAILED",
        };
        return statusTextMap[status] ?? "SUMMARY UNKNOWN";
    }

    function getClassificationStatusText(status: string) {
        const statusTextMap: Record<string, string> = {
            complete: "CLASSIFIED", pending: "CLASSIFYING...", error: "ERROR CLASSIFYING",
            unknown: "CLASSIFICATION UNKNOWN", failed: "CLASSIFICATION FAILED",
        };
        return statusTextMap[status] ?? "CLASSIFICATION UNKNOWN";
    }

    const handleGenerateSummary = async (
        e: React.MouseEvent<HTMLButtonElement>,
        spec_id: string,
        section_number: string
    ) => {
        e.stopPropagation();
        setGeneratingSummaries((prev) => new Set(prev).add(section_number));
        try {
            const response = await fetch(`${BACKEND_URL}/api/summary/generate_section_summary`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ spec_id, section_number }),
            });
            const data = await response.json();
            if (data.error) { toast.error(data.error); return; }
            toast.success(`Generated summary for ${section_number}`);
            const section = activeList.find((s) => s.section_number === section_number);
            if (section) {
                setSections((prev) => ({
                    ...prev,
                    [section.division]: prev[section.division].map((s) =>
                        s.section_number === section_number ? { ...s, summary_status: "complete" } : s
                    ),
                }));
            }
        } finally {
            setGeneratingSummaries((prev) => {
                const newSet = new Set(prev);
                newSet.delete(section_number);
                return newSet;
            });
        }
    };

    // ── Effects ────────────────────────────────────────────────────────────────

    useEffect(() => {
        if (allDivisionsClassificationComplete) return;
        const interval = setInterval(fetchSections, 5000);
        return () => clearInterval(interval);
    }, [allDivisionsClassificationComplete]);

    useEffect(() => { fetchSections(); }, []);
    useEffect(() => { fetchLifecycle(); }, [fetchLifecycle]);

    // ── Render ─────────────────────────────────────────────────────────────────

    return (
        <>
            {/* Section summary modal */}
            {sectionModalsOpen && (
                <SectionSummaryModal
                    spec_id={spec_id ?? ""}
                    section_id={sectionModalSectionId}
                    section_number={sectionModalSectionNumber}
                    section_title={sectionModalSectionTitle}
                    onClose={() => setSectionModalsOpen(false)}
                />
            )}
            {/* Packages modal */}
            {packagesModalOpen && (
                <PackageModal
                    spec_id={spec_id ?? ""}
                    section_id={packagesModalSectionId}
                    section_number={packagesModalSectionNumber}
                    section_title={packagesModalSectionTitle}
                    onClose={() => setPackagesModalOpen(false)}
                />
            )}
            {/* PDF viewer modal */}
            {pdfViewerOpen && (
                <PDFViewer
                    pdfPages={pdfViewerPages}
                    loading={pdfViewerLoading}
                    onClose={() => {
                        setPdfViewerOpen(false);
                        setPdfViewerPages([]);
                    }}
                />
            )}

            <div className="sections-page">
                <div className="sections-header-shell">
                    <div className="sections-header">
                        <div className="sections-header-left">
                            <button className="back-projects-button" onClick={() => navigate('/projects')}>
                                <ArrowBackIosNew fontSize="small" className="back-projects-button-icon" />
                                <span>Back</span>
                            </button>
                            <div className="sections-kicker">Workspace</div>
                            <h1 className="sections-title">Sections</h1>
                            <p className="sections-project-name">{project_name}</p>
                            <div className="sections-subtitle-row">
                                <span className="sections-subtitle">{totalSections} sections</span>
                                {lifecycle && (
                                    <>
                                        <LifecycleDonut score={lifecycle.overall_score} size={43} showLabel={false} />
                                        <span className="sections-subtitle-progress">
                                            {lifecycle.overall_score < 0.01 ? lifecycle.overall_score.toFixed(4) : Math.round(lifecycle.overall_score * 100)}% complete
                                        </span>
                                    </>
                                )}
                            </div>
                        </div>

                        <div className="sections-controls">
                            <input
                                className="sections-search"
                                placeholder="Search section name or number..."
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                            />
                            <select
                                className="sections-select"
                                value={statusFilter}
                                onChange={(e) => setStatusFilter(e.target.value)}
                            >
                                <option value="all">ALL STATUSES</option>
                                <option value="complete">COMPLETE</option>
                                <option value="in progress">IN PROGRESS</option>
                                <option value="excluded">EXCLUDED</option>
                                <option value="pending">PENDING</option>
                                <option value="error">ERROR</option>
                                <option value="manual">MANUAL</option>
                                <option value="failed">FAILED</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div className="sections-layout">
                    <aside className="division-rail-card">
                        <div className="division-rail-header">
                            <div className="division-rail-title">Divisions</div>
                        </div>

                        <div className="division-rail-list">
                            <button
                                className={`division-row${activeDivision === "all" ? " active" : ""}`}
                                onClick={() => setActiveDivision("all")}
                            >
                                <span className="division-row-left">
                                    <span className="division-row-code">All</span>
                                </span>
                                <span className="division-row-right">
                                    <span className="division-row-count">{totalSections} sections</span>
                                    <span className="division-row-indicator neutral">•</span>
                                </span>
                            </button>

                            {divisions.map((d) => {
                                const classification_done = isDivisionClassificationComplete(d);
                                const classification_pending = isDivisionClassificationPending(d);
                                const summary_done = isDivisionSummaryComplete(d);
                                const summary_pending = isDivisionSummaryPending(d);
                                const summary_error = isDivisionSummaryError(d);
                                const divScore = lifecycle?.divisions[d]?.score ?? 0;

                                return (
                                    <button
                                        key={d}
                                        className={`division-row${d === activeDivision ? " active" : ""}`}
                                        onClick={() => setActiveDivision(d)}
                                    >
                                        <span className="division-row-left">
                                            <span className="division-row-code">{d}</span>
                                        </span>
                                        <span className="division-row-right">
                                            <span className="division-row-count">{sections[d]?.length ?? 0} sections</span>
                                            {(classification_done && summary_done) && (
                                                <span className="division-row-indicator success">✓</span>
                                            )}
                                            {(classification_pending || summary_pending) && (
                                                <span className="division-row-spinner">
                                                    <CircularProgress size={14} sx={{ color: "inherit" }} />
                                                </span>
                                            )}
                                            {summary_error && (
                                                <span className="division-row-indicator error">!</span>
                                            )}
                                            <LifecycleDonut score={divScore} size={28} showLabel={false} />
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    </aside>

                    <section className="sections-main">
                        {activeDivision !== "all" && lifecycle?.divisions[activeDivision] && (
                            <div className="sections-main-header-card sections-main-header-card--column">
                                <div className="sections-main-header-row">
                                    <div className="sections-main-header-title">
                                        Division {activeDivision}
                                    </div>
                                    <div className="sections-main-header-meta-group">
                                        <span className="sections-main-header-meta">
                                            {lifecycle.divisions[activeDivision].complete} / {lifecycle.divisions[activeDivision].total} complete
                                        </span>
                                        <span className="sections-main-header-meta">
                                            {activeList.length} sections
                                        </span>
                                    </div>
                                </div>
                                <DivisionProgressBar score={lifecycle.divisions[activeDivision].score} />
                            </div>
                        )}

                        {activeDivision === "all" && (
                            <div className="sections-main-header-card">
                                <div className="sections-main-header-title">All Sections</div>
                                <div className="sections-main-header-meta">{activeList.length} sections</div>
                            </div>
                        )}

                        <div className="section-grid">
                            {activeList.map((s) => {
                                const classification_status = (s.classification_status ?? "none").toLowerCase();
                                const summary_status = (s.summary_status ?? "none").toLowerCase();
                                const lifecycle_status = (s.lifecycle_status ?? "pending") as LifecycleStatus;

                                return (
                                    <div key={s.id} className="section-card system-card">
                                        <div className="section-card-header">
                                            <span className="section-number">{s.section_number}</span>
                                            <div className="section-title-block">
                                                <span className="section-name">{s.section_title}</span>
                                            </div>
                                            <div className="lifecycle-pill-container">
                                                <span className="lifecycle-pill-label">LIFECYCLE</span>
                                                <LifecyclePill
                                                    status={lifecycle_status}
                                                    updating={updatingLifecycle.has(s.id)}
                                                    onClick={() => handleLifecycleClick(s)}
                                                />
                                            </div>
                                        </div>

                                        <div className="section-card-status">
                                            <span className={`status-pill status-pill-${classification_status}`}>
                                                {getStatusIcon(classification_status)} {getClassificationStatusText(classification_status)}
                                            </span>
                                            {summary_status !== "manual" && (
                                                <span className={`status-pill status-pill-${summary_status}`}>
                                                    {getStatusIcon(summary_status)} {getSummaryStatusText(summary_status)}
                                                </span>
                                            )}
                                        </div>

                                        <div className="metrics-row metrics-row-sections">
                                            <div
                                                className="metric page-metric"
                                                onClick={(e) => fetchPdfViewerUrls(e, s.section_number, "primary")}
                                            >
                                                <div className="metric-value">{s.primary_pages?.length ?? "—"}</div>
                                                <div className="metric-label">Primary Pages</div>
                                            </div>
                                            <div className="metric-divider" />
                                            <div
                                                className="metric page-metric"
                                                onClick={(e) => fetchPdfViewerUrls(e, s.section_number, "reference")}
                                            >
                                                <div className="metric-value">{s.reference_pages?.length ?? "—"}</div>
                                                <div className="metric-label">Reference Pages</div>
                                            </div>
                                        </div>

                                        <div className="section-actions">
                                            <button
                                                className="section-action-btn"
                                                onClick={() => openSectionModal(s.section_number, s.section_title)}
                                            >
                                                Summary
                                            </button>
                                            {summary_status === "manual" ? (
                                                <button
                                                    className="section-action-btn section-action-btn--primary"
                                                    disabled={generatingSummaries.has(s.section_number)}
                                                    onClick={(e) => handleGenerateSummary(e, spec_id ?? "", s.section_number)}
                                                >
                                                    {generatingSummaries.has(s.section_number) ? "Generating..." : "Generate Summary"}
                                                </button>
                                            ) : (
                                                <button
                                                    className="section-action-btn section-action-btn--primary"
                                                    onClick={() => openPackagesModal(s.id, s.section_number, s.section_title)}
                                                >
                                                    Packages
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}

                            {activeDivision && activeList.length === 0 && (
                                <div className="sections-empty">No sections match your filters.</div>
                            )}
                            {!activeDivision && (
                                <div className="sections-empty">No divisions found.</div>
                            )}
                        </div>
                    </section>
                </div>
            </div>
        </>
    );
}
