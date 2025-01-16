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
      console.log("API Response:", data); // Log the response to confirm its structure
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const formatResponse = (response) => {
    const result = response.results[0];
    return (
      <div className="response-container">
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
        <div className="defect-summary">
          <strong>Defect Summary:</strong> {result.defectSummary}
        </div>
        {result.analysis.split("\n").map((line, index) => {
          if (/^\d+\./.test(line.trim())) {
            return (
              <p key={index} style={{ textAlign: "left", marginLeft: "2rem" }}>
                {line}
              </p>
            );
          }
          return (
            <p key={index} style={{ textAlign: "left" }}>
              {line}
            </p>
          );
        })}
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
      {response && <ul>{formatResponse(response)}</ul>}
    </div>
  );
};

export default Main;
