import React, { useState, useRef, useEffect } from "react";
import "./main.css";
import { fetchResponse } from "../../api/apiService";

const Main = () => {
  const [messages, setMessages] = useState([]);
  const [currentMessage, setCurrentMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedIndex, setExpandedIndex] = useState(null);
  
  // Reference to the chat messages container for auto-scrolling
  const chatContainerRef = useRef(null);

  // Function to scroll the chat container to the bottom
  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  };

  // Scroll to bottom whenever messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Add initial message when component mounts
  useEffect(() => {
    const initialMessage = {
      id: Date.now(),
      sender: "bot",
      message: "👋 Hello! I'm Bugbuster, your AI assistant for defect resolution. I can help you with:\n\n" +
               "1. Finding defect owners\n" +
               "2. Understanding root causes\n" +
               "3. Getting defect solutions\n" +
               "4. Searching by JIRA ID\n\n" +
               "How can I assist you today?",
      results: []
    };
    setMessages([initialMessage]);
  }, []);

  const handleSendMessage = async () => {
    if (!currentMessage.trim()) return;

    const newMessage = {
      id: Date.now(),
      text: currentMessage,
      sender: "user",
    };
    setMessages((prevMessages) => [...prevMessages, newMessage]);
    
    // Add a loading message to the chat
    const loadingId = Date.now() + 1;
    setMessages((prevMessages) => [
      ...prevMessages, 
      { 
        id: loadingId,
        sender: "bot",
        type: "loading"
      }
    ]);
    
    setIsLoading(true);
    setError("");
    try {
      const data = await fetchResponse(currentMessage);
      // console.log("API Response:", data);
      
      // Create bot message object that includes the entire response
      const botMessage = { 
        id: Date.now() + 2,
        sender: "bot",
        message: data.message || "Sorry, I couldn't understand the response.",
        results: data.results || []
      };
      
      // Replace the loading message with the actual response
      setMessages((prevMessages) => 
        prevMessages.filter(msg => msg.id !== loadingId).concat(botMessage)
      );
    } catch (err) {
      setError(err.message);
      const errorMessage = { 
        id: Date.now() + 2,
        sender: "bot",
        message: `Error: ${err.message}`,
        type: "error"
      }; 
      
      // Replace the loading message with the error message
      setMessages((prevMessages) => 
        prevMessages.filter(msg => msg.id !== loadingId).concat(errorMessage)
      );
    } finally {
      setIsLoading(false);
    }
    setCurrentMessage(""); // Clear input after sending
  };

  const formatTextWithLinks = (text) => {
    // Keep existing HTML links
    if (text.includes('<a href=')) {
      return text;
    }
    // Format plain URLs
    const urlPattern = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlPattern, (url) => {
      return `<a href="${url}" target="_blank" rel="noopener noreferrer">Click here</a>`;
    });
  };

  const toggleExpand = (index) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  const renderMessage = (msg) => {
    if (msg.sender === "user") {
      // For user messages, just render the text
      return <p>{msg.text}</p>;
    } else if (msg.type === "error") {
      // For error messages
      return <p className="error-text">{msg.message}</p>;
    } else if (msg.type === "loading") {
      // For loading messages, show the typing indicator
      return (
        <div className="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
      );
    } else {
      // For bot messages with possible results
      return (
        <div className="bot-response">
          {/* Always show the message */}
          <p className="bot-message" style={{ whiteSpace: 'pre-line' }}>{msg.message}</p>
          
          {/* If there are results, display them */}
          {msg.results && msg.results.length > 0 && (
            <div className="results-container">
              {msg.results.map((result, index) => (
                <div key={index} className="defect-item">
                  <div className="defect-summary">
                    <div className="summary-content" onClick={() => toggleExpand(index)}>
                      <span className={`toggle-icon ${expandedIndex === index ? "expanded" : ""}`}>
                        {expandedIndex === index ? "▼" : "▶"}
                      </span>
                      <span className="summary-text">
                        <strong>Defect Summary:</strong> {result.defectSummary}
                      </span>
                    </div>
                    {/* <button
                      className="detail-view-btn"
                      onClick={() => toggleExpand(index)}
                    >
                      {expandedIndex === index ? "Hide Details" : "View Details"}
                    </button> */}
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
              ))}
            </div>
          )}
        </div>
      );
    }
  };

  return (
    <div className="main">
      <div className="chat-messages-area" ref={chatContainerRef}>
        {messages.map((msg) => (
          <div key={msg.id} className={`message ${msg.sender}`}>
            {renderMessage(msg)}
          </div>
        ))}
      </div>
      <div className="chat-input-container">
        <input
          type="text"
          placeholder="Type your message..."
          className="chat-input"
          value={currentMessage}
          onChange={(e) => setCurrentMessage(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
        />
        <button className="chat-send-button" onClick={handleSendMessage}>
          Send
        </button>
      </div>
      {error && <p className="error-text" style={{ color: "red" }}>Error: {error}</p>}
    </div>
  );
};

export default Main;
