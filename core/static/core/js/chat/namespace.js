window.Harvey = window.Harvey || {};

Harvey.Config = {
    // Will be populated from the HTML template
    csrfToken: null,
    username: null,
    urls: {
        chatWs: null,
        conversations: '/api/conversations/',
        uploadResume: '/upload_resume/'
    }
};

Harvey.State = {
    attachedFiles: [],
    currentConversationId: null,
    messageOffset: 0,
    hasMoreHistory: false,
    isLoadingHistory: false,
    socket: null
};

Harvey.DOM = {
    // Getters to ensure elements are available when accessed
    get sendBtn() { return document.getElementById("send-btn"); },
    get userInput() { return document.getElementById("user-input"); },
    get chatBox() { return document.getElementById("chat-box"); },
    get sidebar() { return document.getElementById('chat-sidebar'); },
    get sidebarOverlay() { return document.getElementById('sidebar-overlay'); },
    get conversationList() { return document.getElementById('conversation-list'); },
    get filePreviews() { return document.getElementById("file-previews"); },
    get uploadBtn() { return document.getElementById("upload-btn"); },
    get resumeUpload() { return document.getElementById("resume-upload"); },
    get userMenuBtn() { return document.getElementById('user-menu-btn'); },
    get userDropdown() { return document.getElementById('user-dropdown'); },
    get menuArrow() { return document.getElementById('menu-arrow'); },
    get userMenuContainer() { return document.getElementById('user-menu-container'); }
};
