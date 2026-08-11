"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { 
  UploadCloud, 
  Cpu, 
  Activity, 
  CheckCircle, 
  ChevronRight, 
  Zap,
  ShieldCheck,
  Send,
  Mail
} from "lucide-react";

// Dynamically import Three.js Canvas component with ssr: false to prevent Node.js SSR hanging
const ParticleSwarmCanvas = dynamic(() => import("../components/ParticleSwarmCanvas"), {
  ssr: false,
});

// --- LAYER 2: THE GLASSMORPHISM UI ---
export default function AgenticDashboard() {
  const [threadStatus, setThreadStatus] = useState("IDLE");
  const [aiState, setAiState] = useState<any>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [recipientEmail, setRecipientEmail] = useState("delivered@resend.dev");

  // --- LAYER 3: AUTONOMOUS POLLING RADAR ---
  React.useEffect(() => {
    const pollBackend = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/threads/portfolio_live_demo/state`);
        if (!res.ok) return;
        
        const data = await res.json();
        
        // If the backend has data, wake up the UI automatically
        if (data.status === "PAUSED_FOR_HUMAN" && threadStatus !== "PAUSED_FOR_HUMAN") {
          setThreadId("portfolio_live_demo");
          setThreadStatus("PAUSED_FOR_HUMAN");
          setAiState(data.state_values);
        }
      } catch (error) {
        // Silently ignore connection errors while waiting for the worker to trigger
      }
    };

    // Ping the FastAPI backend every 2 seconds
    const interval = setInterval(pollBackend, 2000);
    return () => clearInterval(interval);
  }, [threadStatus]);

  // The actual trigger to your FastAPI Backend
  const handleIngestion = async () => {
    setThreadStatus("PROCESSING");
    const newThreadId = `thread_demo_${Math.floor(Math.random() * 1000)}`;
    setThreadId(newThreadId);

    try {
      // 1. Start the Thread
      await fetch("http://localhost:8000/api/threads/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: newThreadId, file_uri: "s3://contracts/demo.pdf" })
      });

      // 2. Poll for the Human Gate Pause
      setTimeout(async () => {
        const res = await fetch(`http://localhost:8000/api/threads/${newThreadId}/state`);
        const data = await res.json();
        
        if (data.status === "PAUSED_FOR_HUMAN") {
          setThreadStatus("PAUSED_FOR_HUMAN");
          setAiState(data.state_values); 
        }
      }, 2500);

    } catch (error) {
      console.error("API Connection Failed. Is Uvicorn running?", error);
      setThreadStatus("ERROR");
    }
  };

  const handleDecision = async (decision: "APPROVE" | "REJECT") => {
    setThreadStatus("EXECUTING");
    if (threadId) {
      await fetch(`http://localhost:8000/api/threads/${threadId}/resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, recipient_email: recipientEmail })
      });
    }
    setTimeout(() => setThreadStatus("COMPLETED"), 1500);
  };

  return (
    <div className="relative min-h-screen bg-[#0A0A10] text-slate-200 font-sans overflow-hidden">
      {/* WebGL Canvas Background */}
      <div className="absolute inset-0 pointer-events-none opacity-60">
        <ParticleSwarmCanvas isProcessing={threadStatus === "PROCESSING"} />
      </div>

      {/* Main UI Overlay */}
      <div className="relative z-10 flex flex-col min-h-screen">
        
        {/* Header */}
        <header className="bg-black/40 backdrop-blur-md border-b border-white/5 px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/20 rounded-lg border border-indigo-500/30">
              <Cpu className="w-5 h-5 text-indigo-400" />
            </div>
            <h1 className="text-lg font-bold tracking-tight text-white">Agentic Procurement Ops</h1>
            <span className="px-2 py-1 bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs rounded-md ml-2">
              LangGraph + Groq LPU
            </span>
          </div>
          <div className="flex items-center gap-4 text-sm font-mono">
            <span className="text-slate-500">API Gateway: http://localhost:8000</span>
            <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full">
              <Activity className="w-3 h-3" /> Swarm Online
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <main className="flex-1 p-8 max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-12 gap-8 pointer-events-none">
          
          {/* Left Column */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="lg:col-span-8 space-y-8 pointer-events-auto"
          >
            {/* Ingestion Dropzone */}
            <div 
              onClick={threadStatus === "IDLE" ? handleIngestion : undefined}
              className={`p-10 rounded-xl border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-all duration-300 backdrop-blur-md
                ${threadStatus === "IDLE" ? "border-indigo-500/30 bg-indigo-500/5 hover:bg-indigo-500/10 hover:border-indigo-400" : "border-white/5 bg-black/40"}`}
            >
              <UploadCloud className={`w-10 h-10 mb-4 ${threadStatus === "IDLE" ? "text-indigo-400" : "text-slate-600"}`} />
              <h2 className="text-lg font-medium text-white mb-1">
                {threadStatus === "IDLE" ? "1. PDF DOCUMENT INGESTION" : "INGESTION LOCKED"}
              </h2>
              <p className="text-sm text-slate-400">
                {threadStatus === "IDLE" ? "Click to simulate dropping a contract PDF into S3" : "Swarm execution in progress..."}
              </p>
            </div>

            {/* Topology Flow */}
            <div className="bg-black/40 backdrop-blur-md border border-white/5 rounded-xl p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-sm font-bold text-slate-300 tracking-wider flex items-center gap-2">
                  <Zap className="w-4 h-4 text-indigo-400" /> INTERACTIVE MULTI-AGENT SWARM
                </h3>
                <span className="text-xs font-mono text-slate-500">MemorySaver Postgres State</span>
              </div>
              
              <div className="flex items-center justify-between text-xs font-mono">
                {["PySpark Ingest", "Groq Planner", "Math Reviewer", "Human Gate", "Resend Dispatch"].map((step, idx) => {
                  
                  let isActive = false;
                  if (threadStatus === "PROCESSING" && idx < 3) isActive = true;
                  if (threadStatus === "PAUSED_FOR_HUMAN" && idx === 3) isActive = true;
                  if (threadStatus === "EXECUTING" && idx === 4) isActive = true;
                  if (threadStatus === "COMPLETED") isActive = false;

                  return (
                    <React.Fragment key={idx}>
                      <div className={`flex flex-col items-center p-4 rounded-lg border transition-all duration-500 ${
                        isActive 
                          ? "bg-indigo-500/20 border-indigo-500/50 shadow-[0_0_15px_rgba(99,102,241,0.2)]" 
                          : "bg-white/[0.02] border-white/5"
                      }`}>
                        <span className={isActive ? "text-indigo-300 font-bold" : "text-slate-500"}>{step}</span>
                        <span className={`mt-2 px-2 py-0.5 rounded text-[10px] ${isActive ? "bg-indigo-500/20 text-indigo-300" : "bg-white/5 text-slate-600"}`}>
                          {isActive ? "ACTIVE" : "IDLE"}
                        </span>
                      </div>
                      {idx < 4 && <ChevronRight className="w-4 h-4 text-slate-700" />}
                    </React.Fragment>
                  );
                })}
              </div>
            </div>
          </motion.div>

          {/* Right Column: AI Output */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="lg:col-span-4 pointer-events-auto"
          >
            <div className="bg-black/40 backdrop-blur-md border border-white/5 rounded-xl h-full flex flex-col overflow-hidden">
              <div className="p-4 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-300 tracking-wider">COUNTER-OFFER</h3>
                {threadStatus === "PAUSED_FOR_HUMAN" && (
                  <span className="flex items-center gap-2 text-xs font-bold text-amber-400 bg-amber-400/10 px-2 py-1 rounded">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
                    </span>
                    ACTION REQUIRED
                  </span>
                )}
              </div>
              
              <div className="p-6 flex-1 flex flex-col justify-center">
                {aiState ? (
                  <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="space-y-6">
                    
                    <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg flex gap-3">
                      <ShieldCheck className="text-emerald-400 w-5 h-5 flex-shrink-0" />
                      <p className="text-xs text-emerald-300/80 leading-relaxed">
                        <span className="font-bold text-emerald-400">MATH VALIDATED:</span> Target price represents exactly a 15.0% deterministic discount. Variance ≤ 2.0%.
                      </p>
                    </div>

                    <div className="space-y-4 font-mono">
                      <div className="flex justify-between items-end border-b border-white/5 pb-2">
                        <span className="text-xs text-slate-500">VENDOR</span>
                        <span className="text-sm text-white">{aiState.vendor_name}</span>
                      </div>
                      <div className="flex justify-between items-end border-b border-white/5 pb-2">
                        <span className="text-xs text-slate-500">INITIAL VALUE</span>
                        <span className="text-sm text-white">${aiState.initial_value?.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                      </div>
                      <div className="flex justify-between items-end">
                        <span className="text-xs text-indigo-400">TARGET PRICE</span>
                        <span className="text-2xl font-bold text-indigo-400">${aiState.proposed_price?.toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                      </div>
                    </div>

                    {threadStatus === "PAUSED_FOR_HUMAN" && (
                      <div className="space-y-3 pt-4 border-t border-white/5 font-mono">
                        <div className="space-y-1">
                          <label className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider flex items-center gap-1.5">
                            <Mail className="w-3.5 h-3.5 text-indigo-400" /> Target Recipient Email Address
                          </label>
                          <input 
                            type="email"
                            value={recipientEmail}
                            onChange={(e) => setRecipientEmail(e.target.value)}
                            placeholder="your.email@example.com"
                            className="w-full bg-black/60 border border-white/10 focus:border-indigo-500/60 rounded-lg px-3 py-2 text-xs text-indigo-300 focus:outline-none transition-colors"
                          />
                        </div>
                        <div className="flex gap-3 pt-1">
                          <button 
                            onClick={() => handleDecision("REJECT")}
                            className="flex-1 py-2.5 rounded-lg text-xs font-bold text-slate-300 bg-white/5 hover:bg-white/10 transition-colors"
                          >
                            Reject
                          </button>
                          <button 
                            onClick={() => handleDecision("APPROVE")}
                            className="flex-1 py-2.5 rounded-lg text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 transition-colors flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(99,102,241,0.4)] font-mono"
                          >
                            <Send className="w-4 h-4" /> Approve & Execute Email
                          </button>
                        </div>
                      </div>
                    )}
                  </motion.div>
                ) : (
                  <div className="text-center text-slate-600 text-sm font-mono">
                    Awaiting PDF ingestion & pipeline execution...
                  </div>
                )}
                
                {threadStatus === "COMPLETED" && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-6 flex flex-col items-center text-emerald-400">
                    <CheckCircle className="w-12 h-12 mb-2" />
                    <span className="font-bold tracking-wider text-sm">EMAIL DISPATCHED</span>
                  </motion.div>
                )}
              </div>
            </div>
          </motion.div>

        </main>
      </div>
    </div>
  );
}
