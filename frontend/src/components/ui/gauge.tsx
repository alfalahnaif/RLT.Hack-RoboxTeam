import type { ReactNode } from "react";

/**
 * Segmented semicircle meter (dashboard direction): `segments` rounded blocks across 180°,
 * filled blocks step from primary-700 → primary-300 in reading order, the rest stay gray-100.
 * Centre shows the value and a caption. Mirrors automatically for RTL (fills from the start side).
 */
export function Gauge({ value, label, caption, segments = 14 }: { value: number; label: ReactNode; caption?: ReactNode; segments?: number }) {
  const v = Math.max(0, Math.min(100, value));
  const filled = Math.round((v / 100) * segments);
  const cx = 110;
  const cy = 110;
  const r1 = 72;
  const r2 = 104;
  const gap = 2.2; // degrees between blocks
  const span = 180 / segments;
  const pt = (r: number, deg: number) => [cx + r * Math.cos((deg * Math.PI) / 180), cy - r * Math.sin((deg * Math.PI) / 180)] as const;
  const fills = ["fill-primary-700", "fill-primary-600", "fill-primary-500", "fill-primary-400", "fill-primary-300"];

  return (
    <div className="relative mx-auto w-full max-w-72">
      {/* Draw from 180° (left) to 0° (right); RTL flips so filling starts at the right/start side. */}
      <svg viewBox="0 0 220 118" className="w-full rtl:-scale-x-100" aria-hidden>
        {Array.from({ length: segments }, (_, i) => {
          const a0 = 180 - i * span - gap / 2;
          const a1 = 180 - (i + 1) * span + gap / 2;
          const [x0, y0] = pt(r2, a0);
          const [x1, y1] = pt(r2, a1);
          const [x2, y2] = pt(r1, a1);
          const [x3, y3] = pt(r1, a0);
          const on = i < filled;
          const tone = fills[Math.min(fills.length - 1, Math.floor((i / Math.max(1, filled)) * fills.length))];
          return <path key={i} d={`M${x0},${y0} A${r2},${r2} 0 0 1 ${x1},${y1} L${x2},${y2} A${r1},${r1} 0 0 0 ${x3},${y3} Z`} className={on ? tone : "fill-gray-100"} strokeLinejoin="round" strokeWidth={3} stroke="transparent" />;
        })}
      </svg>
      <div className="absolute inset-x-0 bottom-0 flex flex-col items-center" role="meter" aria-valuenow={v} aria-valuemin={0} aria-valuemax={100}>
        <span className="text-3xl font-semibold tracking-tight text-heading" dir="ltr">
          {label}
        </span>
        {caption ? <span className="text-xs text-muted">{caption}</span> : null}
      </div>
    </div>
  );
}
