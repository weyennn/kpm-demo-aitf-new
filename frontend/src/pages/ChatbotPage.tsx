import { useState, useRef, useEffect } from 'react'
import { Bot, User, Send, RefreshCw, Zap, MessageCircle, Sparkles } from 'lucide-react'

interface ChatMsg {
  role: 'user' | 'bot'
  text: string
  time: string
}

const FAQ: { keywords: string[]; answer: string }[] = [
  {
    keywords: ['kpm', 'apa itu kpm', 'tentang kpm'],
    answer:
      'KPM (Kehumasan dan Pemberitaan Masyarakat) adalah unit yang bertanggung jawab atas komunikasi publik, pemberitaan, dan manajemen informasi di lingkungan Kementerian Kominfo. KPM bekerja sama dengan AITF untuk menghadirkan platform intelijen berbasis data.',
  },
  {
    keywords: ['aitf', 'apa itu aitf'],
    answer:
      'AITF (AI Task Force) adalah tim khusus yang mengembangkan solusi kecerdasan buatan untuk mendukung operasional pemerintahan, termasuk sistem analisis narasi dan monitoring isu publik ini.',
  },
  {
    keywords: ['dashboard', 'overview', 'beranda'],
    answer:
      'Halaman Dashboard / Overview menampilkan ringkasan kondisi terkini: metrik sentimen publik, early warning isu berisiko tinggi, tren percakapan, dan isu-isu teratas yang sedang dipantau.',
  },
  {
    keywords: ['monitoring', 'isu', 'pantau'],
    answer:
      'Halaman Monitoring Isu menampilkan daftar isu yang sedang dipantau secara real-time beserta label risiko (tinggi/sedang/rendah), platform sumber, dan tren percakapan. Anda dapat memfilter berdasarkan tanggal, platform, dan sentimen.',
  },
  {
    keywords: ['sentimen', 'analisis sentimen', 'positif', 'negatif', 'netral'],
    answer:
      'Analisis Sentimen mengklasifikasikan konten menjadi tiga kategori: Positif, Netral, dan Negatif. Sistem menggunakan model NLP berbasis transformer yang dilatih dengan data teks Bahasa Indonesia.',
  },
  {
    keywords: ['narasi', 'viewer narasi', 'generate narasi'],
    answer:
      'Viewer Narasi menampilkan narasi counter yang telah di-generate oleh sistem AI berdasarkan analisis isu. Narasi dapat diunduh dalam format DOCX atau PDF untuk keperluan distribusi ke media.',
  },
  {
    keywords: ['strategi', 'stratkom', 'komunikasi'],
    answer:
      'Halaman Strategi Komunikasi menyediakan rekomendasi strategi penyebaran narasi: pemilihan platform, waktu optimal posting, tone komunikasi, dan target audiens berdasarkan analisis demografis.',
  },
  {
    keywords: ['brief', 'executive brief', 'laporan'],
    answer:
      'Executive Brief adalah ringkasan eksekutif yang dapat dibagikan kepada pimpinan. Berisi poin-poin kritis, rekomendasi tindakan, dan analisis risiko dalam format yang ringkas dan mudah dipahami.',
  },
  {
    keywords: ['crawling', 'crawler', 'data'],
    answer:
      'Sistem crawling mengumpulkan data dari berbagai platform: Twitter/X, Instagram, TikTok, dan portal berita online. Data diperbarui secara berkala dan diproses melalui pipeline NLP otomatis.',
  },
  {
    keywords: ['labeling', 'label', 'anotasi'],
    answer:
      'Labeling UI digunakan oleh tim anotator untuk memberikan label manual pada data teks. Hasil labeling digunakan untuk melatih dan meningkatkan akurasi model AI yang digunakan di sistem.',
  },
  {
    keywords: ['riwayat', 'dokumen', 'histori'],
    answer:
      'Riwayat Dokumen menyimpan semua narasi, brief, dan stratkom yang telah di-generate sebelumnya. Dokumen dapat diakses kembali, diunduh, atau dijadikan referensi untuk analisis lanjutan.',
  },
  {
    keywords: ['tanya isu', 'chat', 'analisis isu'],
    answer:
      'Halaman "Tanya Isu" adalah chatbot analitik yang dapat menganalisis isu secara mendalam. Masukkan nama isu atau pertanyaan, dan sistem akan mengambil dokumen relevan dari database lalu menghasilkan analisis komprehensif beserta narasi counter.',
  },
  {
    keywords: ['cara pakai', 'cara menggunakan', 'panduan', 'tutorial'],
    answer:
      'Cara menggunakan platform ini:\n1. Mulai dari Dashboard untuk melihat situasi terkini\n2. Buka Monitoring untuk memantau isu spesifik\n3. Gunakan "Tanya Isu" untuk analisis mendalam suatu topik\n4. Lihat Narasi & Stratkom untuk rekomendasi komunikasi\n5. Export ke Executive Brief untuk laporan pimpinan',
  },
  {
    keywords: ['akurasi', 'seberapa akurat', 'model ai'],
    answer:
      'Model AI yang digunakan telah dilatih dengan jutaan data teks Bahasa Indonesia. Akurasi klasifikasi sentimen mencapai ~87% pada data uji. Namun, hasil analisis sebaiknya selalu diverifikasi oleh tim analis sebelum digunakan sebagai dasar keputusan.',
  },
  {
    keywords: ['platform', 'sumber data', 'media sosial'],
    answer:
      'Sistem ini memantau data dari: Twitter/X, Instagram, TikTok, Facebook, YouTube, serta ratusan portal berita online dan media cetak digital di Indonesia.',
  },
]

