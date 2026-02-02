Harvey.Conversation = {
    startNew: () => {
        Harvey.State.currentConversationId = null;
        Harvey.State.messageOffset = 0;
        Harvey.State.hasMoreHistory = false;
        Harvey.UI.clearChat();
        Harvey.UI.renderWelcomeScreen();
        Harvey.Data.loadConversations();
        Harvey.Sidebar.closeMobile();
    },

    load: async (id) => {
        Harvey.State.currentConversationId = id;
        Harvey.State.messageOffset = 0;
        Harvey.State.hasMoreHistory = false;
        Harvey.UI.clearChat();
        Harvey.Sidebar.closeMobile();

        await Harvey.Data.fetchMessages(id, 0);
        Harvey.Data.loadConversations();
    }
};

Harvey.Main = {
    sendMessage: () => {
        const input = Harvey.DOM.userInput;
        let prompt = input.value.trim();

        // Append file info
        if (Harvey.State.attachedFiles.length > 0) {
            const constraints = Harvey.State.attachedFiles.map(f => ` [Attached Resume: ${f.path}]`).join(" ");
            prompt += constraints;
        }

        if (!prompt && Harvey.State.attachedFiles.length === 0) return;

        Harvey.UI.removeWelcomeScreen();

        // Optimistic Update
        const displayPrompt = input.value.trim() || (Harvey.State.attachedFiles.length > 0 ? `Sent ${Harvey.State.attachedFiles.length} file(s)...` : "...");
        Harvey.UI.appendMessage("user", displayPrompt);

        input.value = "";
        Harvey.State.attachedFiles = [];
        Harvey.UI.renderAttachments();

        Harvey.Socket.send(prompt);
    },

    initListeners: () => {
        const sendBtn = Harvey.DOM.sendBtn;
        const userInput = Harvey.DOM.userInput;
        const chatBox = Harvey.DOM.chatBox;

        if (sendBtn) sendBtn.addEventListener("click", Harvey.Main.sendMessage);
        if (userInput) userInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") Harvey.Main.sendMessage();
        });

        // Infinite Scroll
        if (chatBox) chatBox.addEventListener('scroll', () => {
            if (chatBox.scrollTop === 0 && Harvey.State.hasMoreHistory && !Harvey.State.isLoadingHistory && Harvey.State.currentConversationId) {
                Harvey.Data.fetchMessages(Harvey.State.currentConversationId, Harvey.State.messageOffset);
            }
        });

        // Dropdown
        const menuBtn = Harvey.DOM.userMenuBtn;
        const dropdown = Harvey.DOM.userDropdown;

        if (menuBtn && dropdown) {
            menuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isHidden = dropdown.classList.contains('hidden');
                if (isHidden) {
                    dropdown.classList.remove('hidden');
                    requestAnimationFrame(() => {
                        dropdown.classList.remove('opacity-0', 'scale-95');
                        dropdown.classList.add('opacity-100', 'scale-100');
                        Harvey.DOM.menuArrow?.classList.add('rotate-180');
                    });
                } else {
                    Harvey.Main.closeDropdown();
                }
            });
            document.addEventListener('click', (e) => {
                if (Harvey.DOM.userMenuContainer && !Harvey.DOM.userMenuContainer.contains(e.target)) {
                    Harvey.Main.closeDropdown();
                }
            });
        }
    },

    closeDropdown: () => {
        const dropdown = Harvey.DOM.userDropdown;
        if (!dropdown) return;
        dropdown.classList.remove('opacity-100', 'scale-100');
        dropdown.classList.add('opacity-0', 'scale-95');
        Harvey.DOM.menuArrow?.classList.remove('rotate-180');
        setTimeout(() => dropdown.classList.add('hidden'), 200);
    },

    init: () => {
        Harvey.Socket.connect();
        Harvey.Upload.init();
        Harvey.Main.initListeners();
        Harvey.Data.loadConversations();
    }
};

// Boot
document.addEventListener("DOMContentLoaded", () => {
    Harvey.Main.init();
});

// Global Bindings for HTML onclick events
window.toggleSidebar = Harvey.Sidebar.toggle;
window.handleSidebarClick = Harvey.Sidebar.handleClick;
window.startNewChat = Harvey.Conversation.startNew;
window.removeAttachment = Harvey.Upload.remove;
