type PageBackProps = {
  onClick: () => void
  disabled?: boolean
  /** "Back" for pages, "Close" for the capture flow */
  label?: string
}

/**
 * Leaving a screen is always the first thing, top left, on every screen
 * (docs/architecture/ui-conventions.md). It is never in the bottom action bar,
 * so a thumb used to "Back" can't land on Save or Delete by habit.
 */
export function PageBack({ onClick, disabled = false, label = 'Back' }: PageBackProps) {
  return (
    <button type="button" className="header-back page-back" onClick={onClick} disabled={disabled}>
      <span aria-hidden>{label === 'Close' ? '✕' : '←'}</span> {label}
    </button>
  )
}
