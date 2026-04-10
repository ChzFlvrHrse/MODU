import React, { useState, useEffect, useCallback } from 'react';
import { CircularProgress } from '@mui/material';
import { Close, Add, Edit, Delete } from '@mui/icons-material';
import './AmendmentsModal.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AMENDMENT_TYPES = [
    { value: 'waived', label: 'Waived' },
    { value: 'alternate_accepted', label: 'Alternate Accepted' },
    { value: 'not_applicable', label: 'Not Applicable' },
    { value: 'deferred', label: 'Deferred' },
];

const TYPE_LABELS: Record<string, string> = {
    waived: 'Waived',
    alternate_accepted: 'Alternate Accepted',
    not_applicable: 'N/A',
    deferred: 'Deferred',
};

interface Amendment {
    id: number;
    section_id: number;
    ref: string;
    type: string;
    note: string | null;
    created_at: string;
    updated_at: string;
}

interface AmendmentsModalProps {
    section_id: number;
    section_number: string;
    section_title: string;
    onClose: () => void;
}

type View = 'list' | 'create' | 'edit';

// ── Amendment Row ──────────────────────────────────────────────────────────────

function AmendmentRow({
    amendment,
    onEdit,
    onDeleted,
}: {
    amendment: Amendment;
    onEdit: (a: Amendment) => void;
    onDeleted: (id: number) => void;
}) {
    const [confirming, setConfirming] = useState(false);
    const [deleting, setDeleting] = useState(false);

    const handleDelete = async () => {
        setDeleting(true);
        try {
            const res = await fetch(`${BACKEND_URL}/api/submittal/delete/amendment/${amendment.id}`, {
                method: 'DELETE',
            });
            const data = await res.json();
            if (data.success) {
                onDeleted(amendment.id);
            }
        } finally {
            setDeleting(false);
            setConfirming(false);
        }
    };

    return (
        <div className="am-row">
            <div className="am-row-left">
                <div className="am-row-top">
                    <span className="am-ref">{amendment.ref}</span>
                    <span className={`am-type am-type-${amendment.type}`}>
                        {TYPE_LABELS[amendment.type] ?? amendment.type}
                    </span>
                </div>
                {amendment.note && <p className="am-note">{amendment.note}</p>}
                {confirming && (
                    <div className="am-delete-confirm">
                        <p>Remove this amendment?</p>
                        <div className="am-delete-confirm-actions">
                            <button className="am-confirm-no" onClick={() => setConfirming(false)}>
                                Cancel
                            </button>
                            <button className="am-confirm-yes" onClick={handleDelete} disabled={deleting}>
                                {deleting ? '...' : 'Remove'}
                            </button>
                        </div>
                    </div>
                )}
            </div>
            <div className="am-row-actions">
                <button className="am-icon-btn" onClick={() => onEdit(amendment)} title="Edit">
                    <Edit sx={{ fontSize: 14 }} />
                </button>
                <button className="am-icon-btn delete" onClick={() => setConfirming(true)} title="Delete">
                    <Delete sx={{ fontSize: 14 }} />
                </button>
            </div>
        </div>
    );
}

// ── Amendment Form (create + edit) ────────────────────────────────────────────

