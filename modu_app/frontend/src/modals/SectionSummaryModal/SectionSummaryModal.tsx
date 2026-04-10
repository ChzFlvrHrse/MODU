import React, { useState, useEffect, useCallback } from 'react';
import { jsPDF } from "jspdf";
import { Download as DownloadIcon } from '@mui/icons-material';
import { CircularProgress } from "@mui/material";
import { Close, Delete } from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import './SectionSummaryModal.css';

interface SpecSummary {
    id: number;
    section_id: number;
    section_number: string;
    section_title: string;
    spec_id: string;
    overview: string;
    key_requirements: string;
    materials: string;
    related_sections: string;
    submittals: string;
    testing: string;
    pages_summarized: string;
    pages_not_summarized: string;
    created_at: string;
    updated_at: string;
}


interface SectionModalProps {
    section_id: number;
    onClose: () => void;
}

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const parseJsonField = (field: string): string[] => {
    try {
        const parsed = JSON.parse(field);
        return Array.isArray(parsed) ? parsed : [];
    } catch {
        return [];
    }
};

type TabKey = 'overview' | 'key_requirements' | 'materials' | 'related_sections' | 'submittals' | 'testing';

const TAB_CONFIG: { key: TabKey; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'key_requirements', label: 'Requirements' },
    { key: 'materials', label: 'Materials' },
    { key: 'related_sections', label: 'Related Sections' },
    { key: 'submittals', label: 'Submittals' },
    { key: 'testing', label: 'Testing' },
];

function EmptyState({ label }: { label: string }) {
    return (
        <div className="sm-empty">
            <span className="sm-empty-icon">∅</span>
            <p>No {label.toLowerCase()} specified for this section.</p>
        </div>
    );
}

function ListTab({ items, label }: { items: string[]; label: string }) {
    if (!items.length) return <EmptyState label={label} />;
    return (
        <ul className="sm-list">
            {items.map((item, i) => (
                <li key={i} className="sm-list-item">
                    <span className="sm-list-index">{String(i + 1).padStart(2, '0')}</span>
                    <span className="sm-list-text">{item}</span>
                </li>
            ))}
        </ul>
    );
}

