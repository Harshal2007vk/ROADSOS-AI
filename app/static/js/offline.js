// ROADSoS AI - Offline Status Manager
(function () {
    const indicator = document.getElementById('offline-indicator');

    function updateStatus() {
        if (!indicator) return;
        if (!navigator.onLine) {
            indicator.classList.remove('hidden');
        } else {
            indicator.classList.add('hidden');
        }
    }

    window.addEventListener('online', updateStatus);
    window.addEventListener('offline', updateStatus);
    window.addEventListener('DOMContentLoaded', updateStatus);
})();
