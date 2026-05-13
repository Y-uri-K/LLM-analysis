// app/page.tsx

"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type AnalysisResponse = {
  dataset_id: string;
  report: string;
  charts: string[];
};

type ErrorResponse = {
  error?: string;
  detail?: string;
};

type AskResponse = {
  answer: string;
  charts: string[];
};

type ChatMessage = {
  question: string;
  answer: string;
  charts: string[];
};

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState("");
  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);

  const uploadWithProgress = (
    formData: FormData
  ): Promise<{ status: number; data: unknown }> =>
    new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_URL}/analyze`);

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(progress);
        }
      };

      xhr.onerror = () => {
        reject(new Error("Network error while uploading file"));
      };

      xhr.onload = () => {
        let parsed: unknown = {};
        try {
          parsed = xhr.responseText ? JSON.parse(xhr.responseText) : {};
        } catch {
          parsed = {};
        }
        resolve({
          status: xhr.status,
          data: parsed,
        });
      };

      xhr.send(formData);
    });

  const handleUpload = async () => {
    if (!file) {
      setError("Please upload a dataset.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setChatHistory([]);
    setFollowUpQuestion("");
    setUploadProgress(0);

    try {
      const formData = new FormData();

      formData.append("file", file);
      formData.append("prompt", prompt);

      const response = await uploadWithProgress(formData);
      setUploadProgress(100);

      if (response.status < 200 || response.status >= 300) {
        const errorData = (response.data || {}) as ErrorResponse;
        throw new Error(
          errorData.detail ||
            errorData.error ||
            "Failed to analyze dataset"
        );
      }

      const data = (response.data || {}) as
        | AnalysisResponse
        | ErrorResponse;

      if ("error" in data || "detail" in data) {
        throw new Error(
          data.detail || data.error || "Failed to analyze dataset"
        );
      }

      if (
        !("report" in data) ||
        typeof data.report !== "string" ||
        !("dataset_id" in data) ||
        typeof data.dataset_id !== "string"
      ) {
        throw new Error("Invalid analysis response format");
      }

      setResult(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Something went wrong.");
      }
    } finally {
      setLoading(false);
      setTimeout(() => {
        setUploadProgress(0);
      }, 600);
    }
  };

  const handleAskQuestion = async () => {
    if (!result?.dataset_id) {
      setError("Сначала загрузите датасет и выполните первичный анализ.");
      return;
    }
    if (!followUpQuestion.trim()) {
      setError("Введите вопрос по датасету.");
      return;
    }

    setChatLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          dataset_id: result.dataset_id,
          question: followUpQuestion.trim(),
        }),
      });

      if (!response.ok) {
        const errorData =
          (await response.json().catch(() => ({}))) as ErrorResponse;
        throw new Error(
          errorData.detail || errorData.error || "Не удалось получить ответ"
        );
      }

      const data = (await response.json()) as AskResponse | ErrorResponse;
      if ("error" in data || "detail" in data || !("answer" in data)) {
        throw new Error(
          ("detail" in data && data.detail) ||
            ("error" in data && data.error) ||
            "Не удалось получить ответ"
        );
      }

      setChatHistory((prev) => [
        ...prev,
        {
          question: followUpQuestion.trim(),
          answer: data.answer,
          charts: data.charts || [],
        },
      ]);
      setFollowUpQuestion("");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Something went wrong.");
      }
    } finally {
      setChatLoading(false);
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

            <div className="mt-6">
              <div className="flex justify-between text-xs text-zinc-400 mb-2">
                <span>Загрузка файла</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-white transition-all duration-200"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
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
                Готовый отчёт
              </h2>

              <div className="prose prose-invert max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    table: ({ ...props }) => (
                      <div className="overflow-x-auto my-4">
                        <table
                          className="min-w-full border border-zinc-700 text-sm"
                          {...props}
                        />
                      </div>
                    ),
                    thead: ({ ...props }) => (
                      <thead className="bg-zinc-800" {...props} />
                    ),
                    th: ({ ...props }) => (
                      <th
                        className="border border-zinc-700 px-3 py-2 text-left"
                        {...props}
                      />
                    ),
                    td: ({ ...props }) => (
                      <td
                        className="border border-zinc-700 px-3 py-2 align-top"
                        {...props}
                      />
                    ),
                  }}
                >
                  {result.report}
                </ReactMarkdown>
              </div>
            </section>

            {result?.charts?.length > 0 && (
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
                        src={`${API_URL}/${chart}`}
                        alt={`Chart ${index}`}
                        className="w-full"
                      />
                    </div>
                  ))}
                </div>
              </section>
            )}

            <section className="bg-zinc-900 border border-zinc-800 rounded-2xl p-8">
              <h2 className="text-3xl font-semibold mb-6">
                Вопросы по датасету
              </h2>
              <p className="text-zinc-400 mb-4">
                Можно продолжить диалог по уже загруженному датасету.
              </p>

              <div className="flex gap-3 mb-6">
                <textarea
                  value={followUpQuestion}
                  onChange={(e) => setFollowUpQuestion(e.target.value)}
                  placeholder="Пример: найди топ-5 клиентов по выручке и объясни почему"
                  className="flex-1 h-24 bg-zinc-950 border border-zinc-800 rounded-xl p-4 outline-none focus:border-zinc-600 resize-none"
                />
                <button
                  onClick={handleAskQuestion}
                  disabled={chatLoading}
                  className="bg-white text-black px-5 py-3 rounded-xl font-medium hover:bg-zinc-200 transition disabled:opacity-50 h-fit"
                >
                  {chatLoading ? "Думаю..." : "Спросить"}
                </button>
              </div>

              <div className="space-y-4">
                {chatHistory.map((item, idx) => (
                  <div
                    key={idx}
                    className="bg-zinc-950 border border-zinc-800 rounded-xl p-4"
                  >
                    <div className="text-zinc-300 mb-3">
                      <span className="font-semibold">Вопрос:</span>{" "}
                      {item.question}
                    </div>
                    <div className="prose prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {item.answer}
                      </ReactMarkdown>
                    </div>
                    {item.charts.length > 0 && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                        {item.charts.map((chart, chartIndex) => (
                          <img
                            key={chartIndex}
                            src={`${API_URL}/${chart}`}
                            alt={`Follow-up chart ${chartIndex + 1}`}
                            className="w-full bg-zinc-900 rounded-lg border border-zinc-800"
                          />
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </main>
  );
}