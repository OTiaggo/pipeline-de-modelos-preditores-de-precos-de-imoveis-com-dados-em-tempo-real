import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Building2,
  CheckCircle2,
  CircleAlert,
  Database,
  Home,
  LoaderCircle,
  RefreshCw,
  Send,
  Upload,
  Waves,
} from "lucide-react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const propertyTypeOptions = [
  { value: "apartamento_padrao", label: "Apartamento", icon: Building2 },
  { value: "casa_padrao", label: "Casa", icon: Home },
];

const neighborhoodSuggestions = [
  "Aldeota",
  "Meireles",
  "Cocó",
  "Guararapes",
  "Papicu",
  "Mucuripe",
  "Varjota",
  "Dionisio Torres",
  "Fátima",
  "Cambeba",
  "Praia de Iracema",
  "Engenheiro Luciano Cavalcante",
];

const fortalezaNeighborhoodOptions = [
  "Aerolândia",
  "Aldeota",
  "Alto da Balança",
  "Álvaro Weyne",
  "Amadeu Furtado",
  "Ancuri",
  "Antônio Bezerra",
  "Aracapé",
  "Autran Nunes",
  "Barra do Ceará",
  "Barroso",
  "Bela Vista",
  "Benfica",
  "Boa Vista/Castelão",
  "Bom Futuro",
  "Bom Jardim",
  "Bonsucesso",
  "Cais do Porto",
  "Cajazeiras",
  "Cambeba",
  "Canindezinho",
  "Carlito Pamplona",
  "Centro",
  "Cidade 2000",
  "Cidade dos Funcionários",
  "Coaçu",
  "Cocó",
  "Conjunto Ceará I",
  "Conjunto Ceará II",
  "Conjunto Esperança",
  "Conjunto Palmeiras",
  "Couto Fernandes",
  "Curió",
  "Damas",
  "De Lourdes",
  "Demócrito Rocha",
  "Dias Macedo",
  "Dionísio Torres",
  "Dom Lustosa",
  "Edson Queiroz",
  "Engenheiro Luciano Cavalcante",
  "Farias Brito",
  "Fátima",
  "Floresta",
  "Genibaú",
  "Granja Lisboa",
  "Guajeru",
  "Guararapes",
  "Henrique Jorge",
  "Itaoca",
  "Itaperi",
  "Jacarecanga",
  "Jangurussu",
  "Jardim América",
  "Jardim Cearense",
  "Jardim das Oliveiras",
  "Jardim Guanabara",
  "João XXIII",
  "Joaquim Távora",
  "Jóquei Clube",
  "José Bonifácio",
  "José de Alencar",
  "Lagoa Redonda",
  "Manoel Sátiro",
  "Manuel Dias Branco",
  "Maraponga",
  "Meireles",
  "Messejana",
  "Mondubim",
  "Monte Castelo",
  "Montese",
  "Mucuripe",
  "Novo Mondubim",
  "Olavo Oliveira",
  "Padre Andrade",
  "Panamericano",
  "Papicu",
  "Parangaba",
  "Parque Araxá",
  "Parque Dois Irmãos",
  "Parque Iracema",
  "Parque Manibura",
  "Parque Presidente Vargas",
  "Parque Santa Maria",
  "Parque Santa Rosa",
  "Parque São José",
  "Parquelândia",
  "Parreão",
  "Passaré",
  "Paupina",
  "Pedras",
  "Pici",
  "Planalto Ayrton Senna",
  "Praia de Iracema",
  "Praia do Futuro I",
  "Praia do Futuro II",
  "Prefeito José Walter",
  "Presidente Kennedy",
  "Quintino Cunha",
  "Rachel de Queiroz",
  "Rodolfo Teófilo",
  "Sabiaguaba",
  "Salinas",
  "São Bento",
  "São Gerardo",
  "Sapiranga",
  "Sapiranga-Coité",
  "Serrinha",
  "Siqueira",
  "Tauape",
  "Varjota",
  "Vicente Pinzon",
  "Vila Peri",
  "Vila União",
  "Vila Velha",
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
  { id: "dados", label: "Insercao de dados", icon: Database },
  { id: "modelo", label: "Modelo", icon: BarChart3 },
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

function formatCurrency(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function buildApiUrl(pathname) {
  return `${API_BASE_URL}${pathname}`;
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

function PredictionView({ form, onFormChange, onTypeChange, onToggleAmenity, onSubmit, loading, result, error }) {
  return (
    <section className="view-grid">
      <div className="surface surface--form">
        <SectionHeader
          eyebrow="Melhor modelo em acao"
          title="Predicao de preco para Fortaleza"
          description="Preencha os atributos do imovel e consulte o valor estimado usando o modelo campeao carregado pela API."
        />

        <form className="property-form" onSubmit={onSubmit}>
          <label>
            <span>Bairro</span>
            <select name="bairro" value={form.bairro} onChange={onFormChange} required>
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
              <input name="area_m2" type="number" min="1" step="1" value={form.area_m2} onChange={onFormChange} required />
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
                      role="radio"
                      aria-checked={active}
                      onClick={() => onTypeChange(option.value)}
                    >
                      <Icon size={16} />
                      <span>{option.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
            <label>
              <span>Quartos</span>
              <input name="quartos" type="number" min="0" step="1" value={form.quartos} onChange={onFormChange} required />
            </label>
            <label>
              <span>Banheiros</span>
              <input name="banheiros" type="number" min="0" step="1" value={form.banheiros} onChange={onFormChange} required />
            </label>
            <label>
              <span>Suites</span>
              <input name="suites" type="number" min="0" step="1" value={form.suites} onChange={onFormChange} required />
            </label>
            <label>
              <span>Andar</span>
              <input name="andar" type="number" min="0" step="1" value={form.andar} onChange={onFormChange} required />
            </label>
            <label>
              <span>Vagas</span>
              <input name="vagas" type="number" min="0" step="1" value={form.vagas} onChange={onFormChange} required />
            </label>
          </div>

          <div className="amenities-block">
            <div className="amenities-block__header">
              <h3>Amenidades</h3>
              <p>Marque os diferenciais presentes no imovel.</p>
            </div>
            <div className="amenity-grid">
              {amenityFields.map((field) => (
                <label key={field.key} className={`switch ${form[field.key] ? "switch--active" : ""}`}>
                  <input type="checkbox" checked={form[field.key]} onChange={() => onToggleAmenity(field.key)} />
                  <span>{field.label}</span>
                </label>
              ))}
            </div>
          </div>

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? <LoaderCircle className="spin" size={18} /> : <Send size={18} />}
            <span>{loading ? "Consultando modelo" : "Predizer preco"}</span>
          </button>
        </form>
      </div>

      <div className="surface surface--result">
        <SectionHeader
          eyebrow="Leitura imediata"
          title="Resposta da predicao"
          description="Acompanhe o retorno da API, veja o valor estimado e valide rapidamente o perfil enviado."
        />

        <div className="result-panel">
          {result ? (
            <>
              <div className="price-highlight">
                <span>Preco estimado</span>
                <strong>{formatCurrency(result.preco_estimado)}</strong>
                <small>
                  {result.tipo_imovel_padronizado} em {result.bairro}
                </small>
              </div>
              <div className="result-summary">
                <StatPill icon={CheckCircle2} label="Status" value="Sucesso" tone="success" />
                <StatPill icon={Building2} label="Bairro" value={result.bairro} />
                <StatPill icon={Waves} label="Categoria" value={result.tipo_imovel_padronizado.replaceAll("_", " ")} />
              </div>
            </>
          ) : (
            <div className="empty-state">
              <ArrowRight size={28} />
              <p>Envie uma simulacao para visualizar o valor estimado do imovel.</p>
            </div>
          )}

          {error ? (
            <div className="feedback feedback--error">
              <CircleAlert size={18} />
              <span>{error}</span>
            </div>
          ) : null}
        </div>

        <div className="preview-card">
          <div>
            <span className="preview-card__label">API alvo</span>
            <strong>{API_BASE_URL}</strong>
          </div>
          <p>Os campos desta tela seguem o contrato descrito no `AGENTS.md` e conversam com o endpoint `/predict`.</p>
        </div>
      </div>
    </section>
  );
}

function DataIngestionView({ selectedFile, uploading, uploadResult, uploadError, onFileChange, onUpload }) {
  return (
    <section className="view-grid view-grid--data">
      <div className="surface surface--form">
        <SectionHeader
          eyebrow="Atualizacao da base"
          title="Inserir novos dados para tratamento"
          description="Envie o CSV bruto para a pipeline de dados. A API trata, resume os filtros aplicados e persiste os registros no Postgres."
        />

        <div className="upload-box">
          <Upload size={30} />
          <div>
            <strong>{selectedFile ? selectedFile.name : "Selecione um arquivo CSV"}</strong>
            <p>Formatos esperados: `.csv` com dados brutos extraidos via scraping.</p>
          </div>
          <label className="secondary-button" htmlFor="csv-upload">
            <Upload size={18} />
            <span>Escolher arquivo</span>
          </label>
          <input id="csv-upload" type="file" accept=".csv,text/csv" onChange={onFileChange} hidden />
        </div>

        <button className="primary-button" type="button" onClick={onUpload} disabled={!selectedFile || uploading}>
          {uploading ? <LoaderCircle className="spin" size={18} /> : <Database size={18} />}
          <span>{uploading ? "Enviando CSV" : "Enviar para /insertData"}</span>
        </button>

        {uploadError ? (
          <div className="feedback feedback--error">
            <CircleAlert size={18} />
            <span>{uploadError}</span>
          </div>
        ) : null}
      </div>

      <div className="surface surface--result">
        <SectionHeader
          eyebrow="Resumo operacional"
          title="Resultado da ingestao"
          description="Veja a quantidade de linhas recebidas, tratadas e persistidas depois do processamento."
        />

        {uploadResult ? (
          <>
            <div className="metrics-grid">
              <StatPill icon={Database} label="Recebidas" value={String(uploadResult.linhas_recebidas)} tone="success" />
              <StatPill icon={Activity} label="Tratadas" value={String(uploadResult.linhas_tratadas)} />
              <StatPill icon={CheckCircle2} label="Salvas" value={String(uploadResult.linhas_salvas)} tone="success" />
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Etapa</th>
                    <th>Registros restantes</th>
                  </tr>
                </thead>
                <tbody>
                  {(uploadResult.resumo_filtros || []).map((row, index) => (
                    <tr key={`${row.etapa}-${index}`}>
                      <td>{row.etapa}</td>
                      <td>{row.registros_restantes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="empty-state">
            <Upload size={28} />
            <p>Quando um CSV for processado, o resumo da pipeline aparece aqui.</p>
          </div>
        )}
      </div>
    </section>
  );
}

function ModelView({ health, training, trainingError, trainingLoading, onTrain }) {
  return (
    <section className="view-grid view-grid--model">
      <div className="surface surface--form">
        <SectionHeader
          eyebrow="Governanca do modelo"
          title="Treinamento e monitoramento de sessao"
          description="Acione o retreino com os dados do ultimo ano e acompanhe metricas, ranking e disponibilidade da API."
        />

        <div className="status-stack">
          <StatPill
            icon={health.ok ? CheckCircle2 : CircleAlert}
            label="API"
            value={health.label}
            tone={health.ok ? "success" : "error"}
          />
          <StatPill icon={RefreshCw} label="Ultimo treino" value={training ? "Executado nesta sessao" : "Ainda nao executado"} />
        </div>

        <button className="primary-button" type="button" onClick={onTrain} disabled={trainingLoading}>
          {trainingLoading ? <LoaderCircle className="spin" size={18} /> : <RefreshCw size={18} />}
          <span>{trainingLoading ? "Treinando modelos" : "Retreinar com /trainModels"}</span>
        </button>

        {trainingError ? (
          <div className="feedback feedback--error">
            <CircleAlert size={18} />
            <span>{trainingError}</span>
          </div>
        ) : null}
      </div>

      <div className="surface surface--result">
        <SectionHeader
          eyebrow="Painel do campeao"
          title="Melhor modelo e ranking"
          description="A resposta de treinamento fica salva nesta interface para consulta rapida durante a operacao."
        />

        {training ? (
          <>
            <div className="price-highlight price-highlight--model">
              <span>Modelo campeao</span>
              <strong>{training.modelo_campeao}</strong>
              <small>{training.amostras_treinamento} amostras usadas no treino atual</small>
            </div>

            <div className="metrics-grid">
              <StatPill icon={BarChart3} label="RMSE" value={Number(training.rmse).toFixed(2)} />
              <StatPill icon={BarChart3} label="MAE" value={Number(training.mae).toFixed(2)} />
              <StatPill icon={BarChart3} label="R2" value={Number(training.r2).toFixed(4)} tone="success" />
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Modelo</th>
                    <th>RMSE</th>
                    <th>MAE</th>
                    <th>R2</th>
                  </tr>
                </thead>
                <tbody>
                  {(training.ranking || []).map((row) => (
                    <tr key={row.model_key || row.display_name}>
                      <td>{row.display_name || row.model_key}</td>
                      <td>{Number(row.rmse).toFixed(2)}</td>
                      <td>{Number(row.mae).toFixed(2)}</td>
                      <td>{Number(row.r2).toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <div className="empty-state">
            <BarChart3 size={28} />
            <p>Execute um treino para preencher o painel com o ranking e o modelo campeao.</p>
          </div>
        )}
      </div>
    </section>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState("predicao");
  const [form, setForm] = useState(initialForm);
  const [predicting, setPredicting] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [predictionError, setPredictionError] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState("");
  const [trainingLoading, setTrainingLoading] = useState(false);
  const [trainingResult, setTrainingResult] = useState(null);
  const [trainingError, setTrainingError] = useState("");
  const [health, setHealth] = useState({ ok: false, label: "Verificando..." });

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      try {
        const response = await fetch(buildApiUrl("/health"));
        if (!response.ok) {
          throw new Error("Falha ao consultar /health.");
        }
        const payload = await response.json();
        if (!cancelled) {
          setHealth({ ok: payload.status === "ok", label: payload.status === "ok" ? "Online" : "Instavel" });
        }
      } catch {
        if (!cancelled) {
          setHealth({ ok: false, label: "Offline" });
        }
      }
    }

    checkHealth();
    return () => {
      cancelled = true;
    };
  }, []);

  function handleFormChange(event) {
    const { name, value, type } = event.target;
    setForm((current) => ({
      ...current,
      [name]: type === "number" ? Number(value) : value,
    }));
  }

  function handleToggleAmenity(key) {
    setForm((current) => ({
      ...current,
      [key]: !current[key],
    }));
  }

  function handleTypeChange(value) {
    setForm((current) => ({
      ...current,
      tipo_imovel_padronizado: value,
    }));
  }

  async function handlePredict(event) {
    event.preventDefault();
    setPredicting(true);
    setPredictionError("");

    try {
      const response = await fetch(buildApiUrl("/predict"), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Nao foi possivel obter a predicao.");
      }

      setPredictionResult(payload);
    } catch (error) {
      setPredictionResult(null);
      setPredictionError(error.message);
    } finally {
      setPredicting(false);
    }
  }

  function handleFileChange(event) {
    setSelectedFile(event.target.files?.[0] || null);
    setUploadError("");
  }

  async function handleUpload() {
    if (!selectedFile) {
      setUploadError("Selecione um arquivo CSV antes de enviar.");
      return;
    }

    setUploading(true);
    setUploadError("");

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(buildApiUrl("/insertData"), {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail || "Falha ao inserir dados.");
      }

      setUploadResult(payload);
    } catch (error) {
      setUploadResult(null);
      setUploadError(error.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleTrain() {
    setTrainingLoading(true);
    setTrainingError("");

    try {
      const response = await fetch(buildApiUrl("/trainModels"), {
        method: "POST",
      });
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload.detail || "Falha ao treinar modelos.");
      }

      setTrainingResult(payload);
    } catch (error) {
      setTrainingResult(null);
      setTrainingError(error.message);
    } finally {
      setTrainingLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <main className="workspace">
        <header className="workspace-header">
          <div>
            <span className="workspace-header__eyebrow">Plataforma de predicao imobiliaria</span>
            <h2>Operacao do sistema</h2>
          </div>
          <div className="workspace-header__meta">
            <StatPill
              icon={health.ok ? CheckCircle2 : CircleAlert}
              label="API"
              value={health.label}
              tone={health.ok ? "success" : "error"}
            />
          </div>
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

        {activeTab === "predicao" ? (
          <PredictionView
            form={form}
            onFormChange={handleFormChange}
            onTypeChange={handleTypeChange}
            onToggleAmenity={handleToggleAmenity}
            onSubmit={handlePredict}
            loading={predicting}
            result={predictionResult}
            error={predictionError}
          />
        ) : null}

        {activeTab === "dados" ? (
          <DataIngestionView
            selectedFile={selectedFile}
            uploading={uploading}
            uploadResult={uploadResult}
            uploadError={uploadError}
            onFileChange={handleFileChange}
            onUpload={handleUpload}
          />
        ) : null}

        {activeTab === "modelo" ? (
          <ModelView
            health={health}
            training={trainingResult}
            trainingError={trainingError}
            trainingLoading={trainingLoading}
            onTrain={handleTrain}
          />
        ) : null}
      </main>
    </div>
  );
}
