// src/api/weatherService.js
import apiClient from "./axiosConfig";

// Fetch current weather for a given location
export const fetchResponse = async (issue) => {
  try {
    const response = await apiClient.get(
      {
        /* api endpoints with '/' */
      },
      {
        params: { q: issue }, // Dynamic query parameter
      }
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
