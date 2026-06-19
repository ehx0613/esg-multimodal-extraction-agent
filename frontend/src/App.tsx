import { ChangeEvent, DragEvent, FormEvent, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertCircle,
  ArrowUpRight,
  CheckCircle2,
  ClipboardCheck,
  Database,
  FileSearch,
  FileText,
  Loader2,
  RefreshCw,
  UploadCloud,
} from "lucide-react";
import "./styles.css";

const API_BASE = "http://127.0.0.1:8000";

type UploadResult = {
  report: {
    id: string;
    file_name: string;
    company_name?: string | null;
    report_year?: number | null;
    industry?: string | null;
  };
  task: {
    id: string;
    status: string;
    retrieval_profile: string;
  };
  report_dir: string;
  raw_pdf_path: string;
  next: {
    trace_url: string;
  };
};

type TaskOverview = {
  task: {
    id: string;
    status: string;
    industry?: string | null;
    retrieval_profile: string;
  };
  report?: {
    id: string;
    file_name: string;
    company_name?: string | null;
    report_year?: number | null;
  } | null;
  progress: {
    status: string;
    stage: string;
    progress: number;
    message?: string;
    error_message?: string | null;
  };
  timeline: Array<{
    stage: string;
    status: string;
    progress: number;
    message?: string;
    error_message?: string | null;
    created_at?: string;
  }>;
  field_summary: {
    field_count: number;
    extracted_count: number;
    missing_count: number;
    needs_review_count: number;
    auto_cited_count: number;
    auto_cited_rate: number;
    by_category: Record<string, { field_count: number; extracted_count: number; needs_review_count: number }>;
  };
  rating_summary?: {
    overall_score: number;
    overall_rating: string;
    needs_review_count: number;
  } | null;
  urls: Record<string, string>;
};

type FieldResult = {
  field_key: string;
  field_name_cn: string;
  category: string;
  status: string;
  value?: string | number | boolean | null;
  unit?: string | null;
  year?: string | number | null;
  confidence?: number | null;
  source_route?: string | null;
  page_number?: string | number | null;
  chunk_id?: string | null;
  evidence_text?: string;
  review_status: string;
  review_reasons?: string[];
};

