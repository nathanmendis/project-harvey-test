Harvey.Upload = {
    init: () => {
        const btn = Harvey.DOM.uploadBtn;
        const input = Harvey.DOM.resumeUpload;
        if (btn && input) {
            btn.addEventListener("click", () => input.click());
            input.addEventListener("change", Harvey.Upload.handleFile);
        }
    },

    handleFile: function () {
        if (this.files && this.files[0]) {
            const file = this.files[0];
            const formData = new FormData();
            formData.append("resume", file);

            const btn = Harvey.DOM.uploadBtn;
            const originalIcon = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin text-indigo-400"></i>';
            btn.disabled = true;

            fetch(Harvey.Config.urls.uploadResume, {
                method: "POST",
                body: formData,
                headers: { "X-CSRFToken": Harvey.Config.csrfToken }
            })
                .then(r => r.json())
                .then(data => {
                    if (data.file_path) {
                        Harvey.State.attachedFiles.push({ name: data.filename || file.name, path: data.file_path });
                        Harvey.UI.renderAttachments();
                        Harvey.DOM.userInput.focus();
                    } else {
                        alert("Upload failed: " + (data.error || "Unknown error"));
                    }
                })
                .catch(e => { console.error(e); alert("Upload error"); })
                .finally(() => {
                    btn.innerHTML = originalIcon;
                    btn.disabled = false;
                    Harvey.DOM.resumeUpload.value = "";
                });
        }
    },

    remove: (index) => {
        Harvey.State.attachedFiles.splice(index, 1);
        Harvey.UI.renderAttachments();
    }
};
