document.addEventListener('DOMContentLoaded', () => {
    // Initial scroll animation
    const featuresHeader = document.getElementById('features-header');
    const featuresContainer = document.getElementById('features-container');
    const featuresContent = document.getElementById('features-content');
    const beamMobile = document.getElementById('features-beam-mobile');
    const beamDesktop = document.getElementById('features-beam-desktop');

    if (!featuresHeader || !featuresContainer || !featuresContent) {
        return; // Avoid errors if the elements aren't correctly loaded
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                featuresHeader.classList.remove('opacity-0', 'translate-y-8');
                featuresContainer.firstElementChild.classList.remove('opacity-0', '-translate-x-8');
                featuresContent.classList.remove('opacity-0', 'translate-x-8');

                // Fire the beam!
                if (beamDesktop) beamDesktop.style.height = '100%';
                if (beamMobile) beamMobile.style.width = '100%';

                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15 });

    observer.observe(document.getElementById('features'));

    // Tab Switching Logic Attached to Window
    window.switchFeatureTab = function (index) {
        let i = 0;
        while (true) {
            const btn = document.getElementById(`tab-btn-${i}`);
            const content = document.getElementById(`tab-content-${i}`);

            if (!btn || !content) break;

            const iconContainer = btn.querySelector('div:first-of-type');

            if (i === index) {
                // Activate btn
                btn.classList.add('bg-indigo-50', 'border-indigo-200', 'shadow-sm', 'text-indigo-900');
                btn.classList.remove('bg-white', 'border-slate-200', 'text-slate-600');

                // Activate icon styling
                if (iconContainer) {
                    iconContainer.classList.add('bg-indigo-100', 'text-indigo-600', 'scale-110');
                    iconContainer.classList.remove('bg-slate-100', 'text-slate-400');
                }

                // Show content
                content.classList.remove('opacity-0', 'pointer-events-none', 'translate-y-4', 'scale-95');
                content.classList.add('opacity-100', 'translate-y-0', 'scale-100');
                content.style.zIndex = '10'; // Bring to front
            } else {
                // Deactivate btn
                btn.classList.remove('bg-indigo-50', 'border-indigo-200', 'shadow-sm', 'text-indigo-900');
                btn.classList.add('bg-white', 'border-slate-200', 'text-slate-600');

                // Deactivate icon styling
                if (iconContainer) {
                    iconContainer.classList.remove('bg-indigo-100', 'text-indigo-600', 'scale-110');
                    iconContainer.classList.add('bg-slate-100', 'text-slate-400');
                }

                // Hide content
                content.classList.add('opacity-0', 'pointer-events-none', 'translate-y-4', 'scale-95');
                content.classList.remove('opacity-100', 'translate-y-0', 'scale-100');
                content.style.zIndex = '0'; // Send back
            }
            i++;
        }
    };
});
