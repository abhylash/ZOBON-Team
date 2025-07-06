import React, { useState } from "react";
import { askSQLAssistant } from "../services/api";
import "./AskAIBox.css";

export default function AskAIBox() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [isExpanded, setIsExpanded] = useState(false);

  const handleAsk = async () => {
    if (!question.trim()) {
      setError("⚠️ Please enter a question");
      return;
    }

    setIsLoading(true);
    setError("");
    setAnswer("");

    try {
      console.log("📤 Sending question:", question);
      const response = await askSQLAssistant(question);
      const data = response && response.data;

      if (!data || typeof data !== "object") {
        setError("⚠️ No valid response received from assistant");
        return;
      }

      if (data.error) {
        setError(data.error);
      } else if (typeof data.answer === "string") {
        setAnswer(data.answer.trim());
      } else {
        setError("⚠️ Assistant responded with an unexpected format");
      }
    } catch (err) {
      console.error("❌ Assistant error:", err);
      setError(
        err?.message || "Failed to reach assistant. Please ensure the backend is running."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  };

  const clearConversation = () => {
    setQuestion("");
    setAnswer("");
    setError("");
  };

  const toggleExpanded = () => {
    setIsExpanded(!isExpanded);
  };

  const handleClose = () => {
    setIsExpanded(false);
  };

  return (
    <div 
      className={`ask-ai-container ${isExpanded ? 'expanded' : ''}`}
      onClick={!isExpanded ? toggleExpanded : undefined}
    >
      {isExpanded && (
        <button className="close-button" onClick={handleClose}>
          ×
        </button>
      )}
      
      <div className="ask-ai-header">
        <h4>🤖 Ask ZOBON (AI Assistant)</h4>
        <p className="ask-ai-subtitle">
          Ask questions about your campaign data in natural language
        </p>
      </div>

      <div className="ask-ai-input-section">
        <div className="input-wrapper">
          <textarea
            className="ai-input"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Examples:
• What's the average trust score by brand?
• Show me recent sentiment trends for Ola
• Which campaigns have low trust scores?
• Find bias alerts from last week`}
            disabled={isLoading}
            rows={4}
            aria-label="Ask your question to ZOBON AI Assistant"
          />
        </div>

        <div className="button-group">
          <button
            className="ai-button primary"
            onClick={handleAsk}
            disabled={isLoading || !question.trim()}
            aria-label="Ask ZOBON AI Assistant"
          >
            {isLoading ? (
              <>
                <span className="spinner" aria-hidden="true"></span>
                Analyzing...
              </>
            ) : (
              "Ask ZOBON"
            )}
          </button>

          {(answer || error || question) && (
            <button
              className="ai-button secondary"
              onClick={clearConversation}
              disabled={isLoading}
              aria-label="Clear conversation"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      <div className={`ai-loading ${isLoading ? 'show-loading' : ''}`}>
        {isLoading && (
          <>
            <div className="loading-dots" aria-hidden="true">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <p>ZOBON is analyzing your question...</p>
          </>
        )}
      </div>

      <div className={`ai-response-section ${(answer || error) ? 'show-response' : ''}`}>
        {error ? (
          <div className="ai-error" role="alert">
            <h5>❌ Error</h5>
            <p>{error}</p>
          </div>
        ) : answer ? (
          <div className="ai-response">
            <div className="response-header">
              <h5>💬 ZOBON's Response</h5>
            </div>
            <div className="chatbot-answer">
              <p>{answer}</p>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}