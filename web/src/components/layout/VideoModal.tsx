'use client';
import { useState, useEffect, useCallback } from 'react';

interface Props {
  embedUrl?: string;
  localSrc?: string;
}

export default function VideoModal({ embedUrl, localSrc = '/demo.mp4' }: Props) {
  const [open, setOpen] = useState(false);

  const close = useCallback(() => setOpen(false), []);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') close(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, close]);

  // Prevent body scroll when open
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={() => setOpen(true)}
        className="font-mono-cc"
        style={{
          fontSize: 11, letterSpacing: '0.8px', textTransform: 'uppercase',
          color: 'var(--text-2)', background: 'none',
          border: '1px solid var(--border-2)',
          padding: '13px 24px', borderRadius: 5, cursor: 'pointer',
          transition: 'color 0.2s, border-color 0.2s',
          display: 'flex', alignItems: 'center', gap: 8,
        }}
        onMouseEnter={e => {
          (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-1)';
          (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--text-3)';
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-2)';
          (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-2)';
        }}
      >
        <span style={{ fontSize: 13 }}>▶</span> Watch Demo
      </button>

      {/* Modal overlay */}
      {open && (
        <div
          onClick={close}
          style={{
            position: 'fixed', inset: 0, zIndex: 999,
            background: 'rgba(0,0,0,0.85)',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: 24,
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              width: '100%', maxWidth: 900,
              position: 'relative',
            }}
          >
            {/* Close button */}
            <button
              onClick={close}
              className="font-mono-cc"
              style={{
                position: 'absolute', top: -36, right: 0,
                fontSize: 11, letterSpacing: '1px', textTransform: 'uppercase',
                color: 'var(--text-3)', background: 'none', border: 'none',
                cursor: 'pointer', padding: '4px 8px',
                transition: 'color 0.2s',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-1)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-3)')}
            >
              ESC to close ✕
            </button>

            {/* Video container — 16:9 */}
            <div style={{
              position: 'relative', paddingBottom: '56.25%', height: 0,
              background: 'var(--surface)',
              border: '1px solid var(--border-2)',
              borderRadius: 8, overflow: 'hidden',
              boxShadow: '0 24px 80px rgba(0,0,0,0.6)',
            }}>
              {embedUrl ? (
                <iframe
                  src={embedUrl}
                  style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', border: 'none' }}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              ) : (
                <video
                  src={localSrc}
                  controls
                  autoPlay
                  style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'contain', background: '#000' }}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
