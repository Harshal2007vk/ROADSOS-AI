// ROADSoS AI - Theme Manager
(function () {
    // Apply theme immediately to prevent flash
    const stored = localStorage.getItem('roadsos-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = stored || (prefersDark ? 'dark' : 'light');
    if (theme === 'dark') document.documentElement.classList.add('dark');

    window.addEventListener('DOMContentLoaded', () => {
        const btn = document.getElementById('theme-toggle');
        if (!btn) return;

        btn.addEventListener('click', () => {
            const isDark = document.documentElement.classList.toggle('dark');
            localStorage.setItem('roadsos-theme', isDark ? 'dark' : 'light');
        });
    });
})();
