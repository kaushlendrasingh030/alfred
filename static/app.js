async function postJSON(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {}),
  });
  return res.json();
}

function appendLine(role, text) {
  const chat = document.getElementById('chat');
  const el = document.createElement('div');
  el.className = 'line ' + role;
  el.textContent = (role === 'user' ? 'You: ' : 'Alfred: ') + text;
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
}

document.getElementById('send').onclick = async () => {
  const msg = document.getElementById('msg').value;
  if (!msg) return;
  appendLine('user', msg);
  document.getElementById('msg').value = '';
  const r = await postJSON('/api/message', { message: msg });
  appendLine('assistant', r.reply || JSON.stringify(r));
};

document.getElementById('screenshot').onclick = async () => {
  const r = await postJSON('/api/screenshot', {});
  if (r.error) {
    appendLine('assistant', 'screenshot error: ' + r.message || JSON.stringify(r));
    return;
  }
  if (r.image_base64) {
    const img = document.createElement('img');
    img.src = 'data:image/png;base64,' + r.image_base64;
    img.style.maxWidth = '80%';
    document.getElementById('chat').appendChild(img);
  } else {
    appendLine('assistant', JSON.stringify(r));
  }
};

document.getElementById('analyze').onclick = async () => {
  const scr = await postJSON('/api/screenshot', {});
  if (scr.image_base64) {
    const out = await postJSON('/api/vision_analyze', { image_base64: scr.image_base64, instruction: 'Describe the screen contents.' });
    appendLine('assistant', out.model_response || JSON.stringify(out));
  } else {
    appendLine('assistant', 'screenshot failed: ' + JSON.stringify(scr));
  }
};

document.getElementById('listfiles').onclick = async () => {
  const r = await fetch('/api/list_files');
  const j = await r.json();
  appendLine('assistant', JSON.stringify(j));
};

document.getElementById('confirm').onclick = async () => {
  const r = await postJSON('/api/confirm', {});
  appendLine('assistant', r.reply || JSON.stringify(r));
};

document.getElementById('cancel').onclick = async () => {
  const r = await postJSON('/api/cancel', {});
  appendLine('assistant', r.reply || JSON.stringify(r));
};
