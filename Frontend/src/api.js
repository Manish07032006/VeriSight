import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:5000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach the JWT token (if present) to every outgoing request automatically.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function saveToken(token) {
  localStorage.setItem("token", token);
}

export function getToken() {
  return localStorage.getItem("token");
}

export function clearToken() {
  localStorage.removeItem("token");
}

export async function signup(username, email, password) {
  const response = await api.post("/auth/signup", { username, email, password });
  return response.data; // { message, token, user }
}

export async function login(username, password) {
  const response = await api.post("/auth/login", { username, password });
  return response.data; // { message, token, user }
}

export async function getCurrentUser() {
  const response = await api.get("/auth/me");
  return response.data; // { user }
}

export async function scanText(inputText) {
  const response = await api.post("/scan/text", { input_text: inputText });
  return response.data;
}

export async function getHistory() {
  const response = await api.get("/history");
  return response.data; // { history: [...], total }
}

export async function scanMedia(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post("/scan/media", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export default api;