type FieldResultsResponse = {
  summary: TaskOverview["field_summary"];
  items: FieldResult[];
};

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [companyName, setCompanyName] = useState("");
  const [reportYear, setReportYear] = useState("2024");
  const [industry, setIndustry] = useState("manufacturing");
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [upload, setUpload] = useState<UploadResult | null>(null);
  const [overview, setOverview] = useState<TaskOverview | null>(null);
  const [fields, setFields] = useState<FieldResult[]>([]);
  const [error, setError] = useState("");
  const [activeFilter, setActiveFilter] = useState("all");

  const fileSize = useMemo(() => {
    if (!file) return "";
    return `${(file.size / 1024 / 1024).toFixed(2)} MB`;
  }, [file]);

  const taskId = upload?.task.id || overview?.task.id || "";
  const reportDir = upload?.report_dir || "";

  const filteredFields = useMemo(() => {
    if (activeFilter === "all") return fields;
    if (activeFilter === "review") return fields.filter((item) => item.review_status === "needs_review");
    return fields.filter((item) => item.category === activeFilter);
  }, [activeFilter, fields]);

  useEffect(() => {
    if (!taskId || !isAnalyzing) return;
    const timer = window.setInterval(() => {
      void refreshTask(false);
    }, 1800);
    return () => window.clearInterval(timer);
  }, [isAnalyzing, taskId]);

  function acceptFile(nextFile?: File) {
    if (!nextFile) return;
    setError("");
    if (nextFile.type !== "application/pdf" && !nextFile.name.toLowerCase().endsWith(".pdf")) {
      setFile(null);
      setError("请选择 PDF 格式的 ESG 报告。");
      return;
    }
    setFile(nextFile);
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    acceptFile(event.target.files?.[0]);
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
    acceptFile(event.dataTransfer.files?.[0]);
  }

  async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
    const response = await fetch(url, init);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "请求失败");
    }
    return payload;
  }

  async function uploadReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("请先选择一份 PDF 报告。");
      return;
    }

    setIsUploading(true);
    setError("");
    setUpload(null);
    setOverview(null);
    setFields([]);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("company_name", companyName);
    formData.append("report_year", reportYear);
    formData.append("industry", industry);
    formData.append("retrieval_profile", "baseline");

    try {
      const payload = await readJson<UploadResult>(`${API_BASE}/reports/upload`, {
        method: "POST",
        body: formData,
      });
      setUpload(payload);
      await refreshTask(false, payload.task.id, payload.report_dir);
      await runAnalysis(payload);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "上传失败");
    } finally {
      setIsUploading(false);
    }
  }

  async function analyzeReport() {
    if (!upload) return;
    await runAnalysis(upload);
  }

  async function runAnalysis(target: UploadResult) {
    setIsAnalyzing(true);
    setError("");

    try {
      await readJson(`${API_BASE}/runs/analyze-uploaded-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          report_dir: target.report_dir,
          pdf_path: target.raw_pdf_path,
          task_id: target.task.id,
          industry: target.report.industry,
          run_mode: "balanced",
        }),
      });
      await refreshTask(false, target.task.id, target.report_dir);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "分析失败");
      await refreshTask(false);
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function refreshTask(showSpinner = true, nextTaskId = taskId, nextReportDir = reportDir) {
    if (!nextTaskId) return;
    if (showSpinner) setIsRefreshing(true);
    try {
      const nextOverview = await readJson<TaskOverview>(`${API_BASE}/tasks/${nextTaskId}/overview`);
      setOverview(nextOverview);
      const fieldsUrl =
        nextOverview.urls.report_fields ||
        (nextReportDir ? `/reports/fields?report_dir=${encodeURIComponent(nextReportDir)}` : "");
      if (fieldsUrl) {
        const normalizedUrl = fieldsUrl.startsWith("http") ? fieldsUrl : `${API_BASE}${fieldsUrl}`;
        const nextFields = await readJson<FieldResultsResponse>(normalizedUrl);
        setFields(nextFields.items);
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "刷新任务失败");
    } finally {
      if (showSpinner) setIsRefreshing(false);
    }
  }

  const progress = overview?.progress;
  const summary = overview?.field_summary;
  const urls = overview?.urls || {};

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark">
            <Activity size={22} />
          </div>
          <div>
            <h1>ESG 抽取工作台</h1>
            <p>上传、追踪、复核、导出</p>
          </div>
        </div>
        <nav className="nav">
          <span className="navItem active">
            <UploadCloud size={18} />
            报告上传
          </span>
          <span className="navItem">
            <Activity size={18} />
            运行进度
          </span>
          <span className="navItem">
            <Database size={18} />
            字段结果
          </span>
          <span className="navItem">
            <ClipboardCheck size={18} />
            人工复核
          </span>
        </nav>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <h2>报告处理</h2>
            <p>围绕统一抽取流水线展示任务状态、60 字段结果、证据和复核入口。</p>
          </div>
          <div className="topActions">
            <button className="iconButton" type="button" onClick={() => refreshTask()} disabled={!taskId || isRefreshing}>
              {isRefreshing ? <Loader2 className="spin" size={17} /> : <RefreshCw size={17} />}
              刷新
            </button>
            <a className="ghostLink" href={API_BASE} target="_blank" rel="noreferrer">
              后端
              <ArrowUpRight size={16} />
            </a>
          </div>
        </header>

        <section className="workGrid">
          <form className="panel uploadPanel" onSubmit={uploadReport}>
            <div className="panelTitle">
              <FileText size={18} />
              <h3>上传报告</h3>
            </div>
            <label
              className={`dropzone ${isDragging ? "dragging" : ""} ${file ? "hasFile" : ""}`}
              onDragEnter={() => setIsDragging(true)}
              onDragLeave={() => setIsDragging(false)}
              onDragOver={(event) => event.preventDefault()}
              onDrop={onDrop}
            >
              <input type="file" accept="application/pdf,.pdf" onChange={onFileChange} />
              <UploadCloud size={30} />
              <strong>{file ? file.name : "选择或拖入 PDF"}</strong>
              <span>{file ? fileSize : "ESG、CSR、可持续发展报告"}</span>
            </label>

            <div className="field">
              <label>公司名称</label>
              <input value={companyName} onChange={(event) => setCompanyName(event.target.value)} placeholder="例如 新华医疗" />
            </div>
            <div className="fieldRow">
              <div className="field">
                <label>报告年份</label>
                <input value={reportYear} onChange={(event) => setReportYear(event.target.value)} inputMode="numeric" />
              </div>
              <div className="field">
                <label>行业</label>
                <select value={industry} onChange={(event) => setIndustry(event.target.value)}>
                  <option value="manufacturing">制造业</option>
                  <option value="pharma">医药</option>
                  <option value="finance">金融</option>
                  <option value="">暂不指定</option>
                </select>
              </div>
            </div>
            <button className="primaryButton" type="submit" disabled={isUploading}>
              {isUploading ? <Loader2 className="spin" size={18} /> : <UploadCloud size={18} />}
              {isUploading ? "上传并启动分析中" : "上传并自动分析"}
            </button>
          </form>

          <section className="panel progressPanel">
            <div className="panelTitle">
              <Activity size={18} />
              <h3>任务进度</h3>
            </div>
            <div className="progressHeader">
              <div>
                <span className={`statusPill ${progress?.status || "pending"}`}>{progress?.status || "未开始"}</span>
                <strong>{stageName(progress?.stage)}</strong>
                <p>{progress?.message || "上传报告后，这里会显示流水线进度。"}</p>
              </div>
              <b>{progress?.progress ?? 0}%</b>
            </div>
            <div className="progressBar">
              <span style={{ width: `${progress?.progress ?? 0}%` }} />
            </div>
            {progress?.error_message && (
              <div className="errorBox">
                <AlertCircle size={16} />
                {progress.error_message}
              </div>
            )}
            <ol className="timeline">
              {(overview?.timeline || []).map((item, index) => (
                <li key={`${item.stage}-${index}`}>
                  <CheckCircle2 size={16} />
                  <div>
                    <strong>{stageName(item.stage)}</strong>
                    <span>{item.message || item.status}</span>
                  </div>
                </li>
              ))}
            </ol>
            <div className="actions">
              <button className="secondaryButton" type="button" onClick={analyzeReport} disabled={!upload || isAnalyzing}>
                {isAnalyzing ? <Loader2 className="spin" size={18} /> : <FileSearch size={18} />}
                {isAnalyzing ? "分析中" : "重新分析"}
              </button>
              {urls.review && (
                <a href={`${API_BASE}${urls.review}`} target="_blank" rel="noreferrer">
                  <ClipboardCheck size={16} />
                  复核
                </a>
              )}
              {urls.dashboard && (
                <a href={`${API_BASE}${urls.dashboard}`} target="_blank" rel="noreferrer">
                  Dashboard
                </a>
              )}
            </div>
          </section>
        </section>

        {error && (
          <div className="errorBox pageError">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        <section className="metricsGrid">
          <Metric label="字段总数" value={summary?.field_count ?? 0} />
          <Metric label="已抽取" value={summary?.extracted_count ?? 0} />
          <Metric label="待复核" value={summary?.needs_review_count ?? 0} />
          <Metric label="模拟评级" value={overview?.rating_summary?.overall_rating || "-"} />
        </section>

        <section className="panel resultsPanel">
          <div className="resultsHeader">
            <div className="panelTitle">
              <Database size={18} />
              <h3>字段结果</h3>
            </div>
            <div className="filters">
              {["all", "E", "S", "G", "review"].map((filter) => (
                <button
                  className={activeFilter === filter ? "active" : ""}
                  key={filter}
                  type="button"
                  onClick={() => setActiveFilter(filter)}
                >
                  {filterLabel(filter)}
                </button>
              ))}
            </div>
          </div>
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>字段</th>
                  <th>分类</th>
                  <th>值</th>
                  <th>证据</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                {filteredFields.length ? (
                  filteredFields.map((item) => (
                    <tr key={item.field_key}>
                      <td>
                        <strong>{item.field_name_cn || item.field_key}</strong>
                        <span>{item.field_key}</span>
                      </td>
                      <td>{item.category || "-"}</td>
                      <td>
                        <strong>{formatValue(item)}</strong>
                        <span>{item.source_route || "-"}</span>
                      </td>
                      <td>
                        <strong>{item.page_number ? `第 ${item.page_number} 页` : "-"}</strong>
                        <span>{item.evidence_text || item.chunk_id || "-"}</span>
                      </td>
                      <td>
                        <span className={`reviewPill ${item.review_status}`}>{reviewStatus(item.review_status)}</span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="emptyState" colSpan={5}>
                      任务完成后会在这里显示字段结果。
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function stageName(stage?: string) {
  const names: Record<string, string> = {
    uploaded: "已上传",
    unified_pipeline: "统一抽取流水线",
    document_parsing: "MinerU / PyMuPDF 文档解析",
    ingesting: "MinerU / PyMuPDF 文档解析",
    route_a: "路线 A：绩效表格与定量指标",
    route_b: "路线 B：共享 Hybrid RAG",
    fusion: "证据仲裁与保守融合",
    merged_results: "合并后的 60 字段结果",
    citations: "字段引用",
    rating: "模拟评级",
    review_ready: "人工复核",
    failed: "运行失败",
  };
  return names[stage || ""] || "未开始";
}

function filterLabel(filter: string) {
  if (filter === "all") return "全部";
  if (filter === "review") return "待复核";
  return filter;
}

function reviewStatus(status: string) {
  const names: Record<string, string> = {
    auto_cited: "自动通过",
    reviewed_approved: "人工通过",
    reviewed_rejected: "已拒绝",
    needs_review: "待复核",
    not_reviewed: "未复核",
  };
  return names[status] || status || "-";
}

function formatValue(item: FieldResult) {
  if (item.value === null || item.value === undefined || item.value === "") return "-";
  const unit = item.unit ? ` ${item.unit}` : "";
  const year = item.year ? ` (${item.year})` : "";
  return `${String(item.value)}${unit}${year}`;
}

export default App;
