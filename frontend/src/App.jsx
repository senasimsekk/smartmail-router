import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Background,
  Controls,
  MarkerType,
  Position,
  ReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

const EMPTY_IMPORT_FORM = {
  subject: "",
  sender: "",
  body: "",
  source_mailbox: "webmaster@rekabet.gov.tr",
  has_attachment: false,
  attachment_names: "",
};

const CATEGORY_OPTIONS = [
  "KVKK Başvurusu",
  "Teknik Destek",
  "Basın Talebi",
  "Satın Alma",
  "Hukuki Tebligat",
  "Şikayet",
  "İhbar",
  "Bilgi Edinme",
  "Fatura / Ödeme",
  "İnsan Kaynakları",
  "Evrak Kayıt",
  "Genel Başvuru",
];

const DEPARTMENT_OPTIONS = [
  "Hukuk Müşavirliği",
  "Bilgi İşlem",
  "Basın ve Halkla İlişkiler",
  "Satın Alma",
  "Evrak Kayıt",
  "İlgili Uzman Daire",
  "Strateji / Mali İşler",
  "İnsan Kaynakları",
];

const PRIORITY_OPTIONS = ["Kritik", "Yüksek", "Normal", "Düşük"];

const WORKFLOW_STEP_POSITIONS = [
  { id: "received", x: 0, y: 80 },
  { id: "preprocess", x: 210, y: 80 },
  { id: "attachments", x: 420, y: 80 },
  { id: "classification", x: 630, y: 80 },
  { id: "confidence", x: 840, y: 80 },
  { id: "review", x: 1050, y: 0 },
  { id: "routing", x: 1260, y: 80 },
  { id: "closed", x: 1470, y: 80 },
];

function formatPercent(value) {
  if (typeof value !== "number") {
    return "-";
  }

  return `${Math.round(value * 100)}%`;
}

function getStatusLabel(status) {
  return status || "New";
}

function getWorkflowStatusClass(status) {
  if (["Routed", "Approved", "Classified", "Corrected"].includes(status)) {
    return "complete";
  }

  if (status === "Pending Review") {
    return "review";
  }

  return "active";
}

function createWorkflowNode(id, label, detail, state) {
  const position = WORKFLOW_STEP_POSITIONS.find((step) => step.id === id);

  return {
    id,
    position: { x: position.x, y: position.y },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    className: `workflow-node ${state}`,
    data: {
      label: (
        <div>
          <strong>{label}</strong>
          <span>{detail}</span>
        </div>
      ),
    },
  };
}

function buildWorkflowGraph(email, classification, analysis, attachmentAnalysis) {
  const routingStatus = getStatusLabel(email?.routing_status);
  const confidence = classification.confidence_score || 0;
  const needsReview = Boolean(classification.requires_human_review);
  const hasAttachment = Boolean(email?.has_attachment);
  const isRouted = routingStatus === "Routed";
  const isClosed = ["Completed", "Archived"].includes(routingStatus);

  const nodes = [
    createWorkflowNode(
      "received",
      "Mail Alındı",
      email?.source_mailbox || "Kaynak kutu bekleniyor",
      "complete"
    ),
    createWorkflowNode(
      "preprocess",
      "Ön İşleme",
      "HTML, imza ve gereksiz metin temizlenir",
      "complete"
    ),
    createWorkflowNode(
      "attachments",
      "Ek Analizi",
      hasAttachment
        ? `${attachmentAnalysis.attachment_count || 0} ek kontrol edildi`
        : "Ek yok, adım atlandı",
      hasAttachment ? "complete" : "skipped"
    ),
    createWorkflowNode(
      "classification",
      "Sınıflandırma",
      classification.category || "Kategori hesaplanıyor",
      classification.category ? "complete" : "active"
    ),
    createWorkflowNode(
      "confidence",
      "Güven Skoru",
      confidence ? formatPercent(confidence) : "Skor bekleniyor",
      confidence >= 0.85 ? "complete" : "review"
    ),
    createWorkflowNode(
      "review",
      "İnsan Onayı",
      needsReview ? "Operatör kontrolü gerekli" : "Otomatik geçiş uygun",
      needsReview ? getWorkflowStatusClass(routingStatus) : "skipped"
    ),
    createWorkflowNode(
      "routing",
      "Birim Yönlendirme",
      isRouted
        ? email?.approved_department || classification.department
        : analysis.routing_decision?.primary_department ||
          classification.department ||
          "Birim bekleniyor",
      isRouted ? "complete" : "active"
    ),
    createWorkflowNode(
      "closed",
      "Kapanış",
      isClosed ? "Süreç kapandı" : "Cevap ve sonuç bekleniyor",
      isClosed ? "complete" : "waiting"
    ),
  ];

  const edges = [
    ["received", "preprocess"],
    ["preprocess", "attachments"],
    ["attachments", "classification"],
    ["classification", "confidence"],
    ["confidence", "review"],
    ["review", "routing"],
    ["routing", "closed"],
  ].map(([source, target]) => ({
    id: `${source}-${target}`,
    source,
    target,
    type: "smoothstep",
    animated: target === "review" && needsReview,
    markerEnd: {
      type: MarkerType.ArrowClosed,
      color: needsReview && target === "review" ? "#b42318" : "#1f4e79",
    },
    style: {
      stroke: needsReview && target === "review" ? "#b42318" : "#1f4e79",
      strokeWidth: 2,
    },
  }));

  return { nodes, edges };
}

