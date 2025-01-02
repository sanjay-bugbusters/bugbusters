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
      {response && <div>{response.message}</div>}{" "}
      {/* display response here using (response. )*/}
    </div>
  );
};

export default Main;
