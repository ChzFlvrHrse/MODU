import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import moduLogo from '../../modu_logo_transparent.png';
import './Nav.css';

// function ModuLogo({ className = 'h-9 w-9' }: { className?: string }) {
//     return (
//       <div className={cn('relative', className)}>
//         <div className="absolute inset-0 rounded-sm border-2 border-black/90 dark:border-white/95" />
//         <div className="absolute left-1/4 top-1/4 h-1/2 w-1/2 rounded-[2px] border-2 border-black/90 dark:border-white/95" />
//       </div>
//     );
//   }

export default function Nav() {
    const location = useLocation();

    const navItems = [
        { label: 'Projects', href: '/projects' },
        { label: 'About', href: '/about' },
    ];

    return (
        <nav className="nav">
            <div className="nav-shell">
                <Link to="/projects" className="nav-brand">
                    <div className="nav-brand-mark">
                        <img src={moduLogo} className="nav-logo" alt="MODU logo" />
                    </div>
                    <div className="nav-brand-copy">
                        <div className="nav-brand-title">MODU</div>
                        <div className="nav-brand-subtitle">Spec intelligence</div>
                    </div>
                </Link>

                <div className="nav-items">
                    {navItems.map((item) => {
                        const isActive =
                            location.pathname === item.href ||
                            (item.href === '/projects' && location.pathname.startsWith('/projects'));

                        return (
                            <Link className="nav-item" to={item.href} key={item.href}>
                                <button className={`nav-button ${isActive ? 'active' : ''}`}>
                                    <span className="nav-button-label">{item.label}</span>
                                </button>
                            </Link>
                        );
                    })}
                </div>

                <div className="nav-footer">
                    <div className="nav-footer-title">Unified MODU v2</div>
                    <div className="nav-footer-copy">
                        One layout system, one card language, one set of actions.
                    </div>
                </div>
            </div>
        </nav>
    );
}
