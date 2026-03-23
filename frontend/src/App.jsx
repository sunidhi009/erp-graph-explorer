import { useState, useEffect, useRef, useCallback } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ── Color map ──────────────────────────────────────────────────────────────
const NODE_COLORS = {
  SalesOrder:      "#4A90D9",
  Delivery:        "#27AE60",
  BillingDocument: "#E67E22",
  JournalEntry:    "#9B59B6",
  Customer:        "#E74C3C",
  Product:         "#1ABC9C",
  Plant:           "#F39C12",
  BusinessPartner: "#34495E",
};

const TYPE_ICONS = {
  SalesOrder:      "🛒",
  Delivery:        "🚚",
  BillingDocument: "📄",
  JournalEntry:    "📒",
  Customer:        "👤",
  Product:         "📦",
  Plant:           "🏭",
  BusinessPartner: "🤝",
};

// ── Stat Card ──────────────────────────────────────────────────────────────
function StatCard({ icon, label, value, color }) {
  return (
    <div style={{
      background: "#1a1a2e", border: `1px solid ${color}33`,
      borderRadius: 12, padding: "16px 20px", display: "flex",
      alignItems: "center", gap: 14, flex: "1 1 140px"
    }}>
      <span style={{ fontSize: 28 }}>{icon}</span>
      <div>
        <div style={{ color: "#888", fontSize: 11, textTransform: "uppercase", letterSpacing: 1 }}>{label}</div>
        <div style={{ color, fontSize: 22, fontWeight: 700 }}>{typeof value === "number" ? value.toLocaleString() : value}</div>
      </div>
    </div>
  );
}

