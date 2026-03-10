import React, { useEffect, useMemo, useState } from "react";
import { toast } from "react-hot-toast";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import type { Section } from "../../../types/types";
import "./Sections.css";

import { CircularProgress } from "@mui/material";
import { ArrowBackIosNew, AdsClickRounded, Error } from '@mui/icons-material';
import SectionModal from "../../modals/SectionModal/SectionModal";
import PackageModal from "../../modals/PackageModal/PackageModal";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

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

    const { spec_id } = useParams();
    const [searchParams] = useSearchParams();
    const project_name = searchParams.get("project_name");

    const navigate = useNavigate();

    const divisions = useMemo(() => Object.keys(sections).sort(), [sections]);

    const isDivisionClassificationComplete = (division: string) => {
        const list = sections[division] ?? [];
        if (list.length === 0) return false;
        return list.every((s) => (s.classification_status ?? "").toLowerCase() === "complete" || (s.classification_status ?? "").toLowerCase() === "failed");
    };

    const isDivisionClassificationPending = (division: string) => {
        const list = sections[division] ?? [];
        if (list.length === 0) return false;
        return list.some((s) => (s.classification_status ?? "").toLowerCase() === "pending" || (s.classification_status ?? "").toLowerCase() === "error");
    };

    const allDivisionsClassificationComplete = useMemo(() => {
        if (divisions.length === 0) return false;
        return divisions.every((d) => isDivisionClassificationComplete(d));
    }, [divisions, sections]);

    const isDivisionSummaryComplete = (division: string) => {
        const list = sections[division] ?? [];
        if (list.length === 0) return false;
        return list.every((s) => (s.summary_status ?? "").toLowerCase() === "complete" || (s.summary_status ?? "").toLowerCase() === "failed" || (s.summary_status ?? "").toLowerCase() === "manual");
    };

    const isDivisionSummaryPending = (division: string) => {
        const list = sections[division] ?? [];
        if (list.length === 0) return false;
        return list.some((s) => (s.summary_status ?? "").toLowerCase() === "pending");
    };

    const isDivisionSummaryError = (division: string) => {
        const list = sections[division] ?? [];
        if (list.length === 0) return false;
        return list.some((s) => (s.summary_status ?? "").toLowerCase() === "error");
    };

    const allDivisionsSummaryComplete = useMemo(() => {
        if (divisions.length === 0) return false;
        return divisions.every((d) => isDivisionSummaryComplete(d));
    }, [divisions, sections]);

    const normalizeDivisions = (obj: Record<string, unknown>) =>
        Object.keys(obj).sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));

    const fetchSections = async () => {
        const response = await fetch(`${BACKEND_URL}/api/spec/spec_sections/${spec_id}`);
        const data = await response.json();
        const specSections = data.spec_sections ?? {};
        setSections(specSections);
        setActiveDivision((prev) => {
            const keys = normalizeDivisions(specSections);
            if (!prev) return keys[0] ?? "";
            if (specSections[prev]) return prev;
            return keys[0] ?? "";
        });
    };

    const activeList = useMemo(() => {
        let list = sections[activeDivision] ?? [];
        if (activeDivision === "all") {
            list = Object.values(sections).flat();
        }
        const q = query.trim().toLowerCase();
        const filtered = list.filter((s) => {
            const matchesQuery =
                !q ||
                s.section_title?.toLowerCase().includes(q) ||
                s.section_number?.toLowerCase().includes(q);
            const matchesStatus =
                statusFilter === "all" || (s.classification_status ?? "none") === statusFilter;
            return matchesQuery && matchesStatus;
        });
        return filtered.sort((a, b) =>
            (a.section_number ?? "").localeCompare(b.section_number ?? "")
        );
    }, [sections, activeDivision, query, statusFilter]);

    const totalSections = useMemo(
        () => Object.values(sections).reduce((acc, arr) => acc + (arr?.length ?? 0), 0),
        [sections]
    );

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
            'complete': '✓',
            'pending': <CircularProgress size={10} sx={{ color: 'inherit' }} />,
            'manual': <AdsClickRounded sx={{ fontSize: 15, color: 'inherit' }} />,
            'error': '✕',
            'unknown': '○',
        };
        return statusMap[status] ?? <CircularProgress size={10} sx={{ color: 'inherit' }} />;
    }

    function getSummaryStatusText(status: string) {
        const statusTextMap: Record<string, string> = {
            'manual': "GENERATE SUMMARY",
            'complete': "SUMMARIZED",
            'pending': "SUMMARIZING...",
            'error': "ERROR SUMMARIZING",
            'unknown': "SUMMARY UNKNOWN",
        };
        return statusTextMap[status] ?? "SUMMARY UNKNOWN";
    }

    function getClassificationStatusText(status: string) {
        const statusTextMap: Record<string, string> = {
            'complete': "CLASSIFIED",
            'pending': "CLASSIFYING...",
            'error': "ERROR CLASSIFYING",
            'unknown': "CLASSIFICATION UNKNOWN",
        };
        return statusTextMap[status] ?? "CLASSIFICATION UNKNOWN";
    }

    const handleGenerateSummary = async (e: React.MouseEvent<HTMLButtonElement>, spec_id: string, section_number: string) => {
        e.stopPropagation();
        setGeneratingSummaries((prev) => new Set(prev).add(section_number));
        try {
            const response = await fetch(`${BACKEND_URL}/api/summary/generate_section_summary/${spec_id}/${section_number}`, {
                method: "POST",
            });
            const data = await response.json();
            if (data.error) {
                toast.error(data.error);
                return;
            }
            toast.success(`Generated summary for ${section_number}`);
            const section = activeList.find((s) => s.section_number === section_number);
            if (section) {
                setSections((prev) => ({
                    ...prev,
                    [section.division]: prev[section.division].map((s) =>
                        s.section_number === section_number
                            ? { ...s, summary_status: "complete" }
                            : s
                    )
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

    useEffect(() => {
        if (allDivisionsClassificationComplete) return;
        const interval = setInterval(fetchSections, 5000);
        return () => clearInterval(interval);
    }, [allDivisionsClassificationComplete]);

    useEffect(() => {
        fetchSections();
    }, []);

    return (
        <>
            {sectionModalsOpen && (
                <SectionModal
                    spec_id={spec_id ?? ""}
                    section_id={sectionModalSectionId}
                    section_number={sectionModalSectionNumber}
                    section_title={sectionModalSectionTitle}
                    onClose={() => setSectionModalsOpen(false)}
                />
            )}

            {packagesModalOpen && (
                <PackageModal
                    spec_id={spec_id ?? ""}
                    section_id={packagesModalSectionId}
                    section_number={packagesModalSectionNumber}
                    section_title={packagesModalSectionTitle}
                    onClose={() => setPackagesModalOpen(false)}
                />
            )}

            <div className="sections-page">
                <div className="sections-header">
                    <div>
                        <button className="back-projects-button" onClick={() => navigate('/projects')}>
                            <ArrowBackIosNew fontSize="large" className="back-projects-button-icon" />
                        </button>
                        <h1 className="sections-title">Sections</h1>
                        <p className="sections-project-name">{project_name}</p>
                        <p className="sections-subtitle">{totalSections} sections</p>
                    </div>

                    <div className="sections-controls">
                        <input
                            className="sections-search"
                            placeholder="Search section name or number…"
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
                            <option value="pending">PENDING</option>
                            <option value="error">ERROR</option>
                            <option value="none">NONE</option>
                        </select>
                    </div>
                </div>

                <div className="sections-layout">
                    <aside className="division-panel">
                        <div className="division-panel-title">Divisions</div>
                        <div className="division-list">
                            <button
                                className={`division-item ${activeDivision === "all" ? "active" : ""}`}
                                onClick={() => setActiveDivision("all")}
                            >
                                <span className="division-left">
                                    <span className="division-code">All</span>
                                </span>
                                <span className="division-right">
                                    <span className="division-count">{totalSections} sections</span>
                                </span>
                            </button>

                            {divisions.map((d) => {
                                const classification_done = isDivisionClassificationComplete(d);
                                const classification_pending = isDivisionClassificationPending(d);
                                const summary_done = isDivisionSummaryComplete(d);
                                const summary_pending = isDivisionSummaryPending(d);
                                const summary_error = isDivisionSummaryError(d);

                                return (
                                    <button
                                        key={d}
                                        className={`division-item ${d === activeDivision ? "active" : ""}`}
                                        onClick={() => setActiveDivision(d)}
                                    >
                                        <span className="division-left">
                                            <span className="division-code">{d}</span>
                                        </span>
                                        <span className="division-right">
                                            <span className="division-count">{sections[d]?.length ?? 0} sections</span>
                                            {(classification_done && summary_done) && <span className="division-check" title="All sections complete">✓</span>}
                                            {(classification_pending || summary_pending) && <CircularProgress size={18} />}
                                            {summary_error && <Error sx={{ fontSize: 18, color: 'rgba(231,76,60,0.9)' }} />}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    </aside>

                    <div className="section-panel">
                        <div className="section-panel-top">
                            <div className="section-panel-title">Division {activeDivision || "—"}</div>
                            <div className="section-panel-meta">{activeList.length} sections</div>
                        </div>

                        <div className="section-grid">
                            {activeList.map((s) => {
                                const classification_status = s.classification_status ?? "NONE";
                                const summary_status = s.summary_status ?? "NONE";

                                return (
                                    <div key={s.id} className="section-card">
                                        <div className="section-card-header">
                                            <span className="section-number">{s.section_number}</span>
                                            <span className="section-name">{s.section_title}</span>
                                        </div>

                                        <div className="section-card-status">
                                            <span className={`pill pill-${classification_status}`}>
                                                {getStatusIcon(classification_status)} {getClassificationStatusText(classification_status)}
                                            </span>
                                            {s.summary_status === 'manual' ? (
                                                <button
                                                    className="pill pill-manual generate-summary-btn"
                                                    disabled={generatingSummaries.has(s.section_number)}
                                                    onClick={(e) => handleGenerateSummary(e, spec_id ?? "", s.section_number)}
                                                >
                                                    {generatingSummaries.has(s.section_number)
                                                        ? <CircularProgress size={10} sx={{ color: 'inherit' }} />
                                                        : <AdsClickRounded sx={{ fontSize: 12 }} />
                                                    } {generatingSummaries.has(s.section_number) ? "GENERATING..." : "GENERATE SUMMARY"}
                                                </button>
                                            ) : (
                                                <span className={`pill section-pill-${summary_status.toLowerCase()}`}>
                                                    {getStatusIcon(s.summary_status)} {getSummaryStatusText(s.summary_status)}
                                                </span>
                                            )}
                                        </div>

                                        <div className="section-metrics">
                                            <div className="section-metric">
                                                <div className="section-metric-value">{s.primary_pages?.length ?? "—"}</div>
                                                <div className="section-metric-label">Primary Pages</div>
                                            </div>
                                            <div className="section-metric-divider" />
                                            <div className="section-metric">
                                                <div className="section-metric-value">{s.reference_pages?.length ?? "—"}</div>
                                                <div className="section-metric-label">Reference Pages</div>
                                            </div>
                                        </div>

                                        <div className="section-actions">
                                            <button
                                                className="section-action-btn"
                                                onClick={() => openSectionModal(s.section_number, s.section_title)}
                                            >
                                                Summary
                                            </button>
                                            <button
                                                className="section-action-btn section-action-btn--packages"
                                                onClick={() => openPackagesModal(s.id, s.section_number, s.section_title)}
                                            >
                                                Packages
                                            </button>
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
                    </div>
                </div>
            </div>
        </>
    );
}
