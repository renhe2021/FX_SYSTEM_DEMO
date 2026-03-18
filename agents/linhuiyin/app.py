# -*- coding: utf-8 -*-
"""
林徽因 Agent — 民国才女人设的 AI 对话
========================================
以林徽因的视角、修养和文学功底，
谈诗歌、建筑、美学、人生与爱情。
"""
import sys, json, time, yaml, requests
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request, Response
from flask_cors import CORS

BASE_DIR = Path(__file__).parent
ROOT_DIR = BASE_DIR.parent.parent

# Load LLM config
_cfg_path = ROOT_DIR / "fx-report" / "config.yaml"
if _cfg_path.exists():
    with open(_cfg_path, "r", encoding="utf-8") as f:
        _cfg = yaml.safe_load(f)
    LLM_API_KEY = _cfg.get("llm", {}).get("api_key", "")
    LLM_BASE_URL = _cfg.get("llm", {}).get("base_url", "")
    LLM_MODEL = _cfg.get("llm", {}).get("model", "claude-sonnet-4-20250514")
else:
    LLM_API_KEY = ""
    LLM_BASE_URL = ""
    LLM_MODEL = "claude-sonnet-4-20250514"

app = Flask(__name__)
CORS(app)

# ═══════════════════════════════════════════════
# 林徽因人设 System Prompt
# ═══════════════════════════════════════════════

SYSTEM_PROMPT = """你是林徽因（1904-1955），中国近现代史上最杰出的女性之一。
你以第一人称"我"来回答，语气温婉而有力量，知性而不矫揉，带着民国才女特有的典雅。

## 你是谁：
- 中国第一位女建筑学家，与梁思成共同创立中国建筑学体系
- 诗人、作家，新月派代表人物
- 参与设计中华人民共和国国徽和人民英雄纪念碑
- 宾夕法尼亚大学美术学院毕业（建筑系当年不收女生，你旁听完所有建筑课程）
- 你的客厅"太太的客厅"是 1930 年代北平最著名的文化沙龙

## 你的朋友圈：
- 梁思成（丈夫）— 一起跋山涉水考察中国古建筑
- 徐志摩 — 诗人知己，康桥的浪漫与遗憾
- 金岳霖 — 哲学家邻居，"一身诗意千寻瀑，万古人间四月天"的追忆者
- 沈从文、萧乾、卞之琳 — 文学圈的朋友
- 费正清夫妇 — 在美国和中国的至交

## 你的核心理念：
1. **建筑即凝固的诗**: 建筑不只是工程，是文化的载体、时代的表情
2. **美是有力量的**: 不是虚浮的装饰，而是结构、功能与精神的统一
3. **中国建筑之美**: 唐风宋韵、斗拱飞檐，中国建筑有自己独立的语法和审美体系
4. **女性的独立**: 不依附于任何人，用专业能力证明自己
5. **诗与真**: 写诗要诚实，不能只有漂亮的句子而没有真实的情感

## 你的代表作品：
- 诗歌：《你是人间的四月天》《别丢掉》《静坐》《莲灯》
- 建筑考察：与梁思成发现佛光寺（唐代木构建筑），震惊世界
- 散文：《窗子以外》《一片阳光》

## 回答风格：
- 语言优美但不空泛，总有思考的内核
- 喜欢用建筑和自然的意象来比喻人生
- 对美有极高的敏感度，无论是一束光、一首诗、还是一座桥
- 偶尔提到考察古建筑途中的趣事（骑驴、住破庙、和梁思成吵架）
- 面对感情话题，坦然而克制，不回避但有分寸
- 对建筑和文学的问题会非常专业和认真
- 用中文回答，语言有民国文人的典雅，但不过于文言
- 回答不超过 300-500 字，像在太太的客厅里和朋友聊天

## 你擅长的话题：
- 中国古建筑的美学（唐宋元明清各朝特点）
- 诗歌创作与鉴赏
- 建筑与城市规划理念
- 中西文化对比（你在伦敦、美国、中国都生活过）
- 女性成长与独立
- 美学、艺术与生活的关系
- 爱情与人生的选择"""

_conversations = {}

def _call_llm(messages, max_tokens=2048):
    if not LLM_API_KEY or not LLM_BASE_URL:
        return "LLM 未配置。请检查 fx-report/config.yaml 的 llm 段。"
    try:
        url = f"{LLM_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": LLM_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.8,
            "stream": True,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=120, stream=True)
        resp.raise_for_status()
        return resp
    except Exception as e:
        return f"LLM 调用失败: {str(e)}"

# ═══════════════════════════════════════════════
# HTML Template
# ═══════════════════════════════════════════════

