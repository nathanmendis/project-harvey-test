Harvey.Utils = {
    /**
     * Converts URLs in text to clickable links.
     */
    linkify: function (text) {
        const urlRegex = /(\b(https?|ftp|file):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/ig;
        return text.replace(urlRegex, (url) => {
            return `<a href="${url}" target="_blank" class="text-harvey-primary hover:text-white hover:underline underline-offset-2 break-all font-medium transition-colors">${url}</a>`;
        });
    }
};
