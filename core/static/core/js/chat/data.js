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
            div.className = `p-3 rounded-xl cursor-pointer transition-all duration-200 text-sm flex items-center gap-3 overflow-visible group relative mb-0.5 ${isActive ? 'bg-indigo-50 text-indigo-700 border border-indigo-100/50 shadow-sm' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50 hover:shadow-sm'}`;
            
            // Conversation click handler
            div.addEventListener('click', (e) => {
                // Prevent switching if we are clicking the menu button
                if (e.target.closest('.kebab-menu-container')) return;
                Harvey.Conversation.load(c.id);
            });

            const initials = c.title ? c.title.substring(0, 5).toUpperCase() : 'NC';
            
            div.innerHTML = `
                <div class="w-10 min-w-[2.5rem] flex-shrink-0 flex items-center justify-start text-[10px] font-black tracking-widest uppercase truncate ${isActive ? 'text-indigo-600' : 'text-slate-400'}">
                    ${initials}
                </div>
                <span class="whitespace-nowrap truncate transition-opacity duration-200 sidebar-text opacity-100 font-medium flex-1">${c.title}</span>
                <div class="kebab-menu-container ml-auto opacity-0 group-hover:opacity-100 sidebar-text transition-all duration-200 flex-shrink-0">
                    <button class="kebab-button p-1 px-2 text-slate-400 hover:text-slate-900 hover:bg-slate-200/50 rounded-md transition-colors">
                        <i class="fas fa-ellipsis-v text-xs"></i>
                    </button>
                </div>
            `;

            // Menu button handler
            const kBtn = div.querySelector('.kebab-button');
            kBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                Harvey.Data.toggleMenu(e, c.id, kBtn);
            });

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
        menu.className = 'fixed w-48 bg-white/95 backdrop-blur-xl border border-slate-200 rounded-2xl shadow-2xl z-[9999] overflow-hidden ring-1 ring-slate-400/5 animate-in fade-in zoom-in-95 duration-100';
        menu.style.top = `${top}px`;
        menu.style.left = `${left}px`;

        // ONLY Delete button
        menu.innerHTML = `
            <div class="py-1">
                <button id="ctx-delete-btn" class="w-full text-left px-5 py-3 text-sm font-bold text-red-500 hover:bg-red-50 hover:text-red-600 transition-colors flex items-center gap-3">
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

        // Remove menu immediately
        document.getElementById('harvey-context-menu')?.remove();

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
            // Render Messages
            // data.messages is Oldest -> Newest
            const renderAction = () => {
                data.messages.forEach((msg, idx) => {
                    if (offset > 0) {
                        Harvey.UI.prependMessage(msg.sender, msg.text, msg.timestamp);
                    } else {
                        const isLatest = (idx === data.messages.length - 1);
                        Harvey.UI.appendMessage(msg.sender, msg.text, msg.timestamp, isLatest);
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

            // If we have reached the end of history (no more messages), render start time
            // Use the created_at from API (which we added)
            if (!data.has_more && data.created_at) {
                Harvey.UI.renderConversationStart(data.created_at);
            }

        } catch (e) {
            console.error("Error fetching messages:", e);
        } finally {
            Harvey.State.isLoadingHistory = false;
        }
    }
};
