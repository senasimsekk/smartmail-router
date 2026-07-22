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

const ROLE_OPTIONS = [
  {
    role: "admin",
    label: "Yönetici",
    department: "Tüm birimler",
    permissions: [
      "import_email",
      "process_email",
      "upload_attachment",
      "approve_routing",
      "route_email",
      "correct_routing",
      "view_dashboard",
      "view_training_data",
    ],
  },
  {
    role: "operator",
    label: "Operatör",
    department: "Evrak/operasyon",
    permissions: [
      "import_email",
      "process_email",
      "upload_attachment",
      "approve_routing",
      "route_email",
      "correct_routing",
      "view_dashboard",
      "view_training_data",
    ],
  },
  {
    role: "department_user",
    label: "Birim Kullanıcısı",
    department: "İlgili Uzman Daire",
    permissions: ["view_dashboard", "view_training_data"],
  },
  {
    role: "viewer",
    label: "İzleyici",
    department: "Raporlama",
    permissions: ["view_dashboard"],
  },
];

const SLA_FILTERS = [
  { value: "all", label: "Tümü" },
  { value: "Overdue", label: "Geciken" },
  { value: "Due soon", label: "Yaklaşan" },
  { value: "On time", label: "Zamanında" },
];

const STATUS_FILTERS = [
  { value: "all", label: "Tüm durumlar" },
  { value: "New", label: "Yeni" },
  { value: "Classified", label: "Sınıflandırıldı" },
  { value: "Pending Review", label: "İnceleme bekliyor" },
  { value: "Approved", label: "Onaylandı" },
  { value: "Routed", label: "Yönlendirildi" },
  { value: "Corrected", label: "Düzeltildi" },
];

const DETAIL_TABS = [
  { value: "analysis", label: "Analiz" },
  { value: "preprocess", label: "Ön İşleme" },
  { value: "attachments", label: "Ekler" },
  { value: "routing", label: "Yönlendirme" },
  { value: "ticket", label: "Evrak Kaydı" },
  { value: "logs", label: "Günlük" },
];

const PAGE_TABS = [
  { value: "operation", label: "Operasyon" },
  { value: "pipeline", label: "İşlem Hattı" },
  { value: "reports", label: "Raporlama" },
  { value: "evaluation", label: "Değerlendirme" },
  { value: "integrations", label: "Entegrasyonlar" },
  { value: "ingestion", label: "E-posta Alma" },
  { value: "training", label: "Model Eğitimi" },
];

const STATUS_LABELS = {
  New: "Yeni",
  Classified: "Sınıflandırıldı",
  "Pending Review": "İnceleme bekliyor",
  Approved: "Onaylandı",
  Routed: "Yönlendirildi",
  Corrected: "Düzeltildi",
  Completed: "Tamamlandı",
  Archived: "Arşivlendi",
};

const SLA_LABELS = {
  Overdue: "Geciken",
  "Due soon": "Yaklaşan",
  "On time": "Zamanında",
};

const LOG_ACTION_LABELS = {
  EMAIL_IMPORTED: "E-posta içe aktarıldı",
  EMAIL_PROCESSED: "E-posta işlendi",
  EMAIL_ROUTED: "E-posta yönlendirildi",
  ROUTING_APPROVED: "Yönlendirme onaylandı",
  ROUTING_CORRECTED: "Yönlendirme düzeltildi",
  ATTACHMENT_UPLOADED: "Ek dosya yüklendi",
  MAILBOX_SYNCED: "Posta kutusu senkronize edildi",
  MODEL_TRAINED: "Model eğitildi",
  TICKET_CREATED: "Evrak/talep kaydı oluşturuldu",
  TICKET_UPDATED: "Evrak/talep kaydı güncellendi",
  INTEGRATION_TESTED: "Entegrasyon testi çalıştırıldı",
};

const LOG_DETAIL_LABELS = {
  "Email was manually imported into the system.":
    "E-posta manuel olarak sisteme alındı.",
  "Email was routed to the target department.":
    "E-posta hedef birime yönlendirildi.",
  "Email was automatically routed after classification.":
    "E-posta analizden sonra otomatik olarak ilgili birime yönlendirildi.",
  "Email was classified and processing status was updated.":
    "E-posta sınıflandırıldı ve işlem durumu güncellendi.",
  "Email routing was approved by an operator.":
    "E-posta yönlendirmesi operatör tarafından onaylandı.",
  "Email routing was corrected and feedback was saved.":
    "E-posta yönlendirmesi düzeltildi ve geri bildirim kaydedildi.",
  "Attachment was uploaded and text extraction was attempted.":
    "Ek dosya yüklendi ve metin çıkarma denendi.",
  "Trainable email classifier was trained.":
    "Eğitilebilir e-posta sınıflandırma modeli eğitildi.",
  "Synthetic mailbox was synchronized.":
    "Sentetik posta kutusu senkronize edildi.",
  "Mailbox synchronized successfully.":
    "Posta kutusu bağlayıcı üzerinden senkronize edildi.",
  "Ticket record was created or updated for the email.":
    "E-posta için evrak/talep kaydı oluşturuldu veya güncellendi.",
  "Ticket record was updated.": "Evrak/talep kaydı güncellendi.",
};

const CONNECTOR_STATUS_LABELS = {
  ready: "Hazır",
  planned: "Planlandı",
  configuration_required: "Konfigürasyon gerekli",
};

const ACTOR_LABELS = {
  operator: "Operatör",
  admin: "Yönetici",
  mailbox_sync: "Posta kutusu",
  system: "Sistem",
};

const DECISION_SOURCE_LABELS = {
  "Rule-based priority": "Kural tabanlı öncelik",
  "Rule + AI agreement": "Kural ve yapay zeka uyumu",
  "Rule-based result": "Kural tabanlı sonuç",
  "Human review required": "İnsan incelemesi gerekli",
};

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

const INTEGRATION_ROADMAP_STEPS = [
  {
    label: "Posta Kutusu",
    title: "webmaster@rekabet.gov.tr",
    detail: "Exchange, Outlook veya IMAP üzerinden ortak kutu",
  },
  {
    label: "Analiz Katmanı",
    title: "Ön İşleme ve Ek Analizi",
    detail: "Gövde, ek metni, OCR çıktısı ve güvenlik uyarıları",
  },
  {
    label: "Kurumsal Kayıt",
    title: "EBYS / Evrak Kaydı",
    detail: "Kayıt numarası, başvuru türü, birim ve SLA",
  },
  {
    label: "Dış Sistemler",
    title: "SIEM, DMS, Bildirim",
    detail: "Denetim izi, dosya arşivi ve birim bilgilendirmesi",
  },
];

const TRAINING_PIPELINE_STEPS = [
  {
    label: "Veri",
    title: "Etiketli e-postalar",
    detail: "Sentetik örnekler ve operatör düzeltmeleri eğitim setine alınır.",
  },
  {
    label: "Metin",
    title: "Ön işleme",
    detail: "Konu, gövde, gönderen ve ek metinleri tek sınıflandırma metnine çevrilir.",
  },
  {
    label: "Özellik",
    title: "TF-IDF",
    detail: "Sık geçen ama ayırt edici kelime ve ikili kelime grupları ağırlıklandırılır.",
  },
  {
    label: "Model",
    title: "Lojistik regresyon",
    detail: "Kategori, birim ve öncelik için ayrı tahmin modeli eğitilir.",
  },
];

function formatPercent(value) {
  if (typeof value !== "number") {
    return "-";
  }

  return `${Math.round(value * 100)}%`;
}

function formatMailboxDisplay(mailbox) {
  if (!mailbox) {
    return "-";
  }

  return mailbox.replace("@rekabet.gov.tr", "");
}

function formatSeconds(value) {
  if (typeof value !== "number") {
    return "Veri yok";
  }

  if (value < 60) {
    return `${Math.round(value)} sn`;
  }

  if (value >= 3600) {
    const hours = Math.floor(value / 3600);
    const minutes = Math.round((value % 3600) / 60);

    return `${hours} sa ${minutes} dk`;
  }

  const minutes = Math.floor(value / 60);
  const seconds = Math.round(value % 60);

  return `${minutes} dk ${seconds} sn`;
}

function formatDate(value) {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
  }).format(new Date(value));
}

function formatRemainingDays(value) {
  if (typeof value !== "number") {
    return "-";
  }

  if (value < 0) {
    return `${Math.abs(value)} gün gecikti`;
  }

  if (value === 0) {
    return "Bugün";
  }

  return `${value} gün`;
}

function getStatusLabel(status) {
  return STATUS_LABELS[status] || status || "Yeni";
}

function getSlaLabel(status) {
  return SLA_LABELS[status] || status || "-";
}

function getLogActionLabel(action) {
  return LOG_ACTION_LABELS[action] || action;
}

function getLogDetailLabel(detail) {
  return LOG_DETAIL_LABELS[detail] || detail;
}

function getActorLabel(actor) {
  return ACTOR_LABELS[actor] || actor;
}

function getDecisionSourceLabel(source) {
  return DECISION_SOURCE_LABELS[source] || source;
}

function getAttachmentRiskTone(attachment) {
  if (
    attachment?.risk_level === "Kritik" ||
    attachment?.malware_risk === "Şüpheli"
  ) {
    return "danger";
  }

  if (
    attachment?.risk_level === "Yüksek" ||
    attachment?.risk_level === "Orta" ||
    attachment?.contains_personal_data ||
    attachment?.requires_human_review
  ) {
    return "warning";
  }

  return "success";
}

function getAttachmentTextStatus(filename, attachmentTexts = []) {
  const attachmentText = attachmentTexts.find((item) => item.filename === filename);

  return attachmentText?.status || "Metin bekleniyor";
}

function getAttachmentFileTypeLabel(fileType) {
  const labels = {
    "Word Document": "Word belgesi",
    Spreadsheet: "Excel / tablo",
    PowerPoint: "PowerPoint",
    "Image / Scanned Document": "Görsel / taranmış belge",
    "Compressed Archive": "Sıkıştırılmış arşiv",
    "Signed / Official Document": "E-imzalı / resmi belge",
    Unknown: "Bilinmeyen tür",
  };

  return labels[fileType] || fileType || "-";
}