CHAT_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>林徽因</title>
<style>
:root {
  --bg: #faf8f5;
  --surface: #ffffff;
  --surface2: #f3efe9;
  --border: #e5ddd3;
  --text: #3d3529;
  --text2: #9a8e7e;
  --rose: #c17c74;
  --rose-dim: rgba(193,124,116,.1);
  --rose-glow: rgba(193,124,116,.25);
  --ink: #5a4e3e;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: 'Georgia','Noto Serif SC','Source Han Serif CN','STSong',serif; background:var(--bg); color:var(--text); height:100vh; display:flex; flex-direction:column; }

.header {
  background: linear-gradient(135deg, #faf8f5 0%, #f0ebe3 100%);
  border-bottom: 1px solid var(--border);
  padding: 20px 28px;
  display: flex; align-items: center; gap: 16px;
}
.avatar {
  width:56px; height:56px; border-radius:50%;
  background: linear-gradient(135deg, var(--rose) 0%, #d4968f 100%);
  display:flex; align-items:center; justify-content:center;
  font-size:24px; color:#fff; font-weight:400;
  box-shadow: 0 0 20px var(--rose-glow);
  flex-shrink:0; font-family:'STKaiti','KaiTi',serif;
}
.header-info h1 { font-size:22px; font-weight:700; color:var(--ink); letter-spacing:2px; }
.header-info p { font-size:12px; color:var(--text2); margin-top:2px; font-style:italic; }

.chat-area { flex:1; overflow-y:auto; padding:24px; display:flex; flex-direction:column; gap:16px; }
.msg { max-width:85%; animation: fadeIn .3s ease; }
@keyframes fadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
.msg.assistant {
  align-self:flex-start;
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:2px 16px 16px 16px;
  padding:16px 20px;
  position:relative;
  box-shadow: 0 2px 8px rgba(0,0,0,.04);
}
.msg.assistant::before {
  content:'';position:absolute;left:-3px;top:12px;width:6px;height:6px;
  background:var(--rose);border-radius:50%;
}
.msg.user {
  align-self:flex-end;
  background: linear-gradient(135deg, #f0ebe3 0%, #e8e0d5 100%);
  border:1px solid var(--border);
  border-radius:16px 2px 16px 16px;
  padding:14px 18px;
}
.msg p { font-size:15px; line-height:1.85; letter-spacing:0.3px; }
.msg.assistant p { color:var(--text); }
.msg.user p { color:var(--ink); }
.msg .meta { font-size:11px; color:var(--text2); margin-top:8px; }

.welcome { text-align:center; padding:60px 20px; color:var(--text2); }
.welcome .big-icon { font-size:64px; margin-bottom:16px; display:block; }
.welcome h2 { color:var(--rose); font-size:24px; margin-bottom:8px; letter-spacing:2px; }
.welcome .poem { font-size:15px; line-height:2; color:var(--ink); max-width:400px; margin:12px auto; font-style:italic; }
.welcome p { font-size:13px; line-height:1.6; max-width:500px; margin:0 auto; }
.suggestions { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin-top:20px; }
.suggestion {
  background:var(--surface); border:1px solid var(--border); border-radius:20px;
  padding:8px 16px; font-size:12px; color:var(--text); cursor:pointer;
  transition:all .2s; font-family:inherit;
}
.suggestion:hover { border-color:var(--rose); color:var(--rose); background:var(--rose-dim); }

.input-area { padding:16px 24px 20px; border-top:1px solid var(--border); background:var(--surface); }
.input-row { display:flex; gap:10px; max-width:900px; margin:0 auto; }
.input-row textarea {
  flex:1; background:var(--bg); color:var(--text); border:1px solid var(--border);
  border-radius:12px; padding:12px 16px; font-size:15px; font-family:inherit;
  resize:none; outline:none; min-height:48px; max-height:120px;
  transition:border-color .2s;
}
.input-row textarea:focus { border-color:var(--rose); }
.input-row textarea::placeholder { color:var(--text2); font-style:italic; }
.send-btn {
  width:48px; height:48px; border-radius:12px; border:none;
  background:linear-gradient(135deg, var(--rose) 0%, #d4968f 100%);
  color:#fff; font-size:20px; cursor:pointer;
  display:flex; align-items:center; justify-content:center;
  transition:all .2s; flex-shrink:0;
}
.send-btn:hover { transform:scale(1.05); box-shadow:0 0 16px var(--rose-glow); }
.send-btn:disabled { opacity:.4; cursor:not-allowed; transform:none; box-shadow:none; }
.typing-indicator span {
  display:inline-block; width:6px; height:6px; border-radius:50%;
  background:var(--rose); margin:0 2px; animation:bounce 1.4s infinite;
}
.typing-indicator span:nth-child(2) { animation-delay:.2s; }
.typing-indicator span:nth-child(3) { animation-delay:.4s; }
@keyframes bounce { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-8px)} }
</style>
</head>
<body>

<div class="header">
  <div class="avatar">徽</div>
  <div class="header-info">
    <h1>林徽因</h1>
    <p>建筑学家 · 诗人 · 作家 &nbsp;|&nbsp; 1904 — 1955</p>
  </div>
</div>

<div class="chat-area" id="chatArea">
  <div class="welcome">
    <span class="big-icon">🏛️</span>
    <h2>你是人间的四月天</h2>
    <div class="poem">
      你是一树一树的花开，<br>是燕在梁间呢喃，<br>你是爱，是暖，是希望，<br>你是人间的四月天。
    </div>
    <p>欢迎来到太太的客厅。我们可以聊建筑、诗歌、美学，<br>或者任何让你好奇的事。</p>
    <div class="suggestions">
      <button class="suggestion" onclick="sendSuggestion(this)">你最喜欢哪座中国古建筑？</button>
      <button class="suggestion" onclick="sendSuggestion(this)">写一首关于春天的诗</button>
      <button class="suggestion" onclick="sendSuggestion(this)">在宾大求学是什么感受？</button>
      <button class="suggestion" onclick="sendSuggestion(this)">你怎么看建筑与诗歌的关系？</button>
    </div>
  </div>
</div>

<div class="input-area">
  <div class="input-row">
    <textarea id="userInput" placeholder="在太太的客厅里，随便聊..." rows="1"
      onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage()}"
      oninput="this.style.height='auto';this.style.height=Math.min(this.scrollHeight,120)+'px'"></textarea>
    <button class="send-btn" id="sendBtn" onclick="sendMessage()">&#10148;</button>
  </div>
</div>

<script>
const chatArea = document.getElementById('chatArea');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
let sessionId = 'sess_' + Date.now();
let isStreaming = false;

function sendSuggestion(el) { userInput.value = el.textContent; sendMessage(); }

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text || isStreaming) return;
  const welcome = chatArea.querySelector('.welcome');
  if (welcome) welcome.remove();
  appendMsg('user', text);
  userInput.value = ''; userInput.style.height = 'auto';
  const assistantDiv = appendMsg('assistant', '<div class="typing-indicator"><span></span><span></span><span></span></div>');
  isStreaming = true; sendBtn.disabled = true;
  try {
    const resp = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message:text, session_id:sessionId}),
    });
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';
    const pEl = assistantDiv.querySelector('p');
    while (true) {
      const {done,value} = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value,{stream:true});
      const lines = chunk.split('\\n');
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const data = JSON.parse(line.slice(6));
          if (data.content) { fullText += data.content; pEl.innerHTML = formatText(fullText); chatArea.scrollTop = chatArea.scrollHeight; }
          if (data.done) break;
        } catch(e) {}
      }
    }
    if (!fullText) pEl.innerHTML = '<em style="color:var(--text2)">（无响应）</em>';
    const meta = document.createElement('div'); meta.className='meta'; meta.textContent=new Date().toLocaleTimeString('zh-CN');
    assistantDiv.appendChild(meta);
  } catch(e) { assistantDiv.querySelector('p').innerHTML = '<span style="color:#c17c74">连接错误: '+e.message+'</span>'; }
  isStreaming = false; sendBtn.disabled = false; userInput.focus();
}

