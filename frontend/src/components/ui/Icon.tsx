const PATHS: Record<string, React.ReactNode> = {
  upload: <path d="M12 16V4m0 0l-4 4m4-4l4 4M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3" />,
  image: (
    <path d="M4 5h16v14H4zM4 15l4-4 3 3 4-4 5 5M9 9.5a1.25 1.25 0 100-2.5 1.25 1.25 0 000 2.5z" />
  ),
  chart: <path d="M4 20V10m6 10V4m6 16v-7m4 7H2" />,
  script: <path d="M6 3h9l4 4v14H6zM14 3v5h5M9 12h6M9 16h6" />,
  mic: <path d="M12 3a2.5 2.5 0 012.5 2.5v5a2.5 2.5 0 01-5 0v-5A2.5 2.5 0 0112 3zM6 11a6 6 0 0012 0M12 17v4" />,
  film: <path d="M4 5h16v14H4zM8 5v14M16 5v14M4 9h4M4 15h4M16 9h4M16 15h4" />,
  check: <path d="M4 12.5l5 5L20 6.5" />,
  x: <path d="M6 6l12 12M18 6L6 18" />,
  plus: <path d="M12 5v14M5 12h14" />,
  trash: <path d="M5 7h14M10 7V4h4v3M8 7l1 13h6l1-13" />,
  play: <path d="M7 4l13 8-13 8z" />,
  download: <path d="M12 4v12m0 0l-4-4m4 4l4-4M4 17v2a1 1 0 001 1h14a1 1 0 001-1v-2" />,
  back: <path d="M15 5l-7 7 7 7" />,
};

export type IconName = keyof typeof PATHS;

export default function Icon({ name }: { name: IconName }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4 shrink-0"
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  );
}
