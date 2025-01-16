// src/api/apiService.js
//import DummyResponse from "./DummyResponse.json";
import apiClient from "./axiosConfig";

// Fetch current weather for a given location
export const fetchResponse = async (issue) => {
  try {
    console.log("entered");
    const response = await apiClient.post(
      "http://localhost:8000/defects/response",
      {
        prompt: issue,
      } // Dynamic query parameter
    );
    //console.log(response.data.response);
    return response.data.response;

    // Dummy Response
    //return DummyResponse;
  } catch (error) {
    handleApiError(error);
  }
};

// Error handling
const handleApiError = (error) => {
  if (error.response) {
    console.error("Response Error:", error.response.data.error.message);
    throw new Error(error.response.data.error.message);
  } else {
    console.error("Unexpected Error:", error.message);
    throw new Error("Unexpected error occurred. Please try again.");
  }
};
