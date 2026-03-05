import { useState } from "react";

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// COLORS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const C = {
  bg: "#060810", card: "#0c1018", cardAlt: "#101520",
  border: "#1a2235", borderHi: "#2a4060",
  green: "#10b981", red: "#ef4444", orange: "#f59e0b",
  blue: "#3b82f6", purple: "#a855f7", cyan: "#06b6d4",
  gray: "#6b7280", text: "#e2e8f0", textSec: "#94a3b8",
  textMuted: "#475569", grid: "rgba(255,255,255,0.025)",
};

const STRAT_COLORS = {
  vp: { primary: "#f59e0b", bg: "#f59e0b10" },
  gap: { primary: "#3b82f6", bg: "#3b82f610" },
  orb: { primary: "#06b6d4", bg: "#06b6d410" },
  oops: { primary: "#ec4899", bg: "#ec489910" },
  pbd: { primary: "#a855f7", bg: "#a855f710" },
  r4: { primary: "#f97316", bg: "#f9731610" },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MINI CHART (generic candlestick renderer)
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function MiniChart({ candles, overlays = [], markers = [], zones = [], width = 300, height = 190 }) {
  const pad = { t: 14, b: 12, l: 4, r: 4 };
  const cW = width - pad.l - pad.r;
  const cH = height - pad.t - pad.b;

  let allPrices = candles.flatMap(c => [c.h, c.l]);
  overlays.forEach(o => { allPrices.push(o.price); });
  zones.forEach(z => { allPrices.push(z.y0, z.y1); });
  const pMin = Math.min(...allPrices) - 1.5;
  const pMax = Math.max(...allPrices) + 1.5;
  const range = pMax - pMin || 1;
  const y = (p) => pad.t + ((pMax - p) / range) * cH;

  const candleW = Math.min(20, (cW - 10) / candles.length - 3);
  const gap = 3;
  const startX = pad.l + (cW - candles.length * (candleW + gap)) / 2;
  const cx = (i) => startX + i * (candleW + gap) + candleW / 2;

  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      {/* Zones */}
      {zones.map((z, i) => (
        <rect key={`z${i}`} x={pad.l} y={y(z.y1)} width={cW}
          height={y(z.y0) - y(z.y1)}
          fill={z.fill || "rgba(255,255,255,0.03)"}
          stroke={z.stroke || "none"} strokeWidth={1} strokeDasharray={z.dash || "none"}
          rx={3} />
      ))}

      {/* Overlay lines */}
      {overlays.map((o, i) => (
        <line key={`o${i}`} x1={pad.l} y1={y(o.price)} x2={width - pad.r} y2={y(o.price)}
          stroke={o.color} strokeWidth={o.width || 1} strokeDasharray={o.dash || "none"} />
      ))}

      {/* Candles */}
      {candles.map((c, i) => {
        const x = startX + i * (candleW + gap);
        const isG = c.c >= c.o;
        const color = c.color || (isG ? C.green : C.red);
        const opacity = c.opacity ?? 0.85;
        const bodyT = y(Math.max(c.o, c.c));
        const bodyB = y(Math.min(c.o, c.c));
        return (
          <g key={i} opacity={opacity}>
            <line x1={cx(i)} y1={y(c.h)} x2={cx(i)} y2={y(c.l)} stroke={color} strokeWidth={1} />
            <rect x={x} y={bodyT} width={candleW} height={Math.max(bodyB - bodyT, 2)}
              fill={color} rx={1.5} />
            {c.label && (
              <text x={cx(i)} y={y(c.h) - 6} fill={color} fontSize={7} textAnchor="middle" fontWeight={600}>
                {c.label}
              </text>
            )}
          </g>
        );
      })}

      {/* Markers */}
      {markers.map((m, i) => {
        const mx = m.x != null ? m.x : cx(m.ci);
        const my = y(m.price);
        if (m.shape === "tri-up") {
          return <polygon key={i} points={`${mx},${my - 8} ${mx - 6},${my + 3} ${mx + 6},${my + 3}`}
            fill={m.color} opacity={m.opacity ?? 1} />;
        } else if (m.shape === "tri-down") {
          return <polygon key={i} points={`${mx},${my + 8} ${mx - 6},${my - 3} ${mx + 6},${my - 3}`}
            fill={m.color} opacity={m.opacity ?? 1} />;
        } else if (m.shape === "x") {
          return (
            <g key={i} opacity={m.opacity ?? 0.7}>
              <line x1={mx - 4} y1={my - 4} x2={mx + 4} y2={my + 4} stroke={m.color} strokeWidth={2} />
              <line x1={mx + 4} y1={my - 4} x2={mx - 4} y2={my + 4} stroke={m.color} strokeWidth={2} />
            </g>
          );
        } else if (m.shape === "clock") {
          return (
            <g key={i} opacity={m.opacity ?? 0.8}>
              <circle cx={mx} cy={my} r={6} fill="none" stroke={m.color} strokeWidth={1.3} />
              <line x1={mx} y1={my - 2.5} x2={mx} y2={my} stroke={m.color} strokeWidth={1.3} />
              <line x1={mx} y1={my} x2={mx + 2.5} y2={my + 1} stroke={m.color} strokeWidth={1.3} />
            </g>
          );
        } else if (m.shape === "arrow-up") {
          return (
            <g key={i}>
              <line x1={mx} y1={my + 10} x2={mx} y2={my - 4} stroke={m.color} strokeWidth={1.5} />
              <polygon points={`${mx},${my - 8} ${mx - 4},${my - 2} ${mx + 4},${my - 2}`} fill={m.color} />
            </g>
          );
        } else if (m.shape === "arrow-down") {
          return (
            <g key={i}>
              <line x1={mx} y1={my - 10} x2={mx} y2={my + 4} stroke={m.color} strokeWidth={1.5} />
              <polygon points={`${mx},${my + 8} ${mx - 4},${my + 2} ${mx + 4},${my + 2}`} fill={m.color} />
            </g>
          );
        }
        return <circle key={i} cx={mx} cy={my} r={5} fill={m.color} opacity={m.opacity ?? 1} />;
      })}

      {/* Right labels for overlays */}
      {overlays.filter(o => o.label).map((o, i) => (
        <text key={`lbl${i}`} x={width - 2} y={y(o.price) + 3}
          fill={o.color} fontSize={7} textAnchor="end" fontWeight={600}
          fontFamily="monospace">{o.label}</text>
      ))}
    </svg>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ALL STRATEGY DEFINITIONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const STRATEGIES = [
  // ═══════════════════════════════════════════
  // 1. GAP FILL STRATEGY
  // ═══════════════════════════════════════════
  {
    id: "gap",
    name: "Gap Fill Strategy",
    icon: "📉",
    color: STRAT_COLORS.gap.primary,
    description: "เมื่อราคาเปิด Gap (ห่างจาก Close วันก่อน ≥10 จุด) มักจะวิ่งกลับมาปิด Gap ได้ ~65-72% ของเวลา",
    cases: [
      {
        title: "Gap Down → Fill Up ✅",
        badge: "BUY", badgeColor: C.green,
        desc: "เปิดต่ำกว่า Close วันก่อน (Gap Down) → ซื้อ → ราคาวิ่งขึ้นปิด Gap สำเร็จ",
        action: "🟢 BUY ที่ Open วันนี้ | TP = Close วันก่อน | SL = ต่ำกว่า Open",
        chart: {
          candles: [
            { o: 100, h: 112, l: 99, c: 110, opacity: 0.5 },
            { o: 100, h: 110.5, l: 99, c: 110, label: "Close" },
            { o: 102, h: 111, l: 101, c: 110 },
          ],
          overlays: [
            { price: 110, color: C.blue, dash: "6 3", label: "Prev Close", width: 1.2 },
            { price: 102, color: C.red, dash: "3 3", label: "Open (Gap)" },
          ],
          zones: [
            { y0: 102, y1: 110, fill: "rgba(59,130,246,0.06)", stroke: "rgba(59,130,246,0.25)", dash: "4 3" },
          ],
          markers: [
            { ci: 1, price: 102, shape: "tri-up", color: C.green },
            { ci: 2, price: 111, shape: "arrow-up", color: C.green },
          ],
        },
      },
      {
        title: "Gap Up → Fill Down ✅",
        badge: "SELL", badgeColor: C.red,
        desc: "เปิดสูงกว่า Close วันก่อน (Gap Up) → ขาย → ราคาวิ่งลงปิด Gap สำเร็จ",
        action: "🔴 SELL ที่ Open วันนี้ | TP = Close วันก่อน | SL = สูงกว่า Open",
        chart: {
          candles: [
            { o: 108, h: 111, l: 100, c: 102, opacity: 0.5 },
            { o: 108, h: 111, l: 100, c: 102, label: "Close" },
            { o: 112, h: 113, l: 101, c: 102 },
          ],
          overlays: [
            { price: 102, color: C.blue, dash: "6 3", label: "Prev Close", width: 1.2 },
            { price: 112, color: C.green, dash: "3 3", label: "Open (Gap)" },
          ],
          zones: [
            { y0: 102, y1: 112, fill: "rgba(59,130,246,0.06)", stroke: "rgba(59,130,246,0.25)", dash: "4 3" },
          ],
          markers: [
            { ci: 1, price: 112, shape: "tri-down", color: C.red },
            { ci: 2, price: 101, shape: "arrow-down", color: C.red },
          ],
        },
      },
      {
        title: "Gap Down → ไม่ปิด Gap ❌",
        badge: "FAIL", badgeColor: C.gray,
        desc: "Gap Down แต่ราคาวิ่งลงต่อ ไม่สามารถปิด Gap ได้ → Stop Loss",
        action: "🚫 SL ถูกชน — ตลาดมี momentum ขาลงแรง",
        chart: {
          candles: [
            { o: 100, h: 112, l: 99, c: 110, opacity: 0.5 },
            { o: 100, h: 112, l: 99, c: 110, label: "Close" },
            { o: 102, h: 105, l: 95, c: 96 },
          ],
          overlays: [
            { price: 110, color: C.blue, dash: "6 3", label: "Prev Close" },
            { price: 102, color: C.red, dash: "3 3", label: "Open" },
          ],
          zones: [
            { y0: 102, y1: 110, fill: "rgba(59,130,246,0.04)", stroke: "rgba(107,114,128,0.2)", dash: "4 3" },
          ],
          markers: [
            { ci: 2, price: 95, shape: "x", color: C.gray },
          ],
        },
      },
    ],
  },

  // ═══════════════════════════════════════════
  // 2. OPENING RANGE BREAKOUT
  // ═══════════════════════════════════════════
  {
    id: "orb",
    name: "Opening Range Breakout",
    icon: "⏰",
    color: STRAT_COLORS.orb.primary,
    description: "ใช้แท่ง 15 นาทีแรกเป็นกรอบ (Opening Range) แล้วเทรด breakout ด้วยแท่ง 5 นาที",
    cases: [
      {
        title: "ORB Breakout Up ✅",
        badge: "BUY", badgeColor: C.green,
        desc: "แท่ง 5 นาที Close เหนือ High ของ Opening Range 15m → Buy",
        action: "🟢 BUY เมื่อ 5m Close > OR High | SL = OR Low",
        chart: {
          candles: [
            { o: 104, h: 110, l: 100, c: 107, color: "#475569" },
            { o: 108, h: 112, l: 107, c: 111 },
            { o: 111, h: 115, l: 110, c: 114 },
            { o: 114, h: 117, l: 113, c: 116 },
          ],
          overlays: [
            { price: 110, color: C.cyan, dash: "6 3", label: "OR High", width: 1.5 },
            { price: 100, color: C.cyan, dash: "6 3", label: "OR Low", width: 1.5 },
          ],
          zones: [
            { y0: 100, y1: 110, fill: "rgba(6,182,212,0.05)", stroke: "rgba(6,182,212,0.2)", dash: "4 3" },
          ],
          markers: [
            { ci: 1, price: 112, shape: "tri-up", color: C.green },
          ],
        },
      },
      {
        title: "ORB Breakout Down ✅",
        badge: "SELL", badgeColor: C.red,
        desc: "แท่ง 5 นาที Close ต่ำกว่า Low ของ Opening Range 15m → Sell",
        action: "🔴 SELL เมื่อ 5m Close < OR Low | SL = OR High",
        chart: {
          candles: [
            { o: 106, h: 110, l: 100, c: 103, color: "#475569" },
            { o: 101, h: 102, l: 97, c: 98 },
            { o: 98, h: 99, l: 94, c: 95 },
            { o: 95, h: 96, l: 92, c: 93 },
          ],
          overlays: [
            { price: 110, color: C.cyan, dash: "6 3", label: "OR High", width: 1.5 },
            { price: 100, color: C.cyan, dash: "6 3", label: "OR Low", width: 1.5 },
          ],
          zones: [
            { y0: 100, y1: 110, fill: "rgba(6,182,212,0.05)", stroke: "rgba(6,182,212,0.2)", dash: "4 3" },
          ],
          markers: [
            { ci: 1, price: 96, shape: "tri-down", color: C.red },
          ],
        },
      },
      {
        title: "ORB False Breakout ❌",
        badge: "FAIL", badgeColor: C.gray,
        desc: "Breakout ขึ้นแต่กลับลงมาใน Range → False Breakout",
        action: "🚫 SL — ราคากลับเข้า Opening Range",
        chart: {
          candles: [
            { o: 104, h: 110, l: 100, c: 107, color: "#475569" },
            { o: 108, h: 112, l: 107, c: 111 },
            { o: 111, h: 112, l: 104, c: 105 },
            { o: 105, h: 107, l: 102, c: 103 },
          ],
          overlays: [
            { price: 110, color: C.cyan, dash: "6 3", label: "OR High" },
            { price: 100, color: C.cyan, dash: "6 3", label: "OR Low" },
          ],
          zones: [
            { y0: 100, y1: 110, fill: "rgba(6,182,212,0.04)", stroke: "rgba(107,114,128,0.2)", dash: "4 3" },
          ],
          markers: [
            { ci: 2, price: 104, shape: "x", color: C.gray },
          ],
        },
      },
    ],
  },

  // ═══════════════════════════════════════════
  // 3. OOPS STRATEGY
  // ═══════════════════════════════════════════
  {
    id: "oops",
    name: "Oops Strategy",
    icon: "😲",
    color: "#ec4899",
    description: "เมื่อ Gap ≥15 จุด ในทิศตรงข้ามกับแท่งวันก่อน → คาดว่าจะกลับตัว (Oops reversal)",
    cases: [
      {
        title: "Oops Sell (Gap Up หลังวันขึ้น) ✅",
        badge: "SELL", badgeColor: C.red,
        desc: "วันก่อนเขียว (ขึ้น) → วันนี้ Gap Up ≥15 pts → ขายเมื่อราคาหลุด High วันก่อน",
        action: "🔴 SELL เมื่อ price กลับลงถึง Prev High | TP = Prev Close",
        chart: {
          candles: [
            { o: 100, h: 112, l: 99, c: 110 },
            { o: 126, h: 128, l: 113, c: 114 },
          ],
          overlays: [
            { price: 112, color: "#ec4899", dash: "6 3", label: "Prev High", width: 1.2 },
            { price: 110, color: C.blue, dash: "3 3", label: "Prev Close" },
            { price: 126, color: C.green, dash: "3 3", label: "Open +16" },
          ],
          zones: [
            { y0: 112, y1: 126, fill: "rgba(236,72,153,0.06)", stroke: "rgba(236,72,153,0.3)", dash: "4 3" },
          ],
          markers: [
            { ci: 1, price: 112, shape: "tri-down", color: C.red },
          ],
        },
      },
      {
        title: "Oops Buy (Gap Down หลังวันลง) ✅",
        badge: "BUY", badgeColor: C.green,
        desc: "วันก่อนแดง (ลง) → วันนี้ Gap Down ≥15 pts → ซื้อเมื่อราคาขึ้นถึง Low วันก่อน",
        action: "🟢 BUY เมื่อ price กลับขึ้นถึง Prev Low | TP = Prev Close",
        chart: {
          candles: [
            { o: 120, h: 121, l: 108, c: 110 },
            { o: 92, h: 109, l: 90, c: 108 },
          ],
          overlays: [
            { price: 108, color: "#ec4899", dash: "6 3", label: "Prev Low", width: 1.2 },
            { price: 110, color: C.blue, dash: "3 3", label: "Prev Close" },
            { price: 92, color: C.red, dash: "3 3", label: "Open -16" },
          ],
          zones: [
            { y0: 92, y1: 108, fill: "rgba(236,72,153,0.06)", stroke: "rgba(236,72,153,0.3)", dash: "4 3" },
          ],
          markers: [
            { ci: 1, price: 108, shape: "tri-up", color: C.green },
          ],
        },
      },
      {
        title: "Oops ไม่กลับตัว ❌",
        badge: "FAIL", badgeColor: C.gray,
        desc: "Gap Up แต่ราคาไม่กลับลง → วิ่งต่อไปเลย ไม่มีสัญญาณ Oops",
        action: "🚫 NO TRADE — Gap ไม่ reverse, momentum ทิศเดิมแรง",
        chart: {
          candles: [
            { o: 100, h: 112, l: 99, c: 110 },
            { o: 126, h: 134, l: 125, c: 132 },
          ],
          overlays: [
            { price: 112, color: "#ec4899", dash: "6 3", label: "Prev High" },
            { price: 126, color: C.green, dash: "3 3", label: "Open" },
          ],
          zones: [
            { y0: 112, y1: 126, fill: "rgba(107,114,128,0.04)", stroke: "rgba(107,114,128,0.15)", dash: "4 3" },
          ],
          markers: [
            { ci: 1, price: 134, shape: "arrow-up", color: C.gray, opacity: 0.5 },
          ],
        },
      },
    ],
  },

  // ═══════════════════════════════════════════
  // 4. PBD STRATEGY (Price Breakout / Breakdown)
  // ═══════════════════════════════════════════
  {
    id: "pbd",
    name: "PBD Strategy",
    icon: "📐",
    color: STRAT_COLORS.pbd.primary,
    description: "ราคา consolidate ในกรอบแคบ (zigzag) → เทรดเมื่อ breakout ออกจากกรอบ",
    cases: [
      {
        title: "PBD Breakout Up ✅",
        badge: "BUY", badgeColor: C.green,
        desc: "ราคา consolidate ในกรอบ → แท่งเขียว Close เหนือ Range High → Breakout Up",
        action: "🟢 BUY เมื่อ Close > Range High | SL = Range Low",
        chart: {
          candles: [
            { o: 104, h: 107, l: 102, c: 106, color: "#475569", opacity: 0.6 },
            { o: 106, h: 108, l: 103, c: 104, color: "#475569", opacity: 0.6 },
            { o: 104, h: 107, l: 101, c: 106, color: "#475569", opacity: 0.6 },
            { o: 106, h: 108, l: 103, c: 105, color: "#475569", opacity: 0.6 },
            { o: 105, h: 113, l: 104, c: 112 },
            { o: 112, h: 116, l: 111, c: 115 },
          ],
          overlays: [
            { price: 108, color: C.purple, dash: "6 3", label: "Range H", width: 1.3 },
            { price: 101, color: C.purple, dash: "6 3", label: "Range L", width: 1.3 },
          ],
          zones: [
            { y0: 101, y1: 108, fill: "rgba(168,85,247,0.04)", stroke: "rgba(168,85,247,0.2)", dash: "4 3" },
          ],
          markers: [
            { ci: 4, price: 113, shape: "tri-up", color: C.green },
          ],
        },
      },
      {
        title: "PBD Breakdown ✅",
        badge: "SELL", badgeColor: C.red,
        desc: "ราคา consolidate → แท่งแดง Close ต่ำกว่า Range Low → Breakdown",
        action: "🔴 SELL เมื่อ Close < Range Low | SL = Range High",
        chart: {
          candles: [
            { o: 106, h: 108, l: 103, c: 104, color: "#475569", opacity: 0.6 },
            { o: 104, h: 107, l: 102, c: 106, color: "#475569", opacity: 0.6 },
            { o: 106, h: 108, l: 103, c: 105, color: "#475569", opacity: 0.6 },
            { o: 105, h: 107, l: 101, c: 103, color: "#475569", opacity: 0.6 },
            { o: 103, h: 104, l: 97, c: 98 },
            { o: 98, h: 99, l: 94, c: 95 },
          ],
          overlays: [
            { price: 108, color: C.purple, dash: "6 3", label: "Range H", width: 1.3 },
            { price: 101, color: C.purple, dash: "6 3", label: "Range L", width: 1.3 },
          ],
          zones: [
            { y0: 101, y1: 108, fill: "rgba(168,85,247,0.04)", stroke: "rgba(168,85,247,0.2)", dash: "4 3" },
          ],
          markers: [
            { ci: 4, price: 96, shape: "tri-down", color: C.red },
          ],
        },
      },
      {
        title: "PBD False Breakout ❌",
        badge: "FAIL", badgeColor: C.gray,
        desc: "Breakout ขึ้น → กลับเข้า Range → False breakout, SL ถูกชน",
        action: "🚫 SL — ราคากลับเข้ากรอบ consolidation",
        chart: {
          candles: [
            { o: 104, h: 107, l: 102, c: 106, color: "#475569", opacity: 0.6 },
            { o: 106, h: 108, l: 103, c: 105, color: "#475569", opacity: 0.6 },
            { o: 105, h: 107, l: 101, c: 106, color: "#475569", opacity: 0.6 },
            { o: 106, h: 110, l: 105, c: 109 },
            { o: 109, h: 110, l: 103, c: 104 },
            { o: 104, h: 106, l: 100, c: 101 },
          ],
          overlays: [
            { price: 108, color: C.purple, dash: "6 3", label: "Range H" },
            { price: 101, color: C.purple, dash: "6 3", label: "Range L" },
          ],
          zones: [
            { y0: 101, y1: 108, fill: "rgba(168,85,247,0.03)", stroke: "rgba(107,114,128,0.15)", dash: "4 3" },
          ],
          markers: [
            { ci: 4, price: 103, shape: "x", color: C.gray },
          ],
        },
      },
      {
        title: "PBD Still Consolidating ⏳",
        badge: "WAIT", badgeColor: C.orange,
        desc: "ราคายังคง zigzag อยู่ในกรอบ ยังไม่ breakout → รอ",
        action: "⏸ WAIT — รอให้ Close ทะลุกรอบก่อน",
        chart: {
          candles: [
            { o: 104, h: 107, l: 102, c: 106, color: "#475569", opacity: 0.6 },
            { o: 106, h: 108, l: 103, c: 104, color: "#475569", opacity: 0.6 },
            { o: 104, h: 107, l: 101, c: 106, color: "#475569", opacity: 0.6 },
            { o: 106, h: 108, l: 102, c: 103, color: "#475569", opacity: 0.6 },
            { o: 103, h: 107, l: 102, c: 106, color: "#475569", opacity: 0.6 },
            { o: 106, h: 107, l: 103, c: 104, color: "#475569", opacity: 0.6 },
          ],
          overlays: [
            { price: 108, color: C.purple, dash: "6 3", label: "Range H" },
            { price: 101, color: C.purple, dash: "6 3", label: "Range L" },
          ],
          zones: [
            { y0: 101, y1: 108, fill: "rgba(168,85,247,0.04)", stroke: "rgba(168,85,247,0.2)", dash: "4 3" },
          ],
          markers: [
            { ci: 5, price: 105, shape: "clock", color: C.orange },
          ],
        },
      },
    ],
  },

  // ═══════════════════════════════════════════
  // 5. RULE OF 4
  // ═══════════════════════════════════════════
  {
    id: "r4",
    name: "Rule of 4",
    icon: "4️⃣",
    color: STRAT_COLORS.r4.primary,
    description: "หลังเหตุการณ์สำคัญ (NFP/FOMC/DAX/FTSE) รอ 4 แท่งแรก → เทรดตามทิศทางที่ออก",
    cases: [
      {
        title: "Rule of 4 → Buy ✅",
        badge: "BUY", badgeColor: C.green,
        desc: "4 แท่งแรกหลัง event → ราคา Close เหนือ High ของ 4 แท่ง → Buy",
        action: "🟢 BUY เมื่อ Close > High(4 bars) | SL = Low(4 bars)",
        chart: {
          candles: [
            { o: 104, h: 108, l: 103, c: 107, color: "#475569" },
            { o: 107, h: 109, l: 104, c: 105, color: "#475569" },
            { o: 105, h: 108, l: 103, c: 107, color: "#475569" },
            { o: 107, h: 110, l: 106, c: 109, color: "#475569" },
            { o: 109, h: 114, l: 108, c: 113 },
            { o: 113, h: 118, l: 112, c: 117 },
          ],
          overlays: [
            { price: 110, color: C.orange, dash: "6 3", label: "4-Bar High", width: 1.3 },
            { price: 103, color: C.orange, dash: "6 3", label: "4-Bar Low", width: 1.3 },
          ],
          zones: [
            { y0: 103, y1: 110, fill: "rgba(249,115,22,0.04)", stroke: "rgba(249,115,22,0.2)", dash: "4 3" },
          ],
          markers: [
            { ci: 4, price: 114, shape: "tri-up", color: C.green },
          ],
        },
      },
      {
        title: "Rule of 4 → Sell ✅",
        badge: "SELL", badgeColor: C.red,
        desc: "4 แท่งแรก → ราคา Close ต่ำกว่า Low ของ 4 แท่ง → Sell",
        action: "🔴 SELL เมื่อ Close < Low(4 bars) | SL = High(4 bars)",
        chart: {
          candles: [
            { o: 108, h: 110, l: 104, c: 105, color: "#475569" },
            { o: 105, h: 109, l: 103, c: 107, color: "#475569" },
            { o: 107, h: 110, l: 105, c: 106, color: "#475569" },
            { o: 106, h: 108, l: 103, c: 104, color: "#475569" },
            { o: 104, h: 105, l: 99, c: 100 },
            { o: 100, h: 101, l: 95, c: 96 },
          ],
          overlays: [
            { price: 110, color: C.orange, dash: "6 3", label: "4-Bar High", width: 1.3 },
            { price: 103, color: C.orange, dash: "6 3", label: "4-Bar Low", width: 1.3 },
          ],
          zones: [
            { y0: 103, y1: 110, fill: "rgba(249,115,22,0.04)", stroke: "rgba(249,115,22,0.2)", dash: "4 3" },
          ],
          markers: [
            { ci: 4, price: 98, shape: "tri-down", color: C.red },
          ],
        },
      },
      {
        title: "Rule of 4 → ยังอยู่ใน Range ⏳",
        badge: "WAIT", badgeColor: C.orange,
        desc: "หลัง 4 แท่ง ราคายังไม่ทะลุ High/Low ของกรอบ → รอ",
        action: "⏸ WAIT — ราคายังไม่ตัดสินใจทิศทาง",
        chart: {
          candles: [
            { o: 104, h: 108, l: 103, c: 107, color: "#475569" },
            { o: 107, h: 109, l: 104, c: 105, color: "#475569" },
            { o: 105, h: 108, l: 103, c: 107, color: "#475569" },
            { o: 107, h: 110, l: 106, c: 108, color: "#475569" },
            { o: 108, h: 109, l: 105, c: 106, color: "#475569", opacity: 0.7 },
            { o: 106, h: 109, l: 104, c: 108, color: "#475569", opacity: 0.7 },
          ],
          overlays: [
            { price: 110, color: C.orange, dash: "6 3", label: "4-Bar High" },
            { price: 103, color: C.orange, dash: "6 3", label: "4-Bar Low" },
          ],
          zones: [
            { y0: 103, y1: 110, fill: "rgba(249,115,22,0.04)", stroke: "rgba(249,115,22,0.2)", dash: "4 3" },
          ],
          markers: [
            { ci: 5, price: 107, shape: "clock", color: C.orange },
          ],
        },
      },
    ],
  },

  // ═══════════════════════════════════════════
  // 6. VOLUME PROFILE BREAKOUT ZONES
  // ═══════════════════════════════════════════
  {
    id: "vp",
    name: "VP Breakout Zones",
    icon: "📊",
    color: STRAT_COLORS.vp.primary,
    description: "กล่อง VAH→LVN(บน) / VAL→LVN(ล่าง) — เฉพาะตลาด Balanced เท่านั้น",
    cases: [
      {
        title: "Confirmed Breakout ↑ ✅",
        badge: "BUY", badgeColor: C.green,
        desc: "ราคาทะลุ VAH → เข้ากล่อง → ผ่าน LVN Upper = ยืนยัน",
        action: "🟢 BUY เมื่อ Close > LVN Upper",
        chart: {
          candles: [
            { o: 105, h: 108, l: 104, c: 107 },
            { o: 107, h: 110, l: 106, c: 109 },
            { o: 109, h: 113, l: 108, c: 112 },
            { o: 112, h: 117, l: 111, c: 116 },
            { o: 116, h: 120, l: 115, c: 119 },
          ],
          overlays: [
            { price: 116, color: C.purple, dash: "2 3", label: "LVN↑" },
            { price: 112, color: C.red, label: "VAH", width: 1.5 },
            { price: 106, color: C.orange, dash: "6 4", label: "POC" },
            { price: 100, color: C.green, label: "VAL", width: 1.5 },
            { price: 96, color: C.purple, dash: "2 3", label: "LVN↓" },
          ],
          zones: [
            { y0: 112, y1: 116, fill: "rgba(239,68,68,0.08)", stroke: "rgba(239,68,68,0.3)", dash: "4 3" },
            { y0: 100, y1: 112, fill: "rgba(245,158,11,0.03)" },
            { y0: 96, y1: 100, fill: "rgba(16,185,129,0.08)", stroke: "rgba(16,185,129,0.3)", dash: "4 3" },
          ],
          markers: [
            { ci: 3, price: 117, shape: "tri-up", color: C.green },
          ],
        },
      },
      {
        title: "Confirmed Breakout ↓ ✅",
        badge: "SELL", badgeColor: C.red,
        desc: "ราคาหลุด VAL → เข้ากล่อง → ผ่าน LVN Lower = ยืนยัน",
        action: "🔴 SELL เมื่อ Close < LVN Lower",
        chart: {
          candles: [
            { o: 108, h: 109, l: 105, c: 106 },
            { o: 106, h: 107, l: 102, c: 103 },
            { o: 103, h: 104, l: 98, c: 99 },
            { o: 99, h: 100, l: 94, c: 95 },
            { o: 95, h: 96, l: 92, c: 93 },
          ],
          overlays: [
            { price: 116, color: C.purple, dash: "2 3", label: "LVN↑" },
            { price: 112, color: C.red, label: "VAH", width: 1.5 },
            { price: 106, color: C.orange, dash: "6 4", label: "POC" },
            { price: 100, color: C.green, label: "VAL", width: 1.5 },
            { price: 96, color: C.purple, dash: "2 3", label: "LVN↓" },
          ],
          zones: [
            { y0: 112, y1: 116, fill: "rgba(239,68,68,0.08)", stroke: "rgba(239,68,68,0.3)", dash: "4 3" },
            { y0: 100, y1: 112, fill: "rgba(245,158,11,0.03)" },
            { y0: 96, y1: 100, fill: "rgba(16,185,129,0.08)", stroke: "rgba(16,185,129,0.3)", dash: "4 3" },
          ],
          markers: [
            { ci: 3, price: 93, shape: "tri-down", color: C.red },
          ],
        },
      },
      {
        title: "Pending (อยู่ในกล่อง) ⏳",
        badge: "PENDING", badgeColor: C.orange,
        desc: "ราคาทะลุ VAH แต่ยังอยู่ในกล่อง → ยังไม่ผ่าน LVN",
        action: "⏸ WAIT — รอ Close > LVN หรือ < VAH",
        chart: {
          candles: [
            { o: 106, h: 108, l: 105, c: 107 },
            { o: 107, h: 110, l: 106, c: 109 },
            { o: 109, h: 114, l: 108, c: 113 },
            { o: 113, h: 115, l: 112, c: 114 },
            { o: 114, h: 115.5, l: 113, c: 114.5 },
          ],
          overlays: [
            { price: 116, color: C.purple, dash: "2 3", label: "LVN↑" },
            { price: 112, color: C.red, label: "VAH", width: 1.5 },
            { price: 106, color: C.orange, dash: "6 4", label: "POC" },
            { price: 100, color: C.green, label: "VAL", width: 1.5 },
          ],
          zones: [
            { y0: 112, y1: 116, fill: "rgba(239,68,68,0.08)", stroke: "rgba(239,68,68,0.3)", dash: "4 3" },
            { y0: 100, y1: 112, fill: "rgba(245,158,11,0.03)" },
          ],
          markers: [
            { ci: 4, price: 115.5, shape: "clock", color: C.orange },
          ],
        },
      },
      {
        title: "Rejected (ถูกตีกลับ) ❌",
        badge: "REJECTED", badgeColor: C.gray,
        desc: "เข้ากล่องแล้วกลับเข้า VA → False Breakout",
        action: "🚫 NO TRADE — หรือ Fade กลับ",
        chart: {
          candles: [
            { o: 106, h: 109, l: 105, c: 108 },
            { o: 108, h: 114, l: 107, c: 113 },
            { o: 113, h: 115, l: 112, c: 114 },
            { o: 114, h: 115, l: 107, c: 108 },
            { o: 108, h: 109, l: 105, c: 106 },
          ],
          overlays: [
            { price: 116, color: C.purple, dash: "2 3", label: "LVN↑" },
            { price: 112, color: C.red, label: "VAH", width: 1.5 },
            { price: 106, color: C.orange, dash: "6 4", label: "POC" },
            { price: 100, color: C.green, label: "VAL", width: 1.5 },
          ],
          zones: [
            { y0: 112, y1: 116, fill: "rgba(239,68,68,0.06)", stroke: "rgba(107,114,128,0.2)", dash: "4 3" },
            { y0: 100, y1: 112, fill: "rgba(245,158,11,0.03)" },
          ],
          markers: [
            { ci: 3, price: 107, shape: "x", color: C.gray },
          ],
        },
      },
    ],
  },
];

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// COMPONENTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function CaseCard({ c, stratColor }) {
  return (
    <div style={{
      background: C.card, borderRadius: 12,
      border: `1px solid ${C.border}`, overflow: "hidden",
      transition: "border-color 0.2s",
    }}
    onMouseEnter={e => e.currentTarget.style.borderColor = C.borderHi}
    onMouseLeave={e => e.currentTarget.style.borderColor = C.border}
    >
      <div style={{
        padding: "10px 14px 8px", display: "flex",
        justifyContent: "space-between", alignItems: "flex-start",
        borderBottom: `1px solid ${C.border}`,
      }}>
        <div style={{ fontSize: "0.82rem", fontWeight: 700, color: C.text }}>{c.title}</div>
        <span style={{
          fontSize: "0.65rem", fontWeight: 700, color: c.badgeColor,
          background: `${c.badgeColor}15`, padding: "2px 8px",
          borderRadius: 10, whiteSpace: "nowrap",
        }}>{c.badge}</span>
      </div>

      <div style={{ background: "rgba(0,0,0,0.25)", padding: "2px 4px" }}>
        <MiniChart
          candles={c.chart.candles}
          overlays={c.chart.overlays || []}
          markers={c.chart.markers || []}
          zones={c.chart.zones || []}
          width={300} height={175}
        />
      </div>

      <div style={{ padding: "10px 14px" }}>
        <div style={{ fontSize: "0.72rem", color: C.textSec, lineHeight: 1.6, marginBottom: 8 }}>
          {c.desc}
        </div>
        <div style={{
          fontSize: "0.7rem", fontWeight: 600, color: C.text,
          background: "rgba(255,255,255,0.02)", padding: "6px 10px",
          borderRadius: 6, borderLeft: `3px solid ${c.badgeColor}`,
        }}>
          {c.action}
        </div>
      </div>
    </div>
  );
}

function StrategySection({ strat }) {
  return (
    <div style={{ marginBottom: "2.5rem" }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 10, marginBottom: 6,
        paddingBottom: 10, borderBottom: `2px solid ${strat.color}25`,
      }}>
        <span style={{ fontSize: "1.4rem" }}>{strat.icon}</span>
        <div>
          <h2 style={{
            fontSize: "1.15rem", fontWeight: 800, color: strat.color,
            margin: 0, letterSpacing: "-0.01em",
          }}>{strat.name}</h2>
          <p style={{ fontSize: "0.73rem", color: C.textMuted, margin: 0 }}>{strat.description}</p>
        </div>
        <span style={{
          marginLeft: "auto", fontSize: "0.65rem", color: C.textMuted,
          background: `${strat.color}10`, padding: "3px 10px",
          borderRadius: 10, border: `1px solid ${strat.color}25`,
        }}>
          {strat.cases.length} cases
        </span>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: `repeat(auto-fill, minmax(290px, 1fr))`,
        gap: "0.8rem",
      }}>
        {strat.cases.map((c, i) => (
          <CaseCard key={i} c={c} stratColor={strat.color} />
        ))}
      </div>
    </div>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MAIN
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export default function AllStrategyCases() {
  const [filter, setFilter] = useState("all");

  const filtered = filter === "all" ? STRATEGIES : STRATEGIES.filter(s => s.id === filter);
  const totalCases = STRATEGIES.reduce((sum, s) => sum + s.cases.length, 0);

  return (
    <div style={{
      background: C.bg, minHeight: "100vh", padding: "1.5rem 1.2rem",
      fontFamily: "'SF Mono','JetBrains Mono','Fira Code',monospace",
      color: C.text,
    }}>
      <div style={{ maxWidth: 1250, margin: "0 auto" }}>
        {/* Header */}
        <h1 style={{
          fontSize: "1.5rem", fontWeight: 800, margin: 0, marginBottom: 4,
          background: "linear-gradient(135deg, #3b82f6, #06b6d4, #f59e0b, #ef4444, #a855f7)",
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
        }}>
          Trading Strategy Cases — All 6 Strategies
        </h1>
        <p style={{ color: C.textSec, fontSize: "0.78rem", margin: "0 0 1.2rem" }}>
          ทุกสถานการณ์ของทุก strategy — รวม {totalCases} เคส
        </p>

        {/* Filter tabs */}
        <div style={{
          display: "flex", gap: 6, marginBottom: "1.5rem", flexWrap: "wrap",
          padding: "8px 12px", background: C.card,
          borderRadius: 10, border: `1px solid ${C.border}`,
        }}>
          <button
            onClick={() => setFilter("all")}
            style={{
              background: filter === "all" ? "rgba(255,255,255,0.1)" : "transparent",
              border: `1px solid ${filter === "all" ? "rgba(255,255,255,0.2)" : "transparent"}`,
              color: C.text, borderRadius: 8, padding: "5px 14px",
              fontSize: "0.73rem", fontWeight: 600, cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            All ({totalCases})
          </button>
          {STRATEGIES.map(s => (
            <button
              key={s.id}
              onClick={() => setFilter(s.id)}
              style={{
                background: filter === s.id ? `${s.color}20` : "transparent",
                border: `1px solid ${filter === s.id ? `${s.color}40` : "transparent"}`,
                color: filter === s.id ? s.color : C.textSec,
                borderRadius: 8, padding: "5px 14px",
                fontSize: "0.73rem", fontWeight: 600, cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              {s.icon} {s.name} ({s.cases.length})
            </button>
          ))}
        </div>

        {/* Strategy Sections */}
        {filtered.map(s => (
          <StrategySection key={s.id} strat={s} />
        ))}

        {/* Summary Table */}
        <div style={{
          background: C.card, borderRadius: 12,
          border: `1px solid ${C.border}`, padding: "16px 20px",
          marginTop: "1rem",
        }}>
          <h3 style={{ fontSize: "0.9rem", fontWeight: 700, color: C.text, margin: "0 0 12px" }}>
            📋 สรุปทุก Strategy
          </h3>
          <div style={{ overflowX: "auto" }}>
            <table style={{
              width: "100%", borderCollapse: "collapse",
              fontSize: "0.72rem", color: C.textSec,
            }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  {["Strategy", "Trigger", "Entry", "TP", "SL", "Cases"].map(h => (
                    <th key={h} style={{
                      padding: "8px 10px", textAlign: "left",
                      color: C.textMuted, fontWeight: 600,
                      fontSize: "0.65rem", textTransform: "uppercase",
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  ["📉 Gap Fill", "Gap ≥10 pts จาก Prev Close", "Open วันนี้ (ทิศปิด Gap)", "Prev Close", "เลย Open ตรงข้าม", "3"],
                  ["⏰ ORB", "15m แรก = Range", "5m Close ทะลุ Range", "1:1 หรือ 2:1 RR", "ฝั่งตรงข้ามของ Range", "3"],
                  ["😲 Oops", "Gap ≥15 pts ทิศตรงข้ามวันก่อน", "เมื่อราคากลับถึง Prev H/L", "Prev Close", "เลย Open วันนี้", "3"],
                  ["📐 PBD", "Consolidate ≥4 แท่ง", "Close ทะลุ Range H/L", "1:1 หรือ Measured Move", "ฝั่งตรงข้าม Range", "4"],
                  ["4️⃣ Rule of 4", "หลัง NFP/FOMC 4 แท่ง", "Close ทะลุ 4-bar H/L", "Momentum follow", "ฝั่งตรงข้าม 4-bar", "3"],
                  ["📊 VP Zones", "Balanced Market + VP", "Close ทะลุ LVN (ผ่านกล่อง)", "Next HVN/VA", "กลับเข้า VA", "4"],
                ].map((row, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}` }}>
                    {row.map((cell, j) => (
                      <td key={j} style={{
                        padding: "8px 10px",
                        color: j === 0 ? C.text : C.textSec,
                        fontWeight: j === 0 ? 600 : 400,
                      }}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
