const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://datamart-backend.vercel.app";

let getTokenRef = () => null;
let onUnauthorizedRef = () => {};

export function configureApiAuth({ getToken, onUnauthorized } = {}) {
  if (getToken !== undefined) getTokenRef = getToken;
  if (onUnauthorized !== undefined) onUnauthorizedRef = onUnauthorized;
}

async function request(path, { method = "GET", body, headers = {} } = {}) {
  const token = getTokenRef();
  const requestHeaders = { ...headers };
  const options = { method, headers: requestHeaders };

  if (token) {
    requestHeaders.Authorization = `Bearer ${token}`;
  }

  if (body instanceof FormData) {
    options.body = body;
  } else if (body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, options);

    if (response.status === 401) {
      onUnauthorizedRef();
      throw new Error("UNAUTHORIZED");
    }

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (data && data.answer) {
        return data;
      }
      throw new Error(data.detail || "Request failed");
    }

    return data;
  } catch (error) {
    if (error.message === "UNAUTHORIZED") {
      throw error;
    }
    return {
      answer: "I'm having connection issues. Please check your internet and try again. If the problem persists, contact us at info@dtm.io.",
      _isError: true
    };
  }
}

export async function loginRequest(email, password) {
  const body = new URLSearchParams();
  body.append("username", email);
  body.append("password", password);

  const response = await fetch(`${API_BASE_URL}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Login failed");
  }

  return data;
}

export async function signupRequest(payload) {
  const response = await fetch(`${API_BASE_URL}/api/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = Array.isArray(data.detail)
      ? data.detail.map((issue) => issue.msg).join(", ")
      : data.detail || "Signup failed";
    throw new Error(message);
  }

  return data;
}

async function chatRequest(question) {
  try {
    const result = await request("/api/chat", { method: "POST", body: { question } });
    return result;
  } catch (error) {
    if (error.message === "UNAUTHORIZED") {
      throw error;
    }
    return {
      answer: "I'm having trouble connecting right now. Please try again in a moment. If the issue persists, contact us at info@dtm.io.",
      _isError: true
    };
  }
}

// ============================================================
// PUBLIC CHAT (No authentication required)
// ============================================================
async function publicChatRequest(message) {
  try {
    const result = await request("/api/chat-public", { method: "POST", body: { message } });
    return result;
  } catch (error) {
    return {
      response: "I'm having trouble connecting right now. Please try again in a moment. If the issue persists, contact us at info@dtm.io.",
      _isError: true
    };
  }
}

export const api = {
  chat: chatRequest,
  chatPublic: publicChatRequest,  // NEW: Public chat for widget
  createConversation: () => request("/api/conversations", { method: "POST" }),
  getConversations: () => request("/api/conversations"),
  getConversationMessages: (conversationId) => request(`/api/conversations/${conversationId}/messages`),
  saveMessage: (conversationId, payload) =>
    request(`/api/conversations/${conversationId}/messages`, { method: "POST", body: payload }),
  deleteConversation: (conversationId) =>
    request(`/api/conversations/${conversationId}`, { method: "DELETE" }),
  uploadDocument: (formData) => request("/api/admin/upload", { method: "POST", body: formData }),
  listDocuments: () => request("/api/admin/documents"),
  deleteDocument: (documentId) => request(`/api/admin/documents/${documentId}`, { method: "DELETE" }),
  listUsers: () => request("/api/admin/users"),
  updateUserRole: (userId, role) =>
    request(`/api/admin/users/${userId}/role`, { method: "PATCH", body: { role } }),
  updateUserStatus: (userId, is_active) =>
    request(`/api/admin/users/${userId}/status`, { method: "PATCH", body: { is_active } }),
  listLeads: () => request("/api/admin/leads"),
  updateLeadStatus: (leadId, status) =>
    request(`/api/admin/leads/${leadId}/status?status=${status}`, { method: "PATCH" }),
};