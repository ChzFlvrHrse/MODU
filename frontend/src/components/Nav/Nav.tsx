import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import moduLogo from '../../modu_logo_transparent.png';
import './Nav.css';

export default function Nav() {
    const [activeItem, setActiveItem] = useState<string | null>('/projects');

    const navItems = [
        {
            label: 'Projects',
            href: '/projects',
        },
        {
            label: 'About',
            href: '/about',
        }
    ];

    return (
        <nav className="nav">
            <div className="nav-items">
                <Link to="/projects" onClick={() => setActiveItem('/projects')}>
                    <img src={moduLogo} className="nav-logo" alt="logo" />
                </Link>
                {navItems.map((item) => (
                    <Link className="nav-item" to={item.href} key={item.href}>
                        <button className={`nav-button ${activeItem === item.href ? 'active' : ''}`} onClick={() => setActiveItem(item.href)}>
                            {item.label}
                        </button>
                    </Link>
                ))}
            </div>
        </nav>
    );
}
