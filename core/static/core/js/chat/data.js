Harvey.Data = {
    loadConversations: async () => {
        try {
            const res = await fetch(Harvey.Config.urls.conversations);
            const data = await res.json();
            Harvey.Data.renderList(data.conversations);
        } catch (e) {
            console.error("Failed to load conversations:", e);
        }
    },

    renderList: (conversations) => {
        const container = Harvey.DOM.conversationList;
        if (!container) return;

        container.innerHTML = '';
        conversations.forEach(c => {
            const div = document.createElement('div');
            const isActive = Harvey.State.currentConversationId === c.id;
            div.className = `p-3 rounded-lg cursor-pointer transition-colors text-sm flex items-center gap-3 overflow-hidden ${isActive ? 'bg-white/10 text-white' : 'text-gray-400 hover:text-white hover:bg-white/5'}`;
            div.onclick = (e) => {
                e.stopPropagation();
                // We reference the global Conversation object (defined in main.js or here, wait. main.js connects them usually but let's put logic here or in a Conversation module?
                // The monolithic script had a Conversation object. I should probably separate that too or put it in Data/Main.
                // Let's create a separate logic.js or put it in main.js. 
                // For now, I'll assume Harvey.Conversation exists (I'll add it to main.js or a new conversation.js)
                Harvey.Conversation.load(c.id);
            };

            const initials = c.title ? c.title.substring(0, 5).toUpperCase() : 'NC';
            div.innerHTML = `
                <div class="w-8 min-w-[2rem] flex items-center justify-center text-xs font-bold tracking-wide uppercase ${isActive ? 'text-indigo-400' : 'text-gray-500'}">
                    ${initials}
                </div>
                <span class="whitespace-nowrap truncate transition-opacity duration-200 sidebar-text opacity-100 font-medium">${c.title}</span>
            `;
            container.appendChild(div);
        });

        // Sync sidebar state
        if (Harvey.DOM.sidebar && !Harvey.DOM.sidebar.classList.contains('w-64')) {
            container.querySelectorAll('.sidebar-text').forEach(t => t.classList.add('opacity-0'));
        }
    },

    fetchMessages: async (id, offset) => {
        if (Harvey.State.isLoadingHistory && offset > 0) return;
        Harvey.State.isLoadingHistory = true;

        try {
            if (offset > 0) Harvey.UI.showLoader();

            const res = await fetch(`/api/conversations/${id}/messages/?limit=20&offset=${offset}`);
            const data = await res.json();

            if (offset === 0) {
                Harvey.UI.clearChat();
                // Special check: do not remove welcome placeholder here, handle logic in UI
            } else {
                Harvey.UI.hideLoader();
            }

            // Render Messages
            // data.messages is Oldest -> Newest
            const renderAction = () => {
                data.messages.forEach(msg => {
                    if (offset > 0) {
                        Harvey.UI.prependMessage(msg.sender, msg.text);
                    } else {
                        Harvey.UI.appendMessage(msg.sender, msg.text);
                    }
                });
            };

            if (offset > 0) {
                Harvey.UI.maintainScroll(renderAction);
            } else {
                renderAction();
                Harvey.UI.scrollToBottom();
            }

            Harvey.State.hasMoreHistory = data.has_more;
            Harvey.State.messageOffset = offset + data.messages.length;

        } catch (e) {
            console.error("Error fetching messages:", e);
        } finally {
            Harvey.State.isLoadingHistory = false;
        }
    }
};
