// src/api/apiService.js
import apiClient from "./axiosConfig";

// Fetch current weather for a given location
export const fetchResponse = async (issue) => {
  try {
    const response = await apiClient.post(
      "/issue/",
      {
        text: issue,
      } // Dynamic query parameter
    );
    return response.data;
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
