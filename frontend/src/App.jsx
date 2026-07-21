import { useState, useEffect, useCallback, useRef } from "react";
import { domToPng } from "modern-screenshot";
import {
  Zap, ZapOff, Download, Upload, RefreshCw, SlidersHorizontal,
  ChevronDown, ChevronUp, Radio, TowerControl, Clock, Database,
  Power, PowerOff, Settings, Search, Battery, Lightbulb, Info,
  FlaskConical, Lock, ArrowLeft, Shield, Calendar, Camera
} from "lucide-react";
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ReferenceLine, ReferenceArea
} from "recharts";

const API = import.meta.env.VITE_API_URL || "/api";

const PALETTE = {
  bg: "#0f172a",
  surface: "#1e293b",
  surfaceHover: "#334155",
  border: "#334155",
  text: "#f1f5f9",
  textMuted: "#94a3b8",
  accent: "#3b82f6",
  green: "#22c55e",
  red: "#ef4444",
  amber: "#f59e0b",
  cyan: "#06b6d4",
  purple: "#a855f7",
  pink: "#ec4899",
};

const DATE_INPUT_STYLE = {
  colorScheme: "dark",
  caretColor: PALETTE.text,
};

const dateInputClass = "rounded-xl px-3 py-2 text-sm outline-none w-full";

/* ──────────────────── SCREENSHOT BUTTON ──────────────────── */

function ScreenshotButton({ targetRef, label }) {
  const [capturing, setCapturing] = useState(false);

  const handleCapture = async () => {
    if (!targetRef.current || capturing) return;
    setCapturing(true);
    try {
      const btn = targetRef.current.querySelector("[data-screenshot-btn]");
      if (btn) btn.style.display = "none";
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));

      const now = new Date();
      const dateStr = now.toLocaleDateString("en-US", { weekday: "short", year: "numeric", month: "short", day: "numeric" });
      const timeStr = now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
      const fileName = `${label}_${now.toISOString().slice(0, 10)}_${String(now.getHours()).padStart(2, "0")}.png`;

      const wrapper = document.createElement("div");
      wrapper.style.cssText = `
        font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
        background: #0f172a; padding: 0;
        width: ${targetRef.current.scrollWidth}px;
        border-radius: 16px; overflow: hidden;
      `;

      const header = document.createElement("div");
      header.style.cssText = `
        display: flex; align-items: center; justify-content: space-between;
        padding: 16px 24px;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border-bottom: 1px solid #334155;
      `;
      header.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px;">
          <div style="width: 36px; height: 36px; border-radius: 10px; background: linear-gradient(135deg, #38bdf8, #818cf8); display: flex; align-items: center; justify-content: center;">
            <span style="color: white; font-weight: 700; font-size: 14px;">CP</span>
          </div>
          <div>
            <div style="color: #f1f5f9; font-weight: 600; font-size: 14px; letter-spacing: 0.5px;">${label.replace(/_/g, " ")}</div>
            <div style="color: #94a3b8; font-size: 11px; margin-top: 1px;">Carrier Power System</div>
          </div>
        </div>
        <div style="text-align: right;">
          <div style="color: #94a3b8; font-size: 11px;">${dateStr}</div>
          <div style="color: #64748b; font-size: 10px; margin-top: 1px;">${timeStr}</div>
        </div>
      `;

      const body = document.createElement("div");
      body.style.cssText = "padding: 0;";
      body.appendChild(targetRef.current.cloneNode(true));

      const footer = document.createElement("div");
      footer.style.cssText = `
        display: flex; align-items: center; justify-content: space-between;
        padding: 10px 24px;
        background: #0f172a;
        border-top: 1px solid #1e293b;
      `;
      footer.innerHTML = `
        <span style="color: #475569; font-size: 9px; letter-spacing: 0.3px; text-transform: uppercase;">Carrier Power System</span>
        <span style="color: #475569; font-size: 9px;">KHI0080H SADDAR1</span>
      `;

      wrapper.appendChild(header);
      wrapper.appendChild(body);
      wrapper.appendChild(footer);

      document.body.appendChild(wrapper);

      const dataUrl = await domToPng(wrapper, {
        pixelRatio: 2,
        backgroundColor: "#0f172a",
      });

      document.body.removeChild(wrapper);
      if (btn) btn.style.display = "";

      const link = document.createElement("a");
      link.download = fileName;
      link.href = dataUrl;
      link.click();
    } catch (e) {
      const btn2 = targetRef.current?.querySelector("[data-screenshot-btn]");
      if (btn2) btn2.style.display = "";
      console.error("Screenshot failed:", e);
    } finally {
      setCapturing(false);
    }
  };

  return (
    <button
      data-screenshot-btn
      onClick={handleCapture}
      disabled={capturing}
      className="p-1.5 rounded-lg transition-all duration-150"
      style={{
        background: capturing ? PALETTE.accent + "40" : "transparent",
        color: capturing ? PALETTE.accent : PALETTE.textMuted,
        cursor: capturing ? "wait" : "pointer",
      }}
      onMouseEnter={(e) => { if (!capturing) { e.currentTarget.style.background = PALETTE.bg; e.currentTarget.style.color = PALETTE.accent; } }}
      onMouseLeave={(e) => { if (!capturing) { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = PALETTE.textMuted; } }}
      title={`Download ${label} as PNG`}
    >
      {capturing ? <RefreshCw size={14} className="animate-spin" /> : <Camera size={14} />}
    </button>
  );
}

function CarrierLabel({ code }) {
  return <span>Carrier {code}</span>;
}

function displayCarrier(code) {
  return `Carrier ${code}`;
}

/* ──────────────────── CALENDAR PICKER ──────────────────── */

function CalendarPicker({ selected, onSelect, min, max }) {
  const [viewDate, setViewDate] = useState(() => {
    const [y, m, d] = (selected || new Date().toISOString().slice(0, 10)).split("-").map(Number);
    return new Date(y, m - 1, 1);
  });

  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();
  const today = new Date();
  const todayStr = today.toISOString().slice(0, 10);

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const monthLabel = viewDate.toLocaleString("en-US", { month: "short", year: "numeric" });
  const weekdays = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

  const cells = [];
  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const selectedDate = selected || "";
  const todayDate = today.toISOString().slice(0, 10);

  function dayToDate(d) {
    return `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  }

  function isDisabled(d) {
    if (!d) return true;
    const ds = dayToDate(d);
    if (min && ds < min) return true;
    if (max && ds > max) return true;
    return false;
  }

  const navigate = (delta) => {
    setViewDate(new Date(year, month + delta, 1));
  };

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-2">
        <button onClick={() => navigate(-1)} className="p-1 rounded-lg transition-colors hover:bg-[#334155]" style={{ color: PALETTE.textMuted }}>
          <ChevronDown size={14} style={{ transform: "rotate(90deg)" }} />
        </button>
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: PALETTE.text }}>{monthLabel}</span>
        <button onClick={() => navigate(1)} className="p-1 rounded-lg transition-colors hover:bg-[#334155]" style={{ color: PALETTE.textMuted }}>
          <ChevronDown size={14} style={{ transform: "rotate(-90deg)" }} />
        </button>
      </div>

      <div className="grid grid-cols-7 gap-0.5 mb-1">
        {weekdays.map((w) => (
          <div key={w} className="text-center text-[9px] font-medium py-1" style={{ color: PALETTE.textMuted }}>{w}</div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-0.5">
        {cells.map((d, i) => {
          if (d === null) return <div key={`e${i}`} />;
          const ds = dayToDate(d);
          const isSelected = ds === selectedDate;
          const isToday = ds === todayDate;
          const disabled = isDisabled(d);

          return (
            <button
              key={ds}
              disabled={disabled}
              onClick={() => !disabled && onSelect(ds)}
              className="relative flex items-center justify-center rounded-lg text-xs transition-all duration-150"
              style={{
                width: "100%",
                aspectRatio: "1",
                color: disabled ? PALETTE.textMuted + "40" : isSelected ? "#fff" : PALETTE.text,
                background: isSelected ? PALETTE.accent : "transparent",
                opacity: disabled ? 0.4 : 1,
                cursor: disabled ? "default" : "pointer",
                fontWeight: isSelected || isToday ? 600 : 400,
              }}
              onMouseEnter={(e) => { if (!disabled && !isSelected) e.currentTarget.style.background = PALETTE.surfaceHover; }}
              onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}
            >
              {d}
              {isToday && !isSelected && (
                <span className="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full" style={{ background: PALETTE.accent }} />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ──────────────────── HOUR GRID (Horizontal Strip) ──────────────────── */

function HourGrid({ selected, onSelect, onSelectAndClose }) {
  return (
    <div className="grid grid-cols-6 gap-1">
      {Array.from({ length: 24 }, (_, i) => {
        const isSelected = i === selected;
        return (
          <button
            key={i}
            onClick={() => onSelectAndClose ? onSelectAndClose(i) : onSelect(i)}
            className="rounded-lg px-2 py-1.5 text-[11px] font-mono transition-all duration-150"
            style={{
              color: isSelected ? "#fff" : PALETTE.text,
              background: isSelected ? PALETTE.accent : PALETTE.bg,
              border: `1px solid ${isSelected ? PALETTE.accent : PALETTE.border}`,
              fontWeight: isSelected ? 600 : 400,
            }}
            onMouseEnter={(e) => { if (!isSelected) { e.currentTarget.style.borderColor = PALETTE.accent + "80"; e.currentTarget.style.color = PALETTE.text; } }}
            onMouseLeave={(e) => { if (!isSelected) { e.currentTarget.style.borderColor = PALETTE.border; e.currentTarget.style.color = PALETTE.text; } }}
          >
            {String(i).padStart(2, "0")}:00
          </button>
        );
      })}
    </div>
  );
}

/* ──────────────────── POPOVER WRAPPER ──────────────────── */

function usePopover() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return { open, setOpen, ref };
}

function PopoverPanel({ open, panelRef, width = 280, children }) {
  if (!open) return null;
  return (
    <div
      ref={panelRef}
      className="absolute z-50 mt-2 rounded-2xl p-3 shadow-2xl"
      style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, width }}
    >
      {children}
    </div>
  );
}

/* ──────────────────── DATE PICKER (Calendar Popover) ──────────────────── */

function DatePopover({ value, onSelect, min, max, className }) {
  const { open, setOpen, ref } = usePopover();

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-all duration-150 ${className || ""}`}
        style={{
          background: PALETTE.bg,
          border: `1px solid ${open ? PALETTE.accent : PALETTE.border}`,
          color: PALETTE.text,
          width: "100%",
        }}
        onMouseEnter={(e) => { if (!open) e.currentTarget.style.borderColor = PALETTE.accent + "80"; }}
        onMouseLeave={(e) => { if (!open) e.currentTarget.style.borderColor = PALETTE.border; }}
      >
        <Calendar size={14} style={{ color: PALETTE.accent }} />
        <span className="font-medium">{value || "Select date"}</span>
        <ChevronDown size={12} style={{ color: PALETTE.textMuted, transform: open ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }} />
      </button>

      <PopoverPanel open={open} width={280}>
        <CalendarPicker selected={value} onSelect={(d) => { onSelect(d); setOpen(false); }} min={min} max={max} />
      </PopoverPanel>
    </div>
  );
}

/* ──────────────────── HOUR PICKER (Hour Popover) ──────────────────── */

function HourPopover({ hour, onHourChange }) {
  const { open, setOpen, ref } = usePopover();

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm transition-all duration-150"
        style={{
          background: PALETTE.bg,
          border: `1px solid ${open ? PALETTE.accent : PALETTE.border}`,
          color: PALETTE.text,
        }}
        onMouseEnter={(e) => { if (!open) e.currentTarget.style.borderColor = PALETTE.accent + "80"; }}
        onMouseLeave={(e) => { if (!open) e.currentTarget.style.borderColor = PALETTE.border; }}
      >
        <Clock size={14} style={{ color: PALETTE.accent }} />
        <span className="font-medium font-mono">{String(hour).padStart(2, "0")}:00</span>
        <ChevronDown size={12} style={{ color: PALETTE.textMuted, transform: open ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 0.2s" }} />
      </button>

      <PopoverPanel open={open} width={340}>
        <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: PALETTE.textMuted }}>Select Hour</div>
        <HourGrid selected={hour} onSelectAndClose={(h) => { onHourChange(h); setOpen(false); }} />
      </PopoverPanel>
    </div>
  );
}

/* ──────────────────── DATE PICKER (inline for filters) ──────────────────── */

/* ──────────────────── LIVE STATUS HEADER ──────────────────── */

function LiveStatusHeader({ liveStatus }) {
  const tileRefs = useRef({});
  if (!liveStatus) return null;
  const towers = Object.entries(liveStatus.towers);

  const gridClass = towers.length <= 2
    ? "grid grid-cols-1 lg:grid-cols-" + towers.length + " gap-4 mb-6"
    : "grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4 mb-6";

  return (
    <div className={gridClass}>
      {towers.map(([towerLabel, tower]) => {
        if (!tileRefs.current[towerLabel]) tileRefs.current[towerLabel] = { current: null };
        return (
        <div key={towerLabel} ref={(el) => { tileRefs.current[towerLabel].current = el; }} className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <TowerControl size={18} style={{ color: PALETTE.cyan }} />
              <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>{towerLabel}</h3>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs px-2 py-1 rounded-full" style={{ background: tower.mode === "high" ? "#2d1215" : tower.mode === "balanced" ? "#1a2332" : "#0d2818", color: tower.mode === "high" ? PALETTE.red : tower.mode === "balanced" ? PALETTE.amber : PALETTE.green }}>
                {tower.active_count}/{tower.carriers?.length || 3} active
              </span>
              <div className="flex items-center gap-1.5 text-xs px-2 py-1 rounded-full" style={{ background: "#1a2332", color: PALETTE.textMuted }}>
                <Clock size={12} />
                {String(liveStatus.hour).padStart(2, "0")}:00
              </div>
              <ScreenshotButton targetRef={tileRefs.current[towerLabel]} label={`Live_Status_${towerLabel.replace(/\s+/g, "_")}`} />
            </div>
          </div>
          <div className="space-y-3">
            {(tower.carriers || []).sort((a, b) => (a.activation_order || 0) - (b.activation_order || 0)).map((c) => {
              const isOn = c.is_on;
              return (
                <div key={c.sector_label} className="flex items-center justify-between rounded-xl px-4 py-3" style={{ background: isOn ? "#0d2818" : "#2d1215", border: `1px solid ${isOn ? "#166534" : "#7f1d1d"}` }}>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: isOn ? PALETTE.green : PALETTE.red }}>
                      {isOn ? <Power size={16} color="#fff" /> : <PowerOff size={16} color="#fff" />}
                    </div>
                    <div>
                      <div className="font-mono text-sm font-bold" style={{ color: PALETTE.text }}>Carrier {c.sector_label}</div>
                      <div className="text-xs" style={{ color: PALETTE.textMuted }}>
                        {c.is_primary ? "Primary (Always ON)" : `Order #${c.activation_order} — Predicted: ${c.predicted_prb !== null ? c.predicted_prb.toFixed(1) : "—"}%`}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="text-lg font-bold font-mono" style={{ color: isOn ? PALETTE.green : PALETTE.red }}>{c.predicted_prb !== null ? `${c.predicted_prb.toFixed(1)}%` : "—"}</div>
                    </div>
                    <div className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider" style={{ background: isOn ? "#15803d" : "#b91c1c", color: "#fff" }}>
                      {isOn ? "ON" : "OFF"}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 flex items-center justify-between text-xs" style={{ color: PALETTE.textMuted }}>
            <span>Total demand: <span className="font-mono font-bold" style={{ color: PALETTE.text }}>{tower.total_demand?.toFixed(1)}%</span></span>
            <span>Ceiling: <span className="font-mono font-bold" style={{ color: PALETTE.amber }}>{tower.capacity_ceiling}%</span></span>
            <span>Power: <span className="font-mono font-bold" style={{ color: PALETTE.cyan }}>{tower.tower_power_watts?.toFixed(0)}W</span></span>
          </div>
        </div>
        );
      })}
    </div>
  );
}

