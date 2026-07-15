export default function MessageBubble({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`message-row ${isUser ? "user" : "assistant"}`}>
      <div className={`message-bubble ${isUser ? "user" : "assistant"}`}>
        <p>{message.content}</p>
        {!isUser && message.sources?.length ? (
          <p className="sources">Sourced from: {message.sources.join(", ")}</p>
        ) : null}
      </div>
    </div>
  );
}
