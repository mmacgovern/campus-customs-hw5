import { useState } from "react";

interface Props {
  disabled: boolean;
  onConfirm: () => Promise<void>;
}

export function ResetButton({ disabled, onConfirm }: Props) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  return (
    <>
      <button
        className="btn ghost reset-btn"
        onClick={() => setOpen(true)}
        disabled={disabled}
        title={disabled ? "Wait for the running ticket to finish" : "Reset the working database"}
      >
        ↺ Reset database
      </button>
      {open && (
        <div className="modal-backdrop" onClick={() => !busy && setOpen(false)}>
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="reset-title" onClick={(e) => e.stopPropagation()}>
            <h2 id="reset-title">Reset the shop to the start?</h2>
            <p>This copies the <b>original</b> database over the working copy:</p>
            <ul>
              <li>Cash goes back to $3,400.00 and invoice 501 to unpaid.</li>
              <li>All tickets reopen, and every pending or approved request is cleared.</li>
              <li>Customer drafts are removed.</li>
            </ul>
            <p className="muted small">The original database is never changed, and the audit trail is kept.</p>
            <div className="btn-row">
              <button className="btn ghost" onClick={() => setOpen(false)} disabled={busy}>
                Cancel
              </button>
              <button
                className="btn danger"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    await onConfirm();
                    setOpen(false);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                {busy ? "Resetting…" : "Yes, reset"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
