Harvey.Sidebar = {
    toggle: () => {
        const sidebar = Harvey.DOM.sidebar;
        if (!sidebar) return;

        const isMobile = window.innerWidth < 768;
        const texts = sidebar.querySelectorAll('.sidebar-text');

        if (isMobile) {
            sidebar.classList.toggle('-translate-x-full');
            Harvey.DOM.sidebarOverlay.classList.toggle('hidden');
        } else {
            if (sidebar.classList.contains('w-64')) {
                // Collapse
                sidebar.classList.remove('w-64');
                sidebar.classList.add('w-20');
                texts.forEach(el => el.classList.add('opacity-0', 'w-0', 'p-0', 'm-0', 'overflow-hidden'));
            } else {
                // Expand
                sidebar.classList.add('w-64');
                sidebar.classList.remove('w-20');
                texts.forEach(el => {
                    el.classList.remove('opacity-0', 'w-0', 'p-0', 'm-0', 'overflow-hidden');
                    el.classList.add('opacity-100');
                });
            }
        }
    },

    closeMobile: () => {
        const sidebar = Harvey.DOM.sidebar;
        if (window.innerWidth < 768 && sidebar && !sidebar.classList.contains('-translate-x-full')) {
            Harvey.Sidebar.toggle();
        }
    },

    handleClick: (e) => {
        const sidebar = Harvey.DOM.sidebar;
        const interactive = e.target.closest('button') || e.target.closest('.cursor-pointer');

        if (interactive && interactive !== sidebar) {
            if (sidebar.classList.contains('w-64')) return;
        }
        Harvey.Sidebar.toggle();
    }
};
