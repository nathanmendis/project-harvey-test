Harvey.Socket = {
    connect: () => {
        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        // Need to construct full URL
        const wsUrl = `${protocol}://${window.location.host}/ws/chat/`;

        Harvey.State.socket = new WebSocket(wsUrl);

        Harvey.State.socket.onmessage = Harvey.Socket.handleMessage;
        Harvey.State.socket.onclose = () => console.error("Socket closed unexpectedly.");
    },

    handleMessage: (e) => {
        const data = JSON.parse(e.data);
        const responseText = data.response;

        // Update ID if we just created a new one
        if (data.conversation_id && Harvey.State.currentConversationId !== data.conversation_id) {
            Harvey.State.currentConversationId = data.conversation_id;
            Harvey.Data.loadConversations();
        }

        Harvey.UI.removeWelcomeScreen();

        if (responseText === "Thinking...") {
            Harvey.UI.showThinkingBubble();
        } else {
            Harvey.UI.removeThinkingBubble();
            
            // Clean up any pending confirmation card loader and mark as executed
            const pendingLoaders = document.querySelectorAll('.confirm-card');
            pendingLoaders.forEach(card => {
                if (card.innerHTML.includes("Executing approved action...") || card.innerHTML.includes("Action cancelled.")) {
                    const isCancel = card.innerHTML.includes("Action cancelled.");
                    card.innerHTML = `
                        <div class="flex items-center gap-2 ${isCancel ? 'text-slate-400' : 'text-emerald-600'} text-xs font-bold py-1">
                            <i class="fas ${isCancel ? 'fa-circle-xmark' : 'fa-circle-check'}"></i>
                            <span>${isCancel ? 'Cancelled' : 'Approved & Executed'}</span>
                        </div>
                    `;
                }
            });

            Harvey.UI.appendMessage("ai", responseText, data.timestamp);
        }
    },


    send: (prompt) => {
        if (Harvey.State.socket && Harvey.State.socket.readyState === WebSocket.OPEN) {
            Harvey.State.socket.send(JSON.stringify({
                'prompt': prompt,
                'conversation_id': Harvey.State.currentConversationId
            }));
        } else {
            console.error("Socket not connected");
        }
    },

    sendConfirm: (toolName, buttonEl) => {
        const card = buttonEl.closest('.confirm-card');
        if (card.dataset.submitting === "true") return;
        card.dataset.submitting = "true";

        const inputs = card.querySelectorAll('.edit-field');
        const buttons = card.querySelectorAll('button');
        
        // Disable fields and buttons immediately
        inputs.forEach(input => input.disabled = true);
        buttons.forEach(button => button.disabled = true);

        const args = {};
        inputs.forEach(input => {
            args[input.name] = input.value;
        });
        
        if (Harvey.State.socket && Harvey.State.socket.readyState === WebSocket.OPEN) {
            Harvey.State.socket.send(JSON.stringify({
                'action': 'approve_tool',
                'arguments': args,
                'conversation_id': Harvey.State.currentConversationId
            }));
            
            // Show inline loader
            card.innerHTML = `
                <div class="py-4 text-center text-xs font-bold text-slate-500 flex items-center justify-center gap-2">
                    <div class="w-4 h-4 border-2 border-slate-200 border-t-indigo-600 rounded-full animate-spin"></div>
                    Executing approved action...
                </div>
            `;
            Harvey.UI.showThinkingBubble();
        }
    },

    sendCancel: (buttonEl) => {
        const card = buttonEl.closest('.confirm-card');
        if (card.dataset.submitting === "true") return;
        card.dataset.submitting = "true";

        const inputs = card.querySelectorAll('.edit-field');
        const buttons = card.querySelectorAll('button');
        
        inputs.forEach(input => input.disabled = true);
        buttons.forEach(button => button.disabled = true);

        if (Harvey.State.socket && Harvey.State.socket.readyState === WebSocket.OPEN) {
            Harvey.State.socket.send(JSON.stringify({
                'action': 'cancel_tool',
                'conversation_id': Harvey.State.currentConversationId
            }));
            
            card.innerHTML = `
                <div class="py-4 text-center text-xs font-bold text-slate-400">
                    Action cancelled.
                </div>
            `;
            Harvey.UI.showThinkingBubble();
        }
    }
};