/* ──────────────────── KPI CARDS ──────────────────── */

function KpiCards({ liveStatus, summary, powerSummary }) {
  const tileRef = useRef(null);
  if (!liveStatus) return null;

  let totalOn = 0;
  let totalOff = 0;
  Object.values(liveStatus.towers).forEach((tower) => {
    (tower.carriers || []).forEach((c) => {
      if (c.is_on) totalOn++;
      else totalOff++;
    });
  });
  const totalCarriers = totalOn + totalOff;

  const totalSavedKwh = powerSummary?.total_saved_kwh ?? 0;
  const latestDay = powerSummary?.daily?.[powerSummary.daily.length - 1];
  const todaySavedPct = latestDay?.saved_pct ?? 0;

  const cards = [
    { label: "Carriers ON", value: totalOn, sub: `/ ${totalCarriers} total`, color: PALETTE.green, icon: Zap },
    { label: "Carriers OFF", value: totalOff, sub: totalCarriers > 0 ? `${((totalOff / totalCarriers) * 100).toFixed(0)}% saved` : "—", color: PALETTE.red, icon: ZapOff },
    { label: "Energy Saved", value: `${totalSavedKwh.toFixed(1)}`, sub: `kWh (7d total)`, color: PALETTE.cyan, icon: Battery },
    { label: "Daily Saving", value: `${todaySavedPct.toFixed(0)}%`, sub: `of baseline kWh`, color: PALETTE.amber, icon: Lightbulb },
  ];

  return (
    <div ref={tileRef} className="rounded-2xl p-4 mb-2" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>Key Metrics</h3>
        <ScreenshotButton targetRef={tileRef} label="KPI_Summary" />
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.label} className="rounded-xl p-4 flex items-start gap-3" style={{ background: PALETTE.bg }}>
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: card.color + "20" }}>
                <Icon size={20} style={{ color: card.color }} />
              </div>
              <div>
                <div className="text-xs uppercase tracking-wider mb-0.5" style={{ color: PALETTE.textMuted }}>{card.label}</div>
                <div className="text-2xl font-bold font-mono" style={{ color: PALETTE.text }}>{card.value}</div>
                <div className="text-xs" style={{ color: PALETTE.textMuted }}>{card.sub}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ──────────────────── TODAY VS HISTORY CHART ──────────────────── */

