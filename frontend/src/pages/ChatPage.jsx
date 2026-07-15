import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import ChatInput from "../components/ChatInput";
import MessageList from "../components/MessageList";
import Sidebar from "../components/Sidebar";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";
import { extractChatPayload } from "../utils";

export default function ChatPage() {
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [chatError, setChatError] = useState("");
  const [lastFailedQuestion, setLastFailedQuestion] = useState("");

  const roleLabel = useMemo(() => {
    if (user?.role === "admin") {
      return "Admin access: internal + external docs";
    }
    if (user?.role === "employee") {
      return "Employee access: internal + external docs";
    }
    return "Customer access: external docs only";
  }, [user?.role]);

  useEffect(() => {
    async function loadConversations() {
      setLoadingConversations(true);
      try {
        const result = await api.getConversations();
        setConversations(result);
        setMessages([]);
        if (result.length > 0) {
          setCurrentConversationId(result[0].id);
        } else {
          setCurrentConversationId(null);
        }
      } catch (error) {
        setChatError(error.message || "Could not load conversations.");
      } finally {
        setLoadingConversations(false);
      }
    }

    loadConversations();
  }, []);

  useEffect(() => {
    async function loadMessages() {
      if (!currentConversationId) {
        return;
      }

      setLoadingMessages(true);
      try {
        const result = await api.getConversationMessages(currentConversationId);
        setMessages(result.map((message) => ({ ...message, sources: message.sources || [] })));
      } catch {
        setMessages([]);
      } finally {
        setLoadingMessages(false);
      }
    }

    loadMessages();
  }, [currentConversationId]);

  async function createConversationRaw() {
    const conversation = await api.createConversation();
    setConversations((prev) => [conversation, ...prev]);
    setCurrentConversationId(conversation.id);
    return conversation.id;
  }

  async function createConversation() {
    setChatError("");
    const conversationId = await createConversationRaw();
    setMessages([]);
    return conversationId;
  }

  function selectConversation(conversationId) {
    setCurrentConversationId(conversationId);
  }

  async function deleteConversation(conversationId) {
    const confirmed = window.confirm("Delete this conversation?");
    if (!confirmed) {
      return;
    }

    try {
      await api.deleteConversation(conversationId);
    } catch {
      setChatError("Could not delete conversation.");
      return;
    }

    const nextConversations = conversations.filter((conversation) => conversation.id !== conversationId);
    setConversations(nextConversations);
    const nextId = nextConversations[0]?.id || null;
    setCurrentConversationId(nextId);
    setMessages([]);
  }

  async function sendQuestion(question) {
    setChatError("");

    const userMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: question,
      sources: [],
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoadingMessages(true);

    try {
      let conversationId = currentConversationId;
      if (!conversationId) {
        conversationId = await createConversationRaw();
      }

      const chatRaw = await api.chat(question);
      const { answer, sources } = extractChatPayload(chatRaw);

      const assistantMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: answer,
        sources,
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Integration contract: persist both user and assistant turns after each /chat response.
      await api.saveMessage(conversationId, { role: "user", content: question });
      await api.saveMessage(conversationId, { role: "assistant", content: answer });

      const refreshedConversations = await api.getConversations();
      setConversations(refreshedConversations);
    } catch (error) {
      setChatError(error.message === "UNAUTHORIZED" ? "Session expired" : "Could not get a response.");
      setLastFailedQuestion(question);
    } finally {
      setLoadingMessages(false);
    }
  }

  return (
    <main className="chat-layout">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={selectConversation}
        onCreateConversation={createConversation}
        onDeleteConversation={deleteConversation}
        loading={loadingConversations}
      />

      <section className="chat-panel">
        <header className="chat-header">
          <div>
            <h1>Datamart Chat</h1>
            <span className={`role-badge ${user?.role || "customer"}`}>{roleLabel}</span>
          </div>
          <div className="header-actions">
            {user?.role === "admin" ? (
              <button type="button" className="button secondary" onClick={() => navigate("/admin")}>
                Admin panel
              </button>
            ) : null}
            <button type="button" className="button secondary" onClick={() => logout()}>
              Logout
            </button>
          </div>
        </header>

        {chatError ? (
          <div className="error-banner">
            <span>{chatError}</span>
            {lastFailedQuestion ? (
              <button type="button" className="button secondary" onClick={() => sendQuestion(lastFailedQuestion)}>
                Retry
              </button>
            ) : null}
          </div>
        ) : null}

        <MessageList messages={messages} loading={loadingMessages} />
        <ChatInput onSend={sendQuestion} disabled={loadingMessages} />
      </section>
    </main>
  );
}