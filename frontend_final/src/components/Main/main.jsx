import React, { useState, useRef, useEffect } from "react";
import "./main.css";
import { fetchBugbusterResponse, fetchUVRulesResponse } from "../../api/apiService";

const Main = () => {
  const [messages, setMessages] = useState([]);
  const [currentMessage, setCurrentMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [expandedIndex, setExpandedIndex] = useState(null);
  const [chatbotType, setChatbotType] = useState('bugbuster');
  
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

  // Update welcome message based on chatbot type
  useEffect(() => {
    const welcomeMessage = {
      id: Date.now(),
      sender: "bot",
      message: chatbotType === 'bugbuster' ? `
        <div class="welcome-message">
          <h2>Hello! 👋 I'm Defect Triage Assistant</h2>
          <p>Your AI assistant for defect analysis. Here's how I can help you:</p>
          <ul class="feature-list">
            <li>🔍 Finding specific defects</li>
            <li>📋 Listing all defects</li>
            <li>👥 Showing defect owners</li>
            <li>🔎 Analyzing root causes</li>
            <li>💡 Providing solutions</li>
          </ul>
          <p class="prompt-text">How can I assist you today?</p>
        </div>
      ` : `
        <div class="welcome-message">
          <h2>Hello! 👋 I'm UW Rules Assistant</h2>
          <p>I can help you understand and resolve UW rule violations.</p>
          <p>Please provide your policy number and rule code (e.g., E101) for assistance.</p>
        </div>
      `,
      content_type: 'html'
    };
    setMessages([welcomeMessage]);
  }, [chatbotType]); // Empty dependency array means this runs once on mount

  const handleChatbotChange = (type) => {
    setChatbotType(type);
    setMessages([]);
    setCurrentMessage('');
    setError('');
    setExpandedIndex(null);
  };

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
      const data = chatbotType === 'bugbuster' 
        ? await fetchBugbusterResponse(currentMessage)
        : await fetchUVRulesResponse(currentMessage);
      console.log("API Response:", data);
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
    const urlPattern = /(https?:\/\/[^\s]+)/g;
    return text.replace(urlPattern, (url) => {
      return `<a href="${url}" target="_blank" rel="noopener noreferrer" style="color: blue; text-decoration: underline;">Click here</a>`;
    });
  };

  const toggleExpand = (index) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  const renderMessage = (msg) => {
    if (msg.sender === "user") {
      return <p>{msg.text}</p>;
    } else if (msg.type === "error") {
      return <p className="error-text">{msg.message}</p>;
    } else if (msg.type === "loading") {
      return (
        <div className="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
      );
    } else {
      // Decode HTML entities and create element with HTML content
      const decodedMessage = msg.message.replace(/&lt;/g, '<')
                                      .replace(/&gt;/g, '>')
                                      .replace(/&quot;/g, '"')
                                      .replace(/&#39;/g, "'")
                                      .replace(/&amp;/g, '&');
      
      return (
        <div className="bot-response">
          <div 
            className="bot-message"
            dangerouslySetInnerHTML={{ __html: decodedMessage }}
          />
          
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
      <div className="chatbot-selector">
        <button 
          className={`selector-btn ${chatbotType === 'bugbuster' ? 'active' : ''}`}
          onClick={() => handleChatbotChange('bugbuster')}
        >
          Defect Triage
        </button>
        <button 
          className={`selector-btn ${chatbotType === 'uvrules' ? 'active' : ''}`}
          onClick={() => handleChatbotChange('uvrules')}
        >
          UW Rules
        </button>
      </div>
      <div className="chat-messages-area" ref={chatContainerRef}>
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={`message ${msg.sender} ${msg.content_type === 'html' ? 'html-content' : ''}`}
          >
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
        <select 
          className="chatbot-select"
          value={chatbotType}
          onChange={(e) => handleChatbotChange(e.target.value)}
        >
          <option value="bugbuster">Defect Triage</option>
          <option value="uvrules">UW Rules</option>
        </select>
        <button className="chat-send-button" onClick={handleSendMessage}>
          Send
        </button>
      </div>
      {error && <p className="error-text" style={{ color: "red" }}>Error: {error}</p>}
    </div>
  );
};

export default Main;
