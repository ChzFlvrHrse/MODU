import React, { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import type { Section } from "../../../types/types";
import "./Sections.css";

import { CircularProgress } from "@mui/material";
import { ArrowBackIosNew } from '@mui/icons-material';
import SectionModal from "../../modals/SectionModal";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function fmtPages(pages?: number[]) {
    if (!pages?.length) return "—";
    if (pages.length <= 6) return pages.join(", ");
    return `${pages.slice(0, 6).join(", ")} +${pages.length - 6}`;
}

export default function Sections() {
    const [sections, setSections] = useState<Record<string, Section[]>>({});
    const [activeDivision, setActiveDivision] = useState<string>("");
    const [query, setQuery] = useState("");
    const [statusFilter, setStatusFilter] = useState<string>("all");

    const [sectionModalsOpen, setSectionModalsOpen] = useState<boolean>(false);
    const [sectionModalSectionNumber, setSectionModalSectionNumber] = useState<string>("");
    const [sectionModalSectionTitle, setSectionModalSectionTitle] = useState<string>("");

    const [sectionClassificationStatus, setSectionClassificationStatus] = useState<string>("");
    const [sectionSummaryStatus, setSectionSummaryStatus] = useState<string>("");

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

        return list.every((s) => (s.summary_status ?? "").toLowerCase() === "complete" || (s.summary_status ?? "").toLowerCase() === "failed");
    };

    const isDivisionSummaryPending = (division: string) => {
        const list = sections[division] ?? [];
        if (list.length === 0) return false;

        return list.some((s) => (s.summary_status ?? "").toLowerCase() === "pending" || (s.summary_status ?? "").toLowerCase() === "error");
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

            // if nothing selected yet, choose the first sorted division
            if (!prev) return keys[0] ?? "";

            // if current selection still exists, keep it
            if (specSections[prev]) return prev;

            // otherwise fall back to first available
            return keys[0] ?? "";
        });
    };

    const activeList = useMemo(() => {
        const list = sections[activeDivision] ?? [];

        const q = query.trim().toLowerCase();
        const filtered = list.filter((s) => {
            const matchesQuery =
                !q ||
                s.section_name?.toLowerCase().includes(q) ||
                s.section_number?.toLowerCase().includes(q);

            const matchesStatus =
                statusFilter === "all" || (s.classification_status ?? "none") === statusFilter;

            return matchesQuery && matchesStatus;
        });

        // sort by section_number (string numeric-ish)
        return filtered.sort((a, b) =>
            (a.section_number ?? "").localeCompare(b.section_number ?? "")
        );
    }, [sections, activeDivision, query, statusFilter]);

    const totalSections = useMemo(
        () => Object.values(sections).reduce((acc, arr) => acc + (arr?.length ?? 0), 0),
        [sections]
    );

    const openSectionModal = (section_id: string, section_number: string, section_title: string) => {
        setSectionModalsOpen(true);
        setSectionModalSectionNumber(section_number);
        setSectionModalSectionTitle(section_title);
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
            {sectionModalsOpen &&
                <SectionModal
                    spec_id={spec_id ?? ""}
                    section_number={sectionModalSectionNumber}
                    section_title={sectionModalSectionTitle}
                    onClose={() => setSectionModalsOpen(false)}
                />
            }

            <div className="sections-page">
                <div className="sections-header">
                    <div>
                        <button className="back-projects-button" onClick={() => navigate('/projects')}>
                            <ArrowBackIosNew fontSize="large" className="back-projects-button-icon" />
                        </button>
                        <h1 className="sections-title" >Sections</h1>
                        <h3 className="sections-project-name">Project: <b style={{ color: "#fff" }}>{project_name}</b></h3>
                        <p className="sections-subtitle">
                            Spec ID: <b style={{ color: "#fff" }}>{spec_id}</b>
                        </p>
                        <p className="sections-subtitle">
                            Browse sections by division. {totalSections} total sections.
                        </p>
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
                    {/* LEFT SIDEBAR */}
                    <aside className="division-panel">
                        <div className="division-panel-title">Divisions</div>

                        <div className="division-list">
                            {divisions.map((d) => {
                                const classification_done = isDivisionClassificationComplete(d);
                                const classification_pending = isDivisionClassificationPending(d);
                                const summary_done = isDivisionSummaryComplete(d);
                                const summary_pending = isDivisionSummaryPending(d);

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
                                            <span className="division-count">
                                                {sections[d]?.length ?? 0} sections
                                            </span>
                                            {(classification_done && summary_done) && <span className="division-check" title="All sections complete">✓</span>}
                                            {(classification_pending || summary_pending) && <CircularProgress size={18} />}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                    </aside>

                    {/* MAIN */}
                    <main className="section-panel">
                        <div className="section-panel-top">
                            <div className="section-panel-title">
                                Division {activeDivision || "—"}
                            </div>
                            <div className="section-panel-meta">
                                {activeList.length} sections
                            </div>
                        </div>

                        <div className="section-grid">
                            {activeList.map((s) => {
                                const classification_status = s.classification_status?.toUpperCase() ?? "NONE";
                                const summary_status = s.summary_status?.toUpperCase() ?? "NONE";

                                return (
                                    <div key={s.id} className="section-card" onClick={() => openSectionModal(s.id.toString(), s.section_number, s.section_name)}>
                                        <div className="section-card-top">
                                            <span className={`pill section-pill-${classification_status.toLowerCase()}`}>
                                                Classification: {classification_status}
                                            </span>
                                            <span className={`pill section-pill-${summary_status.toLowerCase()}`}>
                                                Summary: {summary_status}
                                            </span>
                                            <span className="section-number">{s.section_number}</span>
                                        </div>

                                        <div className="section-name">{s.section_name}</div>

                                        <div className="section-badges">
                                            <div className="badge">
                                                <span className="badge-label">Primary Pages</span>
                                                <span className="badge-value">{fmtPages(s.primary_pages)}</span>
                                            </div>
                                            <div className="badge">
                                                <span className="badge-label">Reference Pages</span>
                                                <span className="badge-value">{fmtPages(s.reference_pages)}</span>
                                            </div>
                                        </div>

                                        <div className="section-footer">
                                            <div className="section-footer-col">
                                                <div className="meta-label">Created</div>
                                                <div className="meta-value">{s.created_at ?? "—"}</div>
                                            </div>
                                            <div className="section-footer-col">
                                                <div className="meta-label">Updated</div>
                                                <div className="meta-value">{s.updated_at ?? "—"}</div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}

                            {activeDivision && activeList.length === 0 && (
                                <div className="sections-empty">
                                    No sections match your filters.
                                </div>
                            )}

                            {!activeDivision && (
                                <div className="sections-empty">
                                    No divisions found.
                                </div>
                            )}
                        </div>
                    </main>
                </div>
            </div>
        </>
    );
}
