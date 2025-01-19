import apiClient from "./axiosConfig";

export const fetchResponse = async (issue) => {
  try {
    console.log("entered");
    const response = await apiClient.post(
      "http://localhost:8000/defects/response",
      {
        prompt: issue,
      }
    );
    console.log(response.data.response);
    return response.data.response;
  } catch (error) {
    handleApiError(error);
  }
};

const handleApiError = (error) => {
  if (error.response) {
    console.error("Response Error:", error.response.data.error.message);
    throw new Error(error.response.data.error.message);
  } else {
    console.error("Unexpected Error:", error.message);
    throw new Error("Unexpected error occurred. Please try again.");
  }
};
