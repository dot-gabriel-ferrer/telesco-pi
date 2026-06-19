/**
 * Bottom navigation bar – the primary navigation for mobile.
 */

import { NavLink } from 'react-router-dom'

const TABS = [
  { to: '/', label: 'Inicio', icon: '🏠', end: true },
  { to: '/control', label: 'Control', icon: '🎮' },
  { to: '/capture', label: 'Captura', icon: '📷' },
  { to: '/plan', label: 'Plan', icon: '🌟' },
  { to: '/files', label: 'Archivos', icon: '🗂️' },
]

export function BottomNav() {
  return (
    <nav className="bottom-nav" role="navigation" aria-label="Navegación principal">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.end}
          className={({ isActive }) => `bottom-nav__item${isActive ? ' active' : ''}`}
          aria-label={tab.label}
        >
          <span className="bottom-nav__icon" aria-hidden="true">{tab.icon}</span>
          <span className="bottom-nav__label">{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
