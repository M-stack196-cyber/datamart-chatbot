export function formatDateTime(value) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString();
}

export function extractChatPayload(data) {
  const answer =
    data.answer ||
    data.response ||
    data.message ||
    data.output?.answer ||
    data.data?.answer ||
    "I could not generate a response.";

  const rawSources = data.sources || data.output?.sources || data.data?.sources || [];
  const sources = Array.isArray(rawSources)
    ? rawSources.map((item) => {
        if (typeof item === "string") {
          return item;
        }
        return item.title || item.name || item.filename || "Source";
      })
    : [];

  return { answer, sources };
}
