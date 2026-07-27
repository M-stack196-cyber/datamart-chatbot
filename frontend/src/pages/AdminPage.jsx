import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { formatDateTime } from "../utils";

// Kept in sync by hand with backend app/models/__init__.py.
// MANAGE_ROLES can change roles / deactivate accounts.
// STAFF_ROLES (superset) can view leads/users/documents and take live chats.
const ALL_ROLES = ["admin", "ceo", "cto", "pmo", "hr", "user", "customer"];
const MANAGE_ROLES = ["admin", "ceo"];

export default function AdminPage() {
  const navigate = useNavigate();
  const { logout, user } = useAuth();

  const isManager = MANAGE_ROLES.includes(user?.role);

  const [activeTab, setActiveTab] = useState("documents");
  const [documents, setDocuments] = useState([]);
  const [users, setUsers] = useState([]);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [visibility, setVisibility] = useState("external");
  const [selectedFile, setSelectedFile] = useState(null);
  const [toast, setToast] = useState("");
  const [error, setError] = useState("");

  // ---- Live handoff state ----
  const [isOnline, setIsOnline] = useState(false);
  const [onlineStaff, setOnlineStaff] = useState([]);
  const [handoffQueue, setHandoffQueue] = useState([]);
  const [activeHandoffs, setActiveHandoffs] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [handoffMessages, setHandoffMessages] = useState([]);
  const [replyText, setReplyText] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const [docs, userList, leadsList] = await Promise.all([
        api.listDocuments(),
        api.listUsers(),
        api.listLeads ? api.listLeads() : []
      ]);
      setDocuments(docs);
      setUsers(userList);
      setLeads(leadsList || []);

      // The backend doesn't have a dedicated "who am I, and am I online"
      // endpoint - but the current user's own row is right there in the
      // user list, so we can read is_online off it instead of adding a
      // new route just for this.
      const myEmail = user?.email;
      if (myEmail) {
        const myRow = (userList || []).find((u) => u.email === myEmail);
        if (myRow) {
          setIsOnline(Boolean(myRow.is_online));
        }
      }
    } catch (requestError) {
      setError(requestError.message || "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!toast) {
      return undefined;
    }

    const timeout = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(timeout);
  }, [toast]);

  // ------------------------------------------------------------------
  // Live handoff: load queue / active chats / team status
  // ------------------------------------------------------------------
  const loadHandoffData = useCallback(async () => {
    try {
      const [queueRes, activeRes, staffRes] = await Promise.all([
        api.getHandoffQueue(),
        api.getMyActiveHandoffs(),
        api.listOnlineStaff(),
      ]);
      setHandoffQueue(queueRes?.queue || []);
      setActiveHandoffs(activeRes?.active || []);
      setOnlineStaff(staffRes || []);
    } catch (requestError) {
      setError(requestError.message || "Failed to load live chat data");
    }
  }, []);

  const loadHandoffMessages = useCallback(async (conversationId) => {
    if (!conversationId) return;
    try {
      const res = await api.getHandoffMessages(conversationId);
      setHandoffMessages(res?.messages || []);
    } catch (requestError) {
      setError(requestError.message || "Failed to load chat messages");
    }
  }, []);

  // Poll the queue/active list every 5s while the Live Chats tab is open,
  // and poll the open conversation's messages too so replies from the
  // visitor show up without a manual refresh.
  useEffect(() => {
    if (activeTab !== "livechats") {
      return undefined;
    }

    loadHandoffData();
    const interval = setInterval(() => {
      loadHandoffData();
      if (selectedConversationId) {
        loadHandoffMessages(selectedConversationId);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [activeTab, selectedConversationId, loadHandoffData, loadHandoffMessages]);

  async function onToggleOnline() {
    const next = !isOnline;
    try {
      await api.setMyOnlineStatus(next);
      setIsOnline(next);
      setToast(next ? "You're online - visitors can be connected to you" : "You're offline");
      if (activeTab === "livechats") {
        loadHandoffData();
      }
    } catch (requestError) {
      setError(requestError.message || "Failed to update online status");
    }
  }

  async function onClaim(conversationId) {
    try {
      await api.claimHandoff(conversationId);
      setToast("Chat claimed");
      await loadHandoffData();
      setSelectedConversationId(conversationId);
      await loadHandoffMessages(conversationId);
    } catch (requestError) {
      setError(requestError.message || "Failed to claim chat - it may have already been claimed by someone else");
      await loadHandoffData();
    }
  }

  async function onOpenChat(conversationId) {
    setSelectedConversationId(conversationId);
    await loadHandoffMessages(conversationId);
  }

  async function onSendReply(event) {
    event.preventDefault();
    if (!replyText.trim() || !selectedConversationId) {
      return;
    }
    try {
      await api.sendHandoffMessage(selectedConversationId, replyText.trim());
      setReplyText("");
      await loadHandoffMessages(selectedConversationId);
    } catch (requestError) {
      setError(requestError.message || "Failed to send message");
    }
  }

  async function onEndChat(conversationId) {
    const confirmed = window.confirm("End this live chat? The visitor will see a closing message.");
    if (!confirmed) return;

    try {
      await api.endHandoff(conversationId);
      setToast("Chat ended");
      if (selectedConversationId === conversationId) {
        setSelectedConversationId(null);
        setHandoffMessages([]);
      }
      await loadHandoffData();
    } catch (requestError) {
      setError(requestError.message || "Failed to end chat");
    }
  }

  // ------------------------------------------------------------------
  // Documents
  // ------------------------------------------------------------------
  async function onUpload(event) {
    event.preventDefault();
    if (!selectedFile || !title.trim()) {
      setError("Title and file are required");
      return;
    }

    setError("");
    const formData = new FormData();
    formData.append("title", title);
    formData.append("visibility", visibility);
    formData.append("file", selectedFile);

    try {
      await api.uploadDocument(formData);
      setToast("Document upload submitted");
      setTitle("");
      setVisibility("external");
      setSelectedFile(null);
      await loadData();
    } catch (requestError) {
      setError(requestError.message || "Upload failed");
    }
  }

  async function onDeleteDocument(documentId) {
    const confirmed = window.confirm("Delete this document and its vectors?");
    if (!confirmed) {
      return;
    }

    try {
      await api.deleteDocument(documentId);
      setToast("Document deleted");
      await loadData();
    } catch (requestError) {
      setError(requestError.message || "Delete failed");
    }
  }

  // ------------------------------------------------------------------
  // Users
  // ------------------------------------------------------------------
  async function onChangeRole(userId, role) {
    try {
      await api.updateUserRole(userId, role);
      setToast("User role updated");
      await loadData();
    } catch (requestError) {
      setError(requestError.message || "Role update failed");
    }
  }

  async function onToggleStatus(targetUser) {
    const actionLabel = targetUser.is_active ? "deactivate" : "reactivate";
    const confirmed = window.confirm(
      `Are you sure you want to ${actionLabel} ${targetUser.email}? ${
        targetUser.is_active ? "They will be logged out immediately and unable to sign in again until reactivated." : ""
      }`
    );
    if (!confirmed) {
      return;
    }

    try {
      await api.updateUserStatus(targetUser.id, !targetUser.is_active);
      setToast(`User ${actionLabel}d`);
      await loadData();
    } catch (requestError) {
      setError(requestError.message || "Status update failed");
    }
  }

  // ------------------------------------------------------------------
  // Leads
  // ------------------------------------------------------------------
  async function onUpdateLeadStatus(leadId, status) {
    try {
      await api.updateLeadStatus(leadId, status);
      setToast("Lead status updated");
      await loadData();
    } catch (requestError) {
      setError(requestError.message || "Status update failed");
    }
  }

  // Delete a lead
  async function onDeleteLead(leadId, leadName) {
    const confirmed = window.confirm(`Are you sure you want to delete lead "${leadName}"? This action cannot be undone.`);
    if (!confirmed) return;

    try {
      await api.deleteLead(leadId);
      setToast(`Lead "${leadName}" deleted successfully`);
      await loadData();
    } catch (requestError) {
      setError(requestError.message || "Failed to delete lead");
    }
  }

  // Delete a user
  async function onDeleteUser(userId, userName) {
    const confirmed = window.confirm(`Are you sure you want to delete user "${userName}"? This action cannot be undone.`);
    if (!confirmed) return;

    try {
      await api.deleteUser(userId);
      setToast(`User "${userName}" deleted successfully`);
      await loadData();
    } catch (requestError) {
      setError(requestError.message || "Failed to delete user");
    }
  }

  const getStatusBadge = (status) => {
    const colors = {
      new: "badge-new",
      contacted: "badge-contacted",
      qualified: "badge-qualified",
      closed: "badge-closed"
    };
    return colors[status] || "badge-new";
  };

  return (
    <main className="admin-page">
      <header className="admin-header">
        <h1>Admin Panel</h1>
        <div className="header-actions">
          <button
            type="button"
            className={`status-toggle ${isOnline ? "online" : "offline"}`}
            onClick={onToggleOnline}
            title={isOnline ? "Click to go offline" : "Click to go online for live chat handoffs"}
          >
            <span className="status-dot" /> {isOnline ? "Online" : "Offline"}
          </button>
          <button type="button" className="button secondary" onClick={() => navigate("/chat")}>
            Back to chat
          </button>
          <button type="button" className="button secondary" onClick={() => logout()}>
            Logout
          </button>
        </div>
      </header>

      {toast ? <div className="toast">{toast}</div> : null}
      {error ? <p className="error-message">{error}</p> : null}

      {/* Tabs */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === "documents" ? "active" : ""}`}
          onClick={() => setActiveTab("documents")}
        >
          📄 Documents ({documents.length})
        </button>
        <button
          className={`tab ${activeTab === "users" ? "active" : ""}`}
          onClick={() => setActiveTab("users")}
        >
          👤 Users ({users.length})
        </button>
        <button
          className={`tab ${activeTab === "leads" ? "active" : ""}`}
          onClick={() => setActiveTab("leads")}
        >
          💼 Leads ({leads.length})
        </button>
        <button
          className={`tab ${activeTab === "livechats" ? "active" : ""}`}
          onClick={() => setActiveTab("livechats")}
        >
          💬 Live Chats {handoffQueue.length > 0 ? `(${handoffQueue.length} waiting)` : ""}
        </button>
      </div>

      {/* Documents Tab */}
      {activeTab === "documents" && (
        <>
          <section className="card">
            <h2>Upload document</h2>
            <form className="upload-form" onSubmit={onUpload}>
              <input
                type="text"
                placeholder="Document title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                required
              />

              <select value={visibility} onChange={(event) => setVisibility(event.target.value)}>
                <option value="internal">internal</option>
                <option value="external">external</option>
                <option value="both">both</option>
              </select>

              <input type="file" onChange={(event) => setSelectedFile(event.target.files?.[0] || null)} required />
              <button type="submit" className="button" disabled={!isManager}>
                Upload
              </button>
            </form>
            {!isManager ? <p className="sidebar-note">Only admin/CEO can upload or delete documents.</p> : null}
          </section>

          <section className="card">
            <h2>Documents</h2>
            {loading ? <p>Loading documents...</p> : null}
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Visibility</th>
                    <th>Status</th>
                    <th>Chunk count</th>
                    <th>Uploaded</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr key={doc.id}>
                      <td>{doc.title}</td>
                      <td>{doc.visibility}</td>
                      <td>{doc.status}</td>
                      <td>{doc.chunk_count}</td>
                      <td>{formatDateTime(doc.created_at)}</td>
                      <td>
                        {isManager ? (
                          <button type="button" className="danger-link" onClick={() => onDeleteDocument(doc.id)}>
                            Delete
                          </button>
                        ) : (
                          <span className="sidebar-note">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      {/* Users Tab */}
      {activeTab === "users" && (
        <section className="card">
          <h2>Users</h2>
          {!isManager ? (
            <p className="sidebar-note">You can view the team below. Only admin/CEO can change roles or remove members.</p>
          ) : null}
          {loading ? <p>Loading users...</p> : null}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Online</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((targetUser) => {
                  const isSelf = targetUser.email === user?.email;
                  return (
                    <tr key={targetUser.id}>
                      <td>
                        {targetUser.email}
                        {isSelf ? " (you)" : ""}
                      </td>
                      <td>
                        {isManager && !isSelf ? (
                          <select
                            value={targetUser.role}
                            onChange={(event) => onChangeRole(targetUser.id, event.target.value)}
                          >
                            {ALL_ROLES.map((role) => (
                              <option key={role} value={role}>
                                {role}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <span className="role-badge admin">{targetUser.role}</span>
                        )}
                      </td>
                      <td>{targetUser.is_active ? "Active" : "Deactivated"}</td>
                      <td>
                        <span className={`status-dot ${targetUser.is_online ? "online" : "offline"}`} />
                      </td>
                      <td>{formatDateTime(targetUser.created_at)}</td>
                      <td>
                        {isManager && !isSelf ? (
                          <>
                            <button type="button" className="button secondary small" onClick={() => onToggleStatus(targetUser)}>
                              {targetUser.is_active ? "Deactivate" : "Reactivate"}
                            </button>
                            <button type="button" className="danger-link small" onClick={() => onDeleteUser(targetUser.id, targetUser.email)}>
                              Delete
                            </button>
                          </>
                        ) : (
                          <span className="sidebar-note">{isSelf ? "—" : "Managed by admin/CEO"}</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Leads Tab */}
      {activeTab === "leads" && (
        <section className="card">
          <h2>💼 Leads</h2>
          {loading ? <p>Loading leads...</p> : null}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Project</th>
                  <th>Budget</th>
                  <th>Timeline</th>
                  <th>Status</th>
                  <th>Received</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {leads.map((lead) => (
                  <tr key={lead.id}>
                    <td><strong>{lead.name}</strong></td>
                    <td>{lead.email}</td>
                    <td>{lead.phone}</td>
                    <td>{lead.project_title || 'N/A'}</td>
                    <td>{lead.budget || 'N/A'}</td>
                    <td>{lead.timeline || 'N/A'}</td>
                    <td>
                      <select
                        value={lead.status}
                        onChange={(e) => onUpdateLeadStatus(lead.id, e.target.value)}
                        className={getStatusBadge(lead.status)}
                      >
                        <option value="new">🟢 New</option>
                        <option value="contacted">🟡 Contacted</option>
                        <option value="qualified">🔵 Qualified</option>
                        <option value="closed">⚪ Closed</option>
                      </select>
                    </td>
                    <td>{formatDateTime(lead.created_at)}</td>
                    <td>
                      <button
                        type="button"
                        className="button secondary small"
                        onClick={() => alert(`Lead Details:\nName: ${lead.name}\nEmail: ${lead.email}\nPhone: ${lead.phone}\nProject: ${lead.project_description}`)}
                      >
                        View
                      </button>
                      {isManager && (
                        <button
                          type="button"
                          className="danger-link small"
                          onClick={() => onDeleteLead(lead.id, lead.name)}
                        >
                          Delete
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Live Chats Tab */}
      {activeTab === "livechats" && (
        <>
          <section className="card">
            <h2>Team status</h2>
            <div className="team-status-list">
              {onlineStaff.map((staff) => (
                <div key={staff.id} className="team-status-row">
                  <span className={`status-dot ${staff.is_online ? "online" : "offline"}`} />
                  {staff.name} <span className="sidebar-note">({staff.role})</span>
                </div>
              ))}
              {onlineStaff.length === 0 ? <p className="sidebar-note">No staff found.</p> : null}
            </div>
          </section>

          <section className="card">
            <h2>Waiting for a team member ({handoffQueue.length})</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Visitor</th>
                    <th>Email</th>
                    <th>Requested</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {handoffQueue.map((item) => (
                    <tr key={item.conversation_id}>
                      <td>{item.visitor_name || "Anonymous visitor"}</td>
                      <td>{item.visitor_email || "—"}</td>
                      <td>{formatDateTime(item.requested_at)}</td>
                      <td>
                        <button type="button" className="button" onClick={() => onClaim(item.conversation_id)}>
                          Claim
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {handoffQueue.length === 0 ? <p className="sidebar-note">No one is currently waiting.</p> : null}
            </div>
          </section>

          <section className="card">
            <h2>Your active chats</h2>
            <div className="active-chat-pills">
              {activeHandoffs.map((chat) => (
                <button
                  key={chat.conversation_id}
                  type="button"
                  className={`button secondary small ${selectedConversationId === chat.conversation_id ? "active-pill" : ""}`}
                  onClick={() => onOpenChat(chat.conversation_id)}
                >
                  Chat {chat.conversation_id.slice(0, 8)}
                </button>
              ))}
              {activeHandoffs.length === 0 ? <p className="sidebar-note">You have no active chats. Claim one from the queue above.</p> : null}
            </div>

            {selectedConversationId ? (
              <div className="handoff-chat-window">
                <div className="message-list">
                  {handoffMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`message-row ${msg.role === "agent" ? "user" : "assistant"}`}
                    >
                      <div className={`message-bubble ${msg.role === "agent" ? "user" : "assistant"}`}>
                        <p>{msg.message}</p>
                      </div>
                    </div>
                  ))}
                  {handoffMessages.length === 0 ? <p className="empty-state">No messages yet.</p> : null}
                </div>

                <form className="chat-input-wrap" onSubmit={onSendReply}>
                  <input
                    type="text"
                    placeholder="Reply to visitor..."
                    value={replyText}
                    onChange={(event) => setReplyText(event.target.value)}
                  />
                  <button type="submit" className="button">
                    Send
                  </button>
                </form>

                <button
                  type="button"
                  className="danger-link"
                  onClick={() => onEndChat(selectedConversationId)}
                >
                  End this chat
                </button>
              </div>
            ) : null}
          </section>
        </>
      )}
    </main>
  );
}