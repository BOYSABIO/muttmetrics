/**
 * Home screen / week dashboard shell (#158 fills charts/data).
 * Layout stub so desk width and landing can ship with #157.
 */
export function ThisWeek() {
  return (
    <div className="page page-wide">
      <header className="app-header">
        <h1>This week</h1>
        <p className="step-meta">
          Your week at a glance. Numbers land in the next step — use + to log a
          visit.
        </p>
      </header>
      <div className="section-grid this-week-grid">
        <section className="panel this-week-slot" aria-label="Revenue placeholder">
          <h2 className="profile-section">€ / hour</h2>
          <p className="step-meta">Charts and numbers come next.</p>
        </section>
        <section
          className="panel this-week-slot"
          aria-label="Utilization placeholder"
        >
          <h2 className="profile-section">Utilization</h2>
          <p className="step-meta">Same width shell as Clients on desk.</p>
        </section>
        <section
          className="panel this-week-slot"
          aria-label="Overrun placeholder"
        >
          <h2 className="profile-section">Overruns</h2>
          <p className="step-meta">Placeholder until the API is wired.</p>
        </section>
        <section
          className="panel this-week-slot"
          aria-label="Booked hours placeholder"
        >
          <h2 className="profile-section">Booked hours</h2>
          <p className="step-meta">Placeholder until the API is wired.</p>
        </section>
      </div>
    </div>
  )
}
