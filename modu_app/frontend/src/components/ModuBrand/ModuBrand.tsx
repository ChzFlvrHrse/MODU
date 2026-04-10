import React from 'react';
import './ModuBrand.css';

interface ModuBrandProps {
    logoOnly?: boolean;
    wordmarkOnly?: boolean;
}

export default function ModuBrand({ logoOnly = false, wordmarkOnly = false }: ModuBrandProps) {
    return (
        <div className="modu-brand-lockup" aria-label="MODU logo">
            {!wordmarkOnly && (
                <div className="modu-brand-icon" aria-hidden="true">
                    <div className="modu-brand-icon-outer">
                        <div className="modu-brand-icon-inner" />
                    </div>
                </div>
            )}

            {!logoOnly && (
                <div className="modu-brand-copy">
                    <div className="modu-brand-wordmark" aria-hidden="true">
                        <span className="modu-letter">M</span>
                        <span className="modu-letter">O</span>
                        <span className="modu-letter">D</span>
                        <span className="modu-letter modu-letter-u">U</span>
                    </div>
                    <div className="modu-brand-subtitle">Unified Spec Platform</div>
                </div>
            )}
        </div>
    );
}
