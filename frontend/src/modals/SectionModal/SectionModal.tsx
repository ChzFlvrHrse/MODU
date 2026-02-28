import React, { useState, useEffect, useCallback } from 'react';
import ReactDOM from 'react-dom';
import { CircularProgress } from "@mui/material";
import { Close, Delete } from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import './SectionModal.css';

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
    spec_id: string;
    section_number: string;
    section_title: string;
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

const TAB_CONFIG: { key: TabKey; label: string; short: string }[] = [
    { key: 'overview', label: 'Overview', short: 'OVR' },
    { key: 'key_requirements', label: 'Requirements', short: 'REQ' },
    { key: 'materials', label: 'Materials', short: 'MAT' },
    { key: 'related_sections', label: 'Related Sections', short: 'REL' },
    { key: 'submittals', label: 'Submittals', short: 'SUB' },
    { key: 'testing', label: 'Testing', short: 'TST' },
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

export default function SectionModal({ spec_id, section_number, section_title, onClose }: SectionModalProps) {
    const [summary, setSummary] = useState<SpecSummary | null | undefined>(null);
    const [activeTab, setActiveTab] = useState<TabKey>('overview');
    const [animKey, setAnimKey] = useState(0);

    const fetchSummary = async () => {
        const response = await fetch(`${BACKEND_URL}/api/summary/section_summary/${spec_id}/${section_number}`);
        const data = await response.json();
        setSummary(data.spec_summary || data.existing_summary);
    };

    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
    }, [onClose]);

    const handleDeleteSummary = async (summary_id: number) => {
        const response = await fetch(`${BACKEND_URL}/api/summary/delete/${spec_id}/${encodeURIComponent(section_number)}/${summary_id}`, {
            method: "DELETE",
        });
        const data = await response.json();
        if (response.ok) {
            toast.success("Section summary deleted successfully");
            onClose();
        } else {
            toast.error(data.message || "Error deleting section summary");
        }
    };

    useEffect(() => { fetchSummary(); }, []);
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
        return ReactDOM.createPortal(
            <div className="sm-overlay" onClick={onClose}>
                <div className="sm-loading" onClick={e => e.stopPropagation()}>
                    <CircularProgress size={28} sx={{ color: '#4a9eff' }} />
                    <span>Loading section summary…</span>
                </div>
            </div>,
            document.body
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
                                        <span key={p} className="sm-page-chip">{p}</span>
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
        const counts: Record<Exclude<TabKey, 'overview'>, number> = {
            key_requirements: parseJsonField(summary.key_requirements).length,
            materials: parseJsonField(summary.materials).length,
            related_sections: parseJsonField(summary.related_sections).length,
            submittals: parseJsonField(summary.submittals).length,
            testing: parseJsonField(summary.testing).length,
        };
        return counts[key as Exclude<TabKey, 'overview'>];
    };

    return ReactDOM.createPortal(
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
                <div className="sm-content" key={animKey} role="tabpanel">
                    {renderTabContent()}
                </div>
            </div>
        </div>,
        document.body
    );
}
