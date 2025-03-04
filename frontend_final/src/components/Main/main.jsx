import React, { useState } from "react";
import "./main.css";
import { fetchResponse } from "../../api/apiService";

const Main = () => {
  const [issue, setIssue] = useState("");
  const [response, setResponse] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedIndex, setExpandedIndex] = useState(null);

  const handleClick = async () => {
    setIsLoading(true);
    setError("");
    setResponse(null);

    try {
      const data = await fetchResponse(issue);
      console.log("API Response:", data);
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTextWithLinks = (text) => {
    const urlPattern = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlPattern, (url) => {
      return `<a href="${url}" target="_blank" rel="noopener noreferrer" style="color: blue; text-decoration: underline;">Click here</a>`;
    });
  };

  const toggleExpand = (index) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  const formatResponse = (response) => {
    return (
      <div className="response-container">
        {response.results && response.results.length > 0 ? (
          response.results.map((result, index) => (
            <div key={index} className="defect-item">
              <div className="defect-summary">
                <div className="summary-content">
                  <span
                    className={`toggle-icon ${
                      expandedIndex === index ? "expanded" : ""
                    }`}
                  >
                    {expandedIndex === index ? "▼" : "▶"}
                  </span>
                  <span className="summary-text">
                    <strong>Defect Summary:</strong> {result.defectSummary}
                  </span>
                </div>
                <button
                  className="detail-view-btn"
                  onClick={() => toggleExpand(index)}
                >
                  {expandedIndex === index ? "Hide Details" : "View Details"}
                </button>
              </div>
              {expandedIndex === index && (
                <div className="defect-details">
                  {/* Relevance Section */}
                  {result.relevance && (
                    <div className="accuracy-section">
                      <div className="accuracy-label">Relevance</div>
                      <div className="accuracy-bar-container">
                        <div
                          className="accuracy-bar"
                          style={{ width: `${result.relevance}%` }}
                        >
                          <span className="accuracy-value">
                            {result.relevance}%
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                  {/* Analysis Section */}
                  {result.analysis && (
                    <div className="analysis">
                      <strong>Analysis:</strong>
                      {result.analysis.split("\n").map((line, idx) => (
                        <p
                          key={idx}
                          style={{
                            textAlign: "left",
                            marginLeft: /^\d+\./.test(line.trim())
                              ? "2rem"
                              : "0",
                          }}
                          dangerouslySetInnerHTML={{
                            __html: formatTextWithLinks(line),
                          }}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="fallback-message">
            <p>{response.message}</p>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="main">
      <h2 className="main-title">Welcome to Bugbuster App</h2>
      <p className="main-description">
        Enter your issue below, and we'll help you find a solution!
      </p>
      <div className="main-input-container">
        <input
          type="text"
          placeholder="Describe your issue..."
          className="main-input"
          value={issue}
          onChange={(e) => setIssue(e.target.value)}
        />
        <button className="main-button" onClick={handleClick}>
          Find Solution
        </button>
      </div>
      {isLoading && <p>Loading...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}
      {response && formatResponse(response)}
    </div>
  );
};

export default Main;
