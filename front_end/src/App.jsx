import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  Building2,
  CheckCircle2,
  CircleAlert,
  Database,
  Home,
  LoaderCircle,
  Play,
  RefreshCw,
  RotateCcw,
  Send,
  Upload,
} from "lucide-react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const modelOptions = [
  { key: "xgboost", label: "XGBoost" },
  { key: "lightgbm", label: "LightGBM" },
  { key: "catboost", label: "CatBoost" },
  { key: "random_forest", label: "Random Forest" },
  { key: "ridge", label: "Ridge" },
  { key: "lasso", label: "Lasso" },
  { key: "svr", label: "SVM" },
  { key: "mlp", label: "Rede neural" },
];

const propertyTypeOptions = [
  { value: "apartamento_padrao", label: "Apartamento", icon: Building2 },
  { value: "casa_padrao", label: "Casa", icon: Home },
];

const fortalezaNeighborhoodOptions = [
  "Aldeota",
  "Meireles",
  "Coco",
  "Guararapes",
  "Papicu",
  "Mucuripe",
  "Varjota",
  "Dionisio Torres",
  "Fatima",
  "Cambeba",
  "Praia de Iracema",
  "Engenheiro Luciano Cavalcante",
  "Centro",
  "Benfica",
  "Messejana",
  "Parangaba",
];

const amenityFields = [
  { key: "portaria", label: "Portaria" },
  { key: "vista_mar", label: "Vista mar" },
  { key: "condominio_fechado", label: "Condominio fechado" },
  { key: "piscina", label: "Piscina" },
  { key: "deck", label: "Deck" },
  { key: "varanda_gourmet", label: "Varanda gourmet" },
  { key: "varanda", label: "Varanda" },
  { key: "academia", label: "Academia" },
  { key: "salao_festa", label: "Salao de festa" },
  { key: "salao_jogos", label: "Salao de jogos" },
  { key: "quadra_campo", label: "Quadra ou campo" },
];

const tabItems = [
  { id: "predicao", label: "Predicao", icon: Building2 },
  { id: "dados", label: "Dados", icon: Database },
  { id: "modelo", label: "Modelos", icon: BarChart3 },
];

const initialForm = {
  bairro: "Aldeota",
  area_m2: 85,
  quartos: 3,
  banheiros: 2,
  suites: 1,
  andar: 5,
  vagas: 2,
  tipo_imovel_padronizado: "apartamento_padrao",
  portaria: true,
  vista_mar: false,
  condominio_fechado: true,
  piscina: true,
  deck: false,
  varanda_gourmet: true,
  varanda: true,
  academia: true,
  salao_festa: true,
  salao_jogos: false,
  quadra_campo: false,
};

function buildApiUrl(pathname) {
  return `${API_BASE_URL}${pathname}`;
}

function formatCurrency(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

function formatNumber(value) {
  return new Intl.NumberFormat("pt-BR").format(Number(value || 0));
}

function formatPercent(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "percent",
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(Number(value || 0));
}

function formatDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function normalizeArrayJson(value) {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  return [];
}

function StatPill({ icon: Icon, label, value, tone = "neutral" }) {
  return (
    <div className={`stat-pill stat-pill--${tone}`}>
      <span className="stat-pill__icon">
        <Icon size={16} />
      </span>
      <span className="stat-pill__label">{label}</span>
      <strong className="stat-pill__value">{value}</strong>
    </div>
  );
}

function SectionHeader({ eyebrow, title, description }) {
  return (
    <div className="section-header">
      <span className="section-header__eyebrow">{eyebrow}</span>
      <h2>{title}</h2>
      <p>{description}</p>
    </div>
  );
}

async function apiJson(pathname, options = {}) {
  const response = await fetch(buildApiUrl(pathname), options);
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Falha na comunicacao com a API.");
  }
  return payload;
}