function buildAttachmentGateStats(attachmentAnalysis = {}, attachmentTexts = []) {
  const attachments = attachmentAnalysis.attachments || [];
  const extractedTextFilenames = new Set(
    attachmentTexts
      .filter((item) => item.extracted_text)
      .map((item) => item.filename)
  );

  return {
    total: attachmentAnalysis.attachment_count || attachments.length,
    ocrRequired: attachments.filter((attachment) => attachment.ocr_required).length,
    suspicious: attachments.filter(
      (attachment) =>
        attachment.malware_risk === "Şüpheli" ||
        ["Kritik", "Yüksek"].includes(attachment.risk_level)
    ).length,
    personalData: attachments.filter(
      (attachment) => attachment.contains_personal_data
    ).length,
    encrypted: attachments.filter((attachment) => attachment.is_encrypted).length,
    extractedText: attachments.filter((attachment) =>
      extractedTextFilenames.has(attachment.filename)
    ).length,
  };
}

function getRolePolicy(role) {
  return ROLE_OPTIONS.find((option) => option.role === role) || ROLE_OPTIONS[1];
}

function getSlaSortRank(email) {
  const status = email?.sla?.status;

  if (status === "Overdue") {
    return 0;
  }

  if (status === "Due soon") {
    return 1;
  }

  if (status === "On time") {
    return 2;
  }

  return 3;
}

function getDistributionEntries(distribution = {}) {
  return Object.entries(distribution)
    .filter(([, count]) => count > 0)
    .sort(([, firstCount], [, secondCount]) => secondCount - firstCount);
}

function buildTrainingExampleDistribution(examples = [], field) {
  return examples.reduce((distribution, example) => {
    const label = example.corrected_label?.[field] || example[field];

    if (!label) {
      return distribution;
    }

    return {
      ...distribution,
      [label]: (distribution[label] || 0) + 1,
    };
  }, {});
}

function getModelTypeLabel(modelType) {
  if (!modelType) {
    return "TF-IDF + Lojistik Regresyon";
  }

  return modelType.replace("Logistic Regression", "Lojistik Regresyon");
}

function matchesQueueSearch(email, searchTerm) {
  if (!searchTerm) {
    return true;
  }

  const searchableText = [
    email.subject,
    email.sender,
    email.source_mailbox,
    email.routing_status,
    getStatusLabel(email.routing_status),
    email.sla?.status_label,
  ]
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase("tr-TR");

  return searchableText.includes(searchTerm);
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
  const routingStatus = email?.routing_status || "New";
  const confidence = classification.confidence_score || 0;
  const needsReview = Boolean(classification.requires_human_review);
  const hasAttachment = Boolean(email?.has_attachment);
  const isRouted = routingStatus === "Routed";
  const isClosed = ["Completed", "Archived"].includes(routingStatus);

  const nodes = [
    createWorkflowNode(
      "received",
      "E-posta Alındı",
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
      color: needsReview && target === "review" ? "#b42318" : "#111827",
    },
    style: {
      stroke: needsReview && target === "review" ? "#b42318" : "#111827",
      strokeWidth: 2,
    },
  }));

  return { nodes, edges };
}

function createFallbackPipelineStep(id, order, title, status, detail, evidence = []) {
  const labels = {
    completed: "Tamamlandı",
    active: "İşlemde",
    review: "İnceleme gerekli",
    warning: "Uyarı",
    waiting: "Bekliyor",
    skipped: "Atlandı",
  };

  return {
    id,
    order,
    title,
    status,
    status_label: labels[status] || status,
    detail,
    evidence,
  };
}

function buildFallbackPipeline(email, classification, analysis, preprocessing, ticket) {
  if (!email || !classification?.category || !analysis?.summary) {
    return null;
  }

  const hasAttachment = Boolean(email.has_attachment);
  const attachmentAnalysis = analysis.attachment_analysis || {};
  const needsReview =
    Boolean(classification.requires_human_review) ||
    email.routing_status === "Pending Review";
  const isRouted = ["Routed", "Approved", "Corrected"].includes(
    email.routing_status
  );
  const classificationStatus = isRouted || !needsReview ? "completed" : "review";

  const steps = [
    createFallbackPipelineStep(
      "received",
      1,
      "E-posta Alındı",
      "completed",
      "E-posta ortak posta kutusundan sisteme alındı.",
      [email.source_mailbox]
    ),
    createFallbackPipelineStep(
      "preprocessing",
      2,
      "Ön İşleme",
      "completed",
      "Gövde, imza, footer ve cevap zinciri ayrıştırıldı.",
      [`Dil: ${preprocessing.language || "Bilinmiyor"}`]
    ),
    createFallbackPipelineStep(
      "attachments",
      3,
      "Ek Analizi",
      hasAttachment ? "completed" : "skipped",
      hasAttachment
        ? `${attachmentAnalysis.attachment_count || 0} ek dosya incelendi.`
        : "Ek dosya bulunmadığı için adım atlandı.",
      hasAttachment ? [`Risk: ${attachmentAnalysis.overall_risk_level || "Düşük"}`] : []
    ),
    createFallbackPipelineStep(
      "security",
      4,
      "Güvenlik Kontrolü",
      hasAttachment ? "completed" : "skipped",
      hasAttachment
        ? "Ekler dosya türü, şifre ve kişisel veri sinyalleriyle kontrol edildi."
        : "Ek olmadığı için güvenlik kontrolü atlandı."
    ),
    createFallbackPipelineStep(
      "classification",
      5,
      "Sınıflandırma",
      classificationStatus,
      `${classification.category} kategorisi için ${classification.department} önerildi.`,
      [`Güven: ${formatPercent(classification.confidence_score)}`]
    ),
    createFallbackPipelineStep(
      "summary",
      6,
      "Özetleme",
      "completed",
      "Mail gövdesi ve ek sinyallerinden karar destek özeti üretildi.",
      [analysis.summary.slice(0, 180)]
    ),
    createFallbackPipelineStep(
      "routing",
      7,
      "Yönlendirme",
      isRouted ? "completed" : needsReview ? "review" : "active",
      analysis.routing_decision?.routing_type || "Yönlendirme kararı hazırlanıyor.",
      [classification.department]
    ),
    createFallbackPipelineStep(
      "ticket",
      8,
      "Evrak/Talep Kaydı",
      ticket ? "completed" : "waiting",
      ticket
        ? `${ticket.record_number} numaralı kayıt oluşturuldu.`
        : "Kayıt ihtiyacı yönlendirme kararına göre belirlenir."
    ),
    createFallbackPipelineStep(
      "notification",
      9,
      "Bildirim",
      isRouted ? "completed" : "waiting",
      isRouted
        ? "İlgili birim bilgilendirme adımına hazır."
        : "Bildirim için yönlendirme tamamlanmalı."
    ),
  ];
  const completedCount = steps.filter((step) =>
    ["completed", "skipped"].includes(step.status)
  ).length;
  const attentionCount = steps.filter((step) =>
    ["review", "warning", "active"].includes(step.status)
  ).length;

  return {
    summary: {
      step_count: steps.length,
      completed_count: completedCount,
      attention_count: attentionCount,
      progress_percent: completedCount / steps.length,
      current_step:
        steps.find((step) =>
          ["review", "warning", "active", "waiting"].includes(step.status)
        ) || steps[steps.length - 1],
    },
    steps,
    edges: steps.slice(0, -1).map((step, index) => ({
      source: step.id,
      target: steps[index + 1].id,
    })),
  };
}

