const paths = {
  orbit: 'M21 12a9 9 0 1 1-9-9 M16 3h5v5 M21 3l-8 8 M8 16l3-3',
  home: 'M3 10l9-7 9 7v10H3z M9 20v-7h6v7',
  control: 'M12 3v18 M3 12h18 M9 6l3-3 3 3 M18 9l3 3-3 3 M9 18l3 3 3-3 M6 9l-3 3 3 3',
  camera: 'M3 7h4l2-3h6l2 3h4v14H3z M16 13a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  stars: 'M12 3l2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z M20 2v4 M18 4h4',
  folder: 'M3 5h7l2 3h9v13H3z',
  moon: 'M20 15A9 9 0 0 1 9 4a9 9 0 1 0 11 11',
  bell: 'M5 17h14l-2-4V9a5 5 0 0 0-10 0v4z M10 21h4',
  menu: 'M4 6h16 M4 12h16 M4 18h16',
  close: 'M6 6l12 12 M18 6L6 18',
  arrow: 'M4 12h16 M14 6l6 6-6 6',
  power: 'M12 2v10 M6 5a9 9 0 1 0 12 0',
  mount: 'M4 8l13-5 3 8-13 5z M12 15v3 M7 22l5-4 5 4',
} as const

export function Icon({ name, size = 20 }: { name: keyof typeof paths; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={paths[name]} />
  </svg>
}