// ── Graph Canvas (D3-style force layout using Canvas) ──────────────────────
function GraphCanvas({ nodes, links, onNodeClick, highlightIds }) {
  const canvasRef = useRef(null);
  const stateRef  = useRef({ nodes: [], links: [], dragging: null, offsetX: 0, offsetY: 0, scale: 1, panX: 0, panY: 0, isPanning: false, lastMouse: null });
  const rafRef    = useRef(null);
  const [tooltip, setTooltip] = useState(null);

  // Build simulation data once
  useEffect(() => {
    if (!nodes.length) return;
    const W = canvasRef.current.offsetWidth || 900;
    const H = canvasRef.current.offsetHeight || 600;

    // Assign initial positions in clusters by type
    const typePositions = {
      Customer:        { cx: W * 0.15, cy: H * 0.3 },
      BusinessPartner: { cx: W * 0.15, cy: H * 0.7 },
      SalesOrder:      { cx: W * 0.35, cy: H * 0.5 },
      Delivery:        { cx: W * 0.55, cy: H * 0.5 },
      BillingDocument: { cx: W * 0.72, cy: H * 0.35 },
      JournalEntry:    { cx: W * 0.85, cy: H * 0.5 },
      Product:         { cx: W * 0.72, cy: H * 0.7 },
      Plant:           { cx: W * 0.5,  cy: H * 0.85 },
    };

    const simNodes = nodes.map((n, i) => {
      const base = typePositions[n.type] || { cx: W / 2, cy: H / 2 };
      return {
        ...n,
        x:  base.cx + (Math.random() - 0.5) * 120,
        y:  base.cy + (Math.random() - 0.5) * 120,
        vx: 0,
        vy: 0,
      };
    });

    const idMap = {};
    simNodes.forEach(n => { idMap[n.id] = n; });

    const simLinks = links
      .map(l => ({ source: idMap[l.source], target: idMap[l.target], relation: l.relation }))
      .filter(l => l.source && l.target);

    stateRef.current.nodes = simNodes;
    stateRef.current.links = simLinks;
    stateRef.current.idMap = idMap;

    runSimulation();
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [nodes, links]);

  const runSimulation = () => {
    let alpha = 1;
    const tick = () => {
      const { nodes: ns, links: ls } = stateRef.current;
      const W = canvasRef.current?.offsetWidth || 900;
      const H = canvasRef.current?.offsetHeight || 600;

      if (alpha > 0.01) {
        // Repulsion
        for (let i = 0; i < ns.length; i++) {
          for (let j = i + 1; j < ns.length; j++) {
            const dx = ns[j].x - ns[i].x;
            const dy = ns[j].y - ns[i].y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = 1200 / (dist * dist);
            const fx = (dx / dist) * force * alpha;
            const fy = (dy / dist) * force * alpha;
            ns[i].vx -= fx; ns[i].vy -= fy;
            ns[j].vx += fx; ns[j].vy += fy;
          }
        }
        // Attraction along links
        for (const l of ls) {
          const dx = l.target.x - l.source.x;
          const dy = l.target.y - l.source.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const ideal = 120;
          const force = (dist - ideal) * 0.03 * alpha;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;
          l.source.vx += fx; l.source.vy += fy;
          l.target.vx -= fx; l.target.vy -= fy;
        }
        // Center gravity
        for (const n of ns) {
          n.vx += (W / 2 - n.x) * 0.003 * alpha;
          n.vy += (H / 2 - n.y) * 0.003 * alpha;
          n.x += n.vx; n.y += n.vy;
          n.vx *= 0.85; n.vy *= 0.85;
          n.x = Math.max(20, Math.min(W - 20, n.x));
          n.y = Math.max(20, Math.min(H - 20, n.y));
        }
        alpha *= 0.98;
      }
      draw();
      rafRef.current = requestAnimationFrame(tick);
    };
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(tick);
  };

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const { nodes: ns, links: ls, scale, panX, panY } = stateRef.current;
    const W = canvas.width = canvas.offsetWidth;
    const H = canvas.height = canvas.offsetHeight;

    ctx.clearRect(0, 0, W, H);
    ctx.save();
    ctx.translate(panX, panY);
    ctx.scale(scale, scale);

    // Draw links
    for (const l of ls) {
      const isHighlighted = highlightIds?.includes(l.source.id) && highlightIds?.includes(l.target.id);
      ctx.beginPath();
      ctx.moveTo(l.source.x, l.source.y);
      ctx.lineTo(l.target.x, l.target.y);
      ctx.strokeStyle = isHighlighted ? "#FFD700" : "#ffffff18";
      ctx.lineWidth   = isHighlighted ? 2 : 0.8;
      ctx.stroke();
    }

    // Draw nodes
    for (const n of ns) {
      const r = n.size || 10;
      const isHighlighted = highlightIds?.includes(n.id);
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fillStyle = isHighlighted ? "#FFD700" : (n.color || "#888");
      ctx.fill();
      if (isHighlighted) {
        ctx.strokeStyle = "#fff";
        ctx.lineWidth   = 2;
        ctx.stroke();
      }
      // Label for larger nodes
      if (r >= 14) {
        ctx.fillStyle = "#fff";
        ctx.font = `${Math.max(8, r * 0.7)}px sans-serif`;
        ctx.textAlign = "center";
        ctx.fillText(n.label.substring(0, 12), n.x, n.y + r + 10);
      }
    }
    ctx.restore();
  }, [highlightIds]);

  // Mouse events
  const getNodeAt = (ex, ey) => {
    const { nodes: ns, scale, panX, panY } = stateRef.current;
    const x = (ex - panX) / scale;
    const y = (ey - panY) / scale;
    for (let i = ns.length - 1; i >= 0; i--) {
      const n = ns[i];
      const r = (n.size || 10) + 4;
      if ((x - n.x) ** 2 + (y - n.y) ** 2 < r * r) return n;
    }
    return null;
  };

  const onMouseDown = e => {
    const rect = canvasRef.current.getBoundingClientRect();
    const ex = e.clientX - rect.left, ey = e.clientY - rect.top;
    const node = getNodeAt(ex, ey);
    if (node) {
      stateRef.current.dragging = node;
    } else {
      stateRef.current.isPanning = true;
      stateRef.current.lastMouse = { x: e.clientX, y: e.clientY };
    }
  };

  const onMouseMove = e => {
    const rect = canvasRef.current.getBoundingClientRect();
    const ex = e.clientX - rect.left, ey = e.clientY - rect.top;
    const { dragging, isPanning, lastMouse, scale, panX, panY } = stateRef.current;

    if (dragging) {
      dragging.x = (ex - panX) / scale;
      dragging.y = (ey - panY) / scale;
      dragging.vx = 0; dragging.vy = 0;
    } else if (isPanning && lastMouse) {
      stateRef.current.panX += e.clientX - lastMouse.x;
      stateRef.current.panY += e.clientY - lastMouse.y;
      stateRef.current.lastMouse = { x: e.clientX, y: e.clientY };
    } else {
      const node = getNodeAt(ex, ey);
      setTooltip(node ? { node, x: e.clientX, y: e.clientY } : null);
    }
  };

  const onMouseUp = e => {
    const { dragging } = stateRef.current;
    if (dragging) {
      const rect = canvasRef.current.getBoundingClientRect();
      const ex = e.clientX - rect.left, ey = e.clientY - rect.top;
      const node = getNodeAt(ex, ey);
      if (node === dragging) onNodeClick(dragging);
    }
    stateRef.current.dragging = null;
    stateRef.current.isPanning = false;
  };

  const onWheel = e => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    stateRef.current.scale = Math.max(0.2, Math.min(4, stateRef.current.scale * factor));
  };

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <canvas
        ref={canvasRef}
        style={{ width: "100%", height: "100%", cursor: "grab", display: "block" }}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onWheel={onWheel}
      />
      {tooltip && (
        <div style={{
          position: "fixed", left: tooltip.x + 12, top: tooltip.y - 10,
          background: "#1a1a2e", border: "1px solid #444", borderRadius: 8,
          padding: "8px 12px", color: "#fff", fontSize: 12, pointerEvents: "none",
          zIndex: 1000, maxWidth: 220,
        }}>
          <div style={{ color: NODE_COLORS[tooltip.node.type], fontWeight: 700 }}>
            {TYPE_ICONS[tooltip.node.type]} {tooltip.node.type}
          </div>
          <div style={{ marginTop: 4 }}>{tooltip.node.label}</div>
          <div style={{ color: "#888", marginTop: 2, fontSize: 10 }}>Click to inspect</div>
        </div>
      )}
    </div>
  );
}