function App() {
  const [emails, setEmails] = useState([]);
  const [selectedEmailId, setSelectedEmailId] = useState(null);
  const [details, setDetails] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [operationalDashboard, setOperationalDashboard] = useState(null);
  const [managementReport, setManagementReport] = useState(null);
  const [evaluationReport, setEvaluationReport] = useState(null);
  const [integrationOverview, setIntegrationOverview] = useState(null);
  const [ingestionOverview, setIngestionOverview] = useState(null);
  const [pendingReview, setPendingReview] = useState([]);
  const [feedbackData, setFeedbackData] = useState({
    feedback_count: 0,
    feedbacks: [],
  });
  const [trainingData, setTrainingData] = useState({
    training_example_count: 0,
    training_examples: [],
  });
  const [modelStatus, setModelStatus] = useState({
    is_trained: false,
    metadata: null,
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
  const [activeRole, setActiveRole] = useState("operator");
  const [activePage, setActivePage] = useState("operation");
  const [slaFilter, setSlaFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [queueSearch, setQueueSearch] = useState("");
  const [activeDetailTab, setActiveDetailTab] = useState("analysis");

  const selectedEmail = useMemo(
    () => emails.find((email) => email.id === selectedEmailId) || null,
    [emails, selectedEmailId]
  );
  const visibleEmails = useMemo(() => {
    const normalizedSearch = queueSearch.trim().toLocaleLowerCase("tr-TR");

    return emails
      .filter((email) => slaFilter === "all" || email.sla?.status === slaFilter)
      .filter(
        (email) =>
          statusFilter === "all" || (email.routing_status || "New") === statusFilter
      )
      .filter((email) => matchesQueueSearch(email, normalizedSearch))
      .sort((firstEmail, secondEmail) => {
        const rankDifference =
          getSlaSortRank(firstEmail) - getSlaSortRank(secondEmail);

        if (rankDifference !== 0) {
          return rankDifference;
        }

        return firstEmail.id - secondEmail.id;
      });
  }, [emails, queueSearch, slaFilter, statusFilter]);
  const activeRolePolicy = useMemo(
    () => getRolePolicy(activeRole),
    [activeRole]
  );
  const can = useCallback(
    (permission) => activeRolePolicy.permissions.includes(permission),
    [activeRolePolicy]
  );

  const request = useCallback(async function request(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `${path} returned ${response.status}`);
    }

    return data;
  }, []);

  const refreshWorkspace = useCallback(async function refreshWorkspace() {
    setErrorMessage("");

    try {
      const [
        emailData,
        dashboardData,
        operationalData,
        reportData,
        evaluationData,
        integrationData,
        ingestionData,
        pendingData,
        feedbackResult,
        trainingResult,
      ] =
        await Promise.all([
          request("/emails"),
          request("/emails/dashboard/summary"),
          request("/emails/dashboard/operational"),
          request("/emails/reports/management"),
          request("/emails/evaluation/report"),
          request("/emails/integrations/overview"),
          request("/emails/ingestion/overview"),
          request("/emails/review/pending"),
          request("/emails/feedback/all"),
          request("/emails/feedback/training-data"),
        ]);

      setEmails(emailData.emails || []);
      setDashboard(dashboardData);
      setOperationalDashboard(operationalData);
      setManagementReport(reportData);
      setEvaluationReport(evaluationData);
      setIntegrationOverview(integrationData);
      setIngestionOverview(ingestionData);
      setPendingReview(pendingData.pending_emails || []);
      setFeedbackData(feedbackResult);
      setTrainingData(trainingResult);

      setSelectedEmailId((currentEmailId) =>
        currentEmailId || emailData.emails?.[0]?.id || null
      );

      try {
        const modelData = await request("/emails/model/status");
        setModelStatus(modelData);
      } catch (error) {
        setModelStatus({
          is_trained: false,
          metadata: null,
          error: error.message,
        });
      }
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
      const [
        analysis,
        preprocessing,
        aiAnalysis,
        responseSuggestion,
        logData,
      ] =
        await Promise.all([
          request(`/emails/${emailId}/analysis`),
          request(`/emails/${emailId}/preprocess`),
          request(`/emails/${emailId}/ai-analysis`),
          request(`/emails/${emailId}/response-suggestion`),
          request(`/emails/${emailId}/logs`),
        ]);

      let modelPrediction = null;
      let ticket = null;
      let pipelineData = null;

      try {
        modelPrediction = await request(`/emails/${emailId}/model-prediction`);
      } catch {
        modelPrediction = null;
      }

      try {
        const ticketData = await request(`/emails/${emailId}/ticket`);
        ticket = ticketData.ticket;
      } catch {
        ticket = null;
      }

      try {
        pipelineData = await request(`/emails/${emailId}/pipeline`);
      } catch {
        pipelineData = null;
      }

      setDetails({
        analysis,
        preprocessing,
        aiAnalysis,
        responseSuggestion,
        pipeline: pipelineData,
        modelPrediction,
        ticket,
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
      // Seçili e-posta değişince türetilmiş analiz verileri yenilenir.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      fetchEmailDetails(selectedEmailId);
    }
  }, [fetchEmailDetails, selectedEmailId]);

  useEffect(() => {
    // Yeni kayıt seçildiğinde detay sekmesi karar özetinden başlar.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setActiveDetailTab("analysis");
  }, [selectedEmailId]);

  async function handleProcessEmail() {
    if (!selectedEmail) {
      return;
    }

    if (!can("process_email")) {
      setActionMessage("Bu rol e-posta işleme yetkisine sahip değil.");
      return;
    }

    await runEmailAction(
      `/emails/${selectedEmail.id}/process?actor_role=${activeRole}`,
      { method: "POST" },
      "E-posta işlendi ve sınıflandırma kaydedildi."
    );
  }

  async function handleApproveRouting() {
    if (!selectedEmail) {
      return;
    }

    if (!can("approve_routing")) {
      setActionMessage("Bu rol yönlendirme onayı veremez.");
      return;
    }

    await runEmailAction(
      `/emails/${selectedEmail.id}/approve-routing`,
      {
        method: "POST",
        body: JSON.stringify({
          approved_by: "operator",
          actor_role: activeRole,
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

    if (!can("route_email")) {
      setActionMessage("Bu rol e-posta yönlendiremez.");
      return;
    }

    await runEmailAction(
      `/emails/${selectedEmail.id}/route`,
      {
        method: "POST",
        body: JSON.stringify({
          routed_by: "operator",
          actor_role: activeRole,
          target_department:
            details?.analysis?.classification?.department || undefined,
          routing_note: "Panel üzerinden ilgili birim havuzuna aktarıldı.",
        }),
      },
      "E-posta ilgili birim havuzuna yönlendirildi."
    );
  }

  async function handleCorrectRouting(event) {
    event.preventDefault();

    if (!selectedEmail) {
      return;
    }

    if (!can("correct_routing")) {
      setActionMessage("Bu rol yanlış yönlendirme düzeltmesi yapamaz.");
      return;
    }

    await runEmailAction(
      `/emails/${selectedEmail.id}/correct-routing`,
      {
        method: "POST",
        body: JSON.stringify({
          ...correctionForm,
          corrected_by: "operator",
          actor_role: activeRole,
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

    if (!can("import_email")) {
      setActionMessage("Bu rol manuel e-posta içe aktaramaz.");
      return;
    }

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
          actor_role: activeRole,
        }),
      });

      setImportForm(EMPTY_IMPORT_FORM);
      setSelectedEmailId(created.imported_email.id);
      setActionMessage("Sentetik e-posta içe aktarıldı ve işlendi.");
      await refreshWorkspace();
    } catch (error) {
      setErrorMessage(error.message);
    }
  }

  async function handleMailboxSync() {
    setActionMessage("");
    setErrorMessage("");

    if (!can("import_email")) {
      setActionMessage("Bu rol posta kutusu senkronizasyonu yapamaz.");
      return;
    }

    try {
      const result = await request("/emails/ingestion/sync", {
        method: "POST",
        body: JSON.stringify({
          source_mailbox: "webmaster@rekabet.gov.tr",
          connector_id: "synthetic_demo",
          limit: 5,
          actor_role: activeRole,
          process_after_import: true,
        }),
      });

      const firstImportedEmail = result.imported_emails?.[0];

      if (firstImportedEmail) {
        setSelectedEmailId(firstImportedEmail.id);
      }

      setActionMessage(
        result.imported_count > 0
          ? `${result.imported_count} e-posta alındı, analiz edildi ve uygun akışa yönlendirildi.`
          : "Webmaster posta kutusunda yeni e-posta yok."
      );
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

    if (!can("upload_attachment")) {
      setActionMessage("Bu rol ek dosya yükleyemez.");
      return;
    }

    setActionMessage("");
    setErrorMessage("");

    const formData = new FormData();
    formData.append("file", selectedAttachmentFile);
    formData.append("uploaded_by", activeRolePolicy.label);
    formData.append("actor_role", activeRole);

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
    if (!can("view_training_data")) {
      setActionMessage("Bu rol eğitim verisi dışa aktaramaz.");
      return;
    }

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
    setActionMessage("Eğitim verisi dosyası hazırlandı.");
  }

  async function handleTrainModel() {
    if (!can("view_training_data")) {
      setActionMessage("Bu rol model eğitimi başlatamaz.");
      return;
    }

    setActionMessage("");
    setErrorMessage("");

    try {
      const result = await request("/emails/model/train", {
        method: "POST",
        body: JSON.stringify({
          actor_role: activeRole,
        }),
      });

      setModelStatus({
        is_trained: true,
        model_path: result.model_path,
        metadata: result.metadata,
      });
      setActionMessage(
        `Model ${result.metadata.training_example_count} örnekle eğitildi.`
      );

      if (selectedEmailId) {
        await fetchEmailDetails(selectedEmailId);
      }
    } catch (error) {
      setErrorMessage(error.message);
    }
  }

  async function handleIntegrationTest(integrationId) {
    setActionMessage("");
    setErrorMessage("");

    if (!can("view_dashboard")) {
      setActionMessage("Bu rol entegrasyon testi çalıştıramaz.");
      return;
    }

    try {
      const result = await request(`/emails/integrations/${integrationId}/test`, {
        method: "POST",
        body: JSON.stringify({
          actor_role: activeRole,
        }),
      });

      setActionMessage(
        `${result.connection_test.name} bağlantı testi: ${result.connection_test.status}.`
      );
      await refreshWorkspace();
    } catch (error) {
      setErrorMessage(error.message);
    }
  }

  async function handleCreateTicket() {
    if (!selectedEmail) {
      return;
    }

    await runEmailAction(
      `/emails/${selectedEmail.id}/ticket`,
      {
        method: "POST",
        body: JSON.stringify({
          actor_role: activeRole,
        }),
      },
      "Evrak/talep kaydı oluşturuldu."
    );
  }

  async function handleAdvanceTicketStatus(ticket) {
    const nextStatusByCurrentStatus = {
      Yeni: "İşlemde",
      Sınıflandırıldı: "İşlemde",
      "Onay bekliyor": "Birimine yönlendirildi",
      "Birimine yönlendirildi": "İşlemde",
      İşlemde: "Cevap bekleniyor",
      "Cevap bekleniyor": "Tamamlandı",
    };
    const nextStatus = nextStatusByCurrentStatus[ticket.status] || "İşlemde";

    await runEmailAction(
      `/emails/tickets/${ticket.id}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          status: nextStatus,
          note: `${ticket.status} durumundan ${nextStatus} durumuna alındı.`,
          actor_role: activeRole,
        }),
      },
      "Evrak/talep kaydı güncellendi."
    );
  }

  const classification = details?.analysis?.classification || {};
  const analysis = details?.analysis?.analysis || {};
  const preprocessing = details?.preprocessing?.preprocessing || {};
  const sla = analysis?.sla || {};
  const extracted = details?.analysis?.extracted_information || {};
  const attachmentAnalysis = analysis?.attachment_analysis || {};
  const attachmentTexts = selectedEmail?.attachment_texts || [];
  const pipeline =
    details?.pipeline?.pipeline ||
    buildFallbackPipeline(
      selectedEmail,
      classification,
      analysis,
      preprocessing,
      details?.ticket
    );
  const pipelineSummary = pipeline?.summary || {};
  const attachmentGateStats = buildAttachmentGateStats(
    attachmentAnalysis,
    attachmentTexts
  );
  const responseSuggestion =
    details?.responseSuggestion?.response_suggestion || {};
  const ticket = details?.ticket;
  const aiAnalysis = details?.aiAnalysis?.ai_analysis || {};
  const trainedModelPrediction =
    details?.modelPrediction?.model_prediction?.prediction || {};
  const ruleBasedClassification = aiAnalysis.rule_based_classification || {};
  const llmClassification =
    aiAnalysis.llm_classification || aiAnalysis.mock_ai_classification || {};
  const llmConnection = aiAnalysis.llm_connection || {};
  const reportKpis = managementReport?.kpis || {};
  const evaluationSummary = evaluationReport?.summary || {};
  const integrationSummary = integrationOverview?.summary || {};
  const modelMetadata = modelStatus.metadata || {};
  const modelLabelDistribution = modelMetadata.label_distribution || {};
  const totalTrainingExamples =
    modelMetadata.training_example_count ??
    trainingData.training_example_count ??
    0;
  const feedbackTrainingExamples =
    modelMetadata.feedback_example_count ??
    trainingData.training_example_count ??
    0;
  const seedTrainingExamples =
    modelMetadata.seed_example_count ??
    Math.max(totalTrainingExamples - feedbackTrainingExamples, 0);
  const trainingCategoryDistribution =
    modelLabelDistribution.category ||
    buildTrainingExampleDistribution(trainingData.training_examples, "category");
  const trainingDepartmentDistribution =
    modelLabelDistribution.department ||
    buildTrainingExampleDistribution(trainingData.training_examples, "department");
  const trainingPriorityDistribution =
    modelLabelDistribution.priority ||
    buildTrainingExampleDistribution(trainingData.training_examples, "priority");
  const integrations = integrationOverview?.integrations || [];
  const priorityIntegrationIds = [
    "exchange_outlook",
    "ebys",
    "antivirus",
    "object_storage",
    "siem",
    "webhook_api",
  ];
  const priorityIntegrations = integrations.filter((integration) =>
    priorityIntegrationIds.includes(integration.id)
  );
  const identityIntegrations = integrations.filter(
    (integration) => integration.group === "Kimlik ve Yetki"
  );
  const remainingIntegrations = integrations.filter(
    (integration) =>
      !priorityIntegrationIds.includes(integration.id) &&
      integration.group !== "Kimlik ve Yetki"
  );
  const workflowGraph = buildWorkflowGraph(
    selectedEmail,
    classification,
    analysis,
    attachmentAnalysis
  );

  if (loading) {
    return <div className="page-loading">Panel yükleniyor...</div>;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <span className="rk-mark" aria-hidden="true">RK</span>
          <div>
            <p className="eyebrow">Rekabet Kurumu</p>
            <h1>Kurumsal E-Posta Operasyon Paneli</h1>
          </div>
        </div>
        <div className="topbar-actions">
          <label className="role-selector">
            Aktif Rol
            <select
              value={activeRole}
              onChange={(event) => setActiveRole(event.target.value)}
            >
              {ROLE_OPTIONS.map((roleOption) => (
                <option key={roleOption.role} value={roleOption.role}>
                  {roleOption.label}
                </option>
              ))}
            </select>
          </label>
          <button className="secondary-button" onClick={refreshWorkspace}>
            Yenile
          </button>
        </div>
      </header>

      {errorMessage && <div className="alert danger">{errorMessage}</div>}
      {actionMessage && <div className="alert success">{actionMessage}</div>}

      <nav className="page-tabs" aria-label="Ana modüller">
        {PAGE_TABS.map((page) => (
          <button
            key={page.value}
            className={activePage === page.value ? "active" : ""}
            data-page={page.value}
            type="button"
            onClick={() => setActivePage(page.value)}
          >
            {page.label}
          </button>
        ))}
      </nav>

      {activePage === "operation" && (
        <section className="overview-section" aria-label="Operasyon özeti">
          <div className="metrics-grid" aria-label="Panel metrikleri">
            <Metric label="Toplam e-posta" value={dashboard?.total_emails ?? 0} />
            <Metric
              label="Kritik risk"
              value={dashboard?.critical_risk_count ?? 0}
              tone="danger"
            />
            <Metric
              label="Doğruluk"
              value={formatPercent(dashboard?.accuracy)}
              tone="success"
            />
            <Metric
              label="Onay bekleyen"
              value={operationalDashboard?.pending_review_count ?? 0}
              tone="warning"
            />
            <Metric
              label="SLA aşımı"
              value={dashboard?.sla_overdue_count ?? 0}
              tone="danger"
            />
            <Metric
              label="Yönlendirilen"
              value={operationalDashboard?.routing_status_distribution?.Routed ?? 0}
              tone="success"
            />
          </div>
        </section>
      )}

      {activePage === "pipeline" && (
        <section className="pipeline-page page-panel" aria-label="İşlem hattı">
          <div className="panel-heading compact-heading">
            <div>
              <p className="eyebrow">Süreç Takibi</p>
              <h2>E-posta İşlem Hattı</h2>
            </div>
            <label className="pipeline-selector">
              Kayıt
              <select
                value={selectedEmailId || ""}
                onChange={(event) =>
                  setSelectedEmailId(Number(event.target.value) || null)
                }
              >
                {(emails || []).map((email) => (
                  <option key={email.id} value={email.id}>
                    {email.subject}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {!selectedEmail && (
            <div className="empty-state">
              <h2>Süreç görüntülenecek kayıt yok</h2>
              <p>Önce bir e-posta içe aktar veya gelen kayıt seç.</p>
            </div>
          )}

          {selectedEmail && (
            <>
              <div className="pipeline-overview-card">
                <div>
                  <span>Seçili e-posta</span>
                  <strong>{selectedEmail.subject}</strong>
                  <p>{selectedEmail.sender}</p>
                </div>
                <div className="pipeline-overview-meta">
                  <Meta
                    label="Kaynak kutu"
                    value={formatMailboxDisplay(selectedEmail.source_mailbox)}
                  />
                  <Meta
                    label="Durum"
                    value={getStatusLabel(selectedEmail.routing_status)}
                  />
                  <Meta
                    label="Geçerli adım"
                    value={pipelineSummary.current_step?.title || "Yükleniyor"}
                  />
                </div>
              </div>

              <div className="pipeline-summary-grid">
                <Metric
                  label="Tamamlanan adım"
                  value={
                    pipeline
                      ? `${pipelineSummary.completed_count}/${pipelineSummary.step_count}`
                      : "Yükleniyor"
                  }
                  tone="success"
                />
                <Metric
                  label="İlerleme"
                  value={
                    pipeline
                      ? formatPercent(pipelineSummary.progress_percent)
                      : "Yükleniyor"
                  }
                  tone="success"
                />
                <Metric
                  label="Dikkat isteyen"
                  value={pipeline ? pipelineSummary.attention_count : "Yükleniyor"}
                  tone={pipelineSummary.attention_count ? "warning" : "success"}
                />
              </div>

              {pipeline ? (
                <>
                  <div className="pipeline-strip">
                    {pipeline.steps.map((step) => (
                      <article className={`pipeline-strip-step ${step.status}`} key={step.id}>
                        <span>{String(step.order).padStart(2, "0")}</span>
                        <strong>{step.title}</strong>
                        <em>{step.status_label}</em>
                      </article>
                    ))}
                  </div>

                  <div className="pipeline-step-grid">
                    {pipeline.steps.map((step) => (
                      <article
                        className={`pipeline-step-card ${step.status}`}
                        key={step.id}
                      >
                        <div className="pipeline-step-head">
                          <span>{String(step.order).padStart(2, "0")}</span>
                          <strong>{step.status_label}</strong>
                        </div>
                        <h3>{step.title}</h3>
                        <p>{step.detail}</p>
                        {step.evidence?.length > 0 && (
                          <div className="pipeline-evidence">
                            {step.evidence.slice(0, 2).map((item, index) => (
                              <span key={`${step.id}-${index}`}>{item}</span>
                            ))}
                          </div>
                        )}
                        {step.action && (
                          <div className="pipeline-action">{step.action}</div>
                        )}
                      </article>
                    ))}
                  </div>
                </>
              ) : (
                <div className="pipeline-loading-card">
                  Süreç verisi hazırlanıyor.
                </div>
              )}
            </>
          )}
        </section>
      )}

      {activePage === "reports" && (
        <section className="reporting-section" aria-label="Yönetim raporlama">
        <div className="panel-heading compact-heading">
          <div>
            <p className="eyebrow">Raporlama Modülü</p>
            <h2>Yönetim Raporlama</h2>
          </div>
          <span>{formatDate(managementReport?.generated_at)}</span>
        </div>

        <div className="report-kpi-grid">
          <ReportMetric
            label="Bugün gelen mail"
            value={reportKpis.today_email_count ?? 0}
          />
          <ReportMetric
            label="Otomatik sınıflandırılan"
            value={reportKpis.classified_count ?? 0}
          />
          <ReportMetric
            label="Operatör onayına düşen"
            value={reportKpis.pending_review_count ?? 0}
            tone="warning"
          />
          <ReportMetric
            label="Kritik işaretlenen"
            value={reportKpis.critical_risk_count ?? 0}
            tone="danger"
          />
          <ReportMetric
            label="Hatalı yönlendirme"
            value={reportKpis.wrong_routing_count ?? 0}
            tone="danger"
          />
          <ReportMetric
            label="Ortalama yönlendirme"
            value={formatSeconds(reportKpis.average_routing_seconds)}
            tone="success"
          />
          <ReportMetric
            label="Yapay zeka doğruluğu"
            value={formatPercent(reportKpis.ai_accuracy_rate)}
            tone="success"
          />
          <ReportMetric
            label="Operatör müdahalesi"
            value={formatPercent(reportKpis.operator_intervention_rate)}
            tone="warning"
          />
          <ReportMetric
            label="SLA aşımı"
            value={reportKpis.sla_overdue_count ?? 0}
            tone="danger"
          />
          <ReportMetric
            label="Spam / otomatik"
            value={reportKpis.spam_or_automatic_count ?? 0}
          />
        </div>

        <div className="report-grid">
          <div className="report-card">
            <h3>Bekleyen İşler</h3>
            {managementReport?.action_items?.length > 0 ? (
              managementReport.action_items.map((item) => (
                <div className={`action-item ${item.tone}`} key={item.label}>
                  <strong>{item.count}</strong>
                  <div>
                    <span>{item.label}</span>
                    <p>{item.recommendation}</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="muted">Aksiyon gerektiren kayıt yok.</p>
            )}
          </div>

          <div className="report-card">
            <h3>Günlük Gelen Mail</h3>
            <ReportBars entries={managementReport?.daily_volume} labelKey="date" />
          </div>

          <div className="report-card">
            <h3>Birim Bazlı İş Yükü</h3>
            <DistributionList
              title="Birim"
              distribution={managementReport?.department_workload}
            />
          </div>

          <div className="report-card">
            <h3>Konu Bazlı Dağılım</h3>
            <DistributionList
              title="Talep türü"
              distribution={managementReport?.category_distribution}
            />
          </div>
        </div>

        <div className="mailbox-report">
          <div className="panel-heading compact-heading">
            <h3>Posta Kutusu Performansı</h3>
            <span>Ortak kutu ve birim kutusu bazlı görünüm</span>
          </div>
          <div className="mailbox-report-table">
            <span>Kutu</span>
            <span>Toplam</span>
            <span>Otomatik</span>
            <span>Onay</span>
            <span>SLA aşımı</span>
            <span>Kritik</span>
            {(managementReport?.mailbox_performance || []).map((row) => (
              <div className="mailbox-report-row" key={row.mailbox}>
                <strong>{row.mailbox}</strong>
                <span>{row.total}</span>
                <span>{row.auto_routed}</span>
                <span>{row.pending_review}</span>
                <span>{row.overdue}</span>
                <span>{row.critical}</span>
              </div>
            ))}
          </div>
        </div>
        </section>
      )}

      {activePage === "evaluation" && (
        <section className="reporting-section" aria-label="Değerlendirme metrikleri">
          <div className="panel-heading compact-heading">
            <div>
              <p className="eyebrow">Değerlendirme Modülü</p>
              <h2>Başarı Metrikleri</h2>
            </div>
            <span>{formatDate(evaluationReport?.generated_at)}</span>
          </div>

          <div className="report-kpi-grid">
            <ReportMetric
              label="Etiketli e-posta"
              value={evaluationSummary.labeled_email_count ?? 0}
            />
            <ReportMetric
              label="Tam eşleşme"
              value={formatPercent(evaluationSummary.exact_match_rate)}
              tone="success"
            />
            <ReportMetric
              label="Kategori doğruluğu"
              value={formatPercent(evaluationSummary.category_accuracy_rate)}
              tone="success"
            />
            <ReportMetric
              label="Birim doğruluğu"
              value={formatPercent(evaluationSummary.department_accuracy_rate)}
              tone="success"
            />
            <ReportMetric
              label="Öncelik doğruluğu"
              value={formatPercent(evaluationSummary.priority_accuracy_rate)}
              tone="success"
            />
            <ReportMetric
              label="Hatalı eşleşme"
              value={evaluationSummary.wrong_match_count ?? 0}
              tone="danger"
            />
            <ReportMetric
              label="Düşük güven"
              value={evaluationSummary.low_confidence_count ?? 0}
              tone="warning"
            />
            <ReportMetric
              label="Düzeltme oranı"
              value={formatPercent(evaluationSummary.feedback_misdirection_rate)}
              tone="warning"
            />
          </div>

          <div className="report-grid evaluation-grid">
            <div className="report-card">
              <h3>Kategori Performansı</h3>
              {(evaluationReport?.category_performance || []).length > 0 ? (
                <div className="evaluation-list">
                  {evaluationReport.category_performance.map((row) => (
                    <div className="evaluation-row" key={row.category}>
                      <div>
                        <strong>{row.category}</strong>
                        <span>
                          {row.correct}/{row.total} doğru
                        </span>
                      </div>
                      <em>{formatPercent(row.accuracy_rate)}</em>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">Etiketli kategori verisi yok.</p>
              )}
            </div>

            <div className="report-card">
              <h3>Karışan Kategoriler</h3>
              {(evaluationReport?.confusion_pairs || []).length > 0 ? (
                <div className="evaluation-list">
                  {evaluationReport.confusion_pairs.map((row) => (
                    <div className="evaluation-row" key={row.pair}>
                      <strong>{row.pair}</strong>
                      <em>{row.count}</em>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">Kategori karışması görünmüyor.</p>
              )}
            </div>

            <div className="report-card">
              <h3>Güven Dağılımı</h3>
              <DistributionList
                title="Güven seviyesi"
                distribution={evaluationReport?.confidence_distribution}
              />
            </div>

            <div className="report-card">
              <h3>İyileştirme Önerileri</h3>
              <ListBlock items={evaluationReport?.recommendations} />
            </div>
          </div>

          <div className="report-grid evaluation-grid compact-evaluation-grid">
            <div className="report-card">
              <h3>Birim Düzeltmeleri</h3>
              <EvaluationCorrectionList
                rows={
                  evaluationReport?.feedback_corrections
                    ?.department_corrections
                }
              />
            </div>

            <div className="report-card">
              <h3>Kategori Düzeltmeleri</h3>
              <EvaluationCorrectionList
                rows={
                  evaluationReport?.feedback_corrections?.category_corrections
                }
              />
            </div>

            <div className="report-card">
              <h3>Öncelik Düzeltmeleri</h3>
              <EvaluationCorrectionList
                rows={
                  evaluationReport?.feedback_corrections?.priority_corrections
                }
              />
            </div>
          </div>

          <div className="mailbox-report">
            <div className="panel-heading compact-heading">
              <h3>Örnek Hatalar</h3>
              <span>Beklenen sonuç ile sistem tahmini karşılaştırması</span>
            </div>
            <div className="evaluation-table">
              <span>E-posta</span>
              <span>Beklenen kategori</span>
              <span>Tahmin</span>
              <span>Birim</span>
              <span>Güven</span>
              {(evaluationReport?.sample_errors || []).length > 0 ? (
                evaluationReport.sample_errors.map((row) => (
                  <div className="evaluation-table-row" key={row.email_id}>
                    <strong>#{row.email_id} {row.subject}</strong>
                    <span>{row.expected_category}</span>
                    <span>{row.predicted_category}</span>
                    <span>{row.predicted_department}</span>
                    <span>{formatPercent(row.confidence_score)}</span>
                  </div>
                ))
              ) : (
                <div className="evaluation-table-empty">
                  Etiketli veri üzerinde örnek hata görünmüyor.
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {activePage === "integrations" && (
        <section className="integrations-page page-panel" aria-label="Entegrasyonlar">
          <div className="panel-heading compact-heading">
            <div>
              <p className="eyebrow">Entegrasyon Modülü</p>
              <h2>Kurumsal Bağlantı Hazırlığı</h2>
            </div>
            <span>{formatDate(integrationOverview?.generated_at)}</span>
          </div>

          <div className="integration-readiness">
            <div>
              <span>Ortam</span>
              <strong>Sentetik test</strong>
              <p>Canlı kurum bilgisi bekleniyor</p>
            </div>
            <div>
              <span>Kaynak kutu</span>
              <strong>webmaster@rekabet.gov.tr</strong>
              <p>Ortak posta kutusu senaryosu</p>
            </div>
            <div>
              <span>Hazır sözleşme</span>
              <strong>{integrationSummary.ready_count ?? 0}</strong>
              <p>Test edilebilir bağlantı tanımı</p>
            </div>
            <div>
              <span>Plan bekleyen</span>
              <strong>{integrationSummary.planned_count ?? 0}</strong>
              <p>Uç nokta veya yetki bekliyor</p>
            </div>
          </div>

          <div className="integration-flow-strip" aria-label="Entegrasyon akışı">
            {INTEGRATION_ROADMAP_STEPS.map((step) => (
              <div className="integration-flow-step" key={step.label}>
                <span>{step.label}</span>
                <strong>{step.title}</strong>
                <p>{step.detail}</p>
              </div>
            ))}
          </div>

          <div className="integration-summary-grid">
            <ReportMetric
              label="Toplam bağlantı"
              value={integrationSummary.total_integrations ?? 0}
            />
            <ReportMetric
              label="İçe aktarım"
              value={integrationSummary.inbound_count ?? 0}
              tone="success"
            />
            <ReportMetric
              label="Dışa aktarım"
              value={integrationSummary.outbound_count ?? 0}
            />
            <ReportMetric
              label="Sentetik çalışan"
              value={integrationSummary.simulated_count ?? 0}
              tone="warning"
            />
            <ReportMetric
              label="Ortalama sağlık"
              value={formatPercent((integrationSummary.average_health ?? 0) / 100)}
              tone="success"
            />
          </div>

          <div className="integration-focus-grid">
            <div className="integration-inventory">
              <div className="panel-heading compact-heading">
                <h3>Kritik Bağlantılar</h3>
                <span>Webmaster kutusundan evrak ve denetim sistemlerine giden yol</span>
              </div>
              <div className="integration-card-grid">
                {priorityIntegrations.map((integration) => (
                  <IntegrationCard
                    integration={integration}
                    key={integration.id}
                    onTest={handleIntegrationTest}
                    testDisabled={!can("view_dashboard")}
                  />
                ))}
              </div>
            </div>

            <aside className="integration-side-panel">
              <div className="compact-section">
                <h3>Birim Eşleştirme</h3>
                {(integrationOverview?.directory_units || []).map((unit) => (
                  <div className="directory-row" key={unit.unit}>
                    <strong>{unit.unit}</strong>
                    <span>{unit.mailbox}</span>
                    <p>
                      {unit.synthetic_users} kullanıcı · {unit.routing_role}
                    </p>
                  </div>
                ))}
              </div>

              <div className="compact-section">
                <h3>Veri Akışı</h3>
                {(integrationOverview?.data_flows || []).map((flow) => (
                  <div className="flow-row" key={`${flow.source}-${flow.target}`}>
                    <div>
                      <strong>{flow.source}</strong>
                      <span>{flow.target}</span>
                    </div>
                    <p>{flow.payload}</p>
                    <em>{flow.status}</em>
                  </div>
                ))}
              </div>
            </aside>
          </div>

          <div className="integration-secondary-grid">
            <div className="integration-inventory">
              <div className="panel-heading compact-heading">
                <h3>Kimlik ve Yetki</h3>
                <span>Kurumsal kullanıcı ve rol aktarımı</span>
              </div>
              <div className="integration-card-grid compact-cards">
                {identityIntegrations.map((integration) => (
                  <IntegrationCard
                    integration={integration}
                    key={integration.id}
                    onTest={handleIntegrationTest}
                    testDisabled={!can("view_dashboard")}
                  />
                ))}
              </div>
            </div>

            <div className="integration-inventory">
              <div className="panel-heading compact-heading">
                <h3>Destekleyici Sistemler</h3>
                <span>Bildirim, KEP ve iş takip bağlantıları</span>
              </div>
              <div className="integration-card-grid compact-cards">
                {remainingIntegrations.map((integration) => (
                  <IntegrationCard
                    integration={integration}
                    key={integration.id}
                    onTest={handleIntegrationTest}
                    testDisabled={!can("view_dashboard")}
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="integration-control-grid">
            <div className="compact-section">
              <h3>Güvenlik Kontrolleri</h3>
              <div className="security-list">
                {(integrationOverview?.security_controls || []).map((control) => (
                  <div className="security-row" key={control.name}>
                    <strong>{control.name}</strong>
                    <span>{control.status}</span>
                    <p>{control.coverage}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="compact-section">
              <h3>Canlıya Geçiş Ön Koşulları</h3>
              <div className="go-live-list">
                <span>Kurumsal uç nokta adresleri</span>
                <span>Servis hesabı ve yetki kapsamı</span>
                <span>IP kısıtı, sertifika ve gizli anahtar kasası</span>
                <span>EBYS, DMS ve bildirim servis sözleşmeleri</span>
              </div>
            </div>
          </div>

          <div className="integration-inventory all-integrations">
            <div className="panel-heading compact-heading">
              <h3>Tüm Entegrasyon Envanteri</h3>
              <span>Hazırlanan bağlantı sözleşmeleri</span>
            </div>
            <div className="integration-table">
              <span>Sistem</span>
              <span>Grup</span>
              <span>Yön</span>
              <span>Durum</span>
              <span>Sonraki adım</span>
              {integrations.map((integration) => (
                <div className="integration-table-row" key={integration.id}>
                  <strong>{integration.name}</strong>
                  <span>{integration.group}</span>
                  <span>{integration.direction}</span>
                  <span>{integration.status}</span>
                  <p>{integration.next_step}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {activePage === "operation" && (
        <main className="workspace-grid">
        <aside className="queue-panel">
          <div className="panel-heading">
            <h2>Gelen E-postalar</h2>
            <span>
              {visibleEmails.length}/{emails.length} kayıt
            </span>
          </div>

          <div className="filter-tabs" aria-label="Süre hedefi filtresi">
            {SLA_FILTERS.map((filterOption) => (
              <button
                key={filterOption.value}
                className={slaFilter === filterOption.value ? "active" : ""}
                type="button"
                onClick={() => setSlaFilter(filterOption.value)}
              >
                {filterOption.label}
              </button>
            ))}
          </div>

          <div className="queue-controls">
            <input
              aria-label="Gelen e-postalarda ara"
              placeholder="Konu, gönderen veya kutu ara"
              value={queueSearch}
              onChange={(event) => setQueueSearch(event.target.value)}
            />
            <select
              aria-label="Durum filtresi"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
            >
              {STATUS_FILTERS.map((filterOption) => (
                <option key={filterOption.value} value={filterOption.value}>
                  {filterOption.label}
                </option>
              ))}
            </select>
          </div>

          <div className="queue-list">
            {visibleEmails.length === 0 && (
              <p className="muted">Bu arama veya filtrede e-posta yok.</p>
            )}

            {visibleEmails.map((email) => (
              <button
                key={email.id}
                className={`queue-item sla-${email.sla?.severity || "normal"} ${
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
                <span className="sla-row">
                  <span>
                    {getSlaLabel(email.sla?.status_label || email.sla?.status)}
                  </span>
                  <strong>{formatRemainingDays(email.sla?.remaining_days)}</strong>
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
              <p>Veritabanına sentetik e-posta ekleyerek başlayabilirsin.</p>
            </div>
          )}

          {selectedEmail && (
            <>
              <div className="detail-header">
                <div>
                  <p className="eyebrow">Seçili E-posta</p>
                  <h2>{selectedEmail.subject}</h2>
                </div>
                <span className={`status-pill sla-${selectedEmail.sla?.severity || "normal"}`}>
                  {getStatusLabel(selectedEmail.routing_status)}
                </span>
                <div className="button-row">
                  <button
                    disabled={!can("process_email")}
                    onClick={handleProcessEmail}
                  >
                    İşle
                  </button>
                  <button
                    disabled={!can("approve_routing")}
                    onClick={handleApproveRouting}
                  >
                    Onayla
                  </button>
                  <button
                    disabled={!can("route_email")}
                    onClick={handleRouteEmail}
                  >
                    Yönlendir
                  </button>
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

              <section className="mail-body-section">
                <div className="panel-heading compact-heading">
                  <h3>E-posta İçeriği</h3>
                  <span>{formatDate(selectedEmail.created_at)}</span>
                </div>
                <div className="body-box">{selectedEmail.body}</div>
              </section>

              {detailsLoading && (
                <p className="muted">Analiz sonuçları yükleniyor...</p>
              )}

              {!detailsLoading && details && (
                <section className="detail-tabs-section">
                  <div className="detail-tab-list" role="tablist" aria-label="E-posta detay sekmeleri">
                    {DETAIL_TABS.map((tab) => (
                      <button
                        key={tab.value}
                        className={activeDetailTab === tab.value ? "active" : ""}
                        type="button"
                        role="tab"
                        aria-selected={activeDetailTab === tab.value}
                        onClick={() => setActiveDetailTab(tab.value)}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  <div className="detail-tab-panel" role="tabpanel">
                    {activeDetailTab === "analysis" && (
                      <>
                        <section className="section-block first-section">
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
                            <Meta
                              label="Süre hedefi"
                              value={getSlaLabel(sla.status_label || sla.status)}
                            />
                            <Meta label="Son tarih" value={formatDate(sla.due_at)} />
                            <Meta
                              label="Kalan süre"
                              value={formatRemainingDays(sla.remaining_days)}
                            />
                          </div>

                          <TextBlock title="Özet" text={analysis.summary} />
                          <TextBlock
                            title="Süre hedefi politikası"
                            text={
                              sla.policy_name
                                ? `${sla.policy_name}: ${sla.sla_days} gün içinde işlem hedeflenir.`
                                : "-"
                            }
                          />
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
                          <h3>LLM Destekli Karar</h3>
                          <div className="analysis-grid">
                            <Meta
                              label="Kural kategorisi"
                              value={ruleBasedClassification.category}
                            />
                            <Meta
                              label="LLM kategorisi"
                              value={llmClassification.ai_category}
                            />
                            <Meta
                              label="LLM güveni"
                              value={formatPercent(
                                llmClassification.ai_confidence_score
                              )}
                            />
                            <Meta
                              label="LLM modu"
                              value={
                                aiAnalysis.ai_mode === "openai_api"
                                  ? "OpenAI API"
                                  : "Demo"
                              }
                            />
                            <Meta
                              label="Bağlantı"
                              value={
                                llmConnection.status === "connected"
                                  ? "API bağlı"
                                  : "Demo cevap"
                              }
                            />
                            <Meta
                              label="Karar kaynağı"
                              value={
                                getDecisionSourceLabel(
                                  aiAnalysis.final_recommendation
                                    ?.final_decision_source
                                )
                              }
                            />
                          </div>
                          <TextBlock
                            title="LLM özeti"
                            text={llmClassification.ai_summary}
                          />
                          <TextBlock
                            title="LLM gerekçesi"
                            text={llmClassification.ai_explanation}
                          />
                          <ListBlock
                            title="LLM kanıtları"
                            items={llmClassification.evidence}
                          />
                        </section>

                        <section className="section-block">
                          <h3>Eğitilebilir Model</h3>
                          {!details.modelPrediction ? (
                            <p className="muted">
                              Model henüz eğitilmedi veya tahmin üretmeye hazır değil.
                            </p>
                          ) : (
                            <>
                              <div className="analysis-grid">
                                <Meta
                                  label="Model kategorisi"
                                  value={trainedModelPrediction.category}
                                />
                                <Meta
                                  label="Model birimi"
                                  value={trainedModelPrediction.department}
                                />
                                <Meta
                                  label="Model önceliği"
                                  value={trainedModelPrediction.priority}
                                />
                                <Meta
                                  label="Model güveni"
                                  value={formatPercent(
                                    trainedModelPrediction.confidence_score
                                  )}
                                />
                              </div>

                              {trainedModelPrediction.evidence_terms?.length > 0 && (
                                <div className="model-evidence">
                                  <span>Model sinyalleri</span>
                                  <div>
                                    {trainedModelPrediction.evidence_terms.map(
                                      (item) => (
                                        <strong key={item.term}>{item.term}</strong>
                                      )
                                    )}
                                  </div>
                                </div>
                              )}
                            </>
                          )}
                        </section>
                      </>
                    )}

                    {activeDetailTab === "preprocess" && (
                      <section className="section-block first-section">
                        <div className="panel-heading">
                          <h3>Ön İşleme Sonucu</h3>
                          <span>{preprocessing.language || "Dil belirlenmedi"}</span>
                        </div>

                        <div className="analysis-grid">
                          <Meta label="Gönderen" value={preprocessing.sender?.parsed} />
                          <Meta
                            label="Alıcı"
                            value={preprocessing.recipients?.join(", ") || "-"}
                          />
                          <Meta
                            label="Tarih"
                            value={preprocessing.date || formatDate(selectedEmail.created_at)}
                          />
                          <Meta
                            label="Otomatik cevap"
                            value={
                              preprocessing.spam_or_automatic?.is_automatic_reply
                                ? "Evet"
                                : "Hayır"
                            }
                          />
                          <Meta
                            label="Spam benzeri"
                            value={
                              preprocessing.spam_or_automatic?.is_spam_like
                                ? "Evet"
                                : "Hayır"
                            }
                          />
                          <Meta
                            label="Ek listesi"
                            value={
                              preprocessing.attachments?.all_names?.join(", ") || "Yok"
                            }
                          />
                        </div>

                        <div className="preprocess-grid">
                          <TextBlock
                            title="Asıl Mesaj"
                            text={preprocessing.main_message}
                          />
                          <TextBlock
                            title="İmza"
                            text={preprocessing.signature || "İmza bulunmadı."}
                          />
                          <TextBlock
                            title="Footer"
                            text={preprocessing.footer || "Footer bulunmadı."}
                          />
                          <TextBlock
                            title="Sınıflandırmaya Giden Metin"
                            text={preprocessing.classification_text}
                          />
                        </div>

                        <div className="preprocess-chain">
                          <h4>Önceki Yazışmalar</h4>
                          {preprocessing.previous_replies?.length > 0 ? (
                            preprocessing.previous_replies.map((reply, index) => (
                              <div className="reply-block" key={`${index}-${reply.slice(0, 20)}`}>
                                <strong>{index + 1}. cevap bloğu</strong>
                                <p>{reply}</p>
                              </div>
                            ))
                          ) : (
                            <p className="empty-log">Önceki yazışma bulunmadı.</p>
                          )}
                        </div>

                        <ListBlock
                          title="Uygulanan İşlemler"
                          items={preprocessing.steps}
                        />
                      </section>
                    )}

                    {activeDetailTab === "attachments" && (
                      <section className="section-block first-section">
                        <div className="attachment-section-header">
                          <div>
                            <h3>Ek Dosya Güvenlik Kapısı</h3>
                            <span>
                              Mail gövdesi yetersiz kaldığında karar ek dosya
                              içeriğiyle desteklenir.
                            </span>
                          </div>
                          <form
                            className="attachment-upload-form"
                            onSubmit={handleAttachmentUpload}
                          >
                            <label className="file-picker">
                              <input
                                type="file"
                                accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.ppt,.pptx,.jpg,.jpeg,.png,.tiff,.bmp,.webp,.zip,.rar,.7z,.p7s,.asice,.mht,.txt"
                                onChange={(event) =>
                                  setSelectedAttachmentFile(
                                    event.target.files?.[0] || null
                                  )
                                }
                              />
                              <span>Dosya Seç</span>
                              <strong>
                                {selectedAttachmentFile?.name || "Dosya seçilmedi"}
                              </strong>
                            </label>
                            <button
                              disabled={!can("upload_attachment")}
                              type="submit"
                            >
                              Ek Yükle ve Oku
                            </button>
                          </form>
                        </div>

                        {!attachmentAnalysis.has_attachments ? (
                          <div className="attachment-empty-state">
                            <strong>Bu kayda iliştirilmiş dosya bulunmuyor.</strong>
                            <span>
                              Mail gövdesi üzerinden sınıflandırma yapılabilir; dosya
                              gelirse OCR, güvenlik ve kişisel veri kontrolleri burada
                              görünür.
                            </span>
                          </div>
                        ) : (
                          <>
                            <div className="attachment-summary-panel">
                              <div>
                                <span>Dosya inceleme özeti</span>
                                <strong>{attachmentAnalysis.summary}</strong>
                              </div>
                              <div className="attachment-summary-grid">
                                <Meta
                                  label="Ek"
                                  value={attachmentGateStats.total}
                                />
                                <Meta
                                  label="Genel risk"
                                  value={attachmentAnalysis.overall_risk_level}
                                />
                                <Meta
                                  label="OCR gereken"
                                  value={attachmentGateStats.ocrRequired}
                                />
                                <Meta
                                  label="Metin çıkarıldı"
                                  value={attachmentGateStats.extractedText}
                                />
                                <Meta
                                  label="Kişisel veri"
                                  value={attachmentGateStats.personalData}
                                />
                                <Meta
                                  label="Güvenlik uyarısı"
                                  value={attachmentGateStats.suspicious}
                                />
                              </div>
                            </div>

                            <div className="attachment-gate-flow">
                              <div>
                                <span>1</span>
                                <strong>Tür tespiti</strong>
                                <p>PDF, Word, Excel, görsel, arşiv ve e-imzalı dosya ayrımı.</p>
                              </div>
                              <div>
                                <span>2</span>
                                <strong>Metin / OCR</strong>
                                <p>Normal metin çıkarma veya taranmış belge için OCR kararı.</p>
                              </div>
                              <div>
                                <span>3</span>
                                <strong>Güvenlik</strong>
                                <p>Antivirüs simülasyonu, şifreli dosya ve arşiv uyarıları.</p>
                              </div>
                              <div>
                                <span>4</span>
                                <strong>Sınıflandırma etkisi</strong>
                                <p>Konu, kişi, tarih ve evrak göstergeleri karar riskine eklenir.</p>
                              </div>
                            </div>

                            <div className="attachment-card-list">
                              {attachmentAnalysis.attachments?.map((attachment) => {
                                const riskTone = getAttachmentRiskTone(attachment);

                                return (
                                  <article
                                    className={`attachment-card ${riskTone}`}
                                    key={attachment.filename}
                                  >
                                    <div className="attachment-card-header">
                                      <div>
                                        <span>
                                          {getAttachmentFileTypeLabel(attachment.file_type)}
                                        </span>
                                        <h4>{attachment.filename}</h4>
                                      </div>
                                      <strong>{attachment.risk_level}</strong>
                                    </div>

                                    <div className="attachment-status-grid">
                                      <Meta
                                        label="Metin durumu"
                                        value={getAttachmentTextStatus(
                                          attachment.filename,
                                          attachmentTexts
                                        )}
                                      />
                                      <Meta
                                        label="OCR"
                                        value={
                                          attachment.ocr_required
                                            ? "Gerekli"
                                            : "Gerekli değil"
                                        }
                                      />
                                      <Meta
                                        label="Güvenlik"
                                        value={`${attachment.security_scan_status} / ${attachment.malware_risk}`}
                                      />
                                      <Meta
                                        label="Şifreli dosya"
                                        value={attachment.is_encrypted ? "Uyarı var" : "Yok"}
                                      />
                                      <Meta
                                        label="Kişisel veri"
                                        value={
                                          attachment.contains_personal_data
                                            ? "İşaret var"
                                            : "İşaret yok"
                                        }
                                      />
                                    </div>

                                    <div className="attachment-detail-grid">
                                      <TextBlock
                                        title="Çıkarılan konu"
                                        text={attachment.extracted_topic}
                                      />
                                      <TextBlock
                                        title="Dosya no / tarih"
                                        text={[
                                          attachment.extracted_file_numbers?.join(", "),
                                          attachment.extracted_dates?.join(", "),
                                        ]
                                          .filter(Boolean)
                                          .join(" / ") || "-"}
                                      />
                                      <TextBlock
                                        title="Kişisel veri bulgusu"
                                        text={
                                          attachment.personal_data_indicators?.join(", ") ||
                                          "Belirgin kişisel veri işareti yok."
                                        }
                                      />
                                      <TextBlock
                                        title="Güvenlik uyarısı"
                                        text={attachment.security_warnings?.join(" ")}
                                      />
                                      <TextBlock
                                        title="Risk gerekçesi"
                                        text={attachment.risk_reasons?.join(" ")}
                                      />
                                      <TextBlock
                                        title="OCR kararı"
                                        text={attachment.ocr_reason}
                                      />
                                    </div>

                                    <div className="attachment-action-note">
                                      {attachment.suggested_action}
                                    </div>
                                  </article>
                                );
                              })}
                            </div>
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
                    )}

                    {activeDetailTab === "routing" && (
                      <>
                        <section className="section-block first-section">
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

                        <section className="section-block correction-section">
                          <h3>Yönlendirme Düzeltme</h3>
                          <form className="correction-form" onSubmit={handleCorrectRouting}>
                            <label>
                              <span>Kategori</span>
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
                            </label>
                            <label>
                              <span>Birim</span>
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
                            </label>
                            <label>
                              <span>Öncelik</span>
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
                            </label>
                            <label>
                              <span>Not</span>
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
                            </label>
                            <button
                              disabled={!can("correct_routing")}
                              type="submit"
                            >
                              Düzeltmeyi Kaydet
                            </button>
                          </form>
                        </section>
                      </>
                    )}

                    {activeDetailTab === "ticket" && (
                      <section className="section-block first-section">
                        <div className="panel-heading">
                          <h3>Evrak/Talep Kaydı</h3>
                          {!ticket && (
                            <button
                              className="secondary-button small-button"
                              disabled={!can("route_email")}
                              type="button"
                              onClick={handleCreateTicket}
                            >
                              Kayıt Aç
                            </button>
                          )}
                        </div>
                        {!ticket ? (
                          <p className="empty-log">
                            Bu e-posta için henüz evrak/talep kaydı açılmadı.
                          </p>
                        ) : (
                          <>
                            <div className="analysis-grid">
                              <Meta label="Kayıt no" value={ticket.record_number} />
                              <Meta label="Başvuru türü" value={ticket.application_type} />
                              <Meta label="Birim" value={ticket.assigned_department} />
                              <Meta label="Sorumlu" value={ticket.responsible_person || "-"} />
                              <Meta label="Durum" value={ticket.status} />
                              <Meta label="Öncelik" value={ticket.priority} />
                              <Meta label="Son tarih" value={formatDate(ticket.sla_due_at)} />
                            </div>
                            <div className="ticket-actions">
                              <button
                                className="secondary-button small-button"
                                disabled={!can("route_email")}
                                type="button"
                                onClick={() => handleAdvanceTicketStatus(ticket)}
                              >
                                Durumu İlerlet
                              </button>
                            </div>
                            {ticket.notes?.length > 0 && (
                              <div className="ticket-notes">
                                <h4>Notlar</h4>
                                {ticket.notes.slice(-3).map((note) => (
                                  <p key={`${note.created_at}-${note.text}`}>
                                    {note.text}
                                  </p>
                                ))}
                              </div>
                            )}
                          </>
                        )}
                      </section>
                    )}

                    {activeDetailTab === "logs" && (
                      <section className="section-block first-section">
                        <h3>İşlem Günlüğü</h3>
                        {logs.length === 0 ? (
                          <p className="empty-log">Bu kayıt için işlem günlüğü yok.</p>
                        ) : (
                          logs.slice(0, 6).map((log) => (
                            <div className="log-row" key={log.id}>
                              <strong>{getLogActionLabel(log.action_type)}</strong>
                              <span>{getActorLabel(log.actor)}</span>
                              <p>{getLogDetailLabel(log.action_detail)}</p>
                            </div>
                          ))
                        )}
                      </section>
                    )}
                  </div>
                </section>
              )}
            </>
          )}
        </section>
      </main>
      )}

      {activePage === "ingestion" && (
        <section className="import-panel page-panel">
          <div className="ingestion-header">
            <div>
              <h2>E-posta Alma</h2>
            <span>webmaster@rekabet.gov.tr ortak kutusu</span>
          </div>
            <button
              className="secondary-button"
              disabled={!can("import_email")}
              type="button"
              onClick={handleMailboxSync}
            >
              Posta Kutusunu Senkronize Et
            </button>
          </div>

          <div className="connector-overview">
            {(ingestionOverview?.connectors || []).map((connector) => (
              <article
                className={`connector-card ${connector.status}`}
                key={connector.connector_id}
              >
                <div>
                  <strong>{connector.name}</strong>
                  <span>{connector.source_type}</span>
                </div>
                <p>{connector.next_step}</p>
                <div className="connector-card-footer">
                  <span>{connector.mode}</span>
                  <strong>
                    {CONNECTOR_STATUS_LABELS[connector.status] ||
                      connector.status}
                  </strong>
                </div>
              </article>
            ))}
          </div>

          <form onSubmit={handleImportSubmit}>
            <h3>Manuel E-posta Ekle</h3>
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
              E-posta gövdesi
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
            <button disabled={!can("import_email")} type="submit">
              E-postayı İçe Aktar
            </button>
          </form>

          <div className="compact-section">
            <h3>Durum Dağılımı</h3>
            {Object.entries(
              operationalDashboard?.routing_status_distribution || {}
            ).map(([status, count]) => (
              <div className="mini-row static" key={status}>
                <span>{getStatusLabel(status)}</span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>

          <div className="compact-section">
            <h3>Süre Hedefi Dağılımı</h3>
            {Object.entries(
              operationalDashboard?.sla_status_distribution || {}
            ).map(([status, count]) => (
              <div className="mini-row static" key={status}>
                <span>{getSlaLabel(status)}</span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>

          <div className="compact-section">
            <h3>Operasyon Dağılımı</h3>
            <DistributionList
              title="Kategori"
              distribution={dashboard?.category_distribution}
            />
            <DistributionList
              title="Birim"
              distribution={dashboard?.department_distribution}
            />
            <DistributionList
              title="Risk"
              distribution={dashboard?.risk_level_distribution}
            />
          </div>
        </section>
      )}

      {activePage === "training" && (
        <section className="training-page page-panel">
          <div className="panel-heading compact-heading">
            <div>
              <p className="eyebrow">Model Eğitimi</p>
              <h2>Eğitim ve Öğrenme Yönetimi</h2>
            </div>
            <div className="button-row">
              <button
                className="secondary-button small-button"
                disabled={!can("view_training_data")}
                type="button"
                onClick={handleTrainModel}
              >
                Modeli Eğit
              </button>
              <button
                className="secondary-button small-button"
                disabled={!can("view_training_data")}
                type="button"
                onClick={handleDownloadTrainingJsonl}
              >
                Eğitim Verisini İndir
              </button>
            </div>
          </div>

          <div className="training-kpi-grid">
            <ReportMetric
              label="Model durumu"
              value={modelStatus.is_trained ? "Eğitildi" : "Bekliyor"}
              tone={modelStatus.is_trained ? "success" : "warning"}
            />
            <ReportMetric
              label="Eğitim örneği"
              value={totalTrainingExamples}
            />
            <ReportMetric
              label="Sentetik veri"
              value={seedTrainingExamples}
            />
            <ReportMetric
              label="Geri bildirim"
              value={feedbackTrainingExamples}
              tone={feedbackTrainingExamples > 0 ? "success" : "warning"}
            />
            <ReportMetric
              label="Model tipi"
              value={getModelTypeLabel(modelMetadata.model_type)}
            />
            <ReportMetric
              label="Son eğitim"
              value={modelMetadata.trained_at ? formatDate(modelMetadata.trained_at) : "-"}
            />
          </div>

          {modelStatus.error && (
            <div className="alert warning">{modelStatus.error}</div>
          )}

          <div className="training-layout">
            <div className="training-section-card">
              <div className="panel-heading compact-heading">
                <h3>Öğrenme Akışı</h3>
                <span>LLM olmadan kullanılan eğitilebilir model hattı</span>
              </div>
              <div className="training-pipeline">
                {TRAINING_PIPELINE_STEPS.map((step, index) => (
                  <div className="training-step" key={step.label}>
                    <span>{index + 1}</span>
                    <div>
                      <em>{step.label}</em>
                      <strong>{step.title}</strong>
                      <p>{step.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="training-section-card">
              <div className="panel-heading compact-heading">
                <h3>Veri Seti Kompozisyonu</h3>
                <span>Modelin öğrendiği etiket alanları</span>
              </div>
              <div className="training-distribution-grid">
                <DistributionList
                  title="Kategori dağılımı"
                  distribution={trainingCategoryDistribution}
                />
                <DistributionList
                  title="Birim dağılımı"
                  distribution={trainingDepartmentDistribution}
                />
                <DistributionList
                  title="Öncelik dağılımı"
                  distribution={trainingPriorityDistribution}
                />
              </div>
            </div>
          </div>

          <div className="training-layout secondary-training-layout">
            <div className="training-section-card">
              <div className="panel-heading compact-heading">
                <h3>Operatör Geri Bildirimleri</h3>
                <span>Yanlış yönlendirmeler eğitim verisine dönüşür</span>
              </div>
              {feedbackData.feedbacks.length === 0 ? (
                <p className="muted">Henüz operatör düzeltmesi yok.</p>
              ) : (
              <div className="feedback-list">
                {feedbackData.feedbacks.slice(0, 5).map((feedback) => (
                  <div className="feedback-row" key={feedback.id}>
                    <span>E-posta #{feedback.email_id}</span>
                    <strong>
                      {feedback.original_department} →{" "}
                      {feedback.corrected_department}
                    </strong>
                    <p>{feedback.feedback_note || "Not girilmedi."}</p>
                  </div>
                ))}
              </div>
              )}
            </div>

            <div className="training-section-card">
              <div className="panel-heading compact-heading">
                <h3>Eğitim Örnekleri</h3>
                <span>JSONL dışa aktarımına girecek örnek kayıtlar</span>
              </div>
              {trainingData.training_examples.length === 0 ? (
                <p className="muted">
                  Geri bildirimden gelen yeni eğitim örneği yok. Sentetik seed veri
                  model eğitiminde kullanılmaya devam eder.
                </p>
              ) : (
                <div className="training-example-list">
                  {trainingData.training_examples.slice(0, 5).map((example) => (
                    <div className="training-example-row" key={example.email_id}>
                      <span>#{example.email_id}</span>
                      <strong>{example.subject}</strong>
                      <p>
                        {example.corrected_label.category} ·{" "}
                        {example.corrected_label.department} ·{" "}
                        {example.corrected_label.priority}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

function Metric({ label, value, tone = "neutral" }) {
  return (
    <div className={`metric-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ReportMetric({ label, value, tone = "neutral" }) {
  return (
    <div className={`report-metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function IntegrationCard({ integration, onTest, testDisabled }) {
  const statusTone =
    integration.status === "Hazır"
      ? "success"
      : integration.status === "Uyarı"
        ? "warning"
        : "neutral";

  return (
    <article className={`integration-card ${statusTone}`}>
      <div className="integration-card-header">
        <div>
          <span>{integration.group}</span>
          <h4>{integration.name}</h4>
        </div>
        <strong>{integration.status}</strong>
      </div>
      <div className="integration-meta-grid">
        <Meta label="Yön" value={integration.direction} />
        <Meta label="Bağlantı" value={integration.mode} />
        <Meta label="Sahip" value={integration.owner} />
        <Meta label="Sağlık" value={`${integration.health_score}%`} />
      </div>
      <p className="integration-contract">Veri alanları: {integration.data_contract}</p>
      <div className="integration-capabilities">
        {integration.capabilities?.slice(0, 3).map((capability) => (
          <span key={capability}>{capability}</span>
        ))}
      </div>
      <div className="integration-footer">
        <span>{integration.endpoint_hint}</span>
        <button
          className="secondary-button small-button"
          disabled={testDisabled}
          type="button"
          onClick={() => onTest(integration.id)}
        >
          Test Çalıştır
        </button>
      </div>
      <p className="integration-next-step">{integration.next_step}</p>
    </article>
  );
}

function Meta({ label, value }) {
  const displayValue = value === 0 ? 0 : value || "-";

  return (
    <div className="meta-item">
      <span>{label}</span>
      <strong>{displayValue}</strong>
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
      {title && <h4>{title}</h4>}
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function EvaluationCorrectionList({ rows = [] }) {
  if (!rows.length) {
    return <p className="muted">Düzeltme kaydı yok.</p>;
  }

  return (
    <div className="evaluation-list">
      {rows.map((row) => (
        <div className="evaluation-row" key={row.correction}>
          <strong>{row.correction}</strong>
          <em>{row.count}</em>
        </div>
      ))}
    </div>
  );
}

function ReportBars({ entries = [], labelKey }) {
  if (!entries.length) {
    return <p className="muted">Raporlanacak veri yok.</p>;
  }

  const maxTotal = Math.max(...entries.map((entry) => entry.total || 0), 1);

  return (
    <div className="report-bars">
      {entries.map((entry) => (
        <div className="report-bar-row" key={entry[labelKey]}>
          <div className="distribution-label">
            <span>{entry[labelKey]}</span>
            <strong>{entry.total}</strong>
          </div>
          <div className="distribution-track" aria-hidden="true">
            <div
              className="distribution-fill"
              style={{ width: `${Math.max((entry.total / maxTotal) * 100, 4)}%` }}
            />
          </div>
          <div className="report-bar-meta">
            <span>Kritik: {entry.critical}</span>
            <span>Onay: {entry.pending_review}</span>
            <span>Yönlendirilen: {entry.routed}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function DistributionList({ title, distribution = {} }) {
  const entries = getDistributionEntries(distribution);
  const total = entries.reduce((sum, [, count]) => sum + count, 0);

  if (!entries.length) {
    return null;
  }

  return (
    <div className="distribution-block">
      <h4>{title}</h4>
      {entries.slice(0, 5).map(([label, count]) => {
        const width = total > 0 ? `${Math.max((count / total) * 100, 8)}%` : "0%";

        return (
          <div className="distribution-row" key={label}>
            <div className="distribution-label">
              <span>{label}</span>
              <strong>{count}</strong>
            </div>
            <div className="distribution-track" aria-hidden="true">
              <div
                className="distribution-fill"
                style={{ width }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default App;
