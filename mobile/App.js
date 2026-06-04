import React, { useEffect, useState } from 'react';
import { Modal, Platform, SafeAreaView, ScrollView, StatusBar as NativeStatusBar, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

const API = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.0.14:8000';
const WELCOME_MESSAGE = 'Merhaba, size ürünler, politikalar ve teklifiniz hakkında yardımcı olabilirim.';

function money(value) {
  return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(value || 0);
}

function customerLabel(customer) {
  const backorder = customer.allow_backorder ? 'backorder uygun' : 'backorder yok';
  return `${customer.customer_id} · ${customer.city || '-'} · ${customer.price_tier} · ${backorder}`;
}

async function readSse(response, onEvent) {
  const text = await response.text();
  text.split('\n\n').forEach((chunk) => {
    const event = chunk.match(/^event: (.+)$/m)?.[1];
    const data = chunk.match(/^data: (.+)$/m)?.[1];
    if (event && data) onEvent(event, JSON.parse(data));
  });
}

export default function App() {
  const [loggedCustomer, setLoggedCustomer] = useState(null);
  const [loginCustomerId, setLoginCustomerId] = useState('CUST-ANK-002');
  const [loginError, setLoginError] = useState('');
  const [quoteId, setQuoteId] = useState('');
  const [customerId, setCustomerId] = useState('');
  const [quote, setQuote] = useState(null);
  const [customerQuotes, setCustomerQuotes] = useState([]);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([{ id: 'welcome', role: 'assistant', text: WELCOME_MESSAGE, sources: [] }]);
  const [busy, setBusy] = useState(false);
  const [quotePickerOpen, setQuotePickerOpen] = useState(false);
  const [customerFormOpen, setCustomerFormOpen] = useState(false);
  const [newCustomer, setNewCustomer] = useState({ name: '', city: '', price_tier: 'standard', allow_backorder: false });
  const [viewMode, setViewMode] = useState('chat');

  async function loadQuote() {
    if (!quoteId) {
      setQuote(null);
      return;
    }
    const res = await fetch(`${API}/quotes/${quoteId}`);
    setQuote(await res.json());
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

  useEffect(() => {
    if (!loggedCustomer) return;
    loadCustomerQuotes(customerId).then((quotes) => {
      if (quoteId && !quotes.some((item) => item.quote_id === quoteId)) {
        setQuoteId('');
        setQuote(null);
      }
    });
  }, [customerId, loggedCustomer]);

  useEffect(() => {
    loadQuote();
  }, [quoteId]);

  async function send() {
    const trimmed = message.trim();
    if (!trimmed || busy) return;
    if (!customerId || !quoteId) {
      setMessages((prev) => [...prev, { id: `warn-${Date.now()}`, role: 'assistant', text: 'Lütfen teklif seçin veya yeni teklif oluşturun.', sources: [] }]);
      return;
    }
    setBusy(true);
    const assistantId = `assistant-${Date.now()}`;
    setMessages((prev) => [...prev, { role: 'user', text: trimmed, sources: [] }, { id: assistantId, role: 'assistant', text: '', sources: [] }]);
    setMessage('');
    const res = await fetch(`${API}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        quote_id: quoteId,
        customer_id: customerId,
        channel: 'mobile',
        session_id: `MOB-${quoteId}`,
        message_id: `MOB-${Date.now()}`,
        message: trimmed,
        require_confirmation: true,
      }),
    });
    await readSse(res, (event, data) => {
      if (event === 'text_delta') {
        setMessages((prev) => prev.map((item) => item.id === assistantId ? { ...item, text: item.text + data.text } : item));
      }
      if (event === 'source') {
        const source = { id: data.source_id, label: data.label || data.source_id };
        setMessages((prev) => prev.map((item) => item.id === assistantId && !item.sources?.some((s) => s.id === source.id) ? { ...item, sources: [...(item.sources || []), source] } : item));
      }
    });
    await loadQuote();
    setBusy(false);
  }

  async function setQuantity(item, quantity) {
    await fetch(`${API}/quotes/${quoteId}/items/${item.product_id}/quantity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quantity: Math.max(quantity, 0), reason: 'mobile quantity control', customer_id: customerId }),
    });
    await loadQuote();
  }

  function selectQuote(nextQuoteId) {
    setQuoteId(nextQuoteId);
    setQuotePickerOpen(false);
  }

  async function loginCustomer(nextCustomerId = loginCustomerId) {
    const trimmed = nextCustomerId.trim();
    if (!trimmed) return;
    setLoginError('');
    const res = await fetch(`${API}/customers/${trimmed}`);
    if (!res.ok) {
      setLoginError('Müşteri bulunamadı.');
      return;
    }
    const customer = await res.json();
    setLoggedCustomer(customer);
    setCustomerId(customer.customer_id);
    setQuoteId('');
    setQuote(null);
    setViewMode('chat');
    const quotes = await loadCustomerQuotes(customer.customer_id);
    if (quotes.length === 1) setQuoteId(quotes[0].quote_id);
  }

  async function createCustomer() {
    if (!newCustomer.name.trim()) return;
    const res = await fetch(`${API}/customers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newCustomer),
    });
    const created = await res.json();
    setLoggedCustomer(created);
    setCustomerId(created.customer_id);
    setQuoteId('');
    setQuote(null);
    setCustomerQuotes([]);
    setNewCustomer({ name: '', city: '', price_tier: 'standard', allow_backorder: false });
    setCustomerFormOpen(false);
    setViewMode('chat');
  }

  async function createQuote() {
    if (!customerId) return;
    const res = await fetch(`${API}/quotes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_id: customerId, created_by_channel: 'mobile' }),
    });
    const created = await res.json();
    await loadCustomerQuotes(customerId);
    setQuoteId(created.quote_id);
    setQuote(created);
    setViewMode('quotes');
  }

  if (!loggedCustomer) {
    return (
      <SafeAreaView style={styles.safe}>
        <StatusBar style="dark" />
        <ScrollView contentContainerStyle={styles.container}>
          <View style={styles.header}>
            <View style={styles.logo}>
              <Text style={styles.logoText}>TBR</Text>
            </View>
            <View>
              <Text style={styles.title}>The Blue Red</Text>
              <Text style={styles.subtitle}>Mobil teklif asistanı</Text>
            </View>
          </View>
          <View style={styles.panel}>
            <Text style={styles.panelTitle}>Müşteri Girişi</Text>
            <TextInput style={styles.formInput} placeholder="CUST-ANK-002" value={loginCustomerId} onChangeText={setLoginCustomerId} autoCapitalize="characters" />
            {loginError ? <Text style={styles.errorText}>{loginError}</Text> : null}
            <TouchableOpacity style={styles.primaryAction} onPress={() => loginCustomer()}>
              <Text style={styles.primaryActionText}>Giriş yap</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.secondaryAction} onPress={() => setCustomerFormOpen(true)}>
              <Text style={styles.secondaryActionText}>Yeni müşteri ekle</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
        <CustomerFormModal
          visible={customerFormOpen}
          newCustomer={newCustomer}
          setNewCustomer={setNewCustomer}
          onClose={() => setCustomerFormOpen(false)}
          onCreate={createCustomer}
        />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="dark" />
      <ScrollView contentContainerStyle={styles.container}>
        <View style={styles.header}>
          <View style={styles.logo}>
            <Text style={styles.logoText}>TBR</Text>
          </View>
          <View>
            <Text style={styles.title}>The Blue Red</Text>
            <Text style={styles.subtitle}>{loggedCustomer.customer_id} · {loggedCustomer.price_tier} · {loggedCustomer.allow_backorder ? 'backorder uygun' : 'backorder yok'}</Text>
          </View>
          <TouchableOpacity style={styles.headerAction} onPress={() => setViewMode(viewMode === 'chat' ? 'quotes' : 'chat')}>
            <Text style={styles.headerActionText}>{viewMode === 'chat' ? 'Teklifler' : 'Sohbet'}</Text>
          </TouchableOpacity>
        </View>

        {viewMode === 'quotes' && <View style={styles.selectorRow}>
          <TouchableOpacity style={[styles.selectBox, !customerId && styles.disabled]} onPress={() => customerId && setQuotePickerOpen(true)} disabled={!customerId}>
            <Text style={styles.selectLabel}>Teklif</Text>
            <View style={styles.selectValueRow}>
              <Text style={styles.selectValue}>{quoteId || 'Teklif seçin'}</Text>
              <Ionicons name="chevron-down" size={18} color="#455a64" />
            </View>
            <Text style={styles.selectMeta}>{customerId ? 'Sadece seçili müşterinin teklifleri' : 'Önce müşteri seçin'}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.iconButton, !customerId && styles.disabled]} onPress={createQuote} disabled={!customerId}>
            <Ionicons name="add" size={22} color="#fff" />
          </TouchableOpacity>
        </View>}

        {viewMode === 'quotes' && <View style={styles.panel}>
          <Text style={styles.panelTitle}>Teklif</Text>
          <Text style={styles.total}>{money(quote?.grand_total_try)}</Text>
          {(quote?.items || []).map((item) => (
            <View key={item.quote_item_id} style={[styles.line, item.status !== 'active' && styles.inactive]}>
              <View style={{ flex: 1 }}>
                <Text style={styles.product}>{item.name_tr}</Text>
                <Text style={styles.meta}>{item.product_id} · {item.status}</Text>
              </View>
              <View style={styles.qtyControl}>
                <TouchableOpacity style={styles.qtyButton} onPress={() => setQuantity(item, item.quantity - 1)}>
                  <Text>-</Text>
                </TouchableOpacity>
                <Text style={styles.qty}>{item.quantity}</Text>
                <TouchableOpacity style={styles.qtyButton} onPress={() => setQuantity(item, item.quantity + 1)} disabled={item.status !== 'active'}>
                  <Text>+</Text>
                </TouchableOpacity>
              </View>
              <Text style={styles.amount}>{money(item.line_total_try)}</Text>
            </View>
          ))}
        </View>}

        {viewMode === 'chat' && <View style={styles.panel}>
          <Text style={styles.panelTitle}>Sohbet</Text>
          <View style={styles.messages}>
            {messages.length === 0 && <Text style={styles.empty}>Ürün, stok, garanti, teslimat veya teklifiniz hakkında yazabilirsiniz.</Text>}
            {messages.map((item, idx) => (
              <View key={item.id || idx} style={[styles.bubble, item.role === 'user' ? styles.userBubble : styles.assistantBubble]}>
                <Text style={item.role === 'user' ? styles.userText : styles.assistantText}>{item.text || '...'}</Text>
                {item.sources?.length > 0 && <SourceList sources={item.sources} />}
              </View>
            ))}
          </View>
          <View style={styles.composer}>
            <TextInput
              style={styles.message}
              value={message}
              onChangeText={setMessage}
              placeholder="Ürün, politika veya teklif hakkında yazın…"
              multiline
              scrollEnabled
            />
            <TouchableOpacity style={[styles.sendButton, (busy || !message.trim()) && styles.disabled]} onPress={send} disabled={busy || !message.trim()}>
              <Ionicons name="send" size={18} color="#fff" />
            </TouchableOpacity>
          </View>
        </View>}
      </ScrollView>

      <Modal visible={quotePickerOpen} transparent animationType="fade" onRequestClose={() => setQuotePickerOpen(false)}>
        <View style={styles.modalBackdrop}>
          <TouchableOpacity style={styles.modalDismiss} activeOpacity={1} onPress={() => setQuotePickerOpen(false)} />
          <View style={styles.modalSheet}>
            <Text style={styles.modalTitle}>Teklif Seç</Text>
            {customerQuotes.length === 0 && <Text style={styles.empty}>Bu müşterinin teklifi yok. Yeni teklif oluşturabilirsiniz.</Text>}
            {customerQuotes.map((item) => (
              <TouchableOpacity key={item.quote_id} style={[styles.quoteOption, item.quote_id === quoteId && styles.quoteOptionActive]} onPress={() => selectQuote(item.quote_id)}>
                <Text style={styles.quoteOptionId}>{item.quote_id}</Text>
                <Text style={styles.quoteOptionCustomer}>{item.status}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </Modal>

      <CustomerFormModal
        visible={customerFormOpen}
        newCustomer={newCustomer}
        setNewCustomer={setNewCustomer}
        onClose={() => setCustomerFormOpen(false)}
        onCreate={createCustomer}
      />
    </SafeAreaView>
  );
}

function SourceList({ sources }) {
  const [open, setOpen] = useState(false);
  return (
    <View style={styles.sourceBox}>
      <TouchableOpacity style={styles.sourceToggle} onPress={() => setOpen((value) => !value)}>
        <Ionicons name={open ? 'chevron-up' : 'chevron-down'} size={14} color="#455a64" />
        <Text style={styles.sourceTitle}>Kaynaklar</Text>
      </TouchableOpacity>
      {open && sources.map((source) => <Text key={source.id} style={styles.sourceLine}>{source.id} · {source.label}</Text>)}
    </View>
  );
}

function CustomerFormModal({ visible, newCustomer, setNewCustomer, onClose, onCreate }) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.modalBackdrop}>
        <TouchableOpacity style={styles.modalDismiss} activeOpacity={1} onPress={onClose} />
        <View style={styles.modalSheet}>
          <Text style={styles.modalTitle}>Yeni Müşteri</Text>
          <TextInput style={styles.formInput} placeholder="Müşteri adı" value={newCustomer.name} onChangeText={(text) => setNewCustomer({ ...newCustomer, name: text })} />
          <TextInput style={styles.formInput} placeholder="Şehir" value={newCustomer.city} onChangeText={(text) => setNewCustomer({ ...newCustomer, city: text })} />
          <View style={styles.segmented}>
            {['standard', 'partner'].map((tier) => (
              <TouchableOpacity key={tier} style={[styles.segmentButton, newCustomer.price_tier === tier && styles.segmentButtonActive]} onPress={() => setNewCustomer({ ...newCustomer, price_tier: tier })}>
                <Text style={newCustomer.price_tier === tier ? styles.segmentTextActive : styles.segmentText}>{tier}</Text>
              </TouchableOpacity>
            ))}
          </View>
          <TouchableOpacity style={styles.checkRow} onPress={() => setNewCustomer({ ...newCustomer, allow_backorder: !newCustomer.allow_backorder })}>
            <Ionicons name={newCustomer.allow_backorder ? 'checkbox' : 'square-outline'} size={20} color="#0f766e" />
            <Text>Backorder uygun</Text>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.primaryAction, !newCustomer.name.trim() && styles.disabled]} onPress={onCreate} disabled={!newCustomer.name.trim()}>
            <Text style={styles.primaryActionText}>Müşteri Ekle</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#f4f7f8' },
  container: { paddingHorizontal: 18, paddingBottom: 18, paddingTop: Platform.OS === 'android' ? (NativeStatusBar.currentHeight || 0) + 18 : 34, gap: 14 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 4 },
  logo: { width: 48, height: 48, borderRadius: 6, backgroundColor: '#d64045', alignItems: 'center', justifyContent: 'center' },
  logoText: { color: '#fff', fontWeight: '800' },
  title: { fontSize: 22, fontWeight: '800', color: '#172026' },
  subtitle: { color: '#60737c', marginTop: 2 },
  headerAction: { marginLeft: 'auto', minHeight: 38, borderRadius: 8, paddingHorizontal: 12, backgroundColor: '#294047', alignItems: 'center', justifyContent: 'center' },
  headerActionText: { color: '#fff', fontWeight: '800' },
  row: { flexDirection: 'row', gap: 10 },
  input: { flex: 1, minHeight: 44, backgroundColor: '#fff', borderColor: '#c7d5da', borderWidth: 1, borderRadius: 6, paddingHorizontal: 12 },
  iconButton: { width: 48, borderRadius: 6, alignItems: 'center', justifyContent: 'center', backgroundColor: '#294047' },
  selectorRow: { flexDirection: 'row', gap: 10, alignItems: 'stretch' },
  selectBox: { flex: 1, minHeight: 64, backgroundColor: '#fff', borderColor: '#c7d5da', borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 9, justifyContent: 'center' },
  selectLabel: { color: '#60737c', fontSize: 12, fontWeight: '700' },
  selectValueRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 2 },
  selectValue: { color: '#172026', fontSize: 18, fontWeight: '800' },
  selectMeta: { color: '#60737c', marginTop: 2, fontSize: 12 },
  panel: { backgroundColor: '#fff', borderColor: '#d9e3e7', borderWidth: 1, borderRadius: 8, padding: 14, gap: 10 },
  panelTitle: { fontSize: 16, fontWeight: '800', color: '#172026' },
  messages: { gap: 10, minHeight: 220 },
  empty: { color: '#60737c' },
  bubble: { maxWidth: '86%', borderRadius: 8, padding: 12 },
  userBubble: { alignSelf: 'flex-end', backgroundColor: '#0f766e' },
  assistantBubble: { alignSelf: 'flex-start', backgroundColor: '#eef3f5' },
  userText: { color: '#fff', lineHeight: 20 },
  assistantText: { color: '#172026', lineHeight: 20 },
  sourceBox: { marginTop: 8, gap: 4 },
  sourceToggle: { flexDirection: 'row', alignItems: 'center', gap: 4, minHeight: 28 },
  sourceTitle: { fontWeight: '800', color: '#455a64', fontSize: 12 },
  sourceLine: { color: '#455a64', fontSize: 12 },
  total: { fontSize: 24, fontWeight: '800', color: '#0f766e' },
  line: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 10, borderTopColor: '#eef3f5', borderTopWidth: 1 },
  inactive: { opacity: 0.5 },
  product: { fontWeight: '700', color: '#172026' },
  meta: { color: '#60737c', marginTop: 3 },
  qtyControl: { flexDirection: 'row', alignItems: 'center', borderColor: '#c7d5da', borderWidth: 1, borderRadius: 6, overflow: 'hidden' },
  qtyButton: { width: 28, height: 32, alignItems: 'center', justifyContent: 'center', backgroundColor: '#eef3f5' },
  qty: { width: 28, textAlign: 'center', fontWeight: '700' },
  amount: { width: 90, textAlign: 'right', fontWeight: '700' },
  composer: { minHeight: 52, borderColor: '#c7d5da', borderWidth: 1, borderRadius: 8, padding: 6, flexDirection: 'row', alignItems: 'flex-end', gap: 8, backgroundColor: '#fff' },
  message: { flex: 1, minHeight: 34, maxHeight: 120, paddingHorizontal: 6, paddingVertical: 6, textAlignVertical: 'top' },
  sendButton: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#0f766e', alignItems: 'center', justifyContent: 'center' },
  modalBackdrop: { flex: 1, backgroundColor: 'rgba(23, 32, 38, 0.32)', justifyContent: 'flex-end' },
  modalDismiss: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0 },
  modalSheet: { backgroundColor: '#fff', borderTopLeftRadius: 12, borderTopRightRadius: 12, padding: 16, gap: 8 },
  modalTitle: { fontSize: 16, fontWeight: '800', color: '#172026', marginBottom: 4 },
  quoteOption: { minHeight: 52, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8, backgroundColor: '#f4f7f8', justifyContent: 'center' },
  quoteOptionActive: { borderColor: '#0f766e', borderWidth: 1, backgroundColor: '#eef7f5' },
  quoteOptionId: { fontWeight: '800', color: '#172026' },
  quoteOptionCustomer: { color: '#60737c', marginTop: 2 },
  formInput: { minHeight: 44, backgroundColor: '#fff', borderColor: '#c7d5da', borderWidth: 1, borderRadius: 8, paddingHorizontal: 12 },
  segmented: { flexDirection: 'row', borderColor: '#c7d5da', borderWidth: 1, borderRadius: 8, overflow: 'hidden' },
  segmentButton: { flex: 1, minHeight: 40, alignItems: 'center', justifyContent: 'center', backgroundColor: '#fff' },
  segmentButtonActive: { backgroundColor: '#0f766e' },
  segmentText: { color: '#455a64', fontWeight: '700' },
  segmentTextActive: { color: '#fff', fontWeight: '800' },
  checkRow: { minHeight: 40, flexDirection: 'row', alignItems: 'center', gap: 8 },
  primaryAction: { minHeight: 44, borderRadius: 8, backgroundColor: '#0f766e', alignItems: 'center', justifyContent: 'center' },
  primaryActionText: { color: '#fff', fontWeight: '800' },
  secondaryAction: { minHeight: 44, borderRadius: 8, backgroundColor: '#eef3f5', alignItems: 'center', justifyContent: 'center' },
  secondaryActionText: { color: '#172026', fontWeight: '800' },
  errorText: { color: '#b42318' },
  disabled: { opacity: 0.6 },
});
