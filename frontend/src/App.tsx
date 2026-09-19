import React, { useState, useEffect } from "react";

export function App() {
  const [briefs, setBriefs] = useState<any[]>([]);
  const [stats, setStats] = useState<any>({ total_episodes: 0, accuracy_rate: 0, avg_latency_ms: 0 });
  const [wsStatus, setWsStatus] = useState("Connecting...");

  const fetchStats = () => {
    fetch("http://localhost:8810/api/v1/stats/overview")
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch((err) => console.log("Stats fetch error:", err));
  };

  useEffect(() => {
    fetchStats();
    const ws = new WebSocket("ws://localhost:8810/ws/live");
    ws.onopen = () => setWsStatus("Live Connected");
    ws.onclose = () => setWsStatus("Disconnected");
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.event === "brief_generated") {
          setBriefs((prev) => [msg.data, ...prev]);
          fetchStats();
        }
      } catch (e) {
        console.error(e);
      }
    };

    return () => ws.close();
  }, []);

  const handleFeedback = (episodeId: string, confirmed: boolean) => {
    fetch("http://localhost:8810/api/v1/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ episode_id: episodeId, confirmed }),
    })
      .then((res) => res.json())
      .then(() => {
        fetchStats();
      })
      .catch((err) => console.error(err));
  };

  const latestBrief = briefs.length > 0 ? briefs[0] : null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6">
      <header className="flex justify-between items-center border-b border-slate-800 pb-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-sky-400">RedForesight v2</h1>
          <p className="text-xs text-slate-400">Predictive Threat Intelligence & Telemetry Dashboard</p>
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-xs px-2 py-1 rounded bg-slate-800 text-slate-300">
            WS: <span className={wsStatus.includes("Live") ? "text-emerald-400 font-bold" : "text-amber-400"}>{wsStatus}</span>
          </span>
        </div>
      </header>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <p className="text-xs text-slate-400">Total Incidents</p>
          <p className="text-2xl font-bold text-slate-100">{stats.total_episodes}</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <p className="text-xs text-slate-400">Prediction Accuracy</p>
          <p className="text-2xl font-bold text-sky-400">{stats.accuracy_rate}%</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <p className="text-xs text-slate-400">Avg Agent Latency</p>
          <p className="text-2xl font-bold text-slate-100">{stats.avg_latency_ms}ms</p>
        </div>
        <div className="bg-slate-900 border border-slate-800 p-4 rounded-lg">
          <p className="text-xs text-slate-400">Backend Status</p>
          <p className="text-2xl font-bold text-emerald-400">Active</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-slate-900 border border-slate-800 p-6 rounded-lg">
          <h2 className="text-lg font-semibold text-slate-200 mb-4">Live Threat Brief Stream</h2>
          {briefs.length === 0 ? (
            <p className="text-sm text-slate-500 italic">Waiting for live Splunk telemetry / attack events...</p>
          ) : (
            briefs.map((brief, i) => (
              <div key={i} className="mb-6 border-b border-slate-800 pb-4">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-xs text-sky-400 font-mono">Host: {brief.host}</span>
                  <span className="text-xs text-slate-500">{brief.timestamp}</span>
                </div>
                <h3 className="text-sm font-semibold text-slate-100">Observed: {brief.observed_tactic} ({brief.observed_technique})</h3>
                <div className="mt-3 space-y-2">
                  <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Predicted Next Moves:</p>
                  {brief.predicted_moves.map((m: any, idx: number) => (
                    <div key={idx} className="bg-slate-950 p-2 rounded border border-slate-800 flex justify-between items-center">
                      <div>
                        <span className="text-xs font-bold text-sky-300">{m.technique_id} - {m.technique_name}</span>
                        <p className="text-xs text-slate-400">{m.reasoning}</p>
                      </div>
                      <span className="text-xs font-mono font-bold text-emerald-400">{(m.llm_adjusted_probability * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
                <div className="mt-4 flex space-x-2">
                  <button onClick={() => handleFeedback(brief.episode_id, true)} className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold rounded">Confirm</button>
                  <button onClick={() => handleFeedback(brief.episode_id, false)} className="px-3 py-1 bg-rose-600 hover:bg-rose-500 text-xs font-semibold rounded">Reject</button>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="bg-slate-900 border border-slate-800 p-6 rounded-lg">
          <h2 className="text-lg font-semibold text-slate-200 mb-4">Kill-Chain Visualizer</h2>
          {!latestBrief ? (
            <p className="text-xs text-slate-500 italic">No active incident brief to visualize.</p>
          ) : (
            <div className="text-xs text-slate-400 space-y-3">
              <div className="p-3 bg-slate-950 rounded border border-slate-800">
                <span className="font-bold text-sky-400">Observed Step</span>
                <p className="text-slate-200 font-semibold">{latestBrief.observed_tactic}</p>
                <p className="text-slate-500">{latestBrief.observed_technique}</p>
              </div>
              <div className="text-center text-slate-600">↓</div>
              <div className="p-3 bg-slate-950 rounded border border-slate-800 border-dashed">
                <span className="font-bold text-emerald-400">Top Predicted Next Move</span>
                {latestBrief.predicted_moves.length > 0 ? (
                  <>
                    <p className="text-slate-200 font-semibold">{latestBrief.predicted_moves[0].tactic}</p>
                    <p className="text-slate-500">{latestBrief.predicted_moves[0].technique_id} - {latestBrief.predicted_moves[0].technique_name}</p>
                    <p className="text-emerald-400 text-xs mt-1 font-bold">Confidence: {(latestBrief.predicted_moves[0].llm_adjusted_probability * 100).toFixed(0)}%</p>
                  </>
                ) : (
                  <p className="text-slate-500">None</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
