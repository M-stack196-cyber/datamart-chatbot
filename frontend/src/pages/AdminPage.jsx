import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { formatDateTime } from "../utils";

export default function AdminPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const [documents, setDocuments] = useState([]);
  const [users, setUsers] = useState([]);
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
      const [docs, userList] = await Promise.all([api.listDocuments(), api.listUsers()]);
      setDocuments(docs);
      setUsers(userList);
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
    </main>
  );
}
