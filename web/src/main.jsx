import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { RefreshCw, Send, Database, ScrollText } from 'lucide-react';
import './styles.css';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

function money(value) {
  return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(value || 0);
}

async function readSse(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split('\n\n');
    buffer = chunks.pop() || '';
    for (const chunk of chunks) {
      const event = chunk.match(/^event: (.+)$/m)?.[1];
      const data = chunk.match(/^data: (.+)$/m)?.[1];
      if (event && data) onEvent(event, JSON.parse(data));
    }
  }
}

function App() {
  const [quoteId, setQuoteId] = useState('Q-1002');
  const [customerId, setCustomerId] = useState('CUST-ANK-002');
  const [quote, setQuote] = useState(null);
  const [message, setMessage] = useState('9.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?');
  const [events, setEvents] = useState([]);
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(false);

  const activeItems = useMemo(() => quote?.items?.filter((item) => item.status === 'active') || [], [quote]);

  async function loadQuote() {
    const res = await fetch(`${API}/quotes/${quoteId}`);
    setQuote(await res.json());
  }

  useEffect(() => {
    loadQuote();
  }, [quoteId]);

  async function sendMessage() {
    setBusy(true);
    setEvents([]);
    setAnswer('');
    const res = await fetch(`${API}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        quote_id: quoteId,
        customer_id: customerId,
        channel: 'web',
        session_id: `WEB-${quoteId}`,
        message_id: `WEB-${Date.now()}`,
        message,
      }),
    });
    await readSse(res, (event, data) => {
      setEvents((prev) => [{ event, data }, ...prev].slice(0, 40));
      if (event === 'text_delta') setAnswer((prev) => prev + data.text);
    });
    await loadQuote();
    setBusy(false);
  }

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="mark">TBR</div>
          <div>
            <h1>The Blue Red</h1>
            <p>Teklif Asistanı</p>
          </div>
        </div>
        <label>
          Quote ID
          <select value={quoteId} onChange={(e) => setQuoteId(e.target.value)}>
            {['Q-1001', 'Q-1002', 'Q-1003', 'Q-1004', 'Q-1005', 'Q-2001', 'Q-2002', 'Q-2003', 'Q-2004', 'Q-2005'].map((id) => (
              <option key={id}>{id}</option>
            ))}
          </select>
        </label>
        <label>
          Customer ID
          <input value={customerId} onChange={(e) => setCustomerId(e.target.value)} />
        </label>
        <button className="iconButton" onClick={loadQuote} title="Teklifi yenile">
          <RefreshCw size={18} />
          Yenile
        </button>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <h2>{quote?.quote_id || quoteId}</h2>
            <p>{quote?.customer_name || 'Yükleniyor'}</p>
          </div>
          <div className="totals">
            <span>Ara toplam {money(quote?.subtotal_try)}</span>
            <strong>{money(quote?.grand_total_try)}</strong>
          </div>
        </header>

        <section className="grid">
          <div className="panel quotePanel">
            <div className="panelTitle">
              <Database size={18} />
              Kalıcı Teklif Durumu
            </div>
            <table>
              <thead>
                <tr>
                  <th>Ürün</th>
                  <th>Durum</th>
                  <th>Adet</th>
                  <th>Birim</th>
                  <th>İndirim</th>
                  <th>Toplam</th>
                </tr>
              </thead>
              <tbody>
                {(quote?.items || []).map((item) => (
                  <tr key={item.quote_item_id} className={item.status !== 'active' ? 'muted' : ''}>
                    <td>
                      <strong>{item.name_tr}</strong>
                      <span>{item.product_id}</span>
                    </td>
                    <td>{item.status}</td>
                    <td>{item.quantity}</td>
                    <td>{money(item.unit_price_try)}</td>
                    <td>{item.discount_rule_id || '-'}</td>
                    <td>{money(item.line_total_try)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="panel chatPanel">
            <div className="panelTitle">
              <Send size={18} />
              Chat
            </div>
            <textarea value={message} onChange={(e) => setMessage(e.target.value)} />
            <button className="primary" onClick={sendMessage} disabled={busy}>
              <Send size={18} />
              Gönder
            </button>
            <div className="answer">{answer || 'Yanıt burada akar.'}</div>
          </div>

          <div className="panel eventPanel">
            <div className="panelTitle">
              <ScrollText size={18} />
              Tool Stream
            </div>
            <div className="eventList">
              {events.map((entry, idx) => (
                <div className="event" key={idx}>
                  <strong>{entry.event}</strong>
                  <code>{JSON.stringify(entry.data)}</code>
                </div>
              ))}
            </div>
          </div>
        </section>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')).render(<App />);

