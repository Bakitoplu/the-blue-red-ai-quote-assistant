import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { RefreshCw, Send, Database, ScrollText, Package, BookOpen, Save, ChevronDown } from 'lucide-react';
import './styles.css';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const WELCOME_MESSAGE = 'Merhaba, size ürünler, politikalar ve teklifiniz hakkında yardımcı olabilirim.';

function money(value) {
  return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(value || 0);
}

function customerLabel(customer) {
  const backorder = customer.allow_backorder ? 'backorder uygun' : 'backorder yok';
  return `${customer.name} · ${customer.customer_id} · ${customer.city || '-'} · ${customer.price_tier} · ${backorder}`;
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
  const [tab, setTab] = useState('chat');
  const [quoteId, setQuoteId] = useState('Q-1002');
  const [customerId, setCustomerId] = useState('CUST-ANK-002');
  const [quote, setQuote] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [customerQuotes, setCustomerQuotes] = useState([]);
  const [products, setProducts] = useState([]);
  const [knowledge, setKnowledge] = useState([]);
  const [logs, setLogs] = useState([]);
  const [productForm, setProductForm] = useState(null);
  const [knowledgeForm, setKnowledgeForm] = useState(null);
  const [message, setMessage] = useState('');
  const [events, setEvents] = useState([]);
  const [messages, setMessages] = useState([{ id: 'welcome', role: 'assistant', text: WELCOME_MESSAGE, sources: [] }]);
  const [streamSources, setStreamSources] = useState([]);
  const [busy, setBusy] = useState(false);
  const [newCustomer, setNewCustomer] = useState({ name: '', city: '', price_tier: 'standard', allow_backorder: false });

  async function loadQuote() {
    if (!quoteId) {
      setQuote(null);
      return;
    }
    const res = await fetch(`${API}/quotes/${quoteId}`);
    setQuote(await res.json());
  }

  async function loadCustomers() {
    const res = await fetch(`${API}/customers`);
    setCustomers(await res.json());
  }

  async function loadCustomerQuotes(nextCustomerId = customerId) {
    if (!nextCustomerId) {
      setCustomerQuotes([]);
      return [];
    }
    const res = await fetch(`${API}/customers/${nextCustomerId}/quotes`);
    const data = await res.json();
    setCustomerQuotes(data);
    return data;
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
    loadCustomers();
    loadProducts();
    loadKnowledge();
    loadLogs();
  }, []);

  useEffect(() => {
    loadCustomerQuotes(customerId).then((quotes) => {
      if (quoteId && !quotes.some((item) => item.quote_id === quoteId)) {
        setQuoteId('');
        setQuote(null);
      }
    });
  }, [customerId]);

  useEffect(() => {
    loadQuote();
  }, [quoteId]);

  async function sendMessage() {
    const trimmed = message.trim();
    if (!trimmed || busy) return;
    if (!customerId || !quoteId) {
      setMessages((prev) => [...prev, { id: `warn-${Date.now()}`, role: 'assistant', text: 'Lütfen önce müşteri ve teklif seçin.', sources: [] }]);
      return;
    }
    setBusy(true);
    setEvents([]);
    setStreamSources([]);
    const userMessage = { role: 'user', text: trimmed, sources: [] };
    const assistantId = `assistant-${Date.now()}`;
    setMessages((prev) => [...prev, userMessage, { id: assistantId, role: 'assistant', text: '', sources: [] }]);
    setMessage('');
    const res = await fetch(`${API}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        quote_id: quoteId,
        customer_id: customerId,
        channel: 'web',
        session_id: `WEB-${quoteId}`,
        message_id: `WEB-${Date.now()}`,
        message: trimmed,
        require_confirmation: true,
      }),
    });
    await readSse(res, (event, data) => {
      setEvents((prev) => [{ event, data }, ...prev].slice(0, 40));
      if (event === 'text_delta') {
        setMessages((prev) => prev.map((item) => item.id === assistantId ? { ...item, text: item.text + data.text } : item));
      }
      if (event === 'source') {
        const source = { id: data.source_id, label: data.label || data.source_id };
        setStreamSources((prev) => prev.some((item) => item.id === source.id) ? prev : [...prev, source]);
        setMessages((prev) => prev.map((item) => item.id === assistantId && !item.sources?.some((s) => s.id === source.id) ? { ...item, sources: [...(item.sources || []), source] } : item));
      }
    });
    await loadQuote();
    await loadLogs();
    setBusy(false);
  }

  async function setQuantity(item, quantity) {
    await fetch(`${API}/quotes/${quoteId}/items/${item.product_id}/quantity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quantity: Math.max(quantity, 0), reason: 'web quantity control' }),
    });
    await loadQuote();
  }

  async function createCustomer() {
    if (!newCustomer.name.trim()) return;
    const res = await fetch(`${API}/customers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newCustomer),
    });
    const created = await res.json();
    await loadCustomers();
    setCustomerId(created.customer_id);
    setQuoteId('');
    setQuote(null);
    setNewCustomer({ name: '', city: '', price_tier: 'standard', allow_backorder: false });
  }

  async function createQuote() {
    if (!customerId) return;
    const res = await fetch(`${API}/quotes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_id: customerId, created_by_channel: 'web' }),
    });
    const created = await res.json();
    await loadCustomerQuotes(customerId);
    setQuoteId(created.quote_id);
    setQuote(created);
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
          Müşteri
          <select value={customerId} onChange={(e) => {
            setCustomerId(e.target.value);
            setQuoteId('');
            setQuote(null);
          }}>
            {customers.map((customer) => (
              <option key={customer.customer_id} value={customer.customer_id}>{customerLabel(customer)}</option>
            ))}
          </select>
        </label>
        <label>
          Teklif
          <select value={quoteId} onChange={(e) => setQuoteId(e.target.value)} disabled={!customerId}>
            <option value="">{customerId ? 'Teklif seçin' : 'Önce müşteri seçin'}</option>
            {customerQuotes.map((item) => (
              <option key={item.quote_id} value={item.quote_id}>{item.quote_id} · {item.status}</option>
            ))}
          </select>
        </label>
        <button className="iconButton" onClick={createQuote} disabled={!customerId} title="Yeni teklif oluştur">
          <Database size={18} />
          Yeni Teklif
        </button>
        <button className="iconButton" onClick={loadQuote} title="Teklifi yenile">
          <RefreshCw size={18} />
          Yenile
        </button>
        <div className="sidebarForm">
          <strong>Yeni müşteri</strong>
          <input placeholder="Müşteri adı" value={newCustomer.name} onChange={(e) => setNewCustomer({ ...newCustomer, name: e.target.value })} />
          <input placeholder="Şehir" value={newCustomer.city} onChange={(e) => setNewCustomer({ ...newCustomer, city: e.target.value })} />
          <select value={newCustomer.price_tier} onChange={(e) => setNewCustomer({ ...newCustomer, price_tier: e.target.value })}>
            <option value="standard">standard</option>
            <option value="partner">partner</option>
          </select>
          <label className="checkboxLabel">
            <input type="checkbox" checked={newCustomer.allow_backorder} onChange={(e) => setNewCustomer({ ...newCustomer, allow_backorder: e.target.checked })} />
            Backorder uygun
          </label>
          <button className="smallAction" onClick={createCustomer} disabled={!newCustomer.name.trim()}>Ekle</button>
        </div>
        <nav className="tabs">
          {[
            ['chat', Send, 'Sohbet'],
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
            <h2>{quote?.quote_id || quoteId || 'Teklif seçilmedi'}</h2>
            <p>{quote?.customer_name || customers.find((customer) => customer.customer_id === customerId)?.name || 'Müşteri seçilmedi'}</p>
          </div>
          <div className="totals">
            <span>Ara toplam {money(quote?.subtotal_try)}</span>
            <strong>{money(quote?.grand_total_try)}</strong>
          </div>
        </header>

        {tab === 'quote' && <section className="adminGrid single">
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
                    <td>
                      <div className="qtyControl">
                        <button onClick={() => setQuantity(item, item.quantity - 1)}>-</button>
                        <span>{item.quantity}</span>
                        <button onClick={() => setQuantity(item, item.quantity + 1)} disabled={item.status !== 'active'}>+</button>
                      </div>
                    </td>
                    <td>{money(item.unit_price_try)}</td>
                    <td>{item.discount_rule_id || '-'}</td>
                    <td>{money(item.line_total_try)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>}

        {tab === 'chat' && <section className="chatLayout">
          <div className="panel chatPanel">
            <div className="panelTitle">
              <Send size={18} />
              Sohbet
            </div>
            <div className="messages">
              {messages.length === 0 && <div className="empty">Ürün, stok, garanti, teslimat veya teklifiniz hakkında yazabilirsiniz.</div>}
              {messages.map((item, idx) => (
                <div className={`bubble ${item.role}`} key={item.id || idx}>
                  <p>{item.text || '...'}</p>
                  {item.sources?.length > 0 && <SourceDisclosure sources={item.sources} />}
                </div>
              ))}
            </div>
            <div className="composer">
              <textarea
                value={message}
                rows={1}
                placeholder="Ürün, politika veya teklif hakkında yazın…"
                onChange={(e) => setMessage(e.target.value)}
                onInput={(e) => {
                  e.currentTarget.style.height = 'auto';
                  e.currentTarget.style.height = `${Math.min(e.currentTarget.scrollHeight, 132)}px`;
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
              />
              <button className="sendButton" onClick={sendMessage} disabled={busy || !message.trim()} title="Gönder">
                <Send size={18} />
              </button>
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

function SourceDisclosure({ sources }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`sourceList ${open ? 'open' : ''}`}>
      <button type="button" className="sourceToggle" onClick={() => setOpen((value) => !value)}>
        <ChevronDown size={14} />
        Kaynaklar
      </button>
      {open && (
        <div className="sourceItems">
          {sources.map((source) => <span key={source.id}>{source.id} · {source.label}</span>)}
        </div>
      )}
    </div>
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