function PredictionView({ form, setForm }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  function handleFormChange(event) {
    const { name, value, type } = event.target;
    setForm((current) => ({ ...current, [name]: type === "number" ? Number(value) : value }));
  }

  async function handlePredict(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      setResult(
        await apiJson("/predict", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        }),
      );
    } catch (err) {
      setResult(null);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="view-grid">
      <div className="surface surface--form">
        <SectionHeader
          eyebrow="Modelo ativo"
          title="Predicao de preco"
          description="Preencha os atributos do imovel e consulte a estimativa usando o modelo ativo em producao."
        />
        <form className="property-form" onSubmit={handlePredict}>
          <label>
            <span>Bairro</span>
            <select name="bairro" value={form.bairro} onChange={handleFormChange} required>
              {fortalezaNeighborhoodOptions.map((neighborhood) => (
                <option key={neighborhood} value={neighborhood}>
                  {neighborhood}
                </option>
              ))}
            </select>
          </label>

          <div className="field-grid">
            <label>
              <span>Area (m2)</span>
              <input name="area_m2" type="number" min="1" value={form.area_m2} onChange={handleFormChange} required />
            </label>
            <div className="type-field">
              <span>Tipo</span>
              <div className="type-segment" role="radiogroup" aria-label="Tipo do imovel">
                {propertyTypeOptions.map((option) => {
                  const Icon = option.icon;
                  const active = form.tipo_imovel_padronizado === option.value;
                  return (
                    <button
                      key={option.value}
                      className={`type-option ${active ? "type-option--active" : ""}`}
                      type="button"
                      onClick={() => setForm((current) => ({ ...current, tipo_imovel_padronizado: option.value }))}
                    >
                      <Icon size={16} />
                      <span>{option.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
            {["quartos", "banheiros", "suites", "andar", "vagas"].map((field) => (
              <label key={field}>
                <span>{field}</span>
                <input name={field} type="number" min="0" value={form[field]} onChange={handleFormChange} required />
              </label>
            ))}
          </div>

          <div className="amenity-grid">
            {amenityFields.map((field) => (
              <label key={field.key} className={`switch ${form[field.key] ? "switch--active" : ""}`}>
                <input
                  type="checkbox"
                  checked={form[field.key]}
                  onChange={() => setForm((current) => ({ ...current, [field.key]: !current[field.key] }))}
                />
                <span>{field.label}</span>
              </label>
            ))}
          </div>

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? <LoaderCircle className="spin" size={18} /> : <Send size={18} />}
            <span>{loading ? "Consultando" : "Predizer preco"}</span>
          </button>
        </form>
      </div>

      <div className="surface surface--result">
        <SectionHeader
          eyebrow="Resultado"
          title="Estimativa e explicacao"
          description="Veja o valor estimado e os fatores que o modelo ativo destacou para esta entrada."
        />
        {result ? (
          <>
            <div className="price-highlight">
              <span>Preco estimado</span>
              <strong>{formatCurrency(result.preco_estimado)}</strong>
              <small>
                {result.tipo_imovel_padronizado} em {result.bairro}
              </small>
            </div>
            <div className="list-stack">
              {(result.explicacao || []).map((item, index) => (
                <div className="info-row" key={`${item.feature}-${index}`}>
                  <strong>{item.feature}</strong>
                  <span>{String(item.valor ?? "-")}</span>
                  <small>{item.descricao}</small>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="empty-state">
            <Building2 size={28} />
            <p>Envie uma simulacao para visualizar a estimativa.</p>
          </div>
        )}
        {error ? <Feedback message={error} /> : null}
      </div>
    </section>
  );
}

function Feedback({ message }) {
  return (
    <div className="feedback feedback--error">
      <CircleAlert size={18} />
      <span>{message}</span>
    </div>
  );
}

function DataView() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [ingestions, setIngestions] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  async function refreshData() {
    const [dataStatus, history] = await Promise.all([apiJson("/data/status"), apiJson("/data/ingestions")]);
    setStatus(dataStatus);
    setIngestions(history.ingestions || []);
  }

  useEffect(() => {
    refreshData().catch((err) => setError(err.message));
  }, []);

  async function handleUpload() {
    if (!selectedFile) return;
    setUploading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      await apiJson("/insertData", { method: "POST", body: formData });
      setSelectedFile(null);
      await refreshData();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleRollback(idLote) {
    if (!window.confirm("Desativar este lote e remover seus registros das consultas ativas?")) return;
    try {
      await apiJson(`/data/ingestions/${idLote}/rollback`, { method: "POST" });
      await refreshData();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="view-grid view-grid--data">
      <div className="surface surface--form">
        <SectionHeader
          eyebrow="Estado da base"
          title="Dados ativos"
          description="Resumo dos registros tratados atualmente disponiveis para treinamento e predicao operacional."
        />
        <div className="metrics-grid">
          <StatPill icon={Database} label="Imoveis ativos" value={formatNumber(status?.total_imoveis_ativos)} tone="success" />
          <StatPill icon={Activity} label="Preco medio" value={formatCurrency(status?.preco_medio_geral)} />
          <StatPill icon={Activity} label="Preco/m2 medio" value={formatCurrency(status?.preco_m2_medio)} />
          <StatPill icon={RefreshCw} label="Ultimo upload" value={formatDate(status?.ultima_atualizacao)} />
        </div>

        <div className="upload-box">
          <Upload size={28} />
          <strong>{selectedFile ? selectedFile.name : "Selecione um CSV bruto"}</strong>
          <label className="secondary-button" htmlFor="csv-upload">
            <Upload size={18} />
            <span>Escolher arquivo</span>
          </label>
          <input id="csv-upload" type="file" accept=".csv,text/csv" onChange={(event) => setSelectedFile(event.target.files?.[0] || null)} hidden />
        </div>
        <button className="primary-button" type="button" onClick={handleUpload} disabled={!selectedFile || uploading}>
          {uploading ? <LoaderCircle className="spin" size={18} /> : <Database size={18} />}
          <span>{uploading ? "Enviando" : "Enviar dados"}</span>
        </button>
        {error ? <Feedback message={error} /> : null}
      </div>

      <div className="surface surface--result">
        <SectionHeader
          eyebrow="Historico"
          title="Lotes de ingestao"
          description="Acompanhe uploads, linhas tratadas e desative lotes problemáticos sem apagar registros."
        />
        <div className="mini-grid">
          {(status?.distribuicao_tipos || []).map((item) => (
            <div className="info-row" key={item.tipo || "sem_tipo"}>
              <strong>{item.tipo || "sem tipo"}</strong>
              <span>{formatNumber(item.total)}</span>
            </div>
          ))}
        </div>
        <Table
          columns={["Arquivo", "Status", "Salvas", "Upload", "Acoes"]}
          rows={ingestions.map((row) => [
            row.nome_arquivo,
            row.status,
            formatNumber(row.linhas_salvas),
            formatDate(row.data_upload),
            row.status !== "desativado" ? (
              <button className="icon-button" type="button" onClick={() => handleRollback(row.id_lote)} title="Desfazer ingestao">
                <RotateCcw size={16} />
              </button>
            ) : (
              "-"
            ),
          ])}
        />
      </div>
    </section>
  );
}

function ModelView() {
  const [selectedModels, setSelectedModels] = useState(["xgboost", "lightgbm", "random_forest", "ridge"]);
  const [searchType, setSearchType] = useState("bayesiana");
  const [nTrials, setNTrials] = useState(10);
  const [gridJson, setGridJson] = useState("{}");
  const [activeModel, setActiveModel] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [experiments, setExperiments] = useState([]);
  const [drift, setDrift] = useState(null);
  const [currentExperiment, setCurrentExperiment] = useState(null);
  const [logs, setLogs] = useState([]);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState("");

  const activeImportance = useMemo(() => normalizeArrayJson(activeModel?.feature_importance), [activeModel]);

  async function refreshModels() {
    const [active, board, history, driftState] = await Promise.all([
      apiJson("/models/active"),
      apiJson("/models/leaderboard"),
      apiJson("/models/history"),
      apiJson("/model-health/drift"),
    ]);
    setActiveModel(active.modelo_ativo);
    setLeaderboard(board.modelos || []);
    setExperiments(history.experimentos || []);
    setDrift(driftState);
  }

  useEffect(() => {
    refreshModels().catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!currentExperiment || !["pendente", "executando"].includes(currentExperiment.status)) return undefined;
    const interval = window.setInterval(async () => {
      try {
        const [status, logPayload] = await Promise.all([
          apiJson(`/training/${currentExperiment.id_experimento}`),
          apiJson(`/training/${currentExperiment.id_experimento}/logs`),
        ]);
        setCurrentExperiment(status);
        setLogs(logPayload.logs || []);
        if (!["pendente", "executando"].includes(status.status)) {
          setTraining(false);
          refreshModels();
        }
      } catch (err) {
        setError(err.message);
      }
    }, 2500);
    return () => window.clearInterval(interval);
  }, [currentExperiment]);

  async function handleTrain() {
    setError("");
    let paramGrids = {};
    try {
      paramGrids = JSON.parse(gridJson || "{}");
    } catch {
      setError("JSON de hiperparametros invalido.");
      return;
    }
    setTraining(true);
    try {
      const payload = await apiJson("/trainModels", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          modelos: selectedModels,
          tipo_busca: searchType,
          n_trials: Number(nTrials),
          param_grids: paramGrids,
        }),
      });
      setCurrentExperiment({ id_experimento: payload.id_experimento, status: payload.status });
      setLogs([]);
    } catch (err) {
      setTraining(false);
      setError(err.message);
    }
  }

  async function handleActivate(idModel) {
    try {
      await apiJson(`/models/${idModel}/activate`, { method: "POST" });
      await refreshModels();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="view-grid view-grid--model">
      <div className="surface surface--form">
        <SectionHeader
          eyebrow="Governanca do modelo"
          title="Treinamento e modelo ativo"
          description="Configure novos experimentos, acompanhe logs e volte para modelos anteriores quando necessario."
        />
        <div className="metrics-grid">
          <StatPill icon={CheckCircle2} label="Modelo ativo" value={activeModel?.algoritmo || "Nenhum"} tone={activeModel ? "success" : "error"} />
          <StatPill icon={Activity} label="Drift" value={drift?.status || "-"} tone={drift?.status === "verde" ? "success" : "error"} />
          <StatPill icon={BarChart3} label="RMSE ativo" value={activeModel?.rmse ? Number(activeModel.rmse).toFixed(2) : "-"} />
        </div>
        <div className="metric-note">
          <strong>Drift:</strong> {drift?.motivo || "Aguardando avaliacao do modelo ativo."}
          <span>
            Variacao preco medio: {formatPercent(drift?.variacao_preco_medio)} | Amostras recentes:{" "}
            {formatNumber(drift?.amostras_recentes)} | Base: {formatCurrency(drift?.preco_base)} | Recente:{" "}
            {formatCurrency(drift?.preco_recente)}
          </span>
        </div>

        <div className="config-panel">
          <h3>Novo treinamento</h3>
          <div className="checkbox-grid">
            {modelOptions.map((model) => (
              <label key={model.key} className={`switch ${selectedModels.includes(model.key) ? "switch--active" : ""}`}>
                <input
                  type="checkbox"
                  checked={selectedModels.includes(model.key)}
                  onChange={() =>
                    setSelectedModels((current) =>
                      current.includes(model.key) ? current.filter((item) => item !== model.key) : [...current, model.key],
                    )
                  }
                />
                <span>{model.label}</span>
              </label>
            ))}
          </div>
          <div className="field-grid">
            <label>
              <span>Busca</span>
              <select value={searchType} onChange={(event) => setSearchType(event.target.value)}>
                <option value="bayesiana">Bayesiana</option>
                <option value="grid">Grid manual</option>
              </select>
            </label>
            <label>
              <span>Tentativas</span>
              <input type="number" min="1" max="200" value={nTrials} onChange={(event) => setNTrials(event.target.value)} />
            </label>
          </div>
          <label className="json-editor">
            <span>Param grids JSON</span>
            <textarea value={gridJson} onChange={(event) => setGridJson(event.target.value)} rows={6} />
          </label>
          <button className="primary-button" type="button" onClick={handleTrain} disabled={training || selectedModels.length === 0}>
            {training ? <LoaderCircle className="spin" size={18} /> : <Play size={18} />}
            <span>{training ? "Treinando" : "Iniciar treinamento"}</span>
          </button>
        </div>
        {error ? <Feedback message={error} /> : null}
      </div>

      <div className="surface surface--result">
        <SectionHeader
          eyebrow="Operacao"
          title="Historico, metricas e logs"
          description={drift?.motivo || "Acompanhe saude, leaderboard e detalhes do ultimo experimento."}
        />
        <Table
          columns={["Modelo", "RMSE", "MAE", "R2", "Ativo"]}
          rows={leaderboard.map((row) => [
            row.algoritmo,
            row.rmse ? Number(row.rmse).toFixed(2) : "-",
            row.mae ? Number(row.mae).toFixed(2) : "-",
            row.r2 ? Number(row.r2).toFixed(4) : "-",
            row.ativo ? "Atual" : (
              <button className="secondary-button compact-button" type="button" onClick={() => handleActivate(row.id_modelo)}>
                Ativar
              </button>
            ),
          ])}
        />

        <div className="terminal">
          {(logs.length ? logs : [{ mensagem: "Nenhum log de treinamento em andamento." }]).map((line, index) => (
            <div key={`${line.id_log || "log"}-${index}`}>[{line.nivel || "info"}] {line.mensagem}</div>
          ))}
        </div>

        <div className="mini-grid">
          {activeImportance.slice(0, 6).map((item) => (
            <div className="info-row" key={item.feature}>
              <strong>{item.feature}</strong>
              <span>{Number(item.importance || 0).toFixed(3)}</span>
            </div>
          ))}
        </div>

        <Table
          columns={["Experimento", "Status", "Amostras", "Inicio"]}
          rows={experiments.map((row) => [
            row.id_experimento,
            row.status,
            formatNumber(row.amostras_treinamento),
            formatDate(row.data_inicio),
          ])}
        />
      </div>
    </section>
  );
}

function Table({ columns, rows }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length ? (
            rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <td key={`${rowIndex}-${cellIndex}`}>{cell}</td>
                ))}
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={columns.length}>Nenhum registro encontrado.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState("predicao");
  const [form, setForm] = useState(initialForm);
  const [health, setHealth] = useState({ ok: false, label: "Verificando..." });

  useEffect(() => {
    apiJson("/health")
      .then((payload) => setHealth({ ok: payload.status === "ok", label: payload.status === "ok" ? "Online" : "Instavel" }))
      .catch(() => setHealth({ ok: false, label: "Offline" }));
  }, []);

  return (
    <div className="app-shell">
      <main className="workspace">
        <header className="workspace-header">
          <div>
            <span className="workspace-header__eyebrow">Plataforma de predicao imobiliaria</span>
            <h2>Operacao do sistema</h2>
          </div>
          <StatPill icon={health.ok ? CheckCircle2 : CircleAlert} label="API" value={health.label} tone={health.ok ? "success" : "error"} />
        </header>

        <nav className="tab-bar" aria-label="Areas da aplicacao">
          {tabItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={`tab-button ${activeTab === item.id ? "tab-button--active" : ""}`}
                type="button"
                onClick={() => setActiveTab(item.id)}
              >
                <Icon size={17} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {activeTab === "predicao" ? <PredictionView form={form} setForm={setForm} /> : null}
        {activeTab === "dados" ? <DataView /> : null}
        {activeTab === "modelo" ? <ModelView /> : null}
      </main>
    </div>
  );
}
