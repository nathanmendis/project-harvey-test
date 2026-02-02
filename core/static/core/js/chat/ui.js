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
        loader.className = 'text-center text-xs text-gray-500 py-2';
        loader.innerText = 'Loading history...';
        Harvey.DOM.chatBox.prepend(loader);
    },

    hideLoader: () => {
        document.getElementById('history-loader')?.remove();
    },

    renderWelcomeScreen: () => {
        const div = document.createElement('div');
        div.id = 'welcome-placeholder';
        div.className = "flex flex-col items-center justify-center h-full opacity-60 transition-opacity duration-500";
        div.innerHTML = `
            <div class="w-24 h-24 bg-white/5 rounded-full flex items-center justify-center mb-6 animate-pulse border border-white/5 shadow-[0_0_30px_rgba(79,70,229,0.1)]">
                <i class="fas fa-comment-alt text-4xl text-indigo-400"></i>
            </div>
            <h3 class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400 mb-2">
                Hello, ${Harvey.Config.username || 'User'}</h3>
            <div class="text-center text-gray-400 max-w-sm text-sm leading-relaxed">How can I assist you with your HR
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

    createMessageBubble: (sender, text) => {
        const container = document.createElement("div");
        container.classList.add("flex", "items-start", "gap-3", "animate-fade-in-up", "mb-4");

        const icon = document.createElement("div");
        icon.className = "w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold shadow-md";

        if (sender === "user") {
            container.classList.add("flex-row-reverse");
            icon.classList.add("bg-indigo-600", "text-white");
            icon.innerText = "ME";
        } else {
            icon.classList.add("bg-gradient-to-br", "from-indigo-500", "to-purple-600", "text-white");
            icon.innerHTML = '<i class="fas fa-robot"></i>';
        }

        const bubble = document.createElement("div");
        bubble.classList.add("p-4", "rounded-2xl", "max-w-2xl", "leading-relaxed", "text-sm", "shadow-sm");
        bubble.classList.add(sender === "user" ? "chat-bubble-user" : "chat-bubble-ai");
        if (sender === "user") bubble.classList.add("text-white");

        // Format Content
        let formatted = text.replace(/\n/g, '<br>');
        formatted = Harvey.Utils.linkify(formatted);
        bubble.innerHTML = formatted;

        container.appendChild(icon);
        container.appendChild(bubble);
        return container;
    },

    appendMessage: (sender, text) => {
        const bubble = Harvey.UI.createMessageBubble(sender, text);
        Harvey.DOM.chatBox.appendChild(bubble);
        Harvey.UI.scrollToBottom();
    },

    prependMessage: (sender, text) => {
        const bubble = Harvey.UI.createMessageBubble(sender, text);
        Harvey.DOM.chatBox.insertBefore(bubble, Harvey.DOM.chatBox.firstChild);
    },

    showThinkingBubble: () => {
        let bubble = Harvey.DOM.chatBox.querySelector('.thinking-bubble');
        if (!bubble) {
            bubble = document.createElement("div");
            bubble.className = "flex items-start gap-3 thinking-bubble animate-pulse mb-4";
            bubble.innerHTML = `
                <div class="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs shadow-md">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="chat-bubble-ai px-4 py-3 rounded-2xl flex gap-1 items-center h-10">
                        <div class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                        <div class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                        <div class="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce delay-200"></div>
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
            chip.className = "flex items-center gap-2 bg-indigo-500/20 border border-indigo-500/30 px-3 py-1.5 rounded-lg text-xs text-indigo-200 animate-fade-in";
            chip.innerHTML = `
                <i class="fas fa-file-alt"></i>
                <span class="max-w-[150px] truncate">${file.name}</span>
                <button onclick="Harvey.Upload.remove(${index})" class="hover:text-white transition-colors ml-1">
                    <i class="fas fa-times"></i>
                </button>
            `;
            previews.appendChild(chip);
        });
    }
};
