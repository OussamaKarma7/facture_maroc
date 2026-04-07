'use client';
import { useState } from 'react';
import { api } from '@/lib/api'; // Assure-toi que ton instance api gère les tokens

export default function AssistantPage() {
    const [message, setMessage] = useState('');
    const [chat, setChat] = useState<{role: string, content: string}[]>([]);

    const sendMessage = async () => {
        const userMsg = { role: 'user', content: message };
        setChat([...chat, userMsg]);
        setMessage('');

        try {
            const res = await api.post('/ai/chat', null, { params: { message } });
            setChat(prev => [...prev, { role: 'assistant', content: res.data.reply }]);
        } catch (err) {
            console.error("Erreur IA", err);
        }
    };

    return (
        <div className="p-6 max-w-4xl mx-auto">
            <h1 className="text-2xl font-bold mb-4">Assistant Grok IA</h1>
            <div className="bg-white rounded-lg shadow-md h-[500px] flex flex-col">
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {chat.map((m, i) => (
                        <div key={i} className={`p-3 rounded-lg ${m.role === 'user' ? 'bg-blue-100 ml-auto' : 'bg-gray-100'} max-w-[80%]`}>
                            {m.content}
                        </div>
                    ))}
                </div>
                <div className="p-4 border-t flex gap-2">
                    <input 
                        value={message} 
                        onChange={(e) => setMessage(e.target.value)}
                        className="flex-1 border rounded p-2"
                        placeholder="Posez une question sur vos factures ou clients..."
                    />
                    <button onClick={sendMessage} className="bg-blue-600 text-white px-4 py-2 rounded">Envoyer</button>
                </div>
            </div>
        </div>
    );
}