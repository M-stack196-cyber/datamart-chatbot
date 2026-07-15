import { formatDateTime } from "../utils";

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onCreateConversation,
  onDeleteConversation,
  loading,
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>Conversations</h2>
        <button type="button" onClick={onCreateConversation} className="button secondary">
          New
        </button>
      </div>

      {loading ? <p className="sidebar-note">Loading...</p> : null}

      <ul className="conversation-list">
        {conversations.map((conversation) => (
          <li key={conversation.id}>
            <button
              type="button"
              className={`conversation-item ${currentConversationId === conversation.id ? "active" : ""}`}
              onClick={() => onSelectConversation(conversation.id)}
            >
              <span className="conversation-title">{conversation.title || "Untitled"}</span>
              <span className="conversation-time">{formatDateTime(conversation.updated_at)}</span>
            </button>
            <button
              type="button"
              className="danger-link"
              onClick={() => onDeleteConversation(conversation.id)}
              aria-label="Delete conversation"
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
