'use client';
import { useState } from 'react';
import { api } from '@/lib/api'; 

export default function AssistantPage() {
    const [message, setMessage] = useState('');
    const [chat, setChat] = useState<{role: string, content: string}[]>([]);
    const [loading, setLoading] = useState(false);

    const sendMessage = async () => {
        if (!message.trim() || loading) return;

        const userMsg = { role: 'user', content: message };
        setChat(prev => [...prev, userMsg]);
        const currentMessage = message;
        setMessage('');
        setLoading(true);

        try {
            // Appel à l'API (reçoit { data: { reply: "..." } } grâce au nouveau api.ts)
            const res = await api.post('/ai/chat', { message: currentMessage });
            
            if (res && res.data && res.data.reply) {
                setChat(prev => [...prev, { role: 'assistant', content: res.data.reply }]);
            }
        } catch (err) {
            console.error("Erreur IA", err);
            setChat(prev => [...prev, { role: 'assistant', content: "Désolé, je rencontre une difficulté technique." }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-6 max-w-4xl mx-auto">
            <h1 className="text-2xl font-bold mb-4 text-slate-800">Assistant Grok IA</h1>
            <div className="bg-white rounded-xl shadow-lg h-[600px] flex flex-col border border-slate-200 overflow-hidden">
                <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
                    {chat.length === 0 && (
                        <div className="text-center text-slate-400 mt-10 italic">
                            Posez-moi une question sur vos factures, clients ou votre TVA...
                        </div>
                    )}
                    {chat.map((m, i) => (
                        <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`p-3 rounded-2xl shadow-sm max-w-[85%] ${
                                m.role === 'user' 
                                ? 'bg-blue-600 text-white rounded-tr-none' 
                                : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none'
                            }`}>
                                <p className="text-sm leading-relaxed">{m.content}</p>
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="flex justify-start">
                            <div className="bg-slate-200 animate-pulse p-3 rounded-lg text-xs text-slate-500">
                                Grok réfléchit...
                            </div>
                        </div>
                    )}
                </div>
                <div className="p-4 border-t bg-white flex gap-2">
                    <input 
                        value={message} 
                        onChange={(e) => setMessage(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                        className="flex-1 border border-slate-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                        placeholder="Ex: Quel est mon CA du mois ?"
                        disabled={loading}
                    />
                    <button 
                        onClick={sendMessage} 
                        disabled={loading || !message.trim()}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-all disabled:bg-slate-300"
                    >
                        {loading ? '...' : 'Envoyer'}
                    </button>
                </div>
            </div>
        </div>
    );
}