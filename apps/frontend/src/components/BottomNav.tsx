/**
 * Bottom navigation bar – the primary navigation for mobile.
 */

import { NavLink } from 'react-router-dom'
import { Icon } from './Icon'

const TABS = [
  { to: '/', label: 'Inicio', icon: 'home', end: true },
  { to: '/control', label: 'Control', icon: 'control' },
  { to: '/capture', label: 'Captura', icon: 'camera' },
  { to: '/plan', label: 'Plan', icon: 'stars' },
  { to: '/files', label: 'Archivos', icon: 'folder' },
] as const

export function BottomNav() {
  return (
    <nav className="bottom-nav" role="navigation" aria-label="Navegación principal">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.to === '/'}
          className={({ isActive }) => `bottom-nav__item${isActive ? ' active' : ''}`}
          aria-label={tab.label}
        >
          <span className="bottom-nav__icon"><Icon name={tab.icon} size={21} /></span>
          <span className="bottom-nav__label">{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