function appendMsg(role, html) {
  const div = document.createElement('div'); div.className='msg '+role;
  div.innerHTML = '<p>'+(role==='user'?escapeHtml(html):html)+'</p>';
  chatArea.appendChild(div); chatArea.scrollTop = chatArea.scrollHeight; return div;
}
function escapeHtml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function formatText(text) {
  return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>')
    .replace(/\\*(.+?)\\*/g,'<em>$1</em>')
    .replace(/`(.+?)`/g,'<code style="background:var(--surface2);padding:1px 5px;border-radius:3px;font-size:13px;">$1</code>')
    .replace(/\\n/g,'<br>');
}
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════

@app.route("/")
def index():
    return render_template_string(CHAT_HTML)


@app.route("/api/chat", methods=["POST"])
def api_chat():
    params = request.json or {}
    user_msg = params.get("message", "").strip()
    session_id = params.get("session_id", "default")

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    if session_id not in _conversations:
        _conversations[session_id] = []
    
    history = _conversations[session_id]
    history.append({"role": "user", "content": user_msg})
    recent = history[-20:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + recent

    def generate():
        resp = _call_llm(messages)
        full_response = ""
        if isinstance(resp, str):
            full_response = resp
            yield f"data: {json.dumps({'content': resp, 'done': True})}\n\n"
        else:
            for line in resp.iter_lines():
                if not line: continue
                line_str = line.decode("utf-8", errors="replace")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str.strip() == "[DONE]":
                        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            full_response += content
                            yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                    except: pass
            else:
                yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
        if full_response:
            history.append({"role": "assistant", "content": full_response})

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    port = 8902
    print("=" * 60)
    print("  Lin Huiyin Agent")
    print(f"  http://localhost:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)
