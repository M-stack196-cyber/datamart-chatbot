import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { formatDateTime } from "../utils";

export default function AdminPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();

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
    } catch (requestError) {
      setError(requestError.message || "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (!toast) {
      return undefined;
    }

    const timeout = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(timeout);
  }, [toast]);

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

  async function onChangeRole(userId, role) {
    try {
      await api.updateUserRole(userId, role);
      setToast("User role updated");
      await loadData();
    } catch (requestError) {
      setError(requestError.message || "Role update failed");
    }
  }

  async function onToggleStatus(user) {
    const actionLabel = user.is_active ? "deactivate" : "reactivate";
    const confirmed = window.confirm(`Are you sure you want to ${actionLabel} this user?`);
    if (!confirmed) {
      return;
    }

    try {
      await api.updateUserStatus(user.id, !user.is_active);
      setToast("User status updated");
      await loadData();
    } catch (requestError) {
      setError(requestError.message || "Status update failed");
    }
  }

  async function onUpdateLeadStatus(leadId, status) {
    try {
      await api.updateLeadStatus(leadId, status);
      setToast("Lead status updated");
      await loadData();
    } catch (requestError) {
      setError(requestError.message || "Status update failed");
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
              <button type="submit" className="button">
                Upload
              </button>
            </form>
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
                        <button type="button" className="danger-link" onClick={() => onDeleteDocument(doc.id)}>
                          Delete
                        </button>
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
          {loading ? <p>Loading users...</p> : null}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Active</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>{user.email}</td>
                    <td>
                      <select value={user.role} onChange={(event) => onChangeRole(user.id, event.target.value)}>
                        <option value="admin">admin</option>
                        <option value="employee">employee</option>
                        <option value="customer">customer</option>
                      </select>
                    </td>
                    <td>{user.is_active ? "Yes" : "No"}</td>
                    <td>{formatDateTime(user.created_at)}</td>
                    <td>
                      <button type="button" className="button secondary" onClick={() => onToggleStatus(user)}>
                        {user.is_active ? "Deactivate" : "Reactivate"}
                      </button>
                    </td>
                  </tr>
                ))}
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
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  );
}