export default function SectionSummaryModal({ section_id, onClose }: SectionModalProps) {
    const [summary, setSummary] = useState<SpecSummary | null | undefined>(null);
    const [activeTab, setActiveTab] = useState<TabKey>('overview');
    const [animKey, setAnimKey] = useState(0);

    const fetchSummary = async () => {
        const response = await fetch(`${BACKEND_URL}/api/summary/section_summary/${section_id}`);
        const data = await response.json();
        setSummary(data.section_summary || data.existing_summary);
    };

    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
    }, [onClose]);

    const handleDeleteSummary = async (summary_id: number) => {
        const response = await fetch(`${BACKEND_URL}/api/summary/delete/${section_id}/${summary_id}`, {
            method: 'DELETE',
        });
        const data = await response.json();
        if (response.ok) {
            toast.success('Section summary deleted successfully');
            onClose();
        } else {
            toast.error(data.message || 'Error deleting section summary');
        }
    };

    const handleDownload = () => {
        if (!summary) return;

        const doc = new jsPDF({
            unit: "pt",
            format: "letter",
        });

        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const marginX = 50;
        const maxWidth = pageWidth - marginX * 2;
        let y = 50;

        const ensureSpace = (needed = 24) => {
            if (y + needed > pageHeight - 50) {
                doc.addPage();
                y = 50;
            }
        };

        const addTitle = (text: string) => {
            ensureSpace(30);
            doc.setFont("helvetica", "bold");
            doc.setFontSize(18);
            doc.text(text, marginX, y);
            y += 28;
        };

        const addMeta = (text: string) => {
            ensureSpace(20);
            doc.setFont("helvetica", "normal");
            doc.setFontSize(10);
            doc.setTextColor(90);
            doc.text(text, marginX, y);
            doc.setTextColor(0);
            y += 20;
        };

        const addSectionHeader = (text: string) => {
            ensureSpace(26);
            doc.setFont("helvetica", "bold");
            doc.setFontSize(13);
            doc.text(text, marginX, y);
            y += 8;
            doc.setDrawColor(200);
            doc.line(marginX, y, pageWidth - marginX, y);
            y += 16;
        };

        const addParagraph = (text: string) => {
            doc.setFont("times", "normal");
            doc.setFontSize(11);
            const lines = doc.splitTextToSize(text, maxWidth);
            lines.forEach((line: string) => {
                ensureSpace(16);
                doc.text(line, marginX, y);
                y += 15;
            });
            y += 8;
        };

        const addBullets = (items: string[]) => {
            if (!items.length) {
                addParagraph("None specified.");
                return;
            }

            doc.setFont("times", "normal");
            doc.setFontSize(11);

            items.forEach((item) => {
                const bullet = "•";
                const wrapped = doc.splitTextToSize(item, maxWidth - 18);

                ensureSpace(16);
                doc.text(bullet, marginX, y);
                doc.text(wrapped[0], marginX + 14, y);
                y += 15;

                for (let i = 1; i < wrapped.length; i++) {
                    ensureSpace(16);
                    doc.text(wrapped[i], marginX + 14, y);
                    y += 15;
                }

                y += 4;
            });

            y += 6;
        };

        addTitle(`${summary.section_number} - ${summary.section_title}`);
        addMeta(`Project Spec ID: ${summary.spec_id}`);

        addSectionHeader("Overview");
        addParagraph(summary.overview);

        addSectionHeader("Key Requirements");
        addBullets(parseJsonField(summary.key_requirements));

        addSectionHeader("Materials");
        addBullets(parseJsonField(summary.materials));

        addSectionHeader("Related Sections");
        addBullets(parseJsonField(summary.related_sections));

        addSectionHeader("Submittals");
        addBullets(parseJsonField(summary.submittals));

        addSectionHeader("Testing");
        addBullets(parseJsonField(summary.testing));

        doc.save(`section-${summary.section_number}.pdf`);
    };

    useEffect(() => {
        fetchSummary();
    }, []);

    useEffect(() => {
        document.addEventListener('keydown', handleKeyDown);
        document.body.style.overflow = 'hidden';
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.body.style.overflow = '';
        };
    }, [handleKeyDown]);

    const handleTabChange = (key: TabKey) => {
        setActiveTab(key);
        setAnimKey(k => k + 1);
    };

    if (!summary) {
        return (
            <div className="sm-overlay" onClick={onClose}>
                <div className="sm-loading" onClick={e => e.stopPropagation()}>
                    <CircularProgress size={28} sx={{ color: '#4a9eff' }} />
                    <span>Loading section summary…</span>
                </div>
            </div>
        );
    }

    const pages = parseJsonField(summary.pages_summarized);

    const renderTabContent = () => {
        switch (activeTab) {
            case 'overview':
                return (
                    <div className="sm-overview">
                        <p className="sm-overview-text">{summary.overview}</p>
                        {pages.length > 0 && (
                            <div className="sm-pages">
                                <span className="sm-pages-label">Pages Referenced</span>
                                <div className="sm-pages-chips">
                                    {pages.map(p => (
                                        <span key={p} className="sm-page-chip">{p + 1}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                );
            case 'key_requirements':
                return <ListTab items={parseJsonField(summary.key_requirements)} label="Requirements" />;
            case 'materials':
                return <ListTab items={parseJsonField(summary.materials)} label="Materials" />;
            case 'related_sections':
                return <ListTab items={parseJsonField(summary.related_sections)} label="Related Sections" />;
            case 'submittals':
                return <ListTab items={parseJsonField(summary.submittals)} label="Submittals" />;
            case 'testing':
                return <ListTab items={parseJsonField(summary.testing)} label="Testing" />;
        }
    };

    const getTabCount = (key: TabKey): number | null => {
        if (key === 'overview') return null;
        const counts: Record<string, number> = {
            key_requirements: parseJsonField(summary.key_requirements).length,
            materials: parseJsonField(summary.materials).length,
            related_sections: parseJsonField(summary.related_sections).length,
            submittals: parseJsonField(summary.submittals).length,
            testing: parseJsonField(summary.testing).length,
        };
        return counts[key] ?? null;
    };

    return (
        <div className="sm-overlay" onClick={onClose}>
            <div className="sm-root" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div className="sm-header">
                    <div className="sm-header-left">
                        <span className="sm-section-number">{summary.section_number}</span>
                        <h2 className="sm-section-title">{summary.section_title}</h2>
                        <button className="sm-delete-btn" onClick={() => handleDeleteSummary(summary.id)} aria-label="Delete">
                            <Delete fontSize="small" />
                        </button>
                    </div>
                    <div className="sm-header-right">
                        <button
                            className="sm-download-btn"
                            onClick={handleDownload}
                            aria-label="Download"
                            title="Download Summary as PDF"
                        >
                            <DownloadIcon fontSize="small" />
                        </button>
                        <span className="sm-spec-id">SPEC {summary.spec_id.slice(0, 8).toUpperCase()}</span>
                        <button className="sm-close-btn" onClick={onClose} aria-label="Close">
                            <Close fontSize="small" />
                        </button>
                    </div>
                </div>

                {/* Tab Bar */}
                <div className="sm-tabs" role="tablist">
                    {TAB_CONFIG.map(({ key, label }) => {
                        const count = getTabCount(key);
                        const isEmpty = count !== null && count === 0;
                        return (
                            <button
                                key={key}
                                role="tab"
                                aria-selected={activeTab === key}
                                className={`sm-tab ${activeTab === key ? 'sm-tab--active' : ''} ${isEmpty ? 'sm-tab--empty' : ''}`}
                                onClick={() => handleTabChange(key)}
                            >
                                <span className="sm-tab-label">{label}</span>
                                {count !== null && (
                                    <span className={`sm-tab-badge ${count === 0 ? 'sm-tab-badge--zero' : ''}`}>
                                        {count}
                                    </span>
                                )}
                            </button>
                        );
                    })}
                </div>

                {/* Content */}
                <div className="sm-content" id="sm-content" key={animKey} role="tabpanel">
                    {renderTabContent()}
                </div>
            </div>
        </div>
    );
}
