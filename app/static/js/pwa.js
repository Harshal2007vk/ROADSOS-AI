// ROADSoS AI - PWA Install Prompt Manager
(function () {
    let deferredPrompt = null;
    const prompt = document.getElementById('pwa-install-prompt');
    const installBtn = document.getElementById('pwa-install-btn');
    const dismissBtn = document.getElementById('pwa-dismiss-btn');

    // Capture the install event
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;

        // Only show if not dismissed before
        if (!localStorage.getItem('pwa-dismissed')) {
            setTimeout(() => prompt?.classList.remove('hidden'), 3000);
        }
    });

    installBtn?.addEventListener('click', async () => {
        if (!deferredPrompt) return;
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        if (outcome === 'accepted') localStorage.setItem('pwa-installed', 'true');
        deferredPrompt = null;
        prompt?.classList.add('hidden');
    });

    dismissBtn?.addEventListener('click', () => {
        prompt?.classList.add('hidden');
        localStorage.setItem('pwa-dismissed', 'true');
    });

    // Detect standalone mode
    if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone) {
        document.body.classList.add('pwa-mode');
    }
})();
