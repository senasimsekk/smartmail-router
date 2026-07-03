import { useEffect, useState } from "react";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

function App() {
  const [emails, setEmails] = useState([]);
  const [selectedEmail, setSelectedEmail] = useState(null);

  const [analysisData, setAnalysisData] = useState(null);
  const [aiData, setAiData] = useState(null);
  const [responseSuggestionData, setResponseSuggestionData] = useState(null);

  const [loadingEmails, setLoadingEmails] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);

  const [errorMessage, setErrorMessage] = useState("");
  const [detailError, setDetailError] = useState("");

  useEffect(() => {
    async function fetchEmails() {
      try {
        const response = await fetch(`${API_BASE_URL}/emails`);

        if (!response.ok) {
          throw new Error(`Backend error: ${response.status}`);
        }

        const data = await response.json();
        setEmails(data.emails || []);
      } catch (error) {
        console.error("Emails could not be fetched:", error);
        setErrorMessage(error.message);
      } finally {
        setLoadingEmails(false);
      }
    }

    fetchEmails();
  }, []);

  async function handleSelectEmail(email) {
    setSelectedEmail(email);
    setAnalysisData(null);
    setAiData(null);
    setResponseSuggestionData(null);
    setDetailError("");
    setLoadingDetails(true);

    try {
      const [analysisResponse, aiResponse, responseSuggestionResponse] =
        await Promise.all([
          fetch(`${API_BASE_URL}/emails/${email.id}/analysis`),
          fetch(`${API_BASE_URL}/emails/${email.id}/ai-analysis`),
          fetch(`${API_BASE_URL}/emails/${email.id}/response-suggestion`),
        ]);

      if (!analysisResponse.ok) {
        throw new Error(`Analysis error: ${analysisResponse.status}`);
      }

      if (!aiResponse.ok) {
        throw new Error(`AI analysis error: ${aiResponse.status}`);
      }

      if (!responseSuggestionResponse.ok) {
        throw new Error(
          `Response suggestion error: ${responseSuggestionResponse.status}`
        );
      }

      const analysisJson = await analysisResponse.json();
      const aiJson = await aiResponse.json();
      const responseSuggestionJson = await responseSuggestionResponse.json();

      console.log("Analysis:", analysisJson);
      console.log("AI:", aiJson);
      console.log("Response Suggestion:", responseSuggestionJson);

      setAnalysisData(analysisJson);
      setAiData(aiJson);
      setResponseSuggestionData(responseSuggestionJson);
    } catch (error) {
      console.error("Details could not be fetched:", error);
      setDetailError(error.message);
    } finally {
      setLoadingDetails(false);
    }
  }

  const classification =
    analysisData?.classification ||
    analysisData?.classification_result ||
    analysisData?.classification_data ||
    {};

  const analysis =
    analysisData?.analysis ||
    analysisData?.email_analysis ||
    analysisData ||
    {};

  const aiAnalysis =
    aiData?.ai_analysis ||
    aiData?.analysis ||
    aiData ||
    {};

  const ruleClassification =
    aiAnalysis?.rule_classification ||
    aiAnalysis?.rule_result ||
    {};

  const mockAiResult =
    aiAnalysis?.mock_ai_result ||
    aiAnalysis?.ai_result ||
    aiAnalysis?.ai_classification ||
    {};

  const finalAiDecision =
    aiAnalysis?.final_recommendation ||
    aiAnalysis?.final_decision ||
    aiAnalysis?.final_result ||
    {};

  const responseSuggestion =
    responseSuggestionData?.response_suggestion ||
    responseSuggestionData?.suggestion ||
    responseSuggestionData ||
    {};

  const attachmentNames = Array.isArray(selectedEmail?.attachment_names)
    ? selectedEmail.attachment_names
    : [];

  if (loadingEmails) {
    return <p className="loading-text">Loading emails...</p>;
  }

  return (
    <div className="app-container">
      <aside className="email-list">
        <h1>SmartMail Router</h1>

        {errorMessage && (
          <p className="error-text">Backend connection error: {errorMessage}</p>
        )}

        <p className="email-count">{emails.length} emails found</p>

        {emails.map((email) => (
          <button
            key={email.id}
            className={`email-card ${
              selectedEmail?.id === email.id ? "active-email-card" : ""
            }`}
            onClick={() => handleSelectEmail(email)}
          >
            <h3>{email.subject}</h3>
            <p>{email.sender}</p>
            <span>{email.source_mailbox}</span>
          </button>
        ))}
      </aside>

      <main className="email-detail">
        {!selectedEmail && (
          <div className="empty-state">
            <h2>Select an email</h2>
            <p>Choose an email from the list to see its details.</p>
          </div>
        )}

        {selectedEmail && (
          <div className="detail-card">
            <h2>{selectedEmail.subject}</h2>

            <div className="meta-row">
              <strong>From:</strong>
              <span>{selectedEmail.sender}</span>
            </div>

            <div className="meta-row">
              <strong>Source Mailbox:</strong>
              <span>{selectedEmail.source_mailbox}</span>
            </div>

            <div className="meta-row">
              <strong>Attachment:</strong>
              <span>{selectedEmail.has_attachment ? "Yes" : "No"}</span>
            </div>

            {selectedEmail.has_attachment && (
              <div className="meta-row">
                <strong>Attachment Names:</strong>
                <span>{attachmentNames.join(", ")}</span>
              </div>
            )}

            <hr />

            <section>
              <h3 className="section-title">Email Body</h3>
              <p className="email-body">{selectedEmail.body}</p>
            </section>

            <hr />

            {loadingDetails && (
              <p className="small-loading">Smart details loading...</p>
            )}

            {detailError && (
              <p className="error-text">
                Details could not be loaded: {detailError}
              </p>
            )}

            {!loadingDetails && analysisData && (
              <section>
                <h3 className="section-title">Smart Analysis</h3>

                <div className="info-grid">
                  <div className="info-card">
                    <span>Category</span>
                    <strong>{classification.category || "—"}</strong>
                  </div>

                  <div className="info-card">
                    <span>Department</span>
                    <strong>{classification.department || "—"}</strong>
                  </div>

                  <div className="info-card">
                    <span>Priority</span>
                    <strong>{classification.priority || "—"}</strong>
                  </div>

                  <div className="info-card">
                    <span>Confidence</span>
                    <strong>
                      {classification.confidence_score !== undefined
                        ? `${Math.round(classification.confidence_score * 100)}%`
                        : "—"}
                    </strong>
                  </div>

                  <div className="info-card">
                    <span>Risk Level</span>
                    <strong>{analysis.risk_level || "—"}</strong>
                  </div>

                  <div className="info-card">
                    <span>Operation Type</span>
                    <strong>{analysis.operation_type || "—"}</strong>
                  </div>

                  <div className="info-card">
                    <span>Needs Response</span>
                    <strong>{analysis.needs_response ? "Yes" : "No"}</strong>
                  </div>

                  <div className="info-card">
                    <span>Human Review</span>
                    <strong>
                      {classification.requires_human_review
                        ? "Required"
                        : "Not required"}
                    </strong>
                  </div>
                </div>

                <div className="summary-box">
                  <h4>Summary</h4>
                  <p>{analysis.summary || "No summary available."}</p>
                </div>

                <div className="summary-box">
                  <h4>Suggested Action</h4>
                  <p>
                    {analysis.suggested_action ||
                      "No suggested action available."}
                  </p>
                </div>

                {Array.isArray(analysis.risk_reasons) &&
                  analysis.risk_reasons.length > 0 && (
                    <div className="summary-box">
                      <h4>Risk Reasons</h4>
                      <ul>
                        {analysis.risk_reasons.map((reason, index) => (
                          <li key={index}>{reason}</li>
                        ))}
                      </ul>
                    </div>
                  )}
              </section>
            )}

            {!loadingDetails && aiData && (
              <section>
                <hr />
                <h3 className="section-title">AI Analysis</h3>

                <div className="info-grid">
                  <div className="info-card">
                    <span>Rule Category</span>
                    <strong>{ruleClassification.category || "—"}</strong>
                  </div>

                  <div className="info-card">
                    <span>AI Category</span>
                    <strong>{mockAiResult.category || "—"}</strong>
                  </div>

                  <div className="info-card">
                    <span>AI Confidence</span>
                    <strong>
                      {mockAiResult.confidence_score !== undefined
                        ? `${Math.round(mockAiResult.confidence_score * 100)}%`
                        : "—"}
                    </strong>
                  </div>

                  <div className="info-card">
                    <span>Human Review</span>
                    <strong>
                      {finalAiDecision.human_review_required ||
                      mockAiResult.requires_human_review
                        ? "Required"
                        : "Not required"}
                    </strong>
                  </div>
                </div>

                <div className="summary-box">
                  <h4>AI Explanation</h4>
                  <p>
                    {mockAiResult.explanation ||
                      finalAiDecision.explanation ||
                      "No AI explanation available."}
                  </p>
                </div>

                <div className="summary-box">
                  <h4>Final Decision</h4>
                  <p>
                    {finalAiDecision.decision_source ||
                      finalAiDecision.final_decision_source ||
                      finalAiDecision.recommendation ||
                      "No final AI decision available."}
                  </p>
                </div>
              </section>
            )}

            {!loadingDetails && responseSuggestionData && (
              <section>
                <hr />
                <h3 className="section-title">Response Suggestion</h3>

                <div className="info-grid">
                  <div className="info-card">
                    <span>Template Type</span>
                    <strong>{responseSuggestion.template_type || "—"}</strong>
                  </div>

                  <div className="info-card">
                    <span>Human Approval</span>
                    <strong>
                      {responseSuggestion.needs_human_approval
                        ? "Required"
                        : "Required"}
                    </strong>
                  </div>
                </div>

                {responseSuggestion.warning && (
                  <div className="warning-box">
                    {responseSuggestion.warning}
                  </div>
                )}

                <div className="response-box">
                  <h4>Suggested Response Draft</h4>
                  <p>
                    {responseSuggestion.suggested_response ||
                      "No response suggestion available."}
                  </p>
                </div>
              </section>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;