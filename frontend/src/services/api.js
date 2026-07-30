// ============================================================
// API CONFIGURATION
// ============================================================

// Use Vite's import.meta.env for dynamic environment variables
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

let getTokenRef = () => null;
let onUnauthorizedRef = () => {};

export function configureApiAuth({ getToken, onUnauthorized } = {}) {
  if (getToken !== undefined) getTokenRef = getToken;
  if (onUnauthorized !== undefined) onUnauthorizedRef = onUnauthorized;
}

// ============================================================
// BASE REQUEST FUNCTION
// ============================================================

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

  // Build the full URL
  const fullUrl = `${API_BASE_URL}${path}`;
  console.log('🔍 API Request URL:', fullUrl); // Debugging

  try {
    const response = await fetch(fullUrl, options);

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
    console.error('❌ API Error:', error);
    return {
      answer: "I'm having connection issues. Please check your internet and try again. If the problem persists, contact us at info@dtm.io.",
      _isError: true
    };
  }
}

// ============================================================
// AUTHENTICATION ENDPOINTS
// ============================================================

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

// ============================================================
// CHAT ENDPOINTS
// ============================================================

async function chatRequest(message, conversationId) {
  try {
    const result = await request("/api/chat", {
      method: "POST",
      body: { message, conversation_id: conversationId },
    });
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

// PUBLIC CHAT (No authentication required)
async function publicChatRequest(message, conversationId) {
  try {
    const result = await request("/api/chat-public", {
      method: "POST",
      body: { message, conversation_id: conversationId },
    });
    return result;
  } catch (error) {
    console.error('❌ Public Chat Error:', error);
    return {
      response: "I'm having trouble connecting right now. Please try again in a moment. If the issue persists, contact us at info@dtm.io.",
      _isError: true
    };
  }
}

// ============================================================
// API EXPORTS
// ============================================================

export const api = {
  // Chat
  chat: chatRequest,
  chatPublic: publicChatRequest,

  // Conversations
  createConversation: () => request("/api/conversations", { method: "POST" }),
  getConversations: () => request("/api/conversations"),
  getConversationMessages: (conversationId) => request(`/api/conversations/${conversationId}/messages`),
  saveMessage: (conversationId, payload) =>
    request(`/api/conversations/${conversationId}/messages`, { method: "POST", body: payload }),
  deleteConversation: (conversationId) =>
    request(`/api/conversations/${conversationId}`, { method: "DELETE" }),

  // Admin
  uploadDocument: (formData) => request("/api/admin/upload", { method: "POST", body: formData }),
  listDocuments: () => request("/api/admin/documents"),
  deleteDocument: (documentId) => request(`/api/admin/documents/${documentId}`, { method: "DELETE" }),
  listUsers: () => request("/api/admin/users"),
  updateUserRole: (userId, role) =>
    request(`/api/admin/users/${userId}/role`, { method: "PATCH", body: { role } }),
  updateUserStatus: (userId, is_active) =>
    request(`/api/admin/users/${userId}/status`, { method: "PATCH", body: { is_active } }),

  // Leads
  listLeads: () => request("/api/admin/leads"),
  updateLeadStatus: (leadId, status) =>
    request(`/api/admin/leads/${leadId}/status?status=${status}`, { method: "PATCH" }),
  
  // Delete endpoints
  deleteLead: (leadId) => request(`/api/admin/leads/${leadId}`, { method: "DELETE" }),
  deleteUser: (userId) => request(`/api/admin/users/${userId}`, { method: "DELETE" }),

  // Live handoff - staff presence
  setMyOnlineStatus: (is_online) =>
    request("/api/admin/me/online", { method: "PATCH", body: { is_online } }),
  listOnlineStaff: () => request("/api/admin/online-staff"),

  // Live handoff - queue and active chats
  getHandoffQueue: () => request("/api/admin/handoff/queue"),
  getMyActiveHandoffs: () => request("/api/admin/handoff/active"),
  claimHandoff: (conversationId) =>
    request(`/api/admin/handoff/${conversationId}/claim`, { method: "POST" }),
  getHandoffMessages: (conversationId) =>
    request(`/api/admin/handoff/${conversationId}/messages`),
  sendHandoffMessage: (conversationId, message) =>
    request(`/api/admin/handoff/${conversationId}/message`, { method: "POST", body: { message } }),
  endHandoff: (conversationId) =>
    request(`/api/admin/handoff/${conversationId}/end`, { method: "POST" }),
};