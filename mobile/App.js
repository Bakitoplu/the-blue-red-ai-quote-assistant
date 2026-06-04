import React, { useEffect, useState } from 'react';
import { SafeAreaView, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';

const API = process.env.EXPO_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const WELCOME_MESSAGE = 'Merhaba, size ürünler, politikalar ve teklifiniz hakkında yardımcı olabilirim.';

function money(value) {
  return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(value || 0);
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
  const [quoteId, setQuoteId] = useState('Q-1002');
  const [customerId, setCustomerId] = useState('CUST-ANK-002');
  const [quote, setQuote] = useState(null);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([{ id: 'welcome', role: 'assistant', text: WELCOME_MESSAGE, sources: [] }]);
  const [busy, setBusy] = useState(false);

  async function loadQuote() {
    const res = await fetch(`${API}/quotes/${quoteId}`);
    setQuote(await res.json());
  }

  useEffect(() => {
    loadQuote();
  }, [quoteId]);

  async function send() {
    const trimmed = message.trim();
    if (!trimmed || busy) return;
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
      body: JSON.stringify({ quantity: Math.max(quantity, 0), reason: 'mobile quantity control' }),
    });
    await loadQuote();
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
            <Text style={styles.subtitle}>Mobil teklif asistanı</Text>
          </View>
        </View>

        <View style={styles.row}>
          <TextInput style={styles.input} value={quoteId} onChangeText={setQuoteId} />
          <TouchableOpacity style={styles.iconButton} onPress={loadQuote}>
            <Ionicons name="refresh" size={20} color="#fff" />
          </TouchableOpacity>
        </View>
        <TextInput style={styles.input} value={customerId} onChangeText={setCustomerId} />

        <View style={styles.panel}>
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
        </View>

        <View style={styles.panel}>
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
        </View>
      </ScrollView>
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

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: '#f4f7f8' },
  container: { padding: 18, gap: 14 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 4 },
  logo: { width: 48, height: 48, borderRadius: 6, backgroundColor: '#d64045', alignItems: 'center', justifyContent: 'center' },
  logoText: { color: '#fff', fontWeight: '800' },
  title: { fontSize: 22, fontWeight: '800', color: '#172026' },
  subtitle: { color: '#60737c', marginTop: 2 },
  row: { flexDirection: 'row', gap: 10 },
  input: { flex: 1, minHeight: 44, backgroundColor: '#fff', borderColor: '#c7d5da', borderWidth: 1, borderRadius: 6, paddingHorizontal: 12 },
  iconButton: { width: 48, borderRadius: 6, alignItems: 'center', justifyContent: 'center', backgroundColor: '#294047' },
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
  disabled: { opacity: 0.6 },
});
