Harvey.UI = {
    scrollToBottom: () => {
        const box = Harvey.DOM.chatBox;
        if (box) box.scrollTop = box.scrollHeight;
    },

    maintainScroll: (action) => {
        const box = Harvey.DOM.chatBox;
        if (!box) return;
        const oldScrollHeight = box.scrollHeight;
        action();
        box.scrollTop = box.scrollHeight - oldScrollHeight;
    },

    clearChat: () => {
        if (Harvey.DOM.chatBox) Harvey.DOM.chatBox.innerHTML = '';
    },

    showLoader: () => {
        const loader = document.createElement('div');
        loader.id = 'history-loader';
        loader.className = 'text-center text-[10px] font-black uppercase tracking-widest text-slate-400 py-4';
        loader.innerText = 'Syncing History...';
        Harvey.DOM.chatBox.prepend(loader);
    },

    hideLoader: () => {
        document.getElementById('history-loader')?.remove();
    },

    renderWelcomeScreen: () => {
        const div = document.createElement('div');
        div.id = 'welcome-placeholder';
        div.className = "flex flex-col items-center justify-center h-full opacity-80 transition-opacity duration-500";
        div.innerHTML = `
            <img src="/static/core/images/harvey_icon.png" class="w-24 h-24 rounded-[32px] mb-8 shadow-xl shadow-indigo-100 object-contain">
            <h3 class="text-2xl font-black text-slate-900 mb-2">
                Hello, ${Harvey.Config.username || 'User'}</h3>
            <div class="text-center text-slate-500 max-w-sm text-sm font-medium leading-relaxed">How can I assist you with your HR
                tasks or policy questions today?</div>
        `;
        Harvey.DOM.chatBox.appendChild(div);
    },

    removeWelcomeScreen: () => {
        const el = document.getElementById('welcome-placeholder');
        if (el) {
            el.classList.add('opacity-0');
            setTimeout(() => el.remove(), 300);
        }
    },

    formatTime: (isoString) => {
        if (!isoString) return '';
        const date = new Date(isoString);
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    },

    formatDate: (isoString) => {
        if (!isoString) return '';
        const date = new Date(isoString);
        return date.toLocaleDateString([], { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    },

    renderConversationStart: (isoString) => {
        const existing = document.getElementById('conversation-start-indicator');
        if (existing) existing.remove();

        const div = document.createElement('div');
        div.id = 'conversation-start-indicator';
        div.className = "text-center my-8 flex items-center justify-center gap-4 px-6";
        div.innerHTML = `
            <div class="h-px bg-slate-200 w-full max-w-[100px]"></div>
            <span class="text-[10px] text-slate-400 font-black whitespace-nowrap uppercase tracking-widest">
                Session started • ${Harvey.UI.formatDate(isoString)}
            </span>
            <div class="h-px bg-slate-200 w-full max-w-[100px]"></div>
        `;
        Harvey.DOM.chatBox.prepend(div);
    },

    createMessageBubble: (sender, text, timestamp) => {
        const container = document.createElement("div");
        container.classList.add("flex", "items-start", "gap-3", "animate-fade-in-up", "mb-4");

        const icon = document.createElement("div");
        icon.className = "w-11 h-11 md:w-9 md:h-9 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold shadow-md";

        if (sender === "user") {
            container.classList.add("flex-row-reverse");
            icon.classList.add("bg-slate-900", "text-white");
            icon.innerText = "ME";
        } else {
            icon.classList.add("bg-white", "p-2");
            icon.innerHTML = '<img src="/static/core/images/harvey_icon.png" class="w-full h-full object-contain">';
        }

        const contentWrapper = document.createElement("div");
        contentWrapper.className = `flex flex-col ${sender === 'user' ? 'items-end' : 'items-start'} max-w-2xl`;

        const bubble = document.createElement("div");
        bubble.classList.add("p-4", "rounded-2xl", "leading-relaxed", "shadow-sm", "w-full", "prose-chat");
        bubble.style.fontSize = "16px";
        bubble.classList.add(sender === "user" ? "chat-bubble-user" : "chat-bubble-ai");
        if (sender === "user") bubble.classList.add("text-white", "[&_a]:text-white", "[&_a]:underline-offset-2");

        // Format Content
        let formatted = text;

        // 1. First Parse Markdown
        if (typeof marked !== 'undefined') {
            marked.setOptions({ breaks: true, gfm: true });
            formatted = marked.parse(text);
        } else {
            formatted = text.replace(/\n/g, '<br>');
            formatted = Harvey.Utils.linkify(formatted);
        }

        // 2. Then Inject Attachment Cards (So they aren't escaped by Markdown)
        const attachmentRegex = /\[Attached Resume: ([^|\]]+)\|?([^\]]*)\]/g;
        formatted = formatted.replace(attachmentRegex, (match, path, url) => {
            if (!url) return '';
            const fileName = path.split('\\').pop().split('/').pop();
            const isUser = sender === 'user';
            const cardClass = isUser ? 'bg-white/10 border-white/20 text-white' : 'bg-slate-50 border-slate-100 text-slate-900';
            const labelClass = isUser ? 'text-white/60' : 'text-slate-400';
            const btnClass = isUser ? 'bg-white text-slate-900 hover:bg-indigo-50' : 'bg-slate-900 text-white hover:bg-slate-800';

            return `
                <div class="mt-4 p-4 rounded-2xl border flex items-center justify-between gap-4 ${cardClass} not-prose">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 ${isUser ? 'bg-white/20' : 'bg-indigo-50'} rounded-xl flex items-center justify-center ${isUser ? 'text-white' : 'text-indigo-600'}">
                            <i class="fas fa-file-pdf text-lg"></i>
                        </div>
                        <div class="flex-grow min-w-0 text-left">
                            <p class="text-[10px] font-black uppercase tracking-widest ${labelClass}">Resume Attachment</p>
                            <p class="text-xs font-bold truncate max-w-[140px]">${fileName}</p>
                        </div>
                    </div>
                    <a href="${url}" target="_blank" class="px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all active:scale-95 shadow-lg flex-shrink-0 ${btnClass}">
                        View PDF
                    </a>
                </div>
            `;
        });

        bubble.innerHTML = formatted;
        contentWrapper.appendChild(bubble);

        // Timestamp
        if (timestamp) {
            const timeDiv = document.createElement("div");
            timeDiv.className = "text-[10px] text-slate-400 mt-1.5 px-1 font-bold uppercase tracking-wider select-none";
            timeDiv.innerText = Harvey.UI.formatTime(timestamp);
            contentWrapper.appendChild(timeDiv);
        }

        container.appendChild(icon);
        container.appendChild(contentWrapper);
        return container;
    },

    appendMessage: (sender, text, timestamp) => {
        const bubble = Harvey.UI.createMessageBubble(sender, text, timestamp);
        Harvey.DOM.chatBox.appendChild(bubble);
        Harvey.UI.scrollToBottom();
    },

    prependMessage: (sender, text, timestamp) => {
        const bubble = Harvey.UI.createMessageBubble(sender, text, timestamp);
        Harvey.DOM.chatBox.insertBefore(bubble, Harvey.DOM.chatBox.firstChild);
    },

    showThinkingBubble: () => {
        let bubble = Harvey.DOM.chatBox.querySelector('.thinking-bubble');
        if (!bubble) {
            bubble = document.createElement("div");
            bubble.className = "flex items-start gap-3 thinking-bubble animate-pulse mb-4";
            bubble.innerHTML = `
                <div class="w-9 h-9 md:w-8 md:h-8 rounded-full bg-white p-1.5 flex items-center justify-center shadow-sm flex-shrink-0">
                    <img src="/static/core/images/harvey_icon.png" class="w-full h-full object-contain">
                </div>
                <div class="chat-bubble-ai px-4 py-3 rounded-2xl flex gap-1 items-center">
                        <div class="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce"></div>
                        <div class="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce delay-100"></div>
                        <div class="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce delay-200"></div>
                </div>
            `;
            Harvey.DOM.chatBox.appendChild(bubble);
            Harvey.UI.scrollToBottom();
        }
    },

    removeThinkingBubble: () => {
        Harvey.DOM.chatBox.querySelector('.thinking-bubble')?.remove();
    },

    renderAttachments: () => {
        const previews = Harvey.DOM.filePreviews;
        previews.innerHTML = '';
        if (Harvey.State.attachedFiles.length > 0) {
            previews.classList.remove('hidden');
        } else {
            previews.classList.add('hidden');
        }

        Harvey.State.attachedFiles.forEach((file, index) => {
            const chip = document.createElement('div');
            chip.className = "flex items-center gap-2 bg-slate-100 border border-slate-200 px-3 py-1.5 rounded-xl text-xs text-slate-600 font-bold animate-fade-in transition-all hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-600";
            chip.innerHTML = `
                <i class="fas fa-file-invoice"></i>
                <span class="max-w-[150px] truncate">${file.name}</span>
                <button onclick="Harvey.Upload.remove(${index})" class="hover:text-red-500 transition-colors ml-1">
                    <i class="fas fa-times-circle"></i>
                </button>
            `;
            previews.appendChild(chip);
        });
    },

    showConfirmDialog: (message, onConfirm) => {
        document.getElementById('harvey-confirm-dialog')?.remove();

        const dialog = document.createElement('div');
        dialog.id = 'harvey-confirm-dialog';
        dialog.className = 'fixed top-24 left-1/2 -translate-x-1/2 z-[10000] flex items-center gap-4 bg-white/95 backdrop-blur-md border border-red-100 px-6 py-4 rounded-2xl shadow-2xl animate-in fade-in slide-in-from-top-4 duration-200';

        dialog.innerHTML = `
            <div class="flex items-center gap-3 text-sm text-slate-900 font-bold">
                <i class="fas fa-circle-exclamation text-red-500"></i>
                <span>${message}</span>
            </div>
            <div class="flex items-center gap-2 border-l border-slate-200 pl-4 ml-2">
                <button id="confirm-cancel-btn" class="px-3 py-1.5 text-xs font-bold text-slate-400 hover:text-slate-900 rounded-lg transition-colors">
                    Cancel
                </button>
                <button id="confirm-yes-btn" class="px-4 py-2 text-xs font-black bg-red-50 text-red-600 hover:bg-red-500 hover:text-white border border-red-100 rounded-lg transition-all shadow-sm">
                    Delete
                </button>
            </div>
        `;

        document.body.appendChild(dialog);

        const close = () => {
            dialog.classList.add('opacity-0', '-translate-y-4');
            setTimeout(() => dialog.remove(), 200);
        };

        document.getElementById('confirm-cancel-btn').onclick = close;
        document.getElementById('confirm-yes-btn').onclick = () => {
            close();
            onConfirm();
        };

        setTimeout(() => {
            if (document.body.contains(dialog)) close();
        }, 10000);
    }
};
