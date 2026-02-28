import React, { useState } from 'react';
import ReactDOM from 'react-dom';
import { CircularProgress } from "@mui/material";
import { Close } from '@mui/icons-material';
import { toast } from 'react-hot-toast';
import './DeleteModal.css';

interface DeleteModalProps {
    item_type: string;
    spec_id: string;
    item_id?: string;
    onClose: () => void;
}

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export default function DeleteModal({ item_type, spec_id, item_id, onClose }: DeleteModalProps) {
    const [loading, setLoading] = useState(false);
    const url = item_id ? `${BACKEND_URL}/api/${item_type}/delete/${spec_id}/${item_id}` : `${BACKEND_URL}/api/${item_type}/delete/${spec_id}`;

    const handleDelete = async () => {
        setLoading(true);
        try {
            const response = await fetch(url, {
                method: "DELETE",
            });
            if (response.ok) {
                toast.success(`${item_type} deleted successfully`);
            }
        } catch (e) {
            toast.error(`Error deleting ${item_type}`);
        } finally {
            setLoading(false);
            onClose();
        }
    };

    return ReactDOM.createPortal(
        <div className="sm-overlay" onClick={onClose}>
            <div className="sm-root" onClick={e => e.stopPropagation()}>
                <div className="sm-header">
                    <div className="sm-header-left">
                        <h2 className="sm-section-title">Delete {item_type}</h2>
                    </div>
                    <div className="sm-header-right">
                        <button className="sm-close-btn" onClick={onClose} aria-label="Close">
                            <Close fontSize="small" />
                        </button>
                    </div>
                </div>
                <div className="sm-content">
                    <p className="sm-content-text">Are you sure you want to delete this {item_type}?</p>
                    {loading ? (
                        <CircularProgress size={20} />
                    ) : (
                        <>
                            <button className="sm-delete-btn" onClick={handleDelete}>Delete</button>
                            <button className="sm-cancel-btn" onClick={onClose}>Cancel</button>
                        </>
                    )}
                </div>
            </div>
        </div>,
        document.body
    );
}
