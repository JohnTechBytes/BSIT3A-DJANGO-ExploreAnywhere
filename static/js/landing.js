/* Progressive enhancement: content remains visible without JavaScript. */
(() => {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (reducedMotion.matches || !('IntersectionObserver' in window)) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.08 });

    const targets = document.querySelectorAll(
        '.section-heading, .place-card, .steps > div, .workflow > h2, .discovery-stats'
    );
    targets.forEach((target, index) => {
        // Never hide content already reached by keyboard or fragment navigation.
        if (target.getBoundingClientRect().top <= window.innerHeight) return;
        target.style.setProperty('--reveal-delay', `${(index % 3) * 70}ms`);
        target.classList.add('reveal-ready');
        observer.observe(target);
        target.addEventListener('focusin', () => {
            target.classList.add('is-visible');
            observer.unobserve(target);
        });
    });

    reducedMotion.addEventListener('change', (event) => {
        if (event.matches) {
            observer.disconnect();
            targets.forEach((target) => target.classList.remove('reveal-ready'));
        }
    });
})();
