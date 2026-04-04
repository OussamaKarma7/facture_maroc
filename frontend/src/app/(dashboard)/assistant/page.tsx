"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2 } from "lucide-react";
import { apiFetch } from "../../../lib/api";

type Message = {
  role: "user" | "assistant";
  content: string;
};

const suggestions = [
  "Quel est mon chiffre d'affaires ce mois ?",
  "Combien de factures sont impayées ?",
  "Quels sont mes clients actifs ?",
  "Quel est le montant de TVA à payer ?",
];

export default function AssistantPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Bonjour ! Je suis votre assistant comptable. Je peux vous aider a analyser vos factures, suivre vos paiements et repondre a vos questions financieres. Comment puis-je vous aider ?"
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (content: string) => {
    if (!content.trim() || isLoading) return;
    const userMessage: Message = { role: "user", content };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);
    try {
      const data = await apiFetch("/assistant/chat", {
        method: "POST",
        body: { messages: newMessages }
      });
      setMessages([...newMessages, { role: "assistant", content: data.reply }]);
    } catch (err: any) {
      setMessages([...newMessages, { role: "assistant", content: "Desole, une erreur s'est produite. Veuillez reessayer." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-slate-800 flex items-center">
          <Bot className="w-6 h-6 mr-2 text-blue-600" />
          Assistant Comptable IA
        </h1>
        <p className="text-sm text-slate-500 mt-1">Posez vos questions sur vos finances, factures et clients.</p>
      </div>

      <div className="flex-1 overflow-y-auto bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-4 mb-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex items-start space-x-3 ${msg.role === "user" ? "flex-row-reverse space-x-reverse" : ""}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === "assistant" ? "bg-blue-100 text-blue-600" : "bg-slate-200 text-slate-600"}`}>
              {msg.role === "assistant" ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
            </div>
            <div className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${msg.role === "assistant" ? "bg-slate-50 border border-slate-200 text-slate-700" : "bg-blue-600 text-white"}`}>
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex items-start space-x-3">
            <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div className="bg-slate-50 border border-slate-200 px-4 py-3 rounded-2xl">
              <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {messages.length === 1 && (
        <div className="grid grid-cols-2 gap-2 mb-4">
          {suggestions.map((s, i) => (
            <button key={i} onClick={() => sendMessage(s)}
              className="text-left px-3 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-blue-50 hover:border-blue-300 transition-colors">
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="flex space-x-3">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && sendMessage(input)}
          placeholder="Posez votre question..."
          className="flex-1 px-4 py-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm text-slate-700"
          disabled={isLoading}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={isLoading || !input.trim()}
          className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-xl transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
