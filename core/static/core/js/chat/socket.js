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
    }
};
