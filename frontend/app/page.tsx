// app/page.tsx

"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";

type AnalysisResponse = {
  report: string;
  charts: string[];
};

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState("");

  const handleUpload = async () => {
    if (!file) {
      setError("Please upload a dataset.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const formData = new FormData();

      formData.append("file", file);
      formData.append("prompt", prompt);

      const response = await fetch(
        "http://localhost:8000/analyze",
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error("Failed to analyze dataset");
      }

      const data = await response.json();

      setResult(data);
    } catch (err) {
      setError("Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-zinc-950 text-white px-6 py-10 flex justify-center">
      <div className="max-w-5xl mx-auto">
        <div className="mb-10">
          <h1 className="text-5xl font-bold mb-4">
            LLM Analyst
          </h1>

          <p className="text-zinc-400 text-lg">
            Загрузите набор данных в формате CSV или Excel, и позвольте ИИ автоматически анализировать даный датасет.
          </p>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 mb-8">
          <div className="mb-6">
            <label className="block text-lg font-bold italic mb-2 text-zinc-300">
              Загрузите файл
            </label>

            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              onChange={(e) =>
                setFile(e.target.files?.[0] || null)
              }
              className="block w-full text-sm text-zinc-300
              file:mr-4
              file:py-2
              file:px-4
              file:rounded-lg
              file:border-0
              file:bg-white
              file:text-black
              hover:file:bg-zinc-200"
            />
          </div>

          <div className="mb-6">
            <label className="block text-sm mb-2 text-zinc-300">
              Инструкции для ИИ-агента
            </label>

            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Пример: выяви аномалии, построй графики и определи корреляции"
              className="w-full h-36 bg-zinc-950 border border-zinc-800 rounded-xl p-4 outline-none focus:border-zinc-600 resize-none"
            />
          </div>

          <button
            onClick={handleUpload}
            disabled={loading}
            className="bg-white text-black px-6 py-3 rounded-xl font-medium hover:bg-zinc-200 transition disabled:opacity-50"
          >
            {loading ? "Идёт анализ датасета..." : "Анализировать"}
          </button>

          {error && (
            <div className="mt-4 text-red-400">
              {error}
            </div>
          )}
        </div>

        {loading && (
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6">
            <div className="animate-pulse space-y-4">
              <div className="h-6 bg-zinc-800 rounded w-1/3"></div>
              <div className="h-4 bg-zinc-800 rounded"></div>
              <div className="h-4 bg-zinc-800 rounded"></div>
              <div className="h-4 bg-zinc-800 rounded w-2/3"></div>
            </div>

            <p className="mt-6 text-zinc-400">
              Агент анализирует датасет....
            </p>
          </div>
        )}

        {result && (
          <div className="space-y-8">
            <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8">
              <h2 className="text-3xl font-semibold mb-6">
                AI Report
              </h2>

              <div className="prose prose-invert max-w-none">
                <ReactMarkdown>
                  {result.report}
                </ReactMarkdown>
              </div>
            </section>

            {result.charts.length > 0 && (
              <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8">
                <h2 className="text-3xl font-semibold mb-6">
                  Generated Charts
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {result.charts.map((chart, index) => (
                    <div
                      key={index}
                      className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden"
                    >
                      <img
                        src={`http://localhost:8000/${chart}`}
                        alt={`Chart ${index}`}
                        className="w-full"
                      />
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </main>
  );
}