// ── Node Detail Panel ──────────────────────────────────────────────────────
function NodeDetail({ node, onClose }) {
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    fetch(`${API}/api/graph/expand`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ node_id: node.id, node_type: node.type }),
    })
      .then(r => r.json())
      .then(setExpanded);
  }, [node]);

  const meta = node.metadata || {};

  return (
    <div style={{
      position: "absolute", top: 16, right: 16, width: 300,
      background: "#1a1a2e", border: `1px solid ${NODE_COLORS[node.type]}66`,
      borderRadius: 12, padding: 16, zIndex: 100, color: "#fff",
      maxHeight: "80vh", overflowY: "auto",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div>
          <span style={{ color: NODE_COLORS[node.type], fontWeight: 700, fontSize: 14 }}>
            {TYPE_ICONS[node.type]} {node.type}
          </span>
          <div style={{ fontSize: 12, color: "#aaa", marginTop: 2 }}>{node.id}</div>
        </div>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "#888", fontSize: 18, cursor: "pointer" }}>×</button>
      </div>

      {Object.entries(meta).filter(([k, v]) => v !== null && v !== "" && k !== "items").map(([k, v]) => (
        <div key={k} style={{ marginBottom: 6, fontSize: 12 }}>
          <span style={{ color: "#888" }}>{k}: </span>
          <span style={{ color: "#ddd" }}>{String(v).substring(0, 60)}</span>
        </div>
      ))}

      {meta.items && meta.items.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div style={{ color: "#888", fontSize: 11, marginBottom: 4 }}>LINE ITEMS ({meta.items.length})</div>
          {meta.items.slice(0, 5).map((item, i) => (
            <div key={i} style={{ background: "#0d0d1a", borderRadius: 6, padding: "6px 8px", marginBottom: 4, fontSize: 11 }}>
              {Object.entries(item).filter(([k, v]) => v).map(([k, v]) => (
                <span key={k} style={{ marginRight: 8 }}>
                  <span style={{ color: "#666" }}>{k}:</span>
                  <span style={{ color: "#bbb" }}> {String(v).substring(0, 20)}</span>
                </span>
              ))}
            </div>
          ))}
        </div>
      )}

      {expanded?.related_ids?.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div style={{ color: "#888", fontSize: 11, marginBottom: 4 }}>CONNECTED ENTITIES</div>
          {expanded.related_ids.slice(0, 6).map(id => (
            <div key={id} style={{ background: "#0d0d1a", borderRadius: 6, padding: "4px 8px", marginBottom: 3, fontSize: 11, color: "#4A90D9" }}>
              {id}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Chat Interface ─────────────────────────────────────────────────────────
function ChatPanel({ onHighlight }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "👋 Hi! I'm your ERP Graph Agent. Ask me anything about your Order-to-Cash data!\n\nTry: *Which customer spent the most?* or *Show broken flows*",
      rows: [], sql: null,
    }
  ]);
  const [input, setInput]     = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  const SUGGESTIONS = [
    "Which products are billed the most?",
    "Show orders with broken flows",
    "Trace billing document 90504274",
    "Which customer has the highest order value?",
    "How many deliveries are complete?",
  ];

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async (text) => {
    const msg = text || input.trim();
    if (!msg || loading) return;
    setInput("");

    const history = messages.filter(m => m.role !== "system").map(m => ({ role: m.role, content: m.content }));
    setMessages(prev => [...prev, { role: "user", content: msg }]);
    setLoading(true);

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, history }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, {
        role: "assistant",
        content: data.answer || "Sorry, I couldn't process that.",
        sql: data.sql,
        rows: data.rows || [],
        referenced_ids: data.referenced_ids || [],
        is_off_topic: data.is_off_topic,
      }]);
      if (data.referenced_ids?.length) onHighlight(data.referenced_ids);
    } catch (e) {
      setMessages(prev => [...prev, { role: "assistant", content: "⚠️ Error connecting to backend." }]);
    }
    setLoading(false);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: "#0d0d1a" }}>
      {/* Header */}
      <div style={{ padding: "14px 16px", borderBottom: "1px solid #222", background: "#1a1a2e" }}>
        <div style={{ fontWeight: 700, fontSize: 14, color: "#fff" }}>🤖 ERP Graph Agent</div>
        <div style={{ fontSize: 11, color: "#4A90D9", marginTop: 2 }}>Order-to-Cash Intelligence</div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "12px 14px" }}>
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: 16 }}>
            <div style={{
              display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start",
            }}>
              <div style={{
                maxWidth: "88%",
                background: m.role === "user" ? "#4A90D9" : "#1a1a2e",
                border: m.role === "assistant" ? "1px solid #333" : "none",
                borderRadius: m.role === "user" ? "14px 14px 0 14px" : "14px 14px 14px 0",
                padding: "10px 14px", color: "#fff", fontSize: 13, lineHeight: 1.5,
                whiteSpace: "pre-wrap",
              }}>
                {m.is_off_topic && <div style={{ color: "#E74C3C", fontWeight: 600, marginBottom: 4 }}>⛔ Off-topic</div>}
                {m.content}
              </div>
            </div>

            {/* SQL block */}
            {m.sql && (
              <div style={{ marginTop: 8, background: "#0a0a15", border: "1px solid #333", borderRadius: 8, padding: "8px 12px", fontSize: 11, color: "#27AE60", fontFamily: "monospace" }}>
                <div style={{ color: "#666", marginBottom: 4 }}>SQL</div>
                {m.sql}
              </div>
            )}

            {/* Results table */}
            {m.rows?.length > 0 && (
              <div style={{ marginTop: 8, overflowX: "auto" }}>
                <table style={{ width: "100%", fontSize: 11, borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      {Object.keys(m.rows[0]).map(k => (
                        <th key={k} style={{ padding: "4px 8px", background: "#1a1a2e", color: "#888", textAlign: "left", borderBottom: "1px solid #333" }}>{k}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {m.rows.slice(0, 10).map((r, j) => (
                      <tr key={j} style={{ background: j % 2 ? "#0d0d1a" : "#111120" }}>
                        {Object.values(r).map((v, k) => (
                          <td key={k} style={{ padding: "4px 8px", color: "#ccc", borderBottom: "1px solid #1a1a1a" }}>{String(v ?? "—").substring(0, 30)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ color: "#4A90D9", fontSize: 13, padding: "8px 0", display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ animation: "spin 1s linear infinite", display: "inline-block" }}>⟳</span> Analyzing data...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions */}
      {messages.length <= 2 && (
        <div style={{ padding: "0 12px 8px" }}>
          <div style={{ color: "#555", fontSize: 10, marginBottom: 6 }}>SUGGESTED QUERIES</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {SUGGESTIONS.map((s, i) => (
              <button key={i} onClick={() => send(s)} style={{
                background: "#1a1a2e", border: "1px solid #333", borderRadius: 20,
                color: "#aaa", fontSize: 11, padding: "5px 10px", cursor: "pointer",
              }}>{s}</button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div style={{ padding: "10px 12px", borderTop: "1px solid #222", display: "flex", gap: 8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask about orders, deliveries, billing..."
          style={{
            flex: 1, background: "#1a1a2e", border: "1px solid #333",
            borderRadius: 8, padding: "8px 12px", color: "#fff", fontSize: 13, outline: "none",
          }}
        />
        <button onClick={() => send()} disabled={loading} style={{
          background: loading ? "#333" : "#4A90D9", border: "none",
          borderRadius: 8, color: "#fff", fontSize: 18, padding: "0 14px", cursor: loading ? "not-allowed" : "pointer",
        }}>➤</button>
      </div>
    </div>
  );
}

// ── Legend ─────────────────────────────────────────────────────────────────
function Legend() {
  return (
    <div style={{
      position: "absolute", bottom: 16, left: 16,
      background: "#1a1a2e99", backdropFilter: "blur(8px)",
      border: "1px solid #333", borderRadius: 10, padding: "10px 14px",
      display: "flex", flexWrap: "wrap", gap: "6px 14px", maxWidth: 360,
    }}>
      {Object.entries(NODE_COLORS).map(([type, color]) => (
        <div key={type} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: color }} />
          <span style={{ color: "#aaa" }}>{TYPE_ICONS[type]} {type}</span>
        </div>
      ))}
    </div>
  );
}

// ── Main App ───────────────────────────────────────────────────────────────
export default function App() {
  const [graphData,    setGraphData]    = useState({ nodes: [], links: [] });
  const [stats,        setStats]        = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [highlightIds, setHighlightIds] = useState([]);
  const [loading,      setLoading]      = useState(true);
  const [activeTab,    setActiveTab]    = useState("graph");

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/graph`).then(r => r.json()),
      fetch(`${API}/api/stats`).then(r => r.json()),
    ]).then(([graph, s]) => {
      setGraphData(graph);
      setStats(s);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "#0d0d1a", color: "#fff", fontFamily: "'Inter', sans-serif" }}>

      {/* ── Top Bar ── */}
      <div style={{ padding: "10px 20px", borderBottom: "1px solid #222", background: "#1a1a2e", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 32, height: 32, background: "linear-gradient(135deg, #4A90D9, #9B59B6)", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>⬡</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15 }}>ERP Graph Explorer</div>
            <div style={{ fontSize: 11, color: "#555" }}>Order-to-Cash Intelligence Platform</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {["graph", "analytics"].map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)} style={{
              background: activeTab === tab ? "#4A90D9" : "#0d0d1a",
              border: "1px solid " + (activeTab === tab ? "#4A90D9" : "#333"),
              borderRadius: 6, color: "#fff", padding: "5px 14px",
              cursor: "pointer", fontSize: 12, textTransform: "capitalize",
            }}>{tab}</button>
          ))}
        </div>
      </div>

      {/* ── Stats Bar ── */}
      {stats && (
        <div style={{ display: "flex", gap: 10, padding: "10px 16px", overflowX: "auto", borderBottom: "1px solid #1a1a1a" }}>
          <StatCard icon="🛒" label="Sales Orders"    value={stats.salesOrders}    color="#4A90D9" />
          <StatCard icon="🚚" label="Deliveries"      value={stats.deliveries}      color="#27AE60" />
          <StatCard icon="📄" label="Billing Docs"    value={stats.billingDocs}     color="#E67E22" />
          <StatCard icon="📒" label="Journal Entries" value={stats.journalEntries}  color="#9B59B6" />
          <StatCard icon="⚠️" label="Broken Flows"   value={stats.brokenFlows}     color="#E74C3C" />
          <StatCard icon="💰" label="Total Revenue"   value={"₹" + (stats.totalRevenue / 1000).toFixed(0) + "K"} color="#1ABC9C" />
        </div>
      )}

      {/* ── Main Content ── */}
      {activeTab === "graph" && (
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          {/* Graph area */}
          <div style={{ flex: 1, position: "relative" }}>
            {loading ? (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#555" }}>
                <div>⟳ Loading graph data...</div>
              </div>
            ) : (
              <>
                <GraphCanvas
                  nodes={graphData.nodes || []}
                  links={graphData.links || []}
                  onNodeClick={setSelectedNode}
                  highlightIds={highlightIds}
                />
                <Legend />
                {selectedNode && (
                  <NodeDetail node={selectedNode} onClose={() => setSelectedNode(null)} />
                )}
                <div style={{ position: "absolute", top: 12, left: 12, background: "#1a1a2e99", borderRadius: 8, padding: "6px 12px", fontSize: 11, color: "#888" }}>
                  {graphData.nodes?.length} nodes · {graphData.links?.length} edges · Scroll to zoom · Drag to pan
                </div>
              </>
            )}
          </div>

          {/* Chat panel */}
          <div style={{ width: 380, borderLeft: "1px solid #222", display: "flex", flexDirection: "column" }}>
            <ChatPanel onHighlight={setHighlightIds} />
          </div>
        </div>
      )}

      {activeTab === "analytics" && (
        <AnalyticsTab conn={null} apiUrl={API} />
      )}

      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; } 
        ::-webkit-scrollbar-track { background: #0d0d1a; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

// ── Analytics Tab ──────────────────────────────────────────────────────────
function AnalyticsTab({ apiUrl }) {
  const [topProducts, setTopProducts] = useState([]);
  const [brokenFlows, setBrokenFlows] = useState([]);

  useEffect(() => {
    fetch(`${apiUrl}/api/top-products`).then(r => r.json()).then(setTopProducts);
    fetch(`${apiUrl}/api/broken-flows`).then(r => r.json()).then(setBrokenFlows);
  }, []);

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: 20, display: "flex", gap: 20, flexWrap: "wrap" }}>
      {/* Top Products */}
      <div style={{ flex: "1 1 400px", background: "#1a1a2e", borderRadius: 12, padding: 16 }}>
        <div style={{ fontWeight: 700, marginBottom: 12, color: "#1ABC9C" }}>📦 Top Products by Billing Count</div>
        <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ color: "#666" }}>
              <th style={{ textAlign: "left", padding: "4px 8px" }}>#</th>
              <th style={{ textAlign: "left", padding: "4px 8px" }}>Product</th>
              <th style={{ textAlign: "right", padding: "4px 8px" }}>Billings</th>
              <th style={{ textAlign: "right", padding: "4px 8px" }}>Revenue</th>
            </tr>
          </thead>
          <tbody>
            {topProducts.map((p, i) => (
              <tr key={i} style={{ borderTop: "1px solid #222" }}>
                <td style={{ padding: "6px 8px", color: "#555" }}>{i + 1}</td>
                <td style={{ padding: "6px 8px", color: "#ddd" }}>{(p.name || p.product).substring(0, 28)}</td>
                <td style={{ padding: "6px 8px", color: "#E67E22", textAlign: "right" }}>{p.billingCount}</td>
                <td style={{ padding: "6px 8px", color: "#27AE60", textAlign: "right" }}>₹{Number(p.totalAmount || 0).toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Broken Flows */}
      <div style={{ flex: "1 1 400px", background: "#1a1a2e", borderRadius: 12, padding: 16 }}>
        <div style={{ fontWeight: 700, marginBottom: 12, color: "#E74C3C" }}>⚠️ Broken / Incomplete Flows</div>
        <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ color: "#666" }}>
              <th style={{ textAlign: "left", padding: "4px 8px" }}>Document</th>
              <th style={{ textAlign: "left", padding: "4px 8px" }}>Issue</th>
            </tr>
          </thead>
          <tbody>
            {brokenFlows.slice(0, 15).map((b, i) => (
              <tr key={i} style={{ borderTop: "1px solid #222" }}>
                <td style={{ padding: "6px 8px", color: "#4A90D9" }}>{b.salesOrder || b.billingDocument}</td>
                <td style={{ padding: "6px 8px", color: "#E74C3C" }}>{b.issue}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}