function App() {
  const [emails, setEmails] = useState([]);
  const [selectedEmailId, setSelectedEmailId] = useState(null);
  const [details, setDetails] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [operationalDashboard, setOperationalDashboard] = useState(null);
  const [pendingReview, setPendingReview] = useState([]);
  const [feedbackData, setFeedbackData] = useState({
    feedback_count: 0,
    feedbacks: [],
  });
  const [trainingData, setTrainingData] = useState({
    training_example_count: 0,
    training_examples: [],
  });
  const [logs, setLogs] = useState([]);
  const [importForm, setImportForm] = useState(EMPTY_IMPORT_FORM);
  const [selectedAttachmentFile, setSelectedAttachmentFile] = useState(null);
  const [correctionForm, setCorrectionForm] = useState({
    corrected_category: "Genel Başvuru",
    corrected_department: "Evrak Kayıt",
    corrected_priority: "Normal",
    feedback_note: "",
  });
  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [actionMessage, setActionMessage] = useState("");

  const selectedEmail = useMemo(
    () => emails.find((email) => email.id === selectedEmailId) || null,
    [emails, selectedEmailId]
  );

  const request = useCallback(async function request(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`${path} returned ${response.status}`);
    }

    return response.json();
  }, []);

  const refreshWorkspace = useCallback(async function refreshWorkspace() {
    setErrorMessage("");

    try {
      const [
        emailData,
        dashboardData,
        operationalData,
        pendingData,
        feedbackResult,
        trainingResult,
      ] =
        await Promise.all([
          request("/emails"),
          request("/emails/dashboard/summary"),
          request("/emails/dashboard/operational"),
          request("/emails/review/pending"),
          request("/emails/feedback/all"),
          request("/emails/feedback/training-data"),
        ]);

      setEmails(emailData.emails || []);
      setDashboard(dashboardData);
      setOperationalDashboard(operationalData);
      setPendingReview(pendingData.pending_emails || []);
      setFeedbackData(feedbackResult);
      setTrainingData(trainingResult);

      setSelectedEmailId((currentEmailId) =>
        currentEmailId || emailData.emails?.[0]?.id || null
      );
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setLoading(false);
    }
  }, [request]);

  const fetchEmailDetails = useCallback(async function fetchEmailDetails(emailId) {
    setDetailsLoading(true);
    setActionMessage("");

    try {
      const [analysis, aiAnalysis, responseSuggestion, logData] =
        await Promise.all([
          request(`/emails/${emailId}/analysis`),
          request(`/emails/${emailId}/ai-analysis`),
          request(`/emails/${emailId}/response-suggestion`),
          request(`/emails/${emailId}/logs`),
        ]);

      setDetails({
        analysis,
        aiAnalysis,
        responseSuggestion,
      });
      setLogs(logData.logs || []);
    } catch (error) {
      setErrorMessage(error.message);
    } finally {
      setDetailsLoading(false);
    }
  }, [request]);

  useEffect(() => {
    // Initial API load is intentionally triggered when the app mounts.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refreshWorkspace();
  }, [refreshWorkspace]);

  useEffect(() => {
    if (selectedEmailId) {
      // Selected mail changes should fetch fresh derived analysis data.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      fetchEmailDetails(selectedEmailId);
    }
  }, [fetchEmailDetails, selectedEmailId]);

  async function handleProcessEmail() {
    if (!selectedEmail) {
      return;
    }

    await runEmailAction(
      `/emails/${selectedEmail.id}/process`,
      { method: "POST" },
      "Mail işlendi ve sınıflandırma kaydedildi."
    );
  }

  async function handleApproveRouting() {
    if (!selectedEmail) {
      return;
    }

    await runEmailAction(
      `/emails/${selectedEmail.id}/approve-routing`,
      {
        method: "POST",
        body: JSON.stringify({
          approved_by: "operator",
          approved_department:
            details?.analysis?.classification?.department || undefined,
          routing_note: "Operatör panelinden onaylandı.",
        }),
      },
      "Yönlendirme operatör tarafından onaylandı."
    );
  }

  async function handleRouteEmail() {
    if (!selectedEmail) {
      return;
    }

    await runEmailAction(
      `/emails/${selectedEmail.id}/route`,
      {
        method: "POST",
        body: JSON.stringify({
          routed_by: "operator",
          target_department:
            details?.analysis?.classification?.department || undefined,
          routing_note: "Panel üzerinden ilgili birim havuzuna aktarıldı.",
        }),
      },
      "Mail ilgili birim havuzuna yönlendirildi."
    );
  }

  async function handleCorrectRouting(event) {
    event.preventDefault();

    if (!selectedEmail) {
      return;
    }

    await runEmailAction(
      `/emails/${selectedEmail.id}/correct-routing`,
      {
        method: "POST",
        body: JSON.stringify({
          ...correctionForm,
          corrected_by: "operator",
        }),
      },
      "Düzeltme kaydedildi ve geri bildirim eğitim verisine eklendi."
    );
  }

  async function runEmailAction(path, options, successMessage) {
    setActionMessage("");
    setErrorMessage("");

    try {
      await request(path, options);
      setActionMessage(successMessage);
      await refreshWorkspace();

      if (selectedEmailId) {
        await fetchEmailDetails(selectedEmailId);
      }
    } catch (error) {
      setErrorMessage(error.message);
    }
  }

  async function handleImportSubmit(event) {
    event.preventDefault();
    setActionMessage("");
    setErrorMessage("");

    const attachmentNames = importForm.attachment_names
      .split(",")
      .map((name) => name.trim())
      .filter(Boolean);

    try {
      const created = await request("/emails/ingestion/manual-import", {
        method: "POST",
        body: JSON.stringify({
          ...importForm,
          has_attachment: attachmentNames.length > 0 || importForm.has_attachment,
          attachment_names: attachmentNames,
        }),
      });

      setImportForm(EMPTY_IMPORT_FORM);
      setSelectedEmailId(created.imported_email.id);
      setActionMessage("Sentetik mail içe aktarıldı ve işlendi.");
      await refreshWorkspace();
    } catch (error) {
      setErrorMessage(error.message);
    }
  }

  async function handleAttachmentUpload(event) {
    event.preventDefault();

    if (!selectedEmail || !selectedAttachmentFile) {
      setActionMessage("Yüklenecek ek dosya seçilmedi.");
      return;
    }

    setActionMessage("");
    setErrorMessage("");

    const formData = new FormData();
    formData.append("file", selectedAttachmentFile);

    try {
      const response = await fetch(
        `${API_BASE_URL}/emails/${selectedEmail.id}/attachments/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error(`Attachment upload returned ${response.status}`);
      }

      setSelectedAttachmentFile(null);
      setActionMessage("Ek dosya yüklendi ve metin çıkarma denendi.");
      await refreshWorkspace();
      await fetchEmailDetails(selectedEmail.id);
    } catch (error) {
      setErrorMessage(error.message);
    }
  }

  function buildTrainingJsonl() {
    return (trainingData.training_examples || [])
      .map((example) =>
        JSON.stringify({
          messages: [
            {
              role: "system",
              content:
                "Kurumsal e-postayı category, department ve priority alanlarıyla sınıflandır.",
            },
            {
              role: "user",
              content: [
                `Subject: ${example.subject}`,
                `Sender: ${example.sender}`,
                `Mailbox: ${example.source_mailbox || "-"}`,
                `Body: ${example.body}`,
              ].join("\n"),
            },
            {
              role: "assistant",
              content: JSON.stringify(example.corrected_label),
            },
          ],
          metadata: {
            email_id: example.email_id,
            original_label: example.original_label,
            feedback_note: example.feedback_note,
          },
        })
      )
      .join("\n");
  }

  function handleDownloadTrainingJsonl() {
    const jsonl = buildTrainingJsonl();

    if (!jsonl) {
      setActionMessage("İndirilecek eğitim verisi yok.");
      return;
    }

    const blob = new Blob([jsonl], {
      type: "application/jsonl;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = "smartmail-training-data.jsonl";
    link.click();

    URL.revokeObjectURL(url);
    setActionMessage("Eğitim verisi JSONL olarak hazırlandı.");
  }

  const classification = details?.analysis?.classification || {};
  const analysis = details?.analysis?.analysis || {};
  const extracted = details?.analysis?.extracted_information || {};
  const attachmentAnalysis = analysis?.attachment_analysis || {};
  const attachmentTexts = selectedEmail?.attachment_texts || [];
  const responseSuggestion =
    details?.responseSuggestion?.response_suggestion || {};
  const aiAnalysis = details?.aiAnalysis?.ai_analysis || {};
  const ruleBasedClassification = aiAnalysis.rule_based_classification || {};
  const mockAiClassification = aiAnalysis.mock_ai_classification || {};
  const workflowGraph = buildWorkflowGraph(
    selectedEmail,
    classification,
    analysis,
    attachmentAnalysis
  );

  if (loading) {
    return <div className="page-loading">SmartMail Router yükleniyor...</div>;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Kurumsal E-posta Sınıflandırma</p>
          <h1>SmartMail Router</h1>
        </div>
        <button className="secondary-button" onClick={refreshWorkspace}>
          Yenile
        </button>
      </header>

      {errorMessage && <div className="alert danger">{errorMessage}</div>}
      {actionMessage && <div className="alert success">{actionMessage}</div>}

      <section className="metrics-grid" aria-label="Dashboard metrikleri">
        <Metric label="Toplam mail" value={dashboard?.total_emails ?? 0} />
        <Metric
          label="İnsan onayı"
          value={dashboard?.human_review_count ?? 0}
        />
        <Metric
          label="Kritik risk"
          value={dashboard?.critical_risk_count ?? 0}
        />
        <Metric
          label="Doğruluk"
          value={formatPercent(dashboard?.accuracy)}
        />
        <Metric
          label="Bekleyen"
          value={operationalDashboard?.pending_review_count ?? 0}
        />
        <Metric
          label="Yönlendirilen"
          value={operationalDashboard?.routing_status_distribution?.Routed ?? 0}
        />
        <Metric label="Feedback" value={feedbackData.feedback_count ?? 0} />
      </section>

      <main className="workspace-grid">
        <aside className="queue-panel">
          <div className="panel-heading">
            <h2>Mail Kuyruğu</h2>
            <span>{emails.length} kayıt</span>
          </div>

          <div className="queue-list">
            {emails.map((email) => (
              <button
                key={email.id}
                className={`queue-item ${
                  selectedEmailId === email.id ? "selected" : ""
                }`}
                onClick={() => setSelectedEmailId(email.id)}
              >
                <span className="queue-subject">{email.subject}</span>
                <span className="queue-meta">{email.sender}</span>
                <span className="status-row">
                  <span>{email.source_mailbox}</span>
                  <strong>{getStatusLabel(email.routing_status)}</strong>
                </span>
              </button>
            ))}
          </div>

          <div className="compact-section">
            <h3>Onay Bekleyenler</h3>
            {pendingReview.length === 0 ? (
              <p className="muted">Bekleyen kritik kayıt yok.</p>
            ) : (
              pendingReview.slice(0, 5).map((item) => (
                <button
                  key={item.email.id}
                  className="mini-row"
                  onClick={() => setSelectedEmailId(item.email.id)}
                >
                  <span>{item.email.subject}</span>
                  <strong>{item.classification.priority}</strong>
                </button>
              ))
            )}
          </div>
        </aside>

        <section className="detail-panel">
          {!selectedEmail && (
            <div className="empty-state">
              <h2>Kayıt bulunamadı</h2>
              <p>Veritabanına sentetik mail ekleyerek başlayabilirsin.</p>
            </div>
          )}

          {selectedEmail && (
            <>
              <div className="detail-header">
                <div>
                  <p className="eyebrow">Seçili Mail</p>
                  <h2>{selectedEmail.subject}</h2>
                </div>
                <div className="button-row">
                  <button onClick={handleProcessEmail}>İşle</button>
                  <button onClick={handleApproveRouting}>Onayla</button>
                  <button onClick={handleRouteEmail}>Yönlendir</button>
                </div>
              </div>

              <div className="meta-grid">
                <Meta label="Gönderen" value={selectedEmail.sender} />
                <Meta label="Kaynak kutu" value={selectedEmail.source_mailbox} />
                <Meta
                  label="Durum"
                  value={getStatusLabel(selectedEmail.routing_status)}
                />
                <Meta
                  label="Ek"
                  value={
                    selectedEmail.has_attachment
                      ? selectedEmail.attachment_names?.join(", ")
                      : "Yok"
                  }
                />
              </div>

              <div className="body-box">{selectedEmail.body}</div>

              {detailsLoading && (
                <p className="muted">Analiz sonuçları yükleniyor...</p>
              )}

              {!detailsLoading && details && (
                <>
                  <section className="section-block">
                    <div className="panel-heading">
                      <h3>Sınıflandırma ve Risk</h3>
                      <span>{formatPercent(classification.confidence_score)}</span>
                    </div>

                    <div className="analysis-grid">
                      <Meta label="Kategori" value={classification.category} />
                      <Meta label="Birim" value={classification.department} />
                      <Meta label="Öncelik" value={classification.priority} />
                      <Meta
                        label="İnsan onayı"
                        value={
                          classification.requires_human_review
                            ? "Gerekli"
                            : "Gerekli değil"
                        }
                      />
                      <Meta label="Risk" value={analysis.risk_level} />
                      <Meta label="İşlem türü" value={analysis.operation_type} />
                    </div>

                    <TextBlock title="Özet" text={analysis.summary} />
                    <TextBlock
                      title="Sistem açıklaması"
                      text={classification.explanation}
                    />
                    <ListBlock
                      title="Risk nedenleri"
                      items={analysis.risk_reasons}
                    />
                  </section>

                  <section className="section-block">
                    <h3>Bilgi Çıkarımı</h3>
                    <div className="analysis-grid">
                      <Meta label="Talep sahibi" value={extracted.sender} />
                      <Meta
                        label="Gizlilik"
                        value={extracted.confidentiality_level}
                      />
                      <Meta
                        label="Talep edilen işlem"
                        value={extracted.requested_action}
                      />
                      <Meta
                        label="Dosya no"
                        value={extracted.file_numbers?.join(", ") || "-"}
                      />
                      <Meta
                        label="Başvuru no"
                        value={extracted.application_numbers?.join(", ") || "-"}
                      />
                      <Meta
                        label="Mevzuat"
                        value={extracted.related_legislation?.join(", ") || "-"}
                      />
                    </div>
                  </section>

                  <section className="section-block">
                    <h3>Ek Dosya Analizi</h3>
                    <form
                      className="attachment-upload-form"
                      onSubmit={handleAttachmentUpload}
                    >
                      <input
                        type="file"
                        accept=".pdf,.docx,.txt,.csv"
                        onChange={(event) =>
                          setSelectedAttachmentFile(
                            event.target.files?.[0] || null
                          )
                        }
                      />
                      <button type="submit">Ek Yükle ve Oku</button>
                    </form>

                    {!attachmentAnalysis.has_attachments ? (
                      <p className="muted">Bu mailde ek dosya yok.</p>
                    ) : (
                      <>
                        <div className="analysis-grid">
                          <Meta
                            label="Ek sayısı"
                            value={attachmentAnalysis.attachment_count}
                          />
                          <Meta
                            label="Genel risk"
                            value={attachmentAnalysis.overall_risk_level}
                          />
                          <Meta
                            label="Evrak kaydı"
                            value={
                              attachmentAnalysis.requires_record
                                ? "Gerekli"
                                : "Gerekli değil"
                            }
                          />
                          <Meta
                            label="İnsan onayı"
                            value={
                              attachmentAnalysis.requires_human_review
                                ? "Gerekli"
                                : "Gerekli değil"
                            }
                          />
                        </div>
                        {attachmentAnalysis.attachments?.map((attachment) => (
                          <div className="attachment-row" key={attachment.filename}>
                            <strong>{attachment.filename}</strong>
                            <span>{attachment.file_type}</span>
                            <span>{attachment.risk_level}</span>
                            <p>{attachment.suggested_action}</p>
                          </div>
                        ))}
                      </>
                    )}

                    {attachmentTexts.length > 0 && (
                      <div className="extracted-text-list">
                        <h4>Ekten Çıkarılan Metin</h4>
                        {attachmentTexts.map((attachmentText) => (
                          <div
                            className="extracted-text-card"
                            key={attachmentText.filename}
                          >
                            <div className="status-row">
                              <strong>{attachmentText.filename}</strong>
                              <span>{attachmentText.status}</span>
                            </div>
                            <p>
                              {attachmentText.extracted_text ||
                                attachmentText.warning ||
                                "Metin bulunamadı."}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </section>

                  <section className="section-block">
                    <h3>Cevap Önerisi</h3>
                    {responseSuggestion.warning && (
                      <div className="alert warning">
                        {responseSuggestion.warning}
                      </div>
                    )}
                    <div className="response-box">
                      {responseSuggestion.suggested_response ||
                        "Cevap önerisi üretilemedi."}
                    </div>
                  </section>

                  <section className="section-block">
                    <h3>AI ve Kural Kararı</h3>
                    <div className="analysis-grid">
                      <Meta
                        label="Kural kategorisi"
                        value={ruleBasedClassification.category}
                      />
                      <Meta
                        label="AI kategorisi"
                        value={mockAiClassification.ai_category}
                      />
                      <Meta
                        label="AI güven"
                        value={formatPercent(
                          mockAiClassification.ai_confidence_score
                        )}
                      />
                      <Meta
                        label="Karar kaynağı"
                        value={
                          aiAnalysis.final_recommendation
                            ?.final_decision_source
                        }
                      />
                    </div>
                  </section>

                  <section className="section-block">
                    <div className="panel-heading">
                      <h3>İş Akışı</h3>
                      <span>{getStatusLabel(selectedEmail.routing_status)}</span>
                    </div>
                    <div className="workflow-canvas">
                      <ReactFlow
                        nodes={workflowGraph.nodes}
                        edges={workflowGraph.edges}
                        fitView
                        fitViewOptions={{ padding: 0.18 }}
                        nodesDraggable={false}
                        nodesConnectable={false}
                        elementsSelectable={false}
                        panOnScroll
                        proOptions={{ hideAttribution: true }}
                      >
                        <Background gap={18} size={1} />
                        <Controls showInteractive={false} />
                      </ReactFlow>
                    </div>
                  </section>

                  <section className="section-block">
                    <h3>Yanlış Yönlendirme Düzelt</h3>
                    <form className="correction-form" onSubmit={handleCorrectRouting}>
                      <select
                        value={correctionForm.corrected_category}
                        onChange={(event) =>
                          setCorrectionForm({
                            ...correctionForm,
                            corrected_category: event.target.value,
                          })
                        }
                      >
                        {CATEGORY_OPTIONS.map((category) => (
                          <option key={category}>{category}</option>
                        ))}
                      </select>
                      <select
                        value={correctionForm.corrected_department}
                        onChange={(event) =>
                          setCorrectionForm({
                            ...correctionForm,
                            corrected_department: event.target.value,
                          })
                        }
                      >
                        {DEPARTMENT_OPTIONS.map((department) => (
                          <option key={department}>{department}</option>
                        ))}
                      </select>
                      <select
                        value={correctionForm.corrected_priority}
                        onChange={(event) =>
                          setCorrectionForm({
                            ...correctionForm,
                            corrected_priority: event.target.value,
                          })
                        }
                      >
                        {PRIORITY_OPTIONS.map((priority) => (
                          <option key={priority}>{priority}</option>
                        ))}
                      </select>
                      <input
                        value={correctionForm.feedback_note}
                        onChange={(event) =>
                          setCorrectionForm({
                            ...correctionForm,
                            feedback_note: event.target.value,
                          })
                        }
                        placeholder="Geri bildirim notu"
                      />
                      <button type="submit">Düzeltmeyi Kaydet</button>
                    </form>
                  </section>

                  <section className="section-block">
                    <h3>Audit Log</h3>
                    {logs.length === 0 ? (
                      <p className="muted">Bu kayıt için log yok.</p>
                    ) : (
                      logs.slice(0, 6).map((log) => (
                        <div className="log-row" key={log.id}>
                          <strong>{log.action_type}</strong>
                          <span>{log.actor}</span>
                          <p>{log.action_detail}</p>
                        </div>
                      ))
                    )}
                  </section>
                </>
              )}
            </>
          )}
        </section>

        <aside className="import-panel">
          <h2>Manuel Sentetik Mail</h2>
          <form onSubmit={handleImportSubmit}>
            <label>
              Konu
              <input
                required
                value={importForm.subject}
                onChange={(event) =>
                  setImportForm({ ...importForm, subject: event.target.value })
                }
              />
            </label>
            <label>
              Gönderen
              <input
                required
                type="email"
                value={importForm.sender}
                onChange={(event) =>
                  setImportForm({ ...importForm, sender: event.target.value })
                }
              />
            </label>
            <label>
              Kaynak posta kutusu
              <input
                value={importForm.source_mailbox}
                onChange={(event) =>
                  setImportForm({
                    ...importForm,
                    source_mailbox: event.target.value,
                  })
                }
              />
            </label>
            <label>
              Mail gövdesi
              <textarea
                required
                rows={7}
                value={importForm.body}
                onChange={(event) =>
                  setImportForm({ ...importForm, body: event.target.value })
                }
              />
            </label>
            <label>
              Ek dosyalar
              <input
                placeholder="tebligat.pdf, kimlik.png"
                value={importForm.attachment_names}
                onChange={(event) =>
                  setImportForm({
                    ...importForm,
                    attachment_names: event.target.value,
                  })
                }
              />
            </label>
            <button type="submit">Maili İçe Aktar</button>
          </form>

          <div className="compact-section">
            <h3>Durum Dağılımı</h3>
            {Object.entries(
              operationalDashboard?.routing_status_distribution || {}
            ).map(([status, count]) => (
              <div className="mini-row static" key={status}>
                <span>{status}</span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>

          <div className="compact-section">
            <div className="panel-heading compact-heading">
              <h3>Eğitim Verisi</h3>
              <button
                className="secondary-button small-button"
                type="button"
                onClick={handleDownloadTrainingJsonl}
              >
                JSONL İndir
              </button>
            </div>

            <div className="training-summary">
              <Meta label="Feedback" value={feedbackData.feedback_count ?? 0} />
              <Meta
                label="Training örneği"
                value={trainingData.training_example_count ?? 0}
              />
            </div>

            {feedbackData.feedbacks.length === 0 ? (
              <p className="muted">Henüz feedback kaydı yok.</p>
            ) : (
              <div className="feedback-list">
                {feedbackData.feedbacks.slice(0, 4).map((feedback) => (
                  <div className="feedback-row" key={feedback.id}>
                    <span>Mail #{feedback.email_id}</span>
                    <strong>
                      {feedback.original_department} →{" "}
                      {feedback.corrected_department}
                    </strong>
                    <p>{feedback.feedback_note || "Not girilmedi."}</p>
                  </div>
                ))}
              </div>
            )}

            {trainingData.training_examples.length > 0 && (
              <pre className="training-preview">
                {buildTrainingJsonl().split("\n").slice(0, 2).join("\n")}
              </pre>
            )}
          </div>
        </aside>
      </main>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Meta({ label, value }) {
  return (
    <div className="meta-item">
      <span>{label}</span>
      <strong>{value || "-"}</strong>
    </div>
  );
}

function TextBlock({ title, text }) {
  return (
    <div className="text-block">
      <h4>{title}</h4>
      <p>{text || "-"}</p>
    </div>
  );
}

function ListBlock({ title, items = [] }) {
  if (!items.length) {
    return null;
  }

  return (
    <div className="text-block">
      <h4>{title}</h4>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default App;