function TodayVsHistoryChart({ carrier, bandLow, bandHigh }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const tileRef = useRef(null);

  useEffect(() => {
    if (!carrier) { setLoading(false); return; }
    setLoading(true);
    fetch(`${API}/data/today-vs-history?carrier=${carrier}`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [carrier]);

  if (!carrier) return <ChartPlaceholder title="Today vs History" message="Select a specific carrier in the Filters panel to view this chart." />;

  if (loading || !data) return <ChartSkeleton title="Today vs History" />;
  if (data.error) return <ChartPlaceholder title="Today vs History" message={data.error} />;

  const chartData = data.historical.map((h) => {
    const todayPt = data.today.find((t) => t.hour === h.hour);
    return {
      hour: `${String(h.hour).padStart(2, "0")}:00`,
      "Historical Avg": h.avg,
      "Range Low": h.min,
      "Range High": h.max,
      "Today Actual": todayPt ? todayPt.prb : null,
    };
  });

  return (
    <div ref={tileRef} className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>
          {data.weekday} vs History — Carrier {data.carrier}
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-1 rounded-full" style={{ background: "#1a2332", color: PALETTE.textMuted }}>{data.date}</span>
          <ScreenshotButton targetRef={tileRef} label={`Today_vs_History_${data.carrier}`} />
        </div>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="rangeGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={PALETTE.accent} stopOpacity={0.3} />
              <stop offset="100%" stopColor={PALETTE.accent} stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={PALETTE.border} />
          <XAxis dataKey="hour" tick={{ fill: PALETTE.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fill: PALETTE.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} unit="%" />
          <Tooltip contentStyle={{ background: PALETTE.bg, border: `1px solid ${PALETTE.border}`, borderRadius: 12, color: PALETTE.text, fontSize: 12 }} />
          {bandLow != null && bandHigh != null && (
            <ReferenceArea y1={bandLow} y2={bandHigh} fill={PALETTE.green} fillOpacity={0.08} stroke={PALETTE.green} strokeOpacity={0.2} strokeDasharray="3 3" />
          )}
          <Area type="monotone" dataKey="Range High" stroke="none" fill="url(#rangeGrad)" />
          <Area type="monotone" dataKey="Range Low" stroke="none" fill={PALETTE.bg} />
          <Line type="monotone" dataKey="Historical Avg" stroke={PALETTE.accent} strokeWidth={2} dot={false} strokeDasharray="5 5" />
          <Line type="monotone" dataKey="Today Actual" stroke={PALETTE.green} strokeWidth={2.5} dot={{ fill: PALETTE.green, r: 3 }} connectNulls={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ──────────────────── ACTUAL VS PREDICTED TREND ──────────────────── */

function TrendChart({ carrier, dateFrom, dateTo, bandLow, bandHigh }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const tileRef = useRef(null);

  useEffect(() => {
    if (!carrier) { setLoading(false); return; }
    setLoading(true);
    const params = new URLSearchParams({ carrier });
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    fetch(`${API}/data/trend?${params}`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [carrier, dateFrom, dateTo]);

  if (!carrier) return <ChartPlaceholder title="Actual vs Predicted" message="Select a specific carrier in the Filters panel to view this chart." />;

  if (loading || !data) return <ChartSkeleton title="Actual vs Predicted" />;
  if (data.error) return <ChartPlaceholder title="Actual vs Predicted" message={data.error} />;

  const chartData = data.data.map((d) => ({
    label: `${d.date.slice(5)} ${String(d.hour).padStart(2, "0")}:00`,
    "Actual PRB %": d.actual_prb,
    "Predicted PRB %": d.predicted_prb,
  })).slice(-168);

  return (
    <div ref={tileRef} className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>
          Actual vs Predicted — Carrier {data.carrier}
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-1 rounded-full" style={{ background: "#1a2332", color: PALETTE.textMuted }}>{data.tower_label}</span>
          <ScreenshotButton targetRef={tileRef} label={`Actual_vs_Predicted_${data.carrier}`} />
        </div>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke={PALETTE.border} />
          <XAxis dataKey="label" tick={{ fill: PALETTE.textMuted, fontSize: 10 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis tick={{ fill: PALETTE.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} unit="%" />
          <Tooltip contentStyle={{ background: PALETTE.bg, border: `1px solid ${PALETTE.border}`, borderRadius: 12, color: PALETTE.text, fontSize: 12 }} />
          <Legend wrapperStyle={{ color: PALETTE.textMuted, fontSize: 11 }} />
          {bandLow != null && bandHigh != null && (
            <ReferenceArea y1={bandLow} y2={bandHigh} fill={PALETTE.green} fillOpacity={0.08} stroke={PALETTE.green} strokeOpacity={0.2} strokeDasharray="3 3" />
          )}
          <Line type="monotone" dataKey="Actual PRB %" stroke={PALETTE.cyan} strokeWidth={1.5} dot={false} />
          <Line type="monotone" dataKey="Predicted PRB %" stroke={PALETTE.amber} strokeWidth={1.5} dot={false} strokeDasharray="5 5" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ──────────────────── CARRIER ON/OFF TIMELINE ──────────────────── */

function CarrierTimeline({ initialDays, tower }) {
  const [days, setDays] = useState(initialDays || 1);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const tileRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);
  const [hoveredRow, setHoveredRow] = useState(null);
  const containerRef = useRef(null);
  const [containerWidth, setContainerWidth] = useState(600);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ days });
    if (tower) params.set("tower", tower);
    fetch(`${API}/data/timeline?${params}`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [days, tower]);

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) setContainerWidth(entry.contentRect.width);
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  if (loading) return <ChartSkeleton title="Carrier ON/OFF Timeline" />;
  if (data.length === 0) return <ChartPlaceholder title="Carrier ON/OFF Timeline" message="No decision data. Generate decisions first." />;

  const carrierOrder = ["1_A", "1_B", "1_C", "2_A", "2_B", "2_C"];
  const carriers = carrierOrder.filter((c) => data.some((d) => d.carrier === c));

  const slotSet = new Set();
  data.forEach((d) => slotSet.add(`${d.date}|${d.hour}`));
  const slots = [...slotSet].map((s) => {
    const [date, hour] = s.split("|");
    return { date, hour: Number(hour), key: `${date}T${String(hour).padStart(2, "0")}` };
  }).sort((a, b) => a.key.localeCompare(b.key));

  const cellMap = {};
  data.forEach((d) => {
    cellMap[`${d.carrier}|${d.date}|${d.hour}`] = d;
  });

  const onCount = data.filter((d) => d.state === "ON").length;
  const totalSlots = data.length;
  const offCount = totalSlots - onCount;
  const onPct = totalSlots > 0 ? Math.round(onCount / totalSlots * 100) : 0;

  const LABEL_W = 76;
  const GAP = 2;
  const available = containerWidth - LABEL_W - 20;
  const rawCell = (available - (slots.length - 1) * GAP) / slots.length;
  const cellW = Math.max(8, Math.min(rawCell, 18));
  const cellH = Math.max(24, Math.min(32, cellW * 1.5));

  const dates = [...new Set(slots.map((s) => s.date))].sort();

  return (
    <div ref={tileRef} className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>
          Carrier ON/OFF Timeline
        </h3>
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg overflow-hidden" style={{ border: `1px solid ${PALETTE.border}` }}>
            {[1, 3, 7].map((d) => (
              <button key={d} onClick={() => setDays(d)}
                className="px-2.5 py-1 text-[10px] font-semibold transition-colors"
                style={{
                  background: days === d ? PALETTE.accent : PALETTE.bg,
                  color: days === d ? "#fff" : PALETTE.textMuted,
                }}>
                {d === 1 ? "24h" : `${d}d`}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1.5 text-[10px]" style={{ color: PALETTE.textMuted }}>
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: PALETTE.green }} /> ON
            <span className="inline-block w-3 h-3 rounded-sm ml-1" style={{ background: PALETTE.red }} /> OFF
          </div>
          <ScreenshotButton targetRef={tileRef} label="Carrier_Timeline" />
        </div>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-4 mb-3 px-3 py-2 rounded-xl text-[11px]" style={{ background: PALETTE.bg, border: `1px solid ${PALETTE.border}` }}>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: PALETTE.green }} />
          <span style={{ color: PALETTE.textMuted }}>ON:</span>
          <span className="font-mono font-bold" style={{ color: PALETTE.green }}>{onCount}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: PALETTE.red }} />
          <span style={{ color: PALETTE.textMuted }}>OFF:</span>
          <span className="font-mono font-bold" style={{ color: PALETTE.red }}>{offCount}</span>
        </div>
        <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: PALETTE.border }}>
          <div className="h-full rounded-full" style={{ width: `${onPct}%`, background: PALETTE.green }} />
        </div>
        <span className="font-mono font-bold" style={{ color: PALETTE.text }}>{onPct}%</span>
      </div>

      <div ref={containerRef} className="relative" style={{ overflow: "auto", maxHeight: 500 }}>
        <div style={{ minWidth: "max-content" }}>
          {/* Date group headers */}
          <div style={{ display: "flex", paddingLeft: LABEL_W + GAP, marginBottom: 2 }}>
            {dates.map((date) => {
              const count = slots.filter((s) => s.date === date).length;
              const weekday = new Date(date + "T12:00:00").toLocaleDateString("en-US", { weekday: "short" });
              return (
                <div key={date} style={{ width: count * (cellW + GAP), flexShrink: 0, textAlign: "center" }}>
                  <span className="text-[9px] font-mono select-none" style={{ color: PALETTE.textMuted }}>
                    {date.slice(5)} <span style={{ color: PALETTE.accent, fontWeight: 600 }}>{weekday}</span>
                  </span>
                </div>
              );
            })}
          </div>

          {/* Heatmap grid */}
          <div style={{ display: "inline-grid", gridTemplateColumns: `${LABEL_W}px repeat(${slots.length}, ${cellW}px)`, gridTemplateRows: `repeat(${carriers.length}, ${cellH}px) 20px`, gap: `${GAP}px` }}>
            {carriers.map((carrier, ci) => (
              <div key={carrier} style={{ display: "contents" }}>
                <div
                  className="flex items-center justify-end pr-2 text-[10px] font-mono select-none whitespace-nowrap"
                  style={{ color: hoveredRow === carrier ? PALETTE.text : PALETTE.textMuted, gridColumn: 1, gridRow: ci + 1, fontWeight: hoveredRow === carrier ? 600 : 400 }}
                >
                  {carrier}
                </div>
                {slots.map((slot, si) => {
                  const rec = cellMap[`${carrier}|${slot.date}|${slot.hour}`];
                  const isOn = rec?.state === "ON";
                  const cellColor = rec ? (isOn ? PALETTE.green : PALETTE.red) : "#1e293b";
                  const isMidnight = slot.hour === 0 && si > 0;
                  const isWeekend = slot.date && [0, 6].includes(new Date(slot.date + "T12:00:00").getDay());
                  const isRowHovered = hoveredRow === carrier;
                  return (
                    <div
                      key={`${carrier}-${slot.date}-${slot.hour}`}
                      className="cursor-default"
                      style={{
                        gridColumn: si + 2,
                        gridRow: ci + 1,
                        background: cellColor,
                        opacity: rec ? (isRowHovered ? 1 : 0.85) : 0.15,
                        borderRadius: 2,
                        borderLeft: isMidnight ? `2px solid ${PALETTE.border}` : "none",
                        boxShadow: isRowHovered ? `0 0 0 1px ${PALETTE.accent}60` : "none",
                        transition: "opacity 0.15s, box-shadow 0.15s",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.zIndex = "10";
                        setHoveredRow(carrier);
                        setTooltip({
                          x: e.clientX,
                          y: e.clientY,
                          carrier,
                          date: slot.date,
                          hour: slot.hour,
                          state: rec?.state || "N/A",
                          predicted: rec?.predicted_prb,
                        });
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.zIndex = "";
                        setHoveredRow(null);
                        setTooltip(null);
                      }}
                    />
                  );
                })}
              </div>
            ))}
            <div style={{ gridColumn: 1, gridRow: carriers.length + 1 }} />
            {slots.map((slot, si) => {
              const showLabel = slot.hour === 0 || slot.hour === 6 || slot.hour === 12 || slot.hour === 18;
              return (
                <div
                  key={`label-${si}`}
                  className="flex items-start justify-center text-[9px] font-mono select-none"
                  style={{
                    gridColumn: si + 2,
                    gridRow: carriers.length + 1,
                    color: showLabel ? PALETTE.textMuted : "transparent",
                  }}
                >
                  {showLabel ? `${String(slot.hour).padStart(2, "0")}` : ""}
                </div>
              );
            })}
          </div>
        </div>

        {tooltip && (
          <div
            className="fixed z-50 pointer-events-none px-3 py-2 rounded-xl text-xs"
            style={{
              left: tooltip.x + 12,
              top: tooltip.y - 10,
              background: PALETTE.bg,
              border: `1px solid ${PALETTE.border}`,
              color: PALETTE.text,
              boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
            }}
          >
            <div className="font-semibold mb-1">Carrier {tooltip.carrier}</div>
            <div style={{ color: PALETTE.textMuted }}>{tooltip.date} @ {String(tooltip.hour).padStart(2, "0")}:00</div>
            <div className="mt-1 flex items-center gap-2">
              <span style={{ color: tooltip.state === "ON" ? PALETTE.green : PALETTE.red, fontWeight: 600 }}>
                {tooltip.state}
              </span>
              {tooltip.predicted != null && (
                <span style={{ color: PALETTE.textMuted }}>
                  PRB: {tooltip.predicted.toFixed(1)}%
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ──────────────────── EXPLAINABILITY PANEL ──────────────────── */

function ExplainabilityPanel({ carrier, towers }) {
  const [expanded, setExpanded] = useState(true);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const tileRef = useRef(null);

  const [selectedTower, setSelectedTower] = useState("");
  const [selectedCarrier, setSelectedCarrier] = useState(carrier || "1_A");

  useEffect(() => {
    if (towers && towers.length > 0 && !selectedTower) {
      setSelectedTower(towers[0].tower_label);
    }
  }, [towers]);

  useEffect(() => {
    if (carrier) {
      setSelectedCarrier(carrier);
      if (towers) {
        const prefix = parseInt(carrier.split("_")[0]);
        const towerIdx = prefix - 1;
        if (towers[towerIdx]) setSelectedTower(towers[towerIdx].tower_label);
      }
    }
  }, [carrier, towers]);

  useEffect(() => {
    if (!expanded) return;
    const now = new Date();
    const today = now.toISOString().slice(0, 10);
    const currentHour = now.getHours();
    setLoading(true);
    setError(null);
    fetch(`${API}/predictions/explain?carrier=${selectedCarrier}&target_date=${today}&target_hour=${currentHour}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        if (json.error) {
          setError(json.error);
          setData(null);
        } else {
          setData(json);
          setError(null);
        }
      })
      .catch((e) => { setError(e.message); setData(null); })
      .finally(() => setLoading(false));
  }, [expanded, selectedCarrier]);

  const handleTowerChange = (towerLabel) => {
    setSelectedTower(towerLabel);
    const tower = towers?.find((t) => t.tower_label === towerLabel);
    if (tower) {
      const tIdx = towers.indexOf(tower);
      setSelectedCarrier(`${tIdx + 1}_A`);
    }
  };

  const carriersForSelectedTower = [];
  if (towers && selectedTower) {
    const tower = towers.find((t) => t.tower_label === selectedTower);
    if (tower) {
      const tIdx = towers.indexOf(tower);
      for (let i = 0; i < tower.carrier_count; i++) {
        const suffix = String.fromCharCode(65 + i);
        carriersForSelectedTower.push(`${tIdx + 1}_${suffix}`);
      }
    }
  }

  return (
    <div ref={tileRef} className="rounded-2xl" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <div className="w-full flex items-center justify-between p-5">
        <button onClick={() => setExpanded(!expanded)} className="flex items-center gap-2 flex-1 text-left">
          <Info size={16} style={{ color: PALETTE.accent }} />
          <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>
            Prediction Explainability — Carrier {selectedCarrier}
          </h3>
          {expanded ? <ChevronUp size={16} style={{ color: PALETTE.textMuted }} /> : <ChevronDown size={16} style={{ color: PALETTE.textMuted }} />}
        </button>
        <ScreenshotButton targetRef={tileRef} label={`Explainability_${selectedCarrier}`} />
      </div>

      {expanded && (
        <div className="px-5 pb-5">
          {towers && towers.length > 0 && (
            <div className="flex gap-3 mb-4">
              <div className="flex-1">
                <label htmlFor="explain-tower" className="block text-xs mb-1.5" style={{ color: PALETTE.textMuted }}>Tower</label>
                <select
                  id="explain-tower"
                  name="explain-tower"
                  value={selectedTower}
                  onChange={(e) => handleTowerChange(e.target.value)}
                  className="w-full rounded-xl px-3 py-2 text-sm outline-none"
                  style={{ background: PALETTE.bg, color: PALETTE.text, border: `1px solid ${PALETTE.border}` }}
                >
                  {towers.map((t) => (
                    <option key={t.id} value={t.tower_label}>{t.tower_label}</option>
                  ))}
                </select>
              </div>
              <div className="flex-1">
                <label htmlFor="explain-carrier" className="block text-xs mb-1.5" style={{ color: PALETTE.textMuted }}>Carrier</label>
                <select
                  id="explain-carrier"
                  name="explain-carrier"
                  value={selectedCarrier}
                  onChange={(e) => setSelectedCarrier(e.target.value)}
                  className="w-full rounded-xl px-3 py-2 text-sm outline-none"
                  style={{ background: PALETTE.bg, color: PALETTE.text, border: `1px solid ${PALETTE.border}` }}
                >
                  {carriersForSelectedTower.map((code) => (
                    <option key={code} value={code}>Carrier {code}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {loading ? (
            <div className="h-32 rounded-xl animate-pulse" style={{ background: PALETTE.bg }} />
          ) : error ? (
            <div className="rounded-xl p-4 text-xs flex items-center gap-2" style={{ background: "#2d1215", border: `1px solid #7f1d1d`, color: PALETTE.red }}>
              <Info size={14} />
              <span>Explainability data unavailable: {error}</span>
            </div>
          ) : data ? (
            <div className="space-y-4">
              {/* Prediction stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="rounded-xl p-3" style={{ background: PALETTE.bg }}>
                  <div className="text-xs" style={{ color: PALETTE.textMuted }}>Predicted PRB</div>
                  <div className="text-lg font-mono font-bold" style={{ color: PALETTE.accent }}>{data.predicted_prb?.toFixed(1)}%</div>
                </div>
                <div className="rounded-xl p-3" style={{ background: PALETTE.bg }}>
                  <div className="text-xs" style={{ color: PALETTE.textMuted }}>Traffic</div>
                  <div className="text-lg font-mono font-bold" style={{ color: PALETTE.text }}>{data.predicted_traffic?.toFixed(0)}</div>
                </div>
                <div className="rounded-xl p-3" style={{ background: PALETTE.bg }}>
                  <div className="text-xs" style={{ color: PALETTE.textMuted }}>Range</div>
                  <div className="text-lg font-mono font-bold" style={{ color: PALETTE.text }}>{data.prb_min?.toFixed(0)}–{data.prb_max?.toFixed(0)}%</div>
                </div>
                <div className="rounded-xl p-3" style={{ background: PALETTE.bg }}>
                  <div className="text-xs" style={{ color: PALETTE.textMuted }}>Samples</div>
                  <div className="text-lg font-mono font-bold" style={{ color: PALETTE.text }}>{data.sample_count}</div>
                  {data.limited_history && <div className="text-xs" style={{ color: PALETTE.amber }}>Limited</div>}
                </div>
              </div>

              {/* Capacity decision math */}
              {data.capacity_decision && (
                <div className="rounded-xl p-4" style={{ background: PALETTE.bg, border: `1px solid ${PALETTE.border}` }}>
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: PALETTE.cyan }}>Capacity-Based Decision Math</h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
                    <div>
                      <div className="text-xs" style={{ color: PALETTE.textMuted }}>Total Demand</div>
                      <div className="font-mono text-sm font-bold" style={{ color: PALETTE.text }}>{data.capacity_decision.total_demand?.toFixed(1)}%</div>
                    </div>
                    <div>
                      <div className="text-xs" style={{ color: PALETTE.textMuted }}>Ceiling Used</div>
                      <div className="font-mono text-sm font-bold" style={{ color: PALETTE.amber }}>{data.capacity_decision.capacity_ceiling}%</div>
                    </div>
                    <div>
                      <div className="text-xs" style={{ color: PALETTE.textMuted }}>Active / Max</div>
                      <div className="font-mono text-sm font-bold" style={{ color: PALETTE.green }}>{data.capacity_decision.active_count} / {data.capacity_decision.max_carriers}</div>
                    </div>
                    <div>
                      <div className="text-xs" style={{ color: PALETTE.textMuted }}>Per-Carrier Load</div>
                      <div className="font-mono text-sm font-bold" style={{ color: PALETTE.text }}>{data.capacity_decision.per_carrier_load?.toFixed(1)}%</div>
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    {(data.capacity_decision.carriers || []).map((c) => (
                      <div key={c.sector_label} className="flex items-center justify-between text-xs rounded-lg px-3 py-2" style={{ background: c.is_on ? "#0d2818" : "#2d1215", border: `1px solid ${c.is_on ? "#166534" : "#7f1d1d"}` }}>
                        <span className="font-mono font-bold" style={{ color: PALETTE.text }}>Carrier {c.sector_label} (order #{c.activation_order})</span>
                        <span className="font-mono" style={{ color: PALETTE.text }}>PRB: {c.predicted_prb?.toFixed(1)}%</span>
                        <span className="font-bold" style={{ color: c.is_on ? PALETTE.green : PALETTE.red }}>{c.is_on ? "ON" : "OFF"}</span>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs mt-2" style={{ color: PALETTE.textMuted }}>
                    Total demand {data.capacity_decision.total_demand?.toFixed(1)}% / {data.capacity_decision.active_count} active = {data.capacity_decision.per_carrier_load?.toFixed(1)}% per carrier {data.capacity_decision.per_carrier_load <= data.capacity_decision.capacity_ceiling ? "≤" : ">"} {data.capacity_decision.capacity_ceiling}% ceiling → {data.capacity_decision.active_count} carrier{data.capacity_decision.active_count > 1 ? "s" : ""} ON
                  </p>
                </div>
              )}

              {/* Historical contributing dates */}
              {data.contributing_dates && data.contributing_dates.length > 0 ? (
                <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${PALETTE.border}` }}>
                  <div className="max-h-64 overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead className="sticky top-0" style={{ background: PALETTE.bg }}>
                        <tr>
                          <th className="text-left px-3 py-2" style={{ color: PALETTE.textMuted }}>Date</th>
                          <th className="text-left px-3 py-2" style={{ color: PALETTE.textMuted }}>Day</th>
                          <th className="text-right px-3 py-2" style={{ color: PALETTE.textMuted }}>Traffic</th>
                          <th className="text-right px-3 py-2" style={{ color: PALETTE.textMuted }}>PRB %</th>
                          <th className="text-right px-3 py-2" style={{ color: PALETTE.textMuted }}>Watts</th>
                          <th className="text-right px-3 py-2" style={{ color: PALETTE.textMuted }}>Source</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.contributing_dates.map((d, i) => (
                          <tr key={i} style={{ borderTop: `1px solid ${PALETTE.border}` }}>
                            <td className="px-3 py-2 font-mono" style={{ color: PALETTE.text }}>{d.date}</td>
                            <td className="px-3 py-2" style={{ color: PALETTE.textMuted }}>{d.weekday}</td>
                            <td className="px-3 py-2 text-right font-mono" style={{ color: PALETTE.text }}>{d.traffic_users?.toFixed(1)}</td>
                            <td className="px-3 py-2 text-right font-mono" style={{ color: PALETTE.text }}>{d.prb_utilization?.toFixed(1)}%</td>
                            <td className="px-3 py-2 text-right font-mono" style={{ color: PALETTE.cyan }}>{d.power_watts != null ? d.power_watts.toFixed(0) : "—"}</td>
                            <td className="px-3 py-2 text-right">
                              <span className="px-1.5 py-0.5 rounded" style={{ background: d.source === "seed" ? "#0d2818" : "#1a2332", color: d.source === "seed" ? PALETTE.green : PALETTE.textMuted }}>
                                {d.source === "seed" ? "Actual" : "Sim"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl p-4 text-xs" style={{ background: PALETTE.bg, color: PALETTE.textMuted }}>
                  No historical contributing dates available for this selection.
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl p-4 text-xs flex items-center gap-2" style={{ background: PALETTE.bg, color: PALETTE.textMuted }}>
              <Info size={14} />
              <span>No explainability data available for this carrier. Try generating predictions first.</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ──────────────────── MONTH POSITION CHART ──────────────────── */

function MonthPositionChart({ carrier }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const tileRef = useRef(null);

  useEffect(() => {
    if (!carrier) { setLoading(false); return; }
    setLoading(true);
    fetch(`${API}/month-position?carrier=${carrier}`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [carrier]);

  if (!carrier) return <ChartPlaceholder title="Month Position" message="Select a specific carrier in the Filters panel to view this chart." />;
  if (!data || data.error) return <ChartSkeleton title="Month Position" />;

  const earlyCount = data.early_month?.count ?? 0;
  const lateCount = data.late_month?.count ?? 0;
  const earlyPrb = data.early_month?.avg_prb;
  const latePrb = data.late_month?.avg_prb;
  const smallSample = earlyCount < 4 || lateCount < 4;

  const diff = earlyPrb != null && latePrb != null ? latePrb - earlyPrb : null;
  const diffPct = earlyPrb != null && earlyPrb > 0 && diff != null ? ((diff / earlyPrb) * 100).toFixed(1) : null;
  const diffColor = diff != null ? (diff > 0 ? PALETTE.red : diff < 0 ? PALETTE.green : PALETTE.textMuted) : PALETTE.textMuted;
  const diffLabel = diff != null ? (diff > 0 ? "higher" : diff < 0 ? "lower" : "same") : "";
  const maxPrb = Math.max(earlyPrb ?? 0, latePrb ?? 0, 1);

  return (
    <div ref={tileRef} className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>
          Month Position — Carrier {carrier}
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-1 rounded-full" style={{ background: "#1a2332", color: PALETTE.textMuted }}>{data.weekday}s</span>
          <ScreenshotButton targetRef={tileRef} label={`Month_Position_${carrier}`} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="rounded-xl p-4" style={{ background: PALETTE.accent + "10", border: `1px solid ${PALETTE.accent}25` }}>
          <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: PALETTE.textMuted }}>Early Month</div>
          <div className="text-3xl font-bold font-mono mb-1" style={{ color: PALETTE.accent }}>
            {earlyPrb != null ? earlyPrb.toFixed(1) : "—"}%
          </div>
          <div className="text-[10px]" style={{ color: PALETTE.textMuted }}>{earlyCount} samples</div>
          <div className="mt-3 h-1.5 rounded-full overflow-hidden" style={{ background: PALETTE.bg }}>
            <div className="h-full rounded-full transition-all" style={{ width: `${earlyPrb != null ? (earlyPrb / maxPrb) * 100 : 0}%`, background: PALETTE.accent }} />
          </div>
        </div>

        <div className="rounded-xl p-4" style={{ background: PALETTE.purple + "10", border: `1px solid ${PALETTE.purple}25` }}>
          <div className="text-[10px] uppercase tracking-wider mb-2" style={{ color: PALETTE.textMuted }}>Late Month</div>
          <div className="text-3xl font-bold font-mono mb-1" style={{ color: PALETTE.purple }}>
            {latePrb != null ? latePrb.toFixed(1) : "—"}%
          </div>
          <div className="text-[10px]" style={{ color: PALETTE.textMuted }}>{lateCount} samples</div>
          <div className="mt-3 h-1.5 rounded-full overflow-hidden" style={{ background: PALETTE.bg }}>
            <div className="h-full rounded-full transition-all" style={{ width: `${latePrb != null ? (latePrb / maxPrb) * 100 : 0}%`, background: PALETTE.purple }} />
          </div>
        </div>
      </div>

      {diff != null && (
        <div className="flex items-center justify-center gap-2 mb-4 py-2 rounded-xl" style={{ background: PALETTE.bg }}>
          <span className="text-xs" style={{ color: PALETTE.textMuted }}>Δ</span>
          <span className="text-sm font-mono font-bold" style={{ color: diffColor }}>
            {diff > 0 ? "+" : ""}{diff.toFixed(1)}%
          </span>
          <span className="text-xs" style={{ color: PALETTE.textMuted }}>{diffLabel} in late month</span>
          {diffPct != null && (
            <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: diffColor + "20", color: diffColor }}>
              {diffPct}%
            </span>
          )}
        </div>
      )}

      <div className="px-3 py-2.5 rounded-xl text-xs leading-relaxed" style={{ background: PALETTE.bg, color: PALETTE.textMuted, border: `1px solid ${PALETTE.border}` }}>
        {data.note}
      </div>

      {smallSample && (
        <div className="mt-2 px-3 py-2 rounded-xl text-[11px] flex items-center gap-1.5" style={{ background: PALETTE.amber + "15", color: PALETTE.amber, border: `1px solid ${PALETTE.amber}30` }}>
          <Info size={12} />
          Small sample size ({earlyCount} early, {lateCount} late) — pattern may not be reliable yet.
        </div>
      )}
    </div>
  );
}

/* ──────────────────── HOUR DRILLDOWN ──────────────────── */

function HourDrilldown() {
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [hour, setHour] = useState(new Date().getHours());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const tileRef = useRef(null);

  const fetchDrilldown = useCallback(() => {
    setLoading(true);
    fetch(`${API}/hour-drilldown?target_date=${date}&target_hour=${hour}`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [date, hour]);

  useEffect(() => { fetchDrilldown(); }, [fetchDrilldown]);

  return (
    <div ref={tileRef} className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Search size={16} style={{ color: PALETTE.purple }} />
          <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>Hour Drilldown</h3>
        </div>
        <ScreenshotButton targetRef={tileRef} label="Hour_Drilldown" />
      </div>

      <div className="flex items-center gap-2 mb-4">
        <DatePopover value={date} onSelect={setDate} />
        <HourPopover hour={hour} onHourChange={setHour} />
      </div>

      {loading ? (
            <div className="h-48 rounded-xl animate-pulse" style={{ background: PALETTE.bg }} />
          ) : data && data.slot_status === "future" ? (
        <div className="h-48 rounded-xl flex flex-col items-center justify-center gap-2" style={{ background: PALETTE.bg, border: `1px dashed ${PALETTE.border}` }}>
          <Clock size={24} style={{ color: PALETTE.textMuted }} />
          <p className="text-sm font-medium" style={{ color: PALETTE.textMuted }}>This hour hasn't occurred yet</p>
          <p className="text-xs" style={{ color: PALETTE.textMuted, opacity: 0.6 }}>{data.weekday} {data.date} at {String(data.hour).padStart(2, "0")}:00 is in the future</p>
        </div>
      ) : data && data.slot_status === "no_data" ? (
        <div className="h-48 rounded-xl flex flex-col items-center justify-center gap-2" style={{ background: "#2d1215", border: `1px dashed ${PALETTE.red}40` }}>
          <Database size={24} style={{ color: PALETTE.red }} />
          <p className="text-sm font-medium" style={{ color: PALETTE.red }}>No data recorded for this slot</p>
          <p className="text-xs" style={{ color: PALETTE.textMuted }}>{data.weekday} {data.date} at {String(data.hour).padStart(2, "0")}:00 — data gap</p>
        </div>
      ) : data && data.carriers && data.carriers.length > 0 ? (
        <div className="space-y-2">
          <div className="text-xs mb-2" style={{ color: PALETTE.textMuted }}>
            {data.weekday} {data.date} at {String(data.hour).padStart(2, "0")}:00
          </div>
          {data.carriers.map((c) => {
            const isOn = c.decision === "ON";
            const hasDecision = c.decision != null;
            const borderColor = hasDecision ? (isOn ? "#166534" : "#7f1d1d") : PALETTE.border;
            const bgColor = hasDecision ? (isOn ? "#0d2818" : "#2d1215") : PALETTE.bg;
            return (
              <div key={c.carrier_sector}
                className="flex items-center justify-between rounded-xl px-4 py-3"
                style={{ background: bgColor, border: `1px solid ${borderColor}` }}>
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-full flex items-center justify-center" style={{ background: hasDecision ? (isOn ? PALETTE.green : PALETTE.red) : PALETTE.textMuted + "40" }}>
                    {hasDecision ? (isOn ? <Power size={14} color="#fff" /> : <PowerOff size={14} color="#fff" />) : <Power size={14} style={{ color: PALETTE.textMuted }} />}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-bold" style={{ color: PALETTE.text }}>Carrier {c.carrier_sector}</span>
                      {c.is_primary && <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: PALETTE.accent + "30", color: PALETTE.accent }}>Primary</span>}
                    </div>
                    <div className="text-xs" style={{ color: PALETTE.textMuted }}>{c.tower_label} — Order #{c.activation_order}</div>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-right">
                  <div>
                    <div className="text-xs" style={{ color: PALETTE.textMuted }}>PRB</div>
                    <div className="font-mono text-sm font-bold" style={{ color: PALETTE.text }}>{c.prb_utilization}%</div>
                  </div>
                  <div>
                    <div className="text-xs" style={{ color: PALETTE.textMuted }}>Traffic</div>
                    <div className="font-mono text-sm font-bold" style={{ color: PALETTE.text }}>{c.traffic_users}</div>
                  </div>
                  <div>
                    <div className="text-xs" style={{ color: PALETTE.textMuted }}>Power</div>
                    <div className="font-mono text-sm font-bold" style={{ color: PALETTE.cyan }}>{c.power_watts?.toFixed(0)}W</div>
                  </div>
                  <div className="px-2.5 py-1 rounded-full text-xs font-bold uppercase" style={{ background: hasDecision ? (isOn ? "#15803d" : "#b91c1c") : PALETTE.textMuted + "30", color: hasDecision ? "#fff" : PALETTE.textMuted }}>
                    {c.decision || "N/A"}
                  </div>
                </div>
              </div>
            );
          })}
          <div className="flex items-center justify-end gap-4 pt-2 text-xs" style={{ color: PALETTE.textMuted }}>
            <span>Mode: {data.carriers[0]?.mode || "—"}</span>
            <span>Active: {data.carriers[0]?.active_count}/{data.carriers.length}</span>
            <span>Demand: {data.carriers[0]?.total_demand?.toFixed(1)}%</span>
            <span>Power: {data.carriers[0]?.tower_power_watts?.toFixed(0) || "—"}W</span>
          </div>
        </div>
      ) : (
        <div className="h-48 rounded-xl flex flex-col items-center justify-center gap-2" style={{ background: "#2d1215", border: `1px dashed ${PALETTE.red}40` }}>
          <Database size={24} style={{ color: PALETTE.red }} />
          <p className="text-sm font-medium" style={{ color: PALETTE.red }}>No data recorded for this slot</p>
        </div>
      )}
    </div>
  );
}

/* ──────────────────── POWER / ENERGY CHART ──────────────────── */

function PowerEnergyChart({ days }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const tileRef = useRef(null);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/data/power-summary?days=${days}`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [days]);

  if (loading || !data) return <ChartSkeleton title="Energy Savings" />;
  if (!data.daily?.length) return <ChartPlaceholder title="Energy Savings" message="No power data available" />;

  const chartData = data.daily.map((d) => ({
    date: d.date.slice(5),
    "Actual kWh": d.actual_kwh,
    "Baseline kWh": d.baseline_kwh,
  }));

  return (
    <div ref={tileRef} className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>
          Energy Savings (last {days} days)
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono" style={{ color: PALETTE.green }}>Total: {data.total_saved_kwh?.toFixed(1)} kWh saved</span>
          <ScreenshotButton targetRef={tileRef} label="Energy_Savings" />
        </div>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={chartData} barGap={4}>
          <CartesianGrid strokeDasharray="3 3" stroke={PALETTE.border} />
          <XAxis dataKey="date" tick={{ fill: PALETTE.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fill: PALETTE.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} unit=" kWh" />
          <Tooltip contentStyle={{ background: PALETTE.bg, border: `1px solid ${PALETTE.border}`, borderRadius: 12, color: PALETTE.text, fontSize: 12 }} />
          <Legend wrapperStyle={{ color: PALETTE.textMuted, fontSize: 11 }} />
          <Bar dataKey="Baseline kWh" fill={PALETTE.textMuted} radius={[4, 4, 0, 0]} opacity={0.3} />
          <Bar dataKey="Actual kWh" fill={PALETTE.green} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ──────────────────── TEST SCENARIO TOOL ──────────────────── */

function TestScenarioTool() {
  const [loads, setLoads] = useState({ a: 50, b: 40, c: 30 });
  const [ceiling, setCeiling] = useState(80);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const runTest = useCallback(() => {
    setLoading(true);
    fetch(`${API}/test-scenario?load_a=${loads.a}&load_b=${loads.b}&load_c=${loads.c}&ceiling=${ceiling}`)
      .then((r) => r.json())
      .then(setResult)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [loads, ceiling]);

  useEffect(() => { runTest(); }, [runTest]);

  return (
    <div className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <div className="flex items-center gap-2 mb-4">
        <FlaskConical size={16} style={{ color: PALETTE.purple }} />
        <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>Test Scenario</h3>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-3">
        {[{ key: "a", label: "Carrier A", color: PALETTE.green }, { key: "b", label: "Carrier B", color: PALETTE.amber }, { key: "c", label: "Carrier C", color: PALETTE.red }].map((f) => (
          <div key={f.key}>
            <label htmlFor={`test-load-${f.key}`} className="block text-xs mb-1" style={{ color: PALETTE.textMuted }}>{f.label}</label>
            <input id={`test-load-${f.key}`} type="number" min="0" max="100" name={f.key} value={loads[f.key]}
              onChange={(e) => setLoads((l) => ({ ...l, [f.key]: Number(e.target.value) }))}
              className="w-full rounded-lg px-2 py-1.5 text-sm font-mono outline-none text-center"
              style={{ background: PALETTE.bg, color: f.color, border: `1px solid ${PALETTE.border}` }} />
          </div>
        ))}
      </div>

      <div className="mb-3">
        <label htmlFor="test-ceiling" className="block text-xs mb-1" style={{ color: PALETTE.textMuted }}>
          Ceiling: <span className="font-mono font-bold" style={{ color: PALETTE.amber }}>{ceiling}%</span>
        </label>
        <input id="test-ceiling" type="range" min="30" max="95" step="5" name="capacity-ceiling" value={ceiling}
          onChange={(e) => setCeiling(Number(e.target.value))}
          className="w-full accent-amber-500" />
      </div>

      {result && (
        <div className="rounded-xl p-3 space-y-2" style={{ background: PALETTE.bg, border: `1px solid ${PALETTE.border}` }}>
          <div className="flex items-center justify-between">
            <span className="text-xs" style={{ color: PALETTE.textMuted }}>Total Demand</span>
            <span className="font-mono text-sm font-bold" style={{ color: PALETTE.text }}>{result.total_demand?.toFixed(1)}%</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs" style={{ color: PALETTE.textMuted }}>Per-Carrier (active)</span>
            <span className="font-mono text-sm font-bold" style={{ color: PALETTE.text }}>{result.per_carrier_load?.toFixed(1)}%</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs" style={{ color: PALETTE.textMuted }}>Carriers ON</span>
            <span className="font-mono text-sm font-bold" style={{ color: result.active_count === 3 ? PALETTE.green : result.active_count === 2 ? PALETTE.amber : PALETTE.red }}>
              {result.active_count} / {result.max_carriers}
            </span>
          </div>
          <div className="space-y-1">
            {result.carriers?.map((c) => (
              <div key={c.sector_label} className="flex items-center justify-between text-xs rounded-lg px-2 py-1" style={{ background: c.is_on ? "#0d2818" : "#2d1215" }}>
                <span className="font-mono" style={{ color: PALETTE.text }}>{c.sector_label}: {loads[c.sector_label.toLowerCase()] ?? "—"}%</span>
                <span className="font-bold" style={{ color: c.is_on ? PALETTE.green : PALETTE.red }}>{c.is_on ? "ON" : "OFF"}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ──────────────────── CAPACITY + POWER SETTINGS ──────────────────── */

function CapacitySettings({ onSaved }) {
  const [expanded, setExpanded] = useState(false);
  const [config, setConfig] = useState(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    if (!expanded) return;
    fetch(`${API}/capacity-config`).then((r) => r.json()).then(setConfig).catch(console.error);
  }, [expanded]);

  const save = async () => {
    setSaving(true);
    setMsg(null);
    try {
      const res = await fetch(`${API}/capacity-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (res.ok) { setMsg({ ok: true, text: "Config saved. Re-generate decisions to apply." }); onSaved?.(); }
      else { setMsg({ ok: false, text: "Failed to save" }); }
    } catch (e) { setMsg({ ok: false, text: e.message }); }
    finally { setSaving(false); }
  };

  return (
    <div className="rounded-2xl" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center justify-between p-5 text-left">
        <div className="flex items-center gap-2">
          <Settings size={16} style={{ color: PALETTE.amber }} />
          <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>Power & Capacity Config</h3>
        </div>
        {expanded ? <ChevronUp size={16} style={{ color: PALETTE.textMuted }} /> : <ChevronDown size={16} style={{ color: PALETTE.textMuted }} />}
      </button>

      {expanded && config && (
        <div className="px-5 pb-5 space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wider pt-1" style={{ color: PALETTE.cyan }}>Capacity Decision</div>
          {[
            { key: "capacity_ceiling", label: "Capacity Ceiling (%)", color: PALETTE.amber, step: 1 },
            { key: "target_band_low", label: "Target Band Low (%)", color: PALETTE.green, step: 1 },
            { key: "target_band_high", label: "Target Band High (%)", color: PALETTE.green, step: 1 },
          ].map((field) => (
            <div key={field.key}>
              <label htmlFor={`cap-${field.key}`} className="block text-xs mb-1" style={{ color: PALETTE.textMuted }}>{field.label}</label>
              <input id={`cap-${field.key}`} type="number" name={field.key} step={field.step} value={config[field.key]}
                onChange={(e) => setConfig((c) => ({ ...c, [field.key]: Number(e.target.value) }))}
                className="w-full rounded-xl px-3 py-2 text-sm font-mono outline-none"
                style={{ background: PALETTE.bg, color: field.color, border: `1px solid ${PALETTE.border}` }} />
            </div>
          ))}

          <div className="text-xs font-semibold uppercase tracking-wider pt-2" style={{ color: PALETTE.cyan }}>Power Model (Watts)</div>
          {[
            { key: "carrier_a_watts", label: "Carrier A (W)", color: PALETTE.green, step: 100 },
            { key: "carrier_b_watts", label: "Carrier B (W)", color: PALETTE.amber, step: 100 },
            { key: "carrier_c_watts", label: "Carrier C (W)", color: PALETTE.red, step: 100 },
            { key: "load_scaling_factor", label: "Load Scaling Factor", color: PALETTE.accent, step: 0.01 },
          ].map((field) => (
            <div key={field.key}>
              <label htmlFor={`power-${field.key}`} className="block text-xs mb-1" style={{ color: PALETTE.textMuted }}>{field.label}</label>
              <input id={`power-${field.key}`} type="number" name={field.key} step={field.step} value={config[field.key]}
                onChange={(e) => setConfig((c) => ({ ...c, [field.key]: Number(e.target.value) }))}
                className="w-full rounded-xl px-3 py-2 text-sm font-mono outline-none"
                style={{ background: PALETTE.bg, color: field.color, border: `1px solid ${PALETTE.border}` }} />
            </div>
          ))}

          <button onClick={save} disabled={saving}
            className="w-full rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-wider transition-colors"
            style={{ background: PALETTE.amber, color: PALETTE.bg }}>
            {saving ? "Saving…" : "Save Config"}
          </button>
          {msg && (
            <div className="p-2 rounded-lg text-xs" style={{ background: msg.ok ? "#0d2818" : "#2d1215", color: msg.ok ? PALETTE.green : PALETTE.red }}>
              {msg.text}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ──────────────────── UPLOAD WIDGET ──────────────────── */

function UploadWidget({ onUploaded }) {
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);

  const handleFile = async (file) => {
    if (!file) return;
    setUploading(true);
    setResult(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(`${API}/upload/`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) setResult({ error: data.detail });
      else { setResult(data); onUploaded?.(); }
    } catch (e) { setResult({ error: e.message }); }
    finally { setUploading(false); }
  };

  return (
    <div className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <h3 className="text-sm font-semibold uppercase tracking-wider mb-3" style={{ color: PALETTE.textMuted }}>Upload Data</h3>
      <div
        className="border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors"
        style={{ borderColor: PALETTE.border }}
        onClick={() => { const i = document.createElement("input"); i.type = "file"; i.accept = ".csv,.xlsx,.xls"; i.onchange = (e) => handleFile(e.target.files[0]); i.click(); }}
        onDragOver={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = PALETTE.accent; }}
        onDragLeave={(e) => { e.currentTarget.style.borderColor = PALETTE.border; }}
        onDrop={(e) => { e.preventDefault(); e.currentTarget.style.borderColor = PALETTE.border; handleFile(e.dataTransfer.files[0]); }}
      >
        {uploading ? <RefreshCw className="mx-auto animate-spin" size={24} style={{ color: PALETTE.accent }} /> : <Upload className="mx-auto" size={24} style={{ color: PALETTE.textMuted }} />}
        <p className="mt-2 text-xs" style={{ color: PALETTE.textMuted }}>
          {uploading ? "Uploading…" : "Drop .csv/.xlsx or click to browse"}
        </p>
      </div>
      {result && (
        <div className="mt-3 p-2 rounded-lg text-xs" style={{ background: result.error ? "#2d1215" : "#0d2818", color: result.error ? PALETTE.red : PALETTE.green }}>
          {result.error || `${result.rows_accepted} rows imported`}
        </div>
      )}
    </div>
  );
}

/* ──────────────────── SKELETON / PLACEHOLDER ──────────────────── */

function ChartSkeleton({ title }) {
  return (
    <div className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <h3 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: PALETTE.textMuted }}>{title}</h3>
      <div className="h-[280px] rounded-xl animate-pulse" style={{ background: PALETTE.bg }} />
    </div>
  );
}

function ChartPlaceholder({ title, message }) {
  return (
    <div className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <h3 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: PALETTE.textMuted }}>{title}</h3>
      <div className="h-[280px] rounded-xl flex items-center justify-center" style={{ background: PALETTE.bg }}>
        <p className="text-sm" style={{ color: PALETTE.textMuted }}>{message}</p>
      </div>
    </div>
  );
}

/* ──────────────────── FILTERS PANEL ──────────────────── */

function FiltersPanel({ filters, setFilters, towers, capacityConfig, onRefresh }) {
  const carriersForTower = useCallback((towerLabel) => {
    if (!towerLabel) return [];
    const t = towers.find((t) => t.tower_label === towerLabel);
    if (!t) return [];
    return Array.from({ length: t.carrier_count }, (_, i) => {
      const suffix = String.fromCharCode(65 + i);
      const prefix = towerLabel.includes("A") || towerLabel === towers[0]?.tower_label ? "1" : "2";
      return `${prefix}_${suffix}`;
    });
  }, [towers]);

  return (
    <div className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>
          <SlidersHorizontal size={14} className="inline mr-1.5" />Filters
        </h3>
        <button onClick={onRefresh} className="p-1.5 rounded-lg transition-colors" style={{ background: PALETTE.bg }} title="Refresh data">
          <RefreshCw size={14} style={{ color: PALETTE.textMuted }} />
        </button>
      </div>

      <div className="space-y-4">
        <div>
          <label htmlFor="filter-tower" className="block text-xs mb-1.5" style={{ color: PALETTE.textMuted }}>Tower</label>
          <select id="filter-tower" name="filter-tower" value={filters.tower} onChange={(e) => {
            const newTower = e.target.value;
            const tIdx = towers.findIndex((t) => t.tower_label === newTower);
            const newCarrier = tIdx >= 0 ? `${tIdx + 1}_A` : "";
            setFilters((f) => ({ ...f, tower: newTower, carrier: newCarrier }));
          }}
            className="w-full rounded-xl px-3 py-2 text-sm outline-none cursor-pointer" style={{ background: PALETTE.bg, color: PALETTE.text, border: `1px solid ${PALETTE.border}`, colorScheme: "dark" }}>
            <option value="">All Towers</option>
            {towers.map((t) => <option key={t.id} value={t.tower_label}>{t.tower_label}</option>)}
          </select>
        </div>

        <div>
          <label htmlFor="filter-carrier" className="block text-xs mb-1.5" style={{ color: PALETTE.textMuted }}>Carrier</label>
          <select id="filter-carrier" name="filter-carrier" value={filters.carrier} onChange={(e) => setFilters((f) => ({ ...f, carrier: e.target.value }))}
            className="w-full rounded-xl px-3 py-2 text-sm outline-none cursor-pointer" style={{ background: PALETTE.bg, color: PALETTE.text, border: `1px solid ${PALETTE.border}`, colorScheme: "dark" }}>
            <option value="">All Carriers</option>
            {towers.filter((t) => !filters.tower || t.tower_label === filters.tower).map((t) => (
              Array.from({ length: t.carrier_count }, (_, i) => {
                const suffix = String.fromCharCode(65 + i);
                const prefix = t.tower_label.match(/\d/) ? t.tower_label : towers.indexOf(t) === 0 ? "1" : String(towers.indexOf(t) + 1);
                const label = `${prefix}_${suffix}`;
                return <option key={label} value={label}>Carrier {label}</option>;
              })
            )).flat()}
          </select>
        </div>

        <div>
          <label className="block text-xs mb-1.5" style={{ color: PALETTE.textMuted }}>From Date</label>
          <DatePopover value={filters.dateFrom} onSelect={(d) => setFilters((f) => ({ ...f, dateFrom: d }))} max={filters.dateTo || undefined} />
        </div>

        <div>
          <label className="block text-xs mb-1.5" style={{ color: PALETTE.textMuted }}>To Date</label>
          <DatePopover value={filters.dateTo} onSelect={(d) => setFilters((f) => ({ ...f, dateTo: d }))} min={filters.dateFrom || undefined} />
          {filters.dateFrom && filters.dateTo && filters.dateTo < filters.dateFrom && (
            <p className="text-xs mt-1" style={{ color: PALETTE.red }}>To Date cannot be before From Date</p>
          )}
        </div>

        <div className="pt-2 space-y-2">
          <a href={`${API}/export/kpi?${new URLSearchParams({ ...(filters.tower && { tower: filters.tower }), ...(filters.carrier && { carrier: filters.carrier }), ...(filters.dateFrom && { date_from: filters.dateFrom }), ...(filters.dateTo && { date_to: filters.dateTo }) })}`}
            className="flex items-center justify-center gap-1.5 w-full rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-wider transition-colors" style={{ background: PALETTE.bg, color: PALETTE.textMuted, border: `1px solid ${PALETTE.border}`, textDecoration: "none" }}>
            <Download size={14} /> Export KPI Data
          </a>
          <a href={`${API}/export/decisions?${new URLSearchParams({ ...(filters.tower && { tower: filters.tower }), ...(filters.dateFrom && { date_from: filters.dateFrom }), ...(filters.dateTo && { date_to: filters.dateTo }) })}`}
            className="flex items-center justify-center gap-1.5 w-full rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-wider transition-colors" style={{ background: PALETTE.bg, color: PALETTE.textMuted, border: `1px solid ${PALETTE.border}`, textDecoration: "none" }}>
            <Download size={14} /> Export Decisions
          </a>
          <a href={`${API}/export/power-energy?${new URLSearchParams({ ...(filters.tower && { tower: filters.tower }), ...(filters.dateFrom && { date_from: filters.dateFrom }), ...(filters.dateTo && { date_to: filters.dateTo }) })}`}
            className="flex items-center justify-center gap-1.5 w-full rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-wider transition-colors" style={{ background: PALETTE.bg, color: PALETTE.cyan, border: `1px solid ${PALETTE.border}`, textDecoration: "none" }}>
            <Battery size={14} /> Export Power / Energy
          </a>
          <a href={`${API}/export/thesis-report`}
            className="flex items-center justify-center gap-1.5 w-full rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-wider transition-colors" style={{ background: PALETTE.purple + "20", color: PALETTE.purple, border: `1px solid ${PALETTE.purple}40`, textDecoration: "none" }}>
            <Download size={14} /> Thesis Report (.xlsx)
          </a>
        </div>
      </div>
    </div>
  );
}

/* ──────────────────── MODEL ACCURACY TREND ──────────────────── */

function ModelAccuracyChart() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const tileRef = useRef(null);

  useEffect(() => {
    setLoading(true);
    fetch(`${API}/ml/accuracy-trend`)
      .then((r) => r.json())
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <ChartSkeleton title="Model Accuracy Trend" />;
  if (!data || data.length === 0) return <ChartPlaceholder title="Model Accuracy Trend" message="No training runs yet. Train models first." />;

  const chartData = data.map((d, i) => ({
    run: `#${d.id}`,
    MAE: d.mae,
    RMSE: d.rmse,
    "Training Rows": d.training_rows,
    time: d.trained_at ? d.trained_at.slice(11, 16) : "",
  })).reverse();

  return (
    <div ref={tileRef} className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>
          Model Accuracy Trend (MAE / RMSE)
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-1 rounded-full" style={{ background: "#1a2332", color: PALETTE.textMuted }}>{data.length} runs</span>
          <ScreenshotButton targetRef={tileRef} label="Model_Accuracy_Trend" />
        </div>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke={PALETTE.border} />
          <XAxis dataKey="run" tick={{ fill: PALETTE.textMuted, fontSize: 10 }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fill: PALETTE.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} unit="%" />
          <Tooltip contentStyle={{ background: PALETTE.bg, border: `1px solid ${PALETTE.border}`, borderRadius: 12, color: PALETTE.text, fontSize: 12 }} />
          <Legend wrapperStyle={{ color: PALETTE.textMuted, fontSize: 11 }} />
          <Line type="monotone" dataKey="MAE" stroke={PALETTE.cyan} strokeWidth={2} dot={{ fill: PALETTE.cyan, r: 3 }} />
          <Line type="monotone" dataKey="RMSE" stroke={PALETTE.amber} strokeWidth={2} dot={{ fill: PALETTE.amber, r: 3 }} strokeDasharray="5 5" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ──────────────────── MODEL STATUS & TRAINING ──────────────────── */

function ModelStatusPanel({ onTrained }) {
  const [expanded, setExpanded] = useState(false);
  const [status, setStatus] = useState(null);
  const [runs, setRuns] = useState([]);
  const [training, setTraining] = useState(false);
  const [msg, setMsg] = useState(null);

  const fetchStatus = useCallback(() => {
    if (!expanded) return;
    Promise.all([
      fetch(`${API}/ml/status`).then((r) => r.json()),
      fetch(`${API}/ml/runs?limit=5`).then((r) => r.json()),
    ]).then(([s, r]) => { setStatus(s); setRuns(r); }).catch(console.error);
  }, [expanded]);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  const trainAll = async () => {
    setTraining(true);
    setMsg(null);
    try {
      const res = await fetch(`${API}/ml/train`, { method: "POST" });
      const data = await res.json();
      setMsg({ ok: true, text: `Trained ${data.trained} models. MAE: ${data.results?.[0]?.mae ?? "—"}` });
      fetchStatus();
      onTrained?.();
    } catch (e) {
      setMsg({ ok: false, text: e.message });
    } finally {
      setTraining(false);
    }
  };

  return (
    <div className="rounded-2xl" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center justify-between p-5 text-left">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: PALETTE.purple + "20" }}>
            <FlaskConical size={15} style={{ color: PALETTE.purple }} />
          </div>
          <div>
            <h3 className="text-sm font-semibold" style={{ color: PALETTE.text }}>ML Models</h3>
            <p className="text-[10px]" style={{ color: PALETTE.textMuted }}>Random Forest regressors</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {status && <span className="text-[10px] px-1.5 py-0.5 rounded-full font-mono" style={{ background: PALETTE.bg, color: PALETTE.textMuted }}>{status.filter((s) => s.has_ml_model).length}/{status.length}</span>}
          {expanded ? <ChevronUp size={14} style={{ color: PALETTE.textMuted }} /> : <ChevronDown size={14} style={{ color: PALETTE.textMuted }} />}
        </div>
      </button>

      {expanded && (
        <div className="px-5 pb-5 space-y-4">
          {status && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>Carrier Models</span>
                <span className="text-[10px] font-mono" style={{ color: PALETTE.textMuted }}>{status.filter((s) => s.has_ml_model).length} trained</span>
              </div>
              <div className="space-y-1">
                {status.map((s) => (
                  <div key={s.carrier_id} className="flex items-center gap-2 rounded-lg px-3 py-2"
                    style={{ background: s.has_ml_model ? "#0d2818" : PALETTE.bg, border: `1px solid ${s.has_ml_model ? "#16653420" : PALETTE.border}` }}>
                    <div className="w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold" style={{ background: s.has_ml_model ? "#15803d30" : "#2d1215", color: s.has_ml_model ? PALETTE.green : PALETTE.red }}>
                      {s.sector_label.split("_")[1]}
                    </div>
                    <span className="font-mono text-xs font-semibold flex-1" style={{ color: PALETTE.text }}>Carrier {s.sector_label}</span>
                    <span className="text-[10px]" style={{ color: PALETTE.textMuted }}>{s.tower_label}</span>
                    {s.has_ml_model ? (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded" style={{ background: "#15803d20", color: PALETTE.green }}>
                        {s.model_version?.slice(-8)}
                      </span>
                    ) : (
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "#2d1215", color: PALETTE.red + "80" }}>—</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {runs.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>Training Runs</span>
                <span className="text-[10px] font-mono" style={{ color: PALETTE.textMuted }}>latest 5</span>
              </div>
              <div className="space-y-1">
                {runs.map((r) => (
                  <div key={r.id} className="flex items-center gap-3 rounded-lg px-3 py-2" style={{ background: PALETTE.bg, border: `1px solid ${PALETTE.border}` }}>
                    <span className="text-[10px] font-mono w-5 text-center" style={{ color: PALETTE.textMuted }}>#{r.id}</span>
                    <div className="flex-1">
                      <span className="text-[10px] font-mono" style={{ color: PALETTE.textMuted }}>{r.training_row_count.toLocaleString()} rows</span>
                    </div>
                    <span className="text-[10px] font-mono font-semibold" style={{ color: PALETTE.cyan }}>{r.mae?.toFixed(1)}%</span>
                    <span className="text-[10px] font-mono" style={{ color: PALETTE.textMuted }}>MAE</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <button onClick={trainAll} disabled={training}
            className="w-full rounded-xl px-3 py-2.5 text-xs font-semibold uppercase tracking-wider transition-colors flex items-center justify-center gap-2"
            style={{ background: training ? PALETTE.purple + "80" : PALETTE.purple, color: "#fff" }}>
            {training ? <><RefreshCw size={12} className="animate-spin" /> Training…</> : "Train All Carriers"}
          </button>

          {msg && (
            <div className="p-2.5 rounded-xl text-xs" style={{ background: msg.ok ? "#0d2818" : "#2d1215", color: msg.ok ? PALETTE.green : PALETTE.red, border: `1px solid ${msg.ok ? "#166534" : "#7f1d1d"}` }}>
              {msg.text}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ──────────────────── BASELINE VS ML CHART ──────────────────── */

function BaselineVsMlChart({ carrier }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const tileRef = useRef(null);

  useEffect(() => {
    if (!carrier) { setLoading(false); return; }
    setLoading(true);
    const today = new Date().toISOString().slice(0, 10);
    const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
    const controller = new AbortController();
    fetch(`${API}/ml/compare-range?carrier_id=${carrier === "1_A" ? 1 : carrier === "1_B" ? 2 : carrier === "1_C" ? 3 : carrier === "2_A" ? 4 : carrier === "2_B" ? 5 : 6}&date_from=${yesterday}&date_to=${today}`, { signal: controller.signal })
      .then((r) => r.json())
      .then(setData)
      .catch((e) => { if (e.name !== "AbortError") console.error(e); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [carrier]);

  if (!carrier) return <ChartPlaceholder title="Baseline vs ML" message="Select a specific carrier in the Filters panel to view this chart." />;

  if (loading) return <ChartSkeleton title="Baseline vs ML Prediction" />;
  if (!data || data.error) return <ChartPlaceholder title="Baseline vs ML Prediction" message={data?.error || "No data. Train ML models first."} />;

  const chartData = data.data
    .filter((d) => d.actual_prb !== null)
    .map((d) => ({
      label: `${d.date.slice(5)} ${String(d.hour).padStart(2, "0")}:00`,
      "Actual": d.actual_prb,
      "Baseline": d.baseline_prb,
      "ML (Random Forest)": d.ml_prb,
    }))
    .slice(-48);

  if (chartData.length === 0) return <ChartPlaceholder title="Baseline vs ML" message="No actual data in range for comparison." />;

  return (
    <div ref={tileRef} className="rounded-2xl p-5" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>
          Baseline vs ML — Carrier {data.carrier_sector}
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-1 rounded-full" style={{ background: "#1a2332", color: PALETTE.textMuted }}>48h window</span>
          <ScreenshotButton targetRef={tileRef} label={`Baseline_vs_ML_${data.carrier_sector}`} />
        </div>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke={PALETTE.border} />
          <XAxis dataKey="label" tick={{ fill: PALETTE.textMuted, fontSize: 9 }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis tick={{ fill: PALETTE.textMuted, fontSize: 11 }} tickLine={false} axisLine={false} unit="%" />
          <Tooltip contentStyle={{ background: PALETTE.bg, border: `1px solid ${PALETTE.border}`, borderRadius: 12, color: PALETTE.text, fontSize: 12 }} />
          <Legend wrapperStyle={{ color: PALETTE.textMuted, fontSize: 11 }} />
          <Line type="monotone" dataKey="Actual" stroke={PALETTE.green} strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="Baseline" stroke={PALETTE.accent} strokeWidth={1.5} dot={false} strokeDasharray="5 5" />
          <Line type="monotone" dataKey="ML (Random Forest)" stroke={PALETTE.purple} strokeWidth={1.5} dot={{ fill: PALETTE.purple, r: 2 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ──────────────────── ADMIN PAGE ──────────────────── */

function AdminPage({ onBack, onRefresh }) {
  const [password, setPassword] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [connectorConfig, setConnectorConfig] = useState(null);
  const [powerConfig, setPowerConfig] = useState(null);
  const [modelRuns, setModelRuns] = useState([]);
  const [dbAudit, setDbAudit] = useState(null);
  const [training, setTraining] = useState(false);
  const [trainMsg, setTrainMsg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState(null);

  const adminHeaders = { "X-Admin-Password": password, "Content-Type": "application/json" };

  const login = async () => {
    setAuthError(null);
    try {
      const res = await fetch(`${API}/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        setAuthenticated(true);
        loadAdminData();
      } else {
        setAuthError("Invalid password");
      }
    } catch (e) {
      setAuthError(e.message);
    }
  };

  const loadAdminData = async () => {
    try {
      const h = { "X-Admin-Password": password };
      const [connRes, powRes, runsRes, auditRes] = await Promise.all([
        fetch(`${API}/admin/connector-config`, { headers: h }),
        fetch(`${API}/admin/power-config`, { headers: h }),
        fetch(`${API}/admin/model-runs?limit=10`, { headers: h }),
        fetch(`${API}/admin/db-audit`, { headers: h }),
      ]);
      setConnectorConfig(await connRes.json());
      setPowerConfig(await powRes.json());
      setModelRuns(await runsRes.json());
      setDbAudit(await auditRes.json());
    } catch (e) { console.error(e); }
  };

  const saveConnectorConfig = async () => {
    setSaving(true); setSaveMsg(null);
    try {
      const res = await fetch(`${API}/admin/connector-config`, { method: "POST", headers: adminHeaders, body: JSON.stringify(connectorConfig) });
      if (res.ok) setSaveMsg({ ok: true, text: "Connector config saved." });
      else setSaveMsg({ ok: false, text: "Failed to save." });
    } catch (e) { setSaveMsg({ ok: false, text: e.message }); }
    finally { setSaving(false); }
  };

  const savePowerConfig = async () => {
    setSaving(true); setSaveMsg(null);
    try {
      const res = await fetch(`${API}/admin/power-config`, { method: "POST", headers: adminHeaders, body: JSON.stringify(powerConfig) });
      if (res.ok) { setSaveMsg({ ok: true, text: "Power config saved. Re-generate decisions to apply." }); onRefresh?.(); }
      else setSaveMsg({ ok: false, text: "Failed to save." });
    } catch (e) { setSaveMsg({ ok: false, text: e.message }); }
    finally { setSaving(false); }
  };

  const retrainAll = async () => {
    setTraining(true); setTrainMsg(null);
    try {
      const res = await fetch(`${API}/admin/retrain`, { method: "POST", headers: adminHeaders });
      const data = await res.json();
      setTrainMsg({ ok: true, text: `Trained ${data.trained} models.` });
      loadAdminData();
      onRefresh?.();
    } catch (e) { setTrainMsg({ ok: false, text: e.message }); }
    finally { setTraining(false); }
  };

  if (!authenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: PALETTE.bg }}>
        <div className="rounded-2xl p-8 w-full max-w-sm" style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}` }}>
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: PALETTE.amber + "20" }}>
              <Lock size={20} style={{ color: PALETTE.amber }} />
            </div>
            <div>
              <h2 className="text-base font-bold" style={{ color: PALETTE.text }}>Admin Access</h2>
              <p className="text-xs" style={{ color: PALETTE.textMuted }}>Enter admin password</p>
            </div>
          </div>
          <input
            type="password" name="admin-password" value={password} onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && login()}
            placeholder="Password"
            className="w-full rounded-xl px-3 py-2.5 text-sm outline-none mb-3"
            style={{ background: PALETTE.bg, color: PALETTE.text, border: `1px solid ${PALETTE.border}` }}
            autoFocus
          />
          {authError && <p className="text-xs mb-3" style={{ color: PALETTE.red }}>{authError}</p>}
          <button onClick={login} className="w-full rounded-xl px-3 py-2.5 text-xs font-semibold uppercase tracking-wider" style={{ background: PALETTE.amber, color: PALETTE.bg }}>
            Login
          </button>
          <button onClick={onBack} className="w-full mt-2 rounded-xl px-3 py-2 text-xs" style={{ background: "transparent", color: PALETTE.textMuted, border: `1px solid ${PALETTE.border}` }}>
            <ArrowLeft size={12} className="inline mr-1" /> Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  const sectionClass = "rounded-2xl p-5 mb-6";
  const sectionStyle = { background: PALETTE.surface, border: `1px solid ${PALETTE.border}` };
  const inputClass = "w-full rounded-xl px-3 py-2 text-sm font-mono outline-none";
  const inputStyle = { background: PALETTE.bg, color: PALETTE.text, border: `1px solid ${PALETTE.border}` };

  return (
    <div className="min-h-screen" style={{ background: PALETTE.bg, color: PALETTE.text }}>
      <header className="px-6 py-4" style={{ background: PALETTE.surface, borderBottom: `1px solid ${PALETTE.border}` }}>
        <div className="max-w-[1000px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: PALETTE.amber + "20" }}>
              <Shield size={22} style={{ color: PALETTE.amber }} />
            </div>
            <div>
              <h1 className="text-base font-bold" style={{ color: PALETTE.text }}>Admin Panel</h1>
              <p className="text-xs" style={{ color: PALETTE.textMuted }}>System configuration and model management</p>
            </div>
          </div>
          <button onClick={onBack} className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold" style={{ background: PALETTE.bg, color: PALETTE.textMuted, border: `1px solid ${PALETTE.border}` }}>
            <ArrowLeft size={14} /> Dashboard
          </button>
        </div>
      </header>

      <main className="max-w-[1000px] mx-auto px-6 py-6">
        {/* Database Audit */}
        {dbAudit && (
          <div className={sectionClass} style={sectionStyle}>
            <h3 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: PALETTE.cyan }}>Database Status</h3>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
              {[
                { label: "KPI Rows", value: dbAudit.kpi_rows },
                { label: "Predictions", value: dbAudit.predictions },
                { label: "Decisions", value: dbAudit.decisions },
                { label: "Model Runs", value: dbAudit.model_runs },
                { label: "Carriers", value: dbAudit.carriers },
                { label: "Towers", value: dbAudit.towers },
              ].map((item) => (
                <div key={item.label} className="rounded-xl p-3 text-center" style={{ background: PALETTE.bg }}>
                  <div className="text-lg font-mono font-bold" style={{ color: PALETTE.text }}>{item.value?.toLocaleString()}</div>
                  <div className="text-[10px] uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>{item.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Connector Config */}
        {connectorConfig && (
          <div className={sectionClass} style={sectionStyle}>
            <h3 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: PALETTE.amber }}>Live Data Connector (OSS)</h3>
            <p className="text-xs mb-4" style={{ color: PALETTE.textMuted }}>Placeholder settings for the future live network data connector.</p>

            <div className="flex items-center gap-6 mb-4">
              <div className="flex items-center gap-3">
                <label className="text-xs font-semibold uppercase tracking-wider" style={{ color: PALETTE.textMuted }}>Status</label>
                <button
                  onClick={() => setConnectorConfig((c) => ({ ...c, enabled: !c.enabled }))}
                  className="relative w-11 h-6 rounded-full transition-colors"
                  style={{ background: connectorConfig.enabled ? PALETTE.green : "#475569" }}
                >
                  <div className="absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform"
                    style={{ left: connectorConfig.enabled ? "22px" : "2px" }} />
                </button>
                <span className="text-xs font-semibold" style={{ color: connectorConfig.enabled ? PALETTE.green : PALETTE.textMuted }}>
                  {connectorConfig.enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
              <div>
                <label htmlFor="connector-type" className="block text-xs mb-1" style={{ color: PALETTE.textMuted }}>Connector Type</label>
                <select id="connector-type" name="connector-type" value={connectorConfig.connector_type || "generic_rest"}
                  onChange={(e) => setConnectorConfig((c) => ({ ...c, connector_type: e.target.value }))}
                  className="rounded-xl px-3 py-2 text-sm outline-none"
                  style={{ background: PALETTE.bg, color: PALETTE.text, border: `1px solid ${PALETTE.border}` }}>
                  <option value="generic_rest">Generic REST API</option>
                  <option value="huawei_u2020">Huawei U2020</option>
                  <option value="nokia_netact">Nokia NetAct</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
              {[
                { key: "base_url", label: "Base URL", placeholder: "https://oss.example.com/api" },
                { key: "api_key", label: "API Key", placeholder: "sk-..." },
                { key: "username", label: "Username", placeholder: "admin" },
                { key: "password", label: "Password", placeholder: "••••••", type: "password" },
              ].map((field) => (
                <div key={field.key}>
                  <label htmlFor={`conn-${field.key}`} className="block text-xs mb-1" style={{ color: PALETTE.textMuted }}>{field.label}</label>
                  <input id={`conn-${field.key}`} type={field.type || "text"} name={field.key} placeholder={field.placeholder} value={connectorConfig[field.key] || ""}
                    onChange={(e) => setConnectorConfig((c) => ({ ...c, [field.key]: e.target.value }))}
                    className={inputClass} style={inputStyle} />
                </div>
              ))}
              <div>
                <label htmlFor="poll-interval" className="block text-xs mb-1" style={{ color: PALETTE.textMuted }}>Poll Interval (sec)</label>
                <input id="poll-interval" type="number" name="poll-interval" min="60" step="60" value={connectorConfig.poll_interval_seconds || 300}
                  onChange={(e) => setConnectorConfig((c) => ({ ...c, poll_interval_seconds: Number(e.target.value) }))}
                  className={inputClass} style={inputStyle} />
              </div>
            </div>
            <button onClick={saveConnectorConfig} disabled={saving} className="rounded-xl px-4 py-2 text-xs font-semibold uppercase tracking-wider" style={{ background: PALETTE.amber, color: PALETTE.bg }}>
              {saving ? "Saving…" : "Save Connector Config"}
            </button>
          </div>
        )}

        {/* Power & Capacity Config */}
        {powerConfig && (
          <div className={sectionClass} style={sectionStyle}>
            <h3 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: PALETTE.cyan }}>Power Model & Capacity Settings</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: PALETTE.green }}>Capacity Decision</div>
                {[
                  { key: "capacity_ceiling", label: "Capacity Ceiling (%)", step: 1 },
                  { key: "target_band_low", label: "Target Band Low (%)", step: 1 },
                  { key: "target_band_high", label: "Target Band High (%)", step: 1 },
                ].map((field) => (
                  <div key={field.key} className="mb-2">
                    <label htmlFor={`admin-cap-${field.key}`} className="block text-xs mb-1" style={{ color: PALETTE.textMuted }}>{field.label}</label>
                    <input id={`admin-cap-${field.key}`} type="number" name={field.key} step={field.step} value={powerConfig[field.key]}
                      onChange={(e) => setPowerConfig((c) => ({ ...c, [field.key]: Number(e.target.value) }))}
                      className={inputClass} style={{ ...inputStyle, color: PALETTE.amber }} />
                  </div>
                ))}
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: PALETTE.purple }}>Power Model (Watts)</div>
                {[
                  { key: "carrier_a_watts", label: "Carrier A (W)", step: 100 },
                  { key: "carrier_b_watts", label: "Carrier B (W)", step: 100 },
                  { key: "carrier_c_watts", label: "Carrier C (W)", step: 100 },
                  { key: "load_scaling_factor", label: "Load Scaling Factor", step: 0.01 },
                ].map((field) => (
                  <div key={field.key} className="mb-2">
                    <label htmlFor={`admin-power-${field.key}`} className="block text-xs mb-1" style={{ color: PALETTE.textMuted }}>{field.label}</label>
                    <input id={`admin-power-${field.key}`} type="number" name={field.key} step={field.step} value={powerConfig[field.key]}
                      onChange={(e) => setPowerConfig((c) => ({ ...c, [field.key]: Number(e.target.value) }))}
                      className={inputClass} style={{ ...inputStyle, color: PALETTE.cyan }} />
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-4">
              <button onClick={savePowerConfig} disabled={saving} className="rounded-xl px-4 py-2 text-xs font-semibold uppercase tracking-wider" style={{ background: PALETTE.accent, color: "#fff" }}>
                {saving ? "Saving…" : "Save Power Config"}
              </button>
              {saveMsg && (
                <span className="ml-3 text-xs" style={{ color: saveMsg.ok ? PALETTE.green : PALETTE.red }}>{saveMsg.text}</span>
              )}
            </div>
          </div>
        )}

        {/* Retrain */}
        <div className={sectionClass} style={sectionStyle}>
          <h3 className="text-sm font-semibold uppercase tracking-wider mb-4" style={{ color: PALETTE.purple }}>Model Training</h3>
          <div className="flex items-center gap-4 mb-4">
            <button onClick={retrainAll} disabled={training}
              className="rounded-xl px-4 py-2.5 text-xs font-semibold uppercase tracking-wider flex items-center gap-2"
              style={{ background: training ? PALETTE.purple + "80" : PALETTE.purple, color: "#fff" }}>
              {training ? <><RefreshCw size={12} className="animate-spin" /> Training…</> : "Retrain All Models"}
            </button>
            {trainMsg && (
              <span className="text-xs" style={{ color: trainMsg.ok ? PALETTE.green : PALETTE.red }}>{trainMsg.text}</span>
            )}
          </div>

          {modelRuns.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: PALETTE.textMuted }}>Recent Training Runs</div>
              <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${PALETTE.border}` }}>
                <table className="w-full text-xs">
                  <thead style={{ background: PALETTE.bg }}>
                    <tr>
                      <th className="text-left px-3 py-2" style={{ color: PALETTE.textMuted }}>#</th>
                      <th className="text-left px-3 py-2" style={{ color: PALETTE.textMuted }}>Time</th>
                      <th className="text-right px-3 py-2" style={{ color: PALETTE.textMuted }}>Rows</th>
                      <th className="text-right px-3 py-2" style={{ color: PALETTE.textMuted }}>MAE</th>
                      <th className="text-right px-3 py-2" style={{ color: PALETTE.textMuted }}>RMSE</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modelRuns.map((r) => (
                      <tr key={r.id} style={{ borderTop: `1px solid ${PALETTE.border}` }}>
                        <td className="px-3 py-2 font-mono" style={{ color: PALETTE.textMuted }}>#{r.id}</td>
                        <td className="px-3 py-2 font-mono" style={{ color: PALETTE.text }}>{r.trained_at?.slice(0, 16).replace("T", " ")}</td>
                        <td className="px-3 py-2 text-right font-mono" style={{ color: PALETTE.text }}>{r.training_row_count?.toLocaleString()}</td>
                        <td className="px-3 py-2 text-right font-mono font-semibold" style={{ color: PALETTE.cyan }}>{r.mae?.toFixed(2)}%</td>
                        <td className="px-3 py-2 text-right font-mono" style={{ color: PALETTE.amber }}>{r.rmse?.toFixed(2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

/* ──────────────────── MAIN APP ──────────────────── */

export default function App() {
  const [page, setPage] = useState("dashboard");
  const [summary, setSummary] = useState(null);
  const [liveStatus, setLiveStatus] = useState(null);
  const [towers, setTowers] = useState([]);
  const [filters, setFilters] = useState({ tower: "Tower A", carrier: "1_A", dateFrom: "", dateTo: "" });
  const [refreshKey, setRefreshKey] = useState(0);
  const [powerSummary, setPowerSummary] = useState(null);
  const [capacityConfig, setCapacityConfig] = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      const [sumRes, liveRes, towersRes, powRes, cfgRes] = await Promise.all([
        fetch(`${API}/data/summary`),
        fetch(`${API}/live-status`),
        fetch(`${API}/data/towers`),
        fetch(`${API}/data/power-summary?days=7`),
        fetch(`${API}/capacity-config`),
      ]);
      setSummary(await sumRes.json());
      setLiveStatus(await liveRes.json());
      setTowers(await towersRes.json());
      setPowerSummary(await powRes.json());
      setCapacityConfig(await cfgRes.json());
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll, refreshKey]);

  if (page === "admin") {
    return <AdminPage onBack={() => setPage("dashboard")} onRefresh={() => setRefreshKey((k) => k + 1)} />;
  }

  const chartCarrier = filters.carrier || null;
  const bandLow = capacityConfig?.target_band_low;
  const bandHigh = capacityConfig?.target_band_high;

  return (
    <div className="min-h-screen" style={{ background: PALETTE.bg, color: PALETTE.text }}>
      <header className="px-6 py-4" style={{ background: PALETTE.surface, borderBottom: `1px solid ${PALETTE.border}` }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/favicon.svg" alt="Logo" className="w-10 h-10 rounded-xl" />
            <div>
              <h1 className="text-base font-bold tracking-tight" style={{ color: PALETTE.text }}>Carrier Power System</h1>
              <p className="text-xs" style={{ color: PALETTE.textMuted }}>Capacity-Based Traffic-Aware Adaptive Carrier Management</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-xs" style={{ color: PALETTE.textMuted }}>Current Time</div>
              <div className="text-sm font-mono font-bold" style={{ color: PALETTE.text }}>{liveStatus ? `${liveStatus.date} ${String(liveStatus.hour).padStart(2, "0")}:00` : "Loading…"}</div>
            </div>
            <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: PALETTE.green }} />
          </div>
        </div>
      </header>

      <main className="px-6 py-6">
        <div className="flex gap-6">
          <aside className="w-64 shrink-0 hidden lg:block">
            <div className="sticky top-6 space-y-4">
              <FiltersPanel
                filters={filters} setFilters={setFilters}
                towers={towers} capacityConfig={capacityConfig}
                onRefresh={() => setRefreshKey((k) => k + 1)}
              />
              <UploadWidget onUploaded={() => setRefreshKey((k) => k + 1)} />
              <TestScenarioTool />
              <ModelStatusPanel onTrained={() => setRefreshKey((k) => k + 1)} />
              <button onClick={() => setPage("admin")}
                className="w-full rounded-2xl p-4 flex items-center gap-3 transition-colors"
                style={{ background: PALETTE.surface, border: `1px solid ${PALETTE.border}`, color: PALETTE.textMuted }}>
                <Lock size={16} style={{ color: PALETTE.amber }} />
                <span className="text-sm font-semibold">Admin Panel</span>
              </button>
            </div>
          </aside>

          <div className="flex-1 min-w-0 space-y-6">
            <LiveStatusHeader liveStatus={liveStatus} />
            <KpiCards liveStatus={liveStatus} summary={summary} powerSummary={powerSummary} />

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <TodayVsHistoryChart carrier={chartCarrier} bandLow={bandLow} bandHigh={bandHigh} />
              <TrendChart carrier={chartCarrier} dateFrom={filters.dateFrom} dateTo={filters.dateTo} bandLow={bandLow} bandHigh={bandHigh} />
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <BaselineVsMlChart carrier={chartCarrier} />
              <ModelAccuracyChart />
            </div>

            <PowerEnergyChart days={7} />

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <ExplainabilityPanel carrier={chartCarrier} towers={towers} />
              <HourDrilldown />
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <MonthPositionChart carrier={chartCarrier} />
              <CarrierTimeline initialDays={1} tower={filters.tower || undefined} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