const QUICK_PROMPTS = [
  'Apa itu KPM?',
  'Bagaimana cara pakai?',
  'Apa fungsi Monitoring Isu?',
  'Jelaskan Analisis Sentimen',
  'Cara generate narasi?',
]

function getBotReply(question: string): string {
  const q = question.toLowerCase()
  const match = FAQ.find(f => f.keywords.some(k => q.includes(k)))
  if (match) return match.answer
  return `Maaf, saya belum memiliki jawaban spesifik untuk pertanyaan tersebut. Silakan coba tanya dengan kata kunci yang berbeda, atau hubungi tim KPM × AITF untuk bantuan lebih lanjut.\n\nContoh pertanyaan: "Apa itu KPM?", "Bagaimana cara pakai platform ini?", atau "Jelaskan fitur Monitoring Isu."`
}

function nowTime() {
  return new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })
}

export default function ChatbotPage() {
  const [messages, setMessages] = useState<ChatMsg[]>([
    {
      role: 'bot',
      text: 'Halo! Saya **Asisten KPM × AITF**. Saya siap menjawab pertanyaan umum seputar platform ini, fitur-fiturnya, dan cara penggunaannya.\n\nSilakan ajukan pertanyaan Anda!',
      time: nowTime(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const endRef   = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text?: string) => {
    const q = (text ?? input).trim()
    if (!q || loading) return
    setInput('')
    const userMsg: ChatMsg = { role: 'user', text: q, time: nowTime() }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)
    await new Promise(r => setTimeout(r, 700 + Math.random() * 500))
    const reply = getBotReply(q)
    setMessages(prev => [...prev, { role: 'bot', text: reply, time: nowTime() }])
    setLoading(false)
  }

  return (
    <div className="flex flex-col h-full bg-background overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b border-border px-6 py-4 flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center shadow-sm">
          <MessageCircle size={17} className="text-white" />
        </div>
        <div>
          <h1 className="text-[14px] font-bold text-text-main">Chatbot Umum</h1>
          <p className="text-[11px] text-text-muted">Tanya apa saja tentang platform KPM × AITF</p>
        </div>
        <div className="ml-auto flex items-center gap-2 px-3 py-1.5 bg-success/10 border border-success/20 rounded-full">
          <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
          <span className="text-[11px] font-medium text-success">Online</span>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Chat Area */}
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm ${
                  m.role === 'bot' ? 'bg-primary' : 'bg-border'
                }`}>
                  {m.role === 'bot'
                    ? <Bot size={14} className="text-white" />
                    : <User size={14} className="text-text-muted" />}
                </div>
                <div className={`flex flex-col gap-1 max-w-[580px] ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`rounded-2xl px-4 py-3 text-[13px] leading-relaxed whitespace-pre-line ${
                    m.role === 'bot'
                      ? 'bg-white border border-border text-text-main rounded-tl-sm'
                      : 'bg-primary text-white rounded-tr-sm'
                  }`}>
                    {m.text.replace(/\*\*(.*?)\*\*/g, '$1')}
                  </div>
                  <span className="text-[10px] text-text-muted px-1">{m.time}</span>
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center flex-shrink-0 shadow-sm">
                  <Bot size={14} className="text-white" />
                </div>
                <div className="bg-white border border-border rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
                  {[0, 1, 2].map(i => (
                    <div key={i} className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: `${i * 150}ms` }} />
                  ))}
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Input */}
          <div className="flex-shrink-0 border-t border-border bg-white px-6 py-4">
            <div className="flex gap-3">
              <input
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); send() } }}
                disabled={loading}
                placeholder="Ketik pertanyaan Anda di sini…"
                className="flex-1 bg-surface border border-border rounded-xl px-4 py-3 text-[13px] outline-none focus:border-primary focus:ring-2 focus:ring-primary/10 transition-all placeholder:text-text-muted disabled:opacity-50"
              />
              <button
                onClick={() => send()}
                disabled={loading || !input.trim()}
                className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center hover:bg-primary-hover transition-all disabled:opacity-40 cursor-pointer flex-shrink-0 shadow-sm"
              >
                {loading
                  ? <RefreshCw size={15} className="text-white animate-spin" />
                  : <Send size={15} className="text-white" />}
              </button>
            </div>
            <div className="text-[10px] font-mono text-text-muted mt-2 flex items-center gap-1.5">
              <Zap size={9} className="text-primary" />
              Pertanyaan dijawab berdasarkan basis pengetahuan KPM × AITF
            </div>
          </div>
        </div>

        {/* FAQ Sidebar */}
        <div className="w-[260px] flex-shrink-0 border-l border-border bg-surface flex flex-col overflow-hidden">
          <div className="px-4 py-3.5 border-b border-border bg-white">
            <div className="flex items-center gap-2">
              <Sparkles size={13} className="text-primary" />
              <span className="text-[12px] font-semibold text-text-main">Pertanyaan Cepat</span>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1.5">
            {QUICK_PROMPTS.map(p => (
              <button
                key={p}
                onClick={() => send(p)}
                disabled={loading}
                className="w-full text-left px-3 py-2.5 text-[12px] text-text-muted bg-white border border-border rounded-lg hover:border-primary hover:text-primary hover:bg-primary/[0.03] transition-all cursor-pointer disabled:opacity-50"
              >
                {p}
              </button>
            ))}
          </div>

          <div className="px-4 py-4 border-t border-border bg-white">
            <div className="text-[11px] text-text-muted leading-relaxed">
              <strong className="text-text-main">Catatan:</strong> Chatbot ini hanya menjawab pertanyaan umum tentang platform. Untuk analisis isu spesifik, gunakan halaman{' '}
              <strong className="text-primary">Tanya Isu</strong>.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
