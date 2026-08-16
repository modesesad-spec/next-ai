let sessionId = localStorage.getItem('sessionId') || 'session_' + Date.now();
localStorage.setItem('sessionId', sessionId);

let currentAvatar = localStorage.getItem('avatar') || 'https://i.imgur.com/default_avatar.png';
document.getElementById('avatar-img').src = currentAvatar;

async function send() {
    const input = document.getElementById('user-input').value.trim();
    if (!input) return;

    appendMessage('user', input);
    document.getElementById('user-input').value = '';

    try {
        const res = await fetch('/api/nexa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input: input, session_id: sessionId })
        });
        const data = await res.json();
        appendMessage('ai', data.answer);

        if (data.avatar) {
            currentAvatar = data.avatar;
            document.getElementById('avatar-img').src = data.avatar;
            localStorage.setItem('avatar', data.avatar);
        }

        if (data.image_url) {
            const chatBox = document.getElementById('chat-box');
            const imgDiv = document.createElement('div');
            imgDiv.className = 'message ai-message';
            imgDiv.innerHTML = `<img src="${data.image_url}" style="max-width:100%; border-radius:8px;">`;
            chatBox.appendChild(imgDiv);
        }

        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(data.answer.replace(/<[^>]*>/g, ''));
            utterance.lang = 'id-ID';
            speechSynthesis.speak(utterance);
        }

        document.getElementById('chat-box').scrollTop = document.getElementById('chat-box').scrollHeight;
    } catch (err) {
        appendMessage('ai', '⚠️ Error: ' + err.message);
    }
}

function startVoice() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Browser tidak support voice input.');
        return;
    }
    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'id-ID';
    recognition.start();
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        document.getElementById('user-input').value = transcript;
        send();
    };
}

async function handleFileUpload(input) {
    const file = input.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async function(e) {
        const content = e.target.result.split(',')[1];
        const fileType = file.name.endsWith('.csv') ? 'csv' : 'json';

        appendMessage('user', `📁 Upload file: ${file.name}`);
        try {
            const res = await fetch('/api/nexa', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    input: '/upload',
                    session_id: sessionId,
                    file: { content: content, type: fileType }
                })
            });
            const data = await res.json();
            appendMessage('ai', data.answer);
        } catch (err) {
            appendMessage('ai', '⚠️ Gagal upload: ' + err.message);
        }
    };
    reader.readAsDataURL(file);
}

function gantiAvatar() {
    const url = prompt('Masukkan URL avatar baru:');
    if (url && url.trim()) {
        currentAvatar = url.trim();
        document.getElementById('avatar-img').src = currentAvatar;
        localStorage.setItem('avatar', currentAvatar);
        fetch('/api/nexa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input: `/ganti_avatar ${currentAvatar}`, session_id: sessionId })
        });
    }
}

async function resetSession() {
    if (!confirm('Reset semua percakapan?')) return;
    const res = await fetch('/api/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
    });
    await res.json();
    document.getElementById('chat-box').innerHTML = '';
    appendMessage('ai', '🧹 Session direset. Mulai baru.');
}

function appendMessage(sender, text) {
    const chatBox = document.getElementById('chat-box');
    const div = document.createElement('div');
    div.className = `message ${sender === 'user' ? 'user-message' : 'ai-message'}`;
    div.innerHTML = text.replace(/\n/g, '<br>');
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

document.getElementById('user-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') send();
});
