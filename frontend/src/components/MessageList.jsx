import MessageBubble from "./MessageBubble";

export default function MessageList({ messages, loading }) {
  return (
    <section className="message-list">
      {messages.length === 0 ? <p className="empty-state">Ask a question to start this conversation.</p> : null}

      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {loading ? (
        <div className="message-row assistant">
          <div className="message-bubble assistant typing">Assistant is typing...</div>
        </div>
      ) : null}
    </section>
  );
}
