import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { RefreshCw, Send, Database, ScrollText, Package, BookOpen, Save } from 'lucide-react';
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
  const [tab, setTab] = useState('quote');
  const [quoteId, setQuoteId] = useState('Q-1002');
  const [customerId, setCustomerId] = useState('CUST-ANK-002');
  const [quote, setQuote] = useState(null);
  const [products, setProducts] = useState([]);
  const [knowledge, setKnowledge] = useState([]);
  const [logs, setLogs] = useState([]);
  const [productForm, setProductForm] = useState(null);
  const [knowledgeForm, setKnowledgeForm] = useState(null);
  const [message, setMessage] = useState('9.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?');
  const [events, setEvents] = useState([]);
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(false);

  async function loadQuote() {
    const res = await fetch(`${API}/quotes/${quoteId}`);
    setQuote(await res.json());
  }

  async function loadProducts() {
    const res = await fetch(`${API}/products`);
    setProducts(await res.json());
  }

  async function loadKnowledge() {
    const res = await fetch(`${API}/knowledge`);
    setKnowledge(await res.json());
  }

  async function loadLogs() {
    const res = await fetch(`${API}/tool-call-logs`);
    setLogs(await res.json());
  }

  useEffect(() => {
    loadQuote();
    loadProducts();
    loadKnowledge();
    loadLogs();
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
    await loadLogs();
    setBusy(false);
  }

  function newProduct() {
    setProductForm({
      product_id: `PRD-NEW-${Date.now()}`,
      sku: 'TBR-NEW',
      name_tr: 'Yeni Ürün',
      category: 'accessory',
      brand: 'The Blue Red',
      price_try: 1000,
      stock_qty: 1,
      active: true,
      min_order_qty: 1,
      delivery_days: 1,
      warranty_months: 12,
      tags: ['aksesuar'],
      aliases: { tr: ['yeni ürün'] },
      substitute_product_ids: [],
      notes: '',
    });
  }

  async function saveProduct() {
    const exists = products.some((product) => product.product_id === productForm.product_id);
    await fetch(`${API}/products${exists ? `/${productForm.product_id}` : ''}`, {
      method: exists ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(productForm),
    });
    setProductForm(null);
    await loadProducts();
  }

  function newKnowledge() {
    setKnowledgeForm({
      knowledge_id: `KNE-NEW-${Date.now()}`,
      topic: 'service_policy',
      locale: 'tr',
      title: 'Yeni Bilgi Kaydı',
      body: 'Kaynaklı cevaplarda kullanılacak bilgi metni.',
      source: 'internal/demo',
      applies_to: ['service'],
      effective_from: '2026-06-03',
    });
  }

  async function saveKnowledge() {
    const exists = knowledge.some((entry) => entry.knowledge_id === knowledgeForm.knowledge_id);
    await fetch(`${API}/knowledge${exists ? `/${knowledgeForm.knowledge_id}` : ''}`, {
      method: exists ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(knowledgeForm),
    });
    setKnowledgeForm(null);
    await loadKnowledge();
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
        <nav className="tabs">
          {[
            ['quote', Database, 'Teklif'],
            ['products', Package, 'Ürünler'],
            ['knowledge', BookOpen, 'Bilgi'],
            ['logs', ScrollText, 'Loglar'],
          ].map(([key, Icon, label]) => (
            <button key={key} className={tab === key ? 'activeTab' : ''} onClick={() => setTab(key)}>
              <Icon size={17} />
              {label}
            </button>
          ))}
        </nav>
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

        {tab === 'quote' && <section className="grid">
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
        </section>}

        {tab === 'products' && <section className="adminGrid">
          <div className="panel">
            <div className="panelTitle">
              <Package size={18} />
              Ürünler
              <button className="smallAction" onClick={newProduct}>Yeni</button>
            </div>
            <div className="list">
              {products.map((product) => (
                <button className="rowButton" key={product.product_id} onClick={() => setProductForm({ ...product })}>
                  <span>
                    <strong>{product.name_tr}</strong>
                    <em>{product.product_id} · {product.category} · stok {product.stock_qty}</em>
                  </span>
                  <b>{money(product.price_try)}</b>
                </button>
              ))}
            </div>
          </div>
          <div className="panel editor">
            <div className="panelTitle">
              <Save size={18} />
              Ürün Düzenle
            </div>
            {productForm ? (
              <FormFields
                value={productForm}
                onChange={setProductForm}
                fields={['product_id', 'sku', 'name_tr', 'category', 'brand', 'price_try', 'stock_qty', 'delivery_days', 'warranty_months', 'notes']}
              />
            ) : <p className="empty">Bir ürün seçin veya yeni ürün ekleyin.</p>}
            {productForm && <button className="primary editorButton" onClick={saveProduct}><Save size={18} />Kaydet</button>}
          </div>
        </section>}

        {tab === 'knowledge' && <section className="adminGrid">
          <div className="panel">
            <div className="panelTitle">
              <BookOpen size={18} />
              Bilgi Kayıtları
              <button className="smallAction" onClick={newKnowledge}>Yeni</button>
            </div>
            <div className="list">
              {knowledge.map((entry) => (
                <button className="rowButton" key={entry.knowledge_id} onClick={() => setKnowledgeForm({ ...entry })}>
                  <span>
                    <strong>{entry.title}</strong>
                    <em>{entry.knowledge_id} · {entry.topic}</em>
                  </span>
                  <b>{entry.locale}</b>
                </button>
              ))}
            </div>
          </div>
          <div className="panel editor">
            <div className="panelTitle">
              <Save size={18} />
              Bilgi Düzenle
            </div>
            {knowledgeForm ? (
              <FormFields
                value={knowledgeForm}
                onChange={setKnowledgeForm}
                fields={['knowledge_id', 'topic', 'locale', 'title', 'body', 'source', 'effective_from']}
                multiline={['body']}
              />
            ) : <p className="empty">Bir bilgi kaydı seçin veya yeni kayıt ekleyin.</p>}
            {knowledgeForm && <button className="primary editorButton" onClick={saveKnowledge}><Save size={18} />Kaydet</button>}
          </div>
        </section>}

        {tab === 'logs' && <section className="adminGrid single">
          <div className="panel">
            <div className="panelTitle">
              <ScrollText size={18} />
              Kalıcı Tool Call Logları
              <button className="smallAction" onClick={loadLogs}>Yenile</button>
            </div>
            <div className="eventList tall">
              {logs.map((log) => (
                <div className="event" key={log.id}>
                  <strong>#{log.sequence_no} {log.tool_name} · {log.success ? 'success' : 'error'}</strong>
                  <span>{log.session_id} · {log.message_id} · {log.quote_id || '-'}</span>
                  <code>{JSON.stringify({ input: log.input_json, sources: log.source_ids, delta: log.quote_delta, error: log.error })}</code>
                </div>
              ))}
            </div>
          </div>
        </section>}
      </section>
    </main>
  );
}

function FormFields({ value, onChange, fields, multiline = [] }) {
  return (
    <div className="formGrid">
      {fields.map((field) => {
        const raw = value[field];
        const set = (next) => {
          const numeric = ['price_try', 'stock_qty', 'delivery_days', 'warranty_months'].includes(field);
          onChange({ ...value, [field]: numeric ? Number(next) : next });
        };
        return (
          <label key={field}>
            {field}
            {multiline.includes(field) ? (
              <textarea value={raw ?? ''} onChange={(e) => set(e.target.value)} />
            ) : (
              <input value={raw ?? ''} onChange={(e) => set(e.target.value)} />
            )}
          </label>
        );
      })}
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
