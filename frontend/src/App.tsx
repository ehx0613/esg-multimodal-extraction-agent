import { ChangeEvent, DragEvent, FormEvent, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  Database,
  FileText,
  Loader2,
  UploadCloud,
} from "lucide-react";
import "./styles.css";

type UploadResult = {
  report: {
    id: string;
    file_name: string;
    file_path: string;
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
    run_url: string;
    trace_url: string;
  };
};

type AnalyzeResult = {
  status: string;
  dashboard_url: string;
  review_url?: string;
  route_a?: {
    raw_row_count?: number | null;
    extracted_count?: number | null;
  };
  route_b?: {
    target_fields?: number;
    matched_fields?: number;
    llm_calls?: number;
  };
  route_b2?: {
    target_fields?: number;
    matched_fields?: number;
    llm_calls?: number;
    industry?: string;
  };
  artifacts?: {
    citations?: {
      field_count: number;
      needs_review_count: number;
    };
    rating?: {
      score: number;
      rating: string;
      needs_review_count: number;
    };
  };
};

const API_BASE = "http://127.0.0.1:8000";

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [companyName, setCompanyName] = useState("");
  const [reportYear, setReportYear] = useState("2024");
  const [industry, setIndustry] = useState("manufacturing");
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState("");

  const fileSize = useMemo(() => {
    if (!file) return "";
    return `${(file.size / 1024 / 1024).toFixed(2)} MB`;
  }, [file]);

  const reviewUrl = useMemo(() => {
    if (!result) return "";
    const params = new URLSearchParams({ report_dir: result.report_dir });
    const reviewIndustry = result.report.industry || industry;
    if (reviewIndustry) params.set("industry", reviewIndustry);
    return `${API_BASE}/review?${params.toString()}`;
  }, [industry, result]);

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

  async function uploadReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("先拖入或选择一份 PDF 报告。");
      return;
    }

    setIsUploading(true);
    setError("");
    setResult(null);
    setAnalysis(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("company_name", companyName);
    formData.append("report_year", reportYear);
    formData.append("industry", industry);
    formData.append("retrieval_profile", "baseline");

    try {
      const response = await fetch(`${API_BASE}/reports/upload`, {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "上传失败");
      }
      setResult(payload);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "上传失败");
    } finally {
      setIsUploading(false);
    }
  }

  async function analyzeReport() {
    if (!result) return;
    setIsAnalyzing(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/runs/analyze-uploaded-report`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          report_dir: result.report_dir,
          pdf_path: result.raw_pdf_path,
          task_id: result.task.id,
          industry: result.report.industry,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "分析失败");
      }
      setAnalysis(payload);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "分析失败");
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <main className="shell">
      <section className="workspace">
        <aside className="sidebar">
          <div className="brand">
            <div className="brandMark">
              <Activity size={22} />
            </div>
            <div>
              <h1>ESG 报告分析</h1>
              <p>上传、入库、追踪分析任务</p>
            </div>
          </div>

          <nav className="nav">
            <span className="navItem active">
              <UploadCloud size={18} />
              报告上传
            </span>
            <span className="navItem">
              <Database size={18} />
              数据入库
            </span>
            <span className="navItem">
              <FileText size={18} />
              分析结果
            </span>
          </nav>
        </aside>

        <section className="content">
          <header className="topbar">
            <div>
              <h2>拖入一份 ESG 报告</h2>
              <p>当前原型会保存 PDF、创建报告记录和待处理任务。</p>
            </div>
            <a className="ghostLink" href="http://127.0.0.1:8000" target="_blank" rel="noreferrer">
              后端首页
              <ArrowRight size={16} />
            </a>
          </header>

          <form className="uploadGrid" onSubmit={uploadReport}>
            <label
              className={`dropzone ${isDragging ? "dragging" : ""} ${file ? "hasFile" : ""}`}
              onDragEnter={() => setIsDragging(true)}
              onDragLeave={() => setIsDragging(false)}
              onDragOver={(event) => event.preventDefault()}
              onDrop={onDrop}
            >
              <input type="file" accept="application/pdf,.pdf" onChange={onFileChange} />
              <div className="uploadIcon">
                <UploadCloud size={34} />
              </div>
              <strong>{file ? file.name : "拖入 PDF 或点击选择文件"}</strong>
              <span>{file ? fileSize : "支持 ESG、CSR、可持续发展报告 PDF"}</span>
            </label>

            <div className="settingsPanel">
              <div className="field">
                <label>公司名称</label>
                <input
                  value={companyName}
                  onChange={(event) => setCompanyName(event.target.value)}
                  placeholder="例如 新华医疗"
                />
              </div>
              <div className="fieldRow">
                <div className="field">
                  <label>报告年份</label>
                  <input
                    value={reportYear}
                    onChange={(event) => setReportYear(event.target.value)}
                    inputMode="numeric"
                  />
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
                {isUploading ? "上传中" : "上传并创建任务"}
              </button>
              {error && <div className="errorBox">{error}</div>}
            </div>
          </form>

          {result && (
            <section className="resultPanel">
              <div className="resultHeader">
                <CheckCircle2 size={22} />
                <div>
                  <h3>报告已保存到数据库</h3>
                  <p>后端已经创建 report 和 task 记录，可以继续接入分析流程。</p>
                </div>
              </div>
              <div className="resultGrid">
                <div>
                  <span>Report ID</span>
                  <strong>{result.report.id}</strong>
                </div>
                <div>
                  <span>Task ID</span>
                  <strong>{result.task.id}</strong>
                </div>
                <div>
                  <span>任务状态</span>
                  <strong>{result.task.status}</strong>
                </div>
                <div>
                  <span>报告目录</span>
                  <strong>{result.report_dir}</strong>
                </div>
              </div>
              <div className="actions">
                <button className="secondaryButton" type="button" onClick={analyzeReport} disabled={isAnalyzing}>
                  {isAnalyzing ? <Loader2 className="spin" size={18} /> : <Activity size={18} />}
                  {isAnalyzing ? "分析中" : "开始分析"}
                </button>
                <a href={`http://127.0.0.1:8000${result.next.trace_url}`} target="_blank" rel="noreferrer">
                  查看 Trace
                </a>
                <a href={reviewUrl} target="_blank" rel="noreferrer">
                  <ClipboardCheck size={16} />
                  人工审核
                </a>
                <a
                  href={`http://127.0.0.1:8000/dashboard?report_dir=${encodeURIComponent(result.report_dir)}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  打开 Dashboard
                </a>
              </div>
            </section>
          )}

          {analysis && (
            <section className="resultPanel">
              <div className="resultHeader">
                <CheckCircle2 size={22} />
                <div>
                  <h3>分析完成</h3>
                  <p>已经生成抽取结果、证据引用和模拟评级。</p>
                </div>
              </div>
              <div className="resultGrid">
                <div>
                  <span>抽取字段</span>
                  <strong>{analysis.route_a?.extracted_count ?? "-"}</strong>
                </div>
                <div>
                  <span>正文定性匹配</span>
                  <strong>
                    {analysis.route_b?.matched_fields ?? "-"}/{analysis.route_b?.target_fields ?? "-"}
                  </strong>
                </div>
                <div>
                  <span>正文定量匹配</span>
                  <strong>
                    {analysis.route_b2?.matched_fields ?? "-"}/{analysis.route_b2?.target_fields ?? "-"}
                  </strong>
                </div>
                <div>
                  <span>证据字段</span>
                  <strong>{analysis.artifacts?.citations?.field_count ?? "-"}</strong>
                </div>
                <div>
                  <span>模拟评分</span>
                  <strong>{analysis.artifacts?.rating?.score ?? "-"}</strong>
                </div>
                <div>
                  <span>评级</span>
                  <strong>{analysis.artifacts?.rating?.rating ?? "-"}</strong>
                </div>
              </div>
              <div className="actions">
                <a
                  href={analysis.review_url ? `${API_BASE}${analysis.review_url}` : reviewUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  <ClipboardCheck size={16} />
                  人工审核
                </a>
                <a
                  href={`http://127.0.0.1:8000${analysis.dashboard_url}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  查看分析结果
                </a>
              </div>
            </section>
          )}
        </section>
      </section>
    </main>
  );
}

export default App;
