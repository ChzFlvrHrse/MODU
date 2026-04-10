import React, { useState } from 'react';
import { CircularProgress } from '@mui/material';
import { Close } from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import './DeleteModal.css';

interface DeleteModalProps {
    prefix: string;
    item_type: string;
    spec_id: string;
    item_id?: string;
    onClose: () => void;
}

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function DeleteModal({
    prefix,
    item_type,
    spec_id,
    item_id,
    onClose,
}: DeleteModalProps) {
    const [loading, setLoading] = useState(false);

    const url = item_id
        ? `${BACKEND_URL}/api/${prefix}/delete/${item_type}/${spec_id}/${item_id}`
        : `${BACKEND_URL}/api/${prefix}/delete/${item_type}/${spec_id}`;

    const prettyItemType =
        item_type.charAt(0).toUpperCase() + item_type.slice(1).replace(/_/g, ' ');

    const handleDelete = async () => {
        setLoading(true);

        try {
            const response = await fetch(url, {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error('Delete failed');
            }

            toast.success(`${prettyItemType} deleted successfully`);
            onClose();
        } catch (e) {
            toast.error(`Error deleting ${prettyItemType}`);
            setLoading(false);
        }
    };

    return (
        <div className="dm-overlay" onClick={onClose}>
            <div
                className="dm-root"
                onClick={(e) => e.stopPropagation()}
                role="dialog"
                aria-modal="true"
                aria-labelledby="delete-modal-title"
            >
                <div className="dm-header">
                    <h2 id="delete-modal-title" className="dm-title">
                        Delete {prettyItemType}
                    </h2>

                    <button
                        className="dm-close-btn"
                        onClick={onClose}
                        aria-label="Close"
                        disabled={loading}
                    >
                        <Close fontSize="small" />
                    </button>
                </div>

                <div className="dm-body">
                    <p className="dm-text">
                        Are you sure you want to delete this {prettyItemType.toLowerCase()}?
                    </p>
                    <p className="dm-subtext">This action cannot be undone.</p>
                </div>

                <div className="dm-footer">
                    <button
                        className="dm-cancel-btn"
                        onClick={onClose}
                        disabled={loading}
                    >
                        Cancel
                    </button>

                    <button
                        className="dm-delete-btn"
                        onClick={handleDelete}
                        disabled={loading}
                    >
                        {loading ? (
                            <>
                                <CircularProgress size={14} sx={{ color: 'inherit' }} />
                                Deleting...
                            </>
                        ) : (
                            'Delete'
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