function AmendmentForm({
    section_id,
    editing,
    onCancel,
    onSaved,
}: {
    section_id: number;
    editing: Amendment | null;
    onCancel: () => void;
    onSaved: (amendment: Amendment) => void;
}) {
    const [ref, setRef] = useState(editing?.ref ?? '');
    const [type, setType] = useState(editing?.type ?? 'waived');
    const [note, setNote] = useState(editing?.note ?? '');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const isEdit = editing !== null;


    const handleSave = async () => {
        if (!ref.trim()) { setError('Spec reference is required.'); return; }
        setLoading(true);
        setError(null);

        console.log(editing);

        try {
            let res: Response;

            if (isEdit) {
                res = await fetch(`${BACKEND_URL}/api/submittal/update/amendment/${editing.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ref: ref.trim(), type, note: note.trim() || null }),
                });
            } else {
                res = await fetch(`${BACKEND_URL}/api/submittal/create_amendment`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        section_id,
                        ref: ref.trim(),
                        type,
                        note: note.trim() || null,
                    }),
                });
            }

            const data = await res.json();

            if (!res.ok || !data.success) {
                setError(data.error ?? 'Something went wrong.');
                return;
            }

            onSaved(isEdit ? data.amendment : data.amendment);
        } catch {
            setError('Network error. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="am-form">
            <p className="am-form-title">{isEdit ? 'Edit Amendment' : 'New Amendment'}</p>

            <div className="am-form-fields">
                <div className="am-form-field">
                    <label className="am-form-label">
                        Spec Reference <span className="am-required">*</span>
                    </label>
                    <input
                        className="am-form-input"
                        placeholder="e.g. 2.3.B.2"
                        value={ref}
                        autoFocus
                        onChange={(e) => { setRef(e.target.value); if (error) setError(null); }}
                        onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                    />
                </div>

                <div className="am-form-field">
                    <label className="am-form-label">
                        Type <span className="am-required">*</span>
                    </label>
                    <select
                        className="am-form-select"
                        value={type}
                        onChange={(e) => setType(e.target.value)}
                    >
                        {AMENDMENT_TYPES.map((t) => (
                            <option key={t.value} value={t.value}>{t.label}</option>
                        ))}
                    </select>
                </div>

                <div className="am-form-field">
                    <label className="am-form-label">
                        Note <span className="am-optional">Optional</span>
                    </label>
                    <textarea
                        className="am-form-textarea"
                        placeholder="e.g. Owner accepted alternate material on 9/15/23"
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                    />
                </div>
            </div>

            {error && <p className="am-form-error">{error}</p>}

            <div className="am-form-actions">
                <button className="am-cancel-btn" onClick={onCancel} disabled={loading}>
                    Cancel
                </button>
                <button
                    className={`am-submit-btn ${loading ? 'loading' : ''}`}
                    onClick={handleSave}
                    disabled={loading || !ref.trim()}
                >
                    {loading
                        ? (isEdit ? 'Saving...' : 'Adding...')
                        : (isEdit ? 'Save Changes' : 'Add Amendment +')}
                </button>
            </div>
        </div>
    );
}

// ── Amendments List ───────────────────────────────────────────────────────────

function AmendmentsList({
    section_id,
    amendments,
    loading,
    onAdd,
    onEdit,
    onDeleted,
}: {
    section_id: number;
    amendments: Amendment[];
    loading: boolean;
    onAdd: () => void;
    onEdit: (a: Amendment) => void;
    onDeleted: (id: number) => void;
}) {
    if (loading) {
        return (
            <div className="am-loading">
                <CircularProgress size={20} sx={{ color: '#4a9eff' }} />
            </div>
        );
    }

    if (!amendments.length) {
        return (
            <div className="am-empty">
                <span className="am-empty-icon">∅</span>
                <p>No amendments for this section yet.</p>
                <button className="am-create-cta" onClick={onAdd}>
                    <Add fontSize="small" /> Add first amendment
                </button>
            </div>
        );
    }

    return (
        <div className="am-list">
            {amendments.map((a) => (
                <AmendmentRow
                    key={a.id}
                    amendment={a}
                    onEdit={onEdit}
                    onDeleted={onDeleted}
                />
            ))}
        </div>
    );
}

// ── Modal Root ────────────────────────────────────────────────────────────────

export default function AmendmentsModal({
    section_id,
    section_number,
    section_title,
    onClose,
}: AmendmentsModalProps) {
    const [view, setView] = useState<View>('list');
    const [amendments, setAmendments] = useState<Amendment[]>([]);
    const [loading, setLoading] = useState(true);
    const [editing, setEditing] = useState<Amendment | null>(null);

    // Fetch amendments on mount
    useEffect(() => {
        const fetch_ = async () => {
            try {
                const res = await fetch(`${BACKEND_URL}/api/submittal/get_amendments/${section_id}`);
                const data = await res.json();
                setAmendments(Array.isArray(data) ? data : []);
            } finally {
                setLoading(false);
            }
        };
        fetch_();
    }, [section_id]);

    // Escape key
    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if (e.key === 'Escape') {
            if (view !== 'list') { setView('list'); setEditing(null); }
            else onClose();
        }
    }, [onClose, view]);

    useEffect(() => {
        document.addEventListener('keydown', handleKeyDown);
        document.body.style.overflow = 'hidden';
        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.body.style.overflow = '';
        };
    }, [handleKeyDown]);

    const handleSaved = (amendment: Amendment) => {
        setAmendments((prev) => {
            const exists = prev.find((a) => a.id === amendment.id);
            return exists
                ? prev.map((a) => (a.id === amendment.id ? amendment : a))
                : [...prev, amendment];
        });
        setView('list');
        setEditing(null);
    };

    const handleDeleted = (id: number) => {
        setAmendments((prev) => prev.filter((a) => a.id !== id));
    };

    const handleEdit = (amendment: Amendment) => {
        setEditing(amendment);
        setView('edit');
    };

    const handleCancel = () => {
        setView('list');
        setEditing(null);
    };

    return (
        <div className="am-overlay" onClick={onClose}>
            <div className="am-root" onClick={(e) => e.stopPropagation()}>

                {/* Header */}
                <div className="am-header">
                    <div className="am-header-left">
                        <span className="am-section-number">{section_number}</span>
                        <h2 className="am-section-title">{section_title}</h2>
                    </div>
                    <div className="am-header-right">
                        {view === 'list' && (
                            <button className="am-new-btn" onClick={() => setView('create')}>
                                <Add fontSize="small" /> New Amendment
                            </button>
                        )}
                        <button className="am-close-btn" onClick={onClose}>
                            <Close fontSize="small" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="am-content">
                    {view === 'list' && (
                        <AmendmentsList
                            section_id={section_id}
                            amendments={amendments}
                            loading={loading}
                            onAdd={() => setView('create')}
                            onEdit={handleEdit}
                            onDeleted={handleDeleted}
                        />
                    )}
                    {(view === 'create' || view === 'edit') && (
                        <AmendmentForm
                            section_id={section_id}
                            editing={editing}
                            onCancel={handleCancel}
                            onSaved={handleSaved}
                        />
                    )}
                </div>

            </div>
        </div>
    );
}
