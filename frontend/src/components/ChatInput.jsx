import { useState } from "react";

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState("");

  const submit = () => {
    const nextValue = value.trim();
    if (!nextValue || disabled) {
      return;
    }
    onSend(nextValue);
    setValue("");
  };

  return (
    <div className="chat-input-wrap">
      <input
        type="text"
        value={value}
        placeholder="Ask a question about the knowledge base..."
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            submit();
          }
        }}
        disabled={disabled}
      />
      <button type="button" onClick={submit} disabled={disabled} className="button">
        Send
      </button>
    </div>
  );
}
