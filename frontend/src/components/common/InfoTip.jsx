// InfoTip — subtle circle icon; tooltip uses fixed position so it is not clipped.

import React, { useCallback, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

const TIP_MAX_WIDTH = 280;
const GAP = 8;

export default function InfoTip({ text }) {
  const [visible, setVisible] = useState(false);
  const [hover, setHover] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const anchorRef = useRef(null);

  const placeTooltip = useCallback(() => {
    const el = anchorRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const margin = 12;
    const vw = window.innerWidth;

    let left =
      rect.right > vw * 0.55
        ? rect.right - TIP_MAX_WIDTH
        : rect.left + rect.width / 2 - TIP_MAX_WIDTH / 2;

    left = Math.max(margin, Math.min(left, vw - TIP_MAX_WIDTH - margin));
    setCoords({ top: rect.bottom + GAP, left });
  }, []);

  const show = () => {
    placeTooltip();
    setHover(true);
    setVisible(true);
  };

  const hide = () => {
    setHover(false);
    setVisible(false);
  };

  return (
    <>
      <span
        ref={anchorRef}
        style={styles.wrap}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        tabIndex={0}
        aria-label={text}
      >
        <span
          style={{
            ...styles.icon,
            ...(hover ? styles.iconHover : {}),
          }}
          aria-hidden="true"
        >
          !
        </span>
      </span>
      {visible &&
        createPortal(
          <div
            style={{ ...styles.tip, top: coords.top, left: coords.left }}
            role="tooltip"
          >
            {text}
          </div>,
          document.body,
        )}
    </>
  );
}

const styles = {
  wrap: {
    display: 'inline-flex',
    marginLeft: 5,
    verticalAlign: 'middle',
  },
  icon: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 13,
    height: 13,
    borderRadius: '50%',
    border: '1px solid #c4c7cc',
    color: '#9aa0a6',
    fontSize: 9,
    fontWeight: 700,
    lineHeight: 1,
    cursor: 'default',
    //opacity: 0.95,
    userSelect: 'none',
  },
  iconHover: {
    opacity: 0.85,
    borderColor: '#9aa0a6',
    color: '#5f6368',
  },
  tip: {
    position: 'fixed',
    maxWidth: TIP_MAX_WIDTH,
    padding: '10px 12px',
    background: '#3c4043',
    color: '#fff',
    fontSize: 13,
    fontWeight: 400,
    lineHeight: 1.55,
    borderRadius: 6,
    boxShadow: '0 2px 10px rgba(0,0,0,0.18)',
    zIndex: 9999,
    pointerEvents: 'none',
    whiteSpace: 'normal',
    wordWrap: 'break-word',
  },
};
