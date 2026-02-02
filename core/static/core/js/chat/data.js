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
            div.className = `p-3 rounded-lg cursor-pointer transition-colors text-sm flex items-center gap-3 overflow-visible group relative ${isActive ? 'bg-white/10 text-white' : 'text-gray-400 hover:text-white hover:bg-white/5'}`;
            div.onclick = (e) => {
                e.stopPropagation();
                // We reference the global Conversation object (defined in main.js or here, wait. main.js connects them usually but let's put logic here or in a Conversation module?
                // The monolithic script had a Conversation object. I should probably separate that too or put it in Data/Main.
                // Let's create a separate logic.js or put it in main.js. 
                // For now, I'll assume Harvey.Conversation exists (I'll add it to main.js or a new conversation.js)
                Harvey.Conversation.load(c.id);
            };

            const initials = c.title ? c.title.substring(0, 5).toUpperCase() : 'NC';
            // Kebab Menu Button
            const menuBtn = `
                <div class="ml-auto opacity-0 group-hover:opacity-100 sidebar-text transition-all duration-200">
                    <button class="p-1 px-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-md transition-colors" 
                        onclick="Harvey.Data.toggleMenu(event, '${c.id}', this)">
                        <i class="fas fa-ellipsis-v text-xs"></i>
                    </button>
                </div>
            `;

            div.innerHTML = `
                <div class="w-8 min-w-[2rem] flex items-center justify-center text-xs font-bold tracking-wide uppercase ${isActive ? 'text-indigo-400' : 'text-gray-500'}">
                    ${initials}
                </div>
                <span class="whitespace-nowrap truncate transition-opacity duration-200 sidebar-text opacity-100 font-medium flex-1">${c.title}</span>
                ${menuBtn}
            `;
            container.appendChild(div);
        });

        // Sync sidebar state
        if (Harvey.DOM.sidebar && !Harvey.DOM.sidebar.classList.contains('w-64')) {
            container.querySelectorAll('.sidebar-text').forEach(t => t.classList.add('opacity-0', 'pointer-events-none'));
        }
    },

    toggleMenu: (e, id, btn) => {
        e.stopPropagation();

        // Remove existing menu if any
        const existing = document.getElementById('harvey-context-menu');
        if (existing) existing.remove();

        // Calculate position (Global Fixed)
        const rect = btn.getBoundingClientRect();
        const top = rect.top;
        const left = rect.right + 10; // offset to right

        // Create Menu Element
        const menu = document.createElement('div');
        menu.id = 'harvey-context-menu';
        // Premium styling, fixed positioning, z-index 9999
        menu.className = 'fixed w-40 bg-[#1e293b] border border-gray-700/50 rounded-xl shadow-2xl z-[9999] overflow-hidden ring-1 ring-black/5 animate-in fade-in zoom-in-95 duration-100';
        menu.style.top = `${top}px`;
        menu.style.left = `${left}px`;

        // ONLY Delete button
        menu.innerHTML = `
            <div class="py-1">
                <button id="ctx-delete-btn" class="w-full text-left px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors flex items-center gap-3">
                    <i class="fas fa-trash-alt w-4 text-center"></i> Delete
                </button>
            </div>
        `;

        document.body.appendChild(menu);

        // Bind delete action
        document.getElementById('ctx-delete-btn').onclick = (ev) => Harvey.Data.deleteConversation(ev, id);

        // Auto-close handler
        const closeHandler = (ev) => {
            if (!menu.contains(ev.target)) {
                menu.remove();
                document.removeEventListener('click', closeHandler);
                window.removeEventListener('resize', closeHandler);
            }
        };
        // Delay adding listener
        setTimeout(() => {
            document.addEventListener('click', closeHandler);
            window.addEventListener('resize', closeHandler);
        }, 50);
    },

    deleteConversation: async (e, id) => {
        e.stopPropagation();

        Harvey.UI.showConfirmDialog("Delete this conversation forever?", async () => {
            try {
                const res = await fetch(`/api/conversations/${id}/delete/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': Harvey.Config.csrfToken
                    }
                });
                const data = await res.json();

                if (data.status === 'success') {
                    // If deleting active chat, clear state
                    if (Harvey.State.currentConversationId == id) {
                        Harvey.UI.clearChat();
                        Harvey.State.currentConversationId = null;
                        if (window.history.pushState) window.history.pushState({}, '', '/app/');
                    }
                    // Reload list
                    Harvey.Data.loadConversations();
                } else {
                    alert("Error: " + (data.error || "Failed to delete"));
                }
            } catch (err) {
                console.error(err);
                alert("Delete failed.");
            }
        });
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
