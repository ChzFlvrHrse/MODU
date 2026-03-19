import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import ModuBrand from '../ModuBrand/ModuBrand';
import './Nav.css';


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
                    <ModuBrand />
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
