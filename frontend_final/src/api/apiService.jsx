import apiClient from "./axiosConfig";
import {marked} from "marked";

// Configure marked options
marked.setOptions({
  headerIds: false,
  mangle: false
});

export const fetchBugbusterResponse = async (issue) => {
  try {
    const response = await apiClient.post(
      "http://localhost:8000/defects/response",
      { prompt: issue }
    );
    
    const data = response.data.response;
    
    // Check if response is in markdown format
    if (typeof data.message === 'string' && 
        (data.message.includes('###') || data.message.includes('##') || data.message.includes('#'))) {
      return {
        message: `<div class="markdown-content">${marked(data.message)}</div>`,
        content_type: "html",
        results: data.results || []
      };
    }
    
    return data;
  } catch (error) {
    handleApiError(error);
  }
};

export const fetchUVRulesResponse = async (query) => {
  try {
    const response = await fetch("http://localhost:8080/rulehelp", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ user_request: query }),
    });

    const text = await response.text();

    // Try to parse as JSON first
    try {
      const data = JSON.parse(text);
      return {
        message: data.message || data,
        content_type: "text",
      };
    } catch (parseError) {
      // If JSON parsing fails, treat as Markdown
      console.log("Parsing response as Markdown");
      const htmlContent = marked(text);
      return {
        message: htmlContent,
        content_type: "html",
      };
    }
  } catch (error) {
    console.error("UV Rules API Error:", error);
    return {
      message:
        "Sorry, I'm having trouble connecting to the UV Rules service. Please try again.",
      content_type: "text",
    };
  }
};

const handleApiError = (error) => {
  if (error.response) {
    // console.error("Response Error:", error.response.data.error.message);
    throw new Error(error.response.data.error.message);
  } else {
    console.error("Unexpected Error:", error.message);
    throw new Error("Unexpected error occurred. Please try again.");
  }
};
