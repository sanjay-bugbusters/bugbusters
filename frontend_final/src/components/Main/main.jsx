import React from "react";
import "./main.css";
import { useState } from "react";
import { fetchResponse } from "../../api/apiService";

const Main = () => {
  const [issue, setIssue] = useState("");
  const [response, setResponse] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

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

  const formatResponse = (response) => {
    const result =
      response.results && response.results[0] ? response.results[0] : null;

    return (
      <div className="response-container">
        {result && (
          <>
            {/* Relevance Section */}
            {result.relevance && (
              <div className="accuracy-section">
                <div className="accuracy-label">Relevance</div>
                <div className="accuracy-bar-container">
                  <div
                    className="accuracy-bar"
                    style={{ width: `${result.relevance}%` }}
                  >
                    <span className="accuracy-value">{result.relevance}%</span>
                  </div>
                </div>
              </div>
            )}

            {/* Defect Summary */}
            {result.defectSummary && (
              <div className="defect-summary">
                <strong>Defect Summary:</strong>
                <p
                  dangerouslySetInnerHTML={{
                    __html: formatTextWithLinks(result.defectSummary),
                  }}
                />
              </div>
            )}

            {/* Analysis Section */}
            {result.analysis && (
              <div className="analysis">
                <strong>Analysis:</strong>
                {result.analysis.split("\n").map((line, index) => {
                  return (
                    <p
                      key={index}
                      style={{
                        textAlign: "left",
                        marginLeft: /^\d+\./.test(line.trim()) ? "2rem" : "0",
                      }}
                      dangerouslySetInnerHTML={{
                        __html: formatTextWithLinks(line),
                      }}
                    />
                  );
                })}
              </div>
            )}
          </>
        )}

        {/* Fallback message */}
        {!result && response.message && (
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
