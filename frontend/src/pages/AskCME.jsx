// src/pages/AskCME.tsx

import React, { useState } from "react";

type CMERecommendation = {
  cme_event_id: number;
  title: string;
  provider?: string | null;
  credit_hours?: number | null;
  url?: string | null;
  score: number;
  rank: number;
  reason: string;
};

type AskCmeResponse = {
  question: string;
  answer: string;
  recommendations: CMERecommendation[];
};

const AskCME: React.FC = () => {
  const [question, setQuestion] = useState("");
  const [physicianId, setPhysicianId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskCmeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const payload: any = { question };
      if (physicianId) {
        payload.physician_id = Number(physicianId);
      }

      const res = await fetch("http://127.0.0.1:8000/ask/cme", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Request failed: ${res.status}`);
      }

      const data: AskCmeResponse = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        <h1 className="text-2xl font-semibold text-slate-900">
          Ask MyCertiQ about CME
        </h1>

        <form onSubmit={handleSubmit} className="space-y-4 bg-white p-4 rounded-2xl shadow-sm">
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Question
            </label>
            <textarea
              className="mt-1 block w-full rounded-xl border border-slate-300 p-2 text-sm"
              rows={3}
              placeholder='e.g. "What CME should I take for breast cancer?"'
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700">
              Physician ID (optional)
            </label>
            <input
              type="number"
              className="mt-1 block w-48 rounded-xl border border-slate-300 p-2 text-sm"
              placeholder="1"
              value={physicianId}
              onChange={(e) => setPhysicianId(e.target.value)}
            />
          </div>

          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="inline-flex items-center rounded-xl border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm disabled:opacity-60"
          >
            {loading ? "Thinking..." : "Ask"}
          </button>
        </form>

        {error && (
          <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {result && (
          <div className="space-y-4">
            <div className="bg-white rounded-2xl shadow-sm p-4">
              <h2 className="text-lg font-semibold text-slate-900 mb-2">
                Answer
              </h2>
              <p className="whitespace-pre-line text-sm text-slate-800">
                {result.answer}
              </p>
            </div>

            <div className="bg-white rounded-2xl shadow-sm p-4">
              <h2 className="text-lg font-semibold text-slate-900 mb-3">
                Recommended CME Activities
              </h2>
              <div className="space-y-3">
                {result.recommendations.map((rec) => (
                  <div
                    key={rec.cme_event_id}
                    className="border border-slate-200 rounded-xl p-3 text-sm"
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-semibold">
                        {rec.title}{" "}
                        <span className="text-xs text-slate-500">
                          (ID: {rec.cme_event_id})
                        </span>
                      </div>
                      <div className="text-xs text-slate-500">
                        Rank {rec.rank} • Score {rec.score.toFixed(2)}
                      </div>
                    </div>
                    <div className="mt-1 text-xs text-slate-600">
                      {rec.provider && <>Provider: {rec.provider} • </>}
                      {rec.credit_hours != null && <>Credits: {rec.credit_hours}</>}
                    </div>
                    <div className="mt-1 text-xs text-slate-600">
                      {rec.url && (
                        <a
                          href={rec.url}
                          className="text-indigo-600 underline"
                          target="_blank"
                          rel="noreferrer"
                        >
                          View CME
                        </a>
                      )}
                    </div>
                    <div className="mt-2 text-xs text-slate-700">
                      {rec.reason}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AskCME;
