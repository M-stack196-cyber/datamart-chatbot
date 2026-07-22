const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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

  const response = await fetch(`${API_BASE_URL}/login`, {
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
  const response = await fetch(`${API_BASE_URL}/signup`, {
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
    const result = await request("/chat", { method: "POST", body: { question } });
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
  createConversation: () => request("/conversations", { method: "POST" }),
  getConversations: () => request("/conversations"),
  getConversationMessages: (conversationId) => request(`/conversations/${conversationId}/messages`),
  saveMessage: (conversationId, payload) =>
    request(`/conversations/${conversationId}/messages`, { method: "POST", body: payload }),
  deleteConversation: (conversationId) =>
    request(`/conversations/${conversationId}`, { method: "DELETE" }),
  uploadDocument: (formData) => request("/admin/upload", { method: "POST", body: formData }),
  listDocuments: () => request("/admin/documents"),
  deleteDocument: (documentId) => request(`/admin/documents/${documentId}`, { method: "DELETE" }),
  listUsers: () => request("/admin/users"),
  updateUserRole: (userId, role) =>
    request(`/admin/users/${userId}/role`, { method: "PATCH", body: { role } }),
  updateUserStatus: (userId, is_active) =>
    request(`/admin/users/${userId}/status`, { method: "PATCH", body: { is_active } }),
  listLeads: () => request("/admin/leads"),
  updateLeadStatus: (leadId, status) =>
    request(`/admin/leads/${leadId}/status?status=${status}`, { method: "PATCH" }),
};