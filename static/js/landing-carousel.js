/* The unenhanced carousel remains a native, scrollable list. */
(() => {
    const viewport = document.querySelector('.places-carousel');
    const track = viewport?.querySelector('.places-grid');
    const controls = document.querySelector('.carousel-controls');
    if (!viewport || !track || !controls) return;

    const toggle = controls.querySelector('[data-carousel-toggle]');
    const prev = controls.querySelector('[data-carousel-prev]');
    const next = controls.querySelector('[data-carousel-next]');
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const originals = Array.from(track.children);
    let loop = 0;
    let span = 0;
    let playing = !motion.matches;
    let hovering = false;
    let focusing = false;
    let touching = false;
    let visible = true;
    let lastTime = 0;
    let fraction = 0;

    function updateToggle() {
        toggle.textContent = playing ? 'Pause' : 'Play';
        toggle.setAttribute('aria-pressed', String(playing));
        toggle.setAttribute('aria-label', playing ? 'Pause places carousel' : 'Play places carousel');
        toggle.hidden = motion.matches;
    }

    function setup() {
        track.querySelectorAll('[data-carousel-clone]').forEach(clone => clone.remove());
        viewport.classList.remove('is-looping');
        loop = 0;
        viewport.scrollLeft = 0;
        if (!originals.length) return;
        span = originals[0].getBoundingClientRect().width + (parseFloat(getComputedStyle(track).gap) || 0);
        if (originals.length < 2 || track.scrollWidth <= viewport.clientWidth + 1) {
            controls.hidden = true;
            return;
        }
        controls.hidden = false;
        // Duplicate only the prefix needed to cover the viewport at the wrap.
        const cloneCount = Math.min(originals.length, Math.ceil(viewport.clientWidth / span) + 1);
        for (let index = 0; index < cloneCount; index++) {
            const clone = originals[index].cloneNode(true);
            clone.dataset.carouselClone = 'true';
            clone.setAttribute('aria-hidden', 'true');
            clone.querySelectorAll('a, button, input, select, textarea').forEach(item => item.tabIndex = -1);
            track.appendChild(clone);
        }
        loop = track.querySelector('[data-carousel-clone]').offsetLeft - originals[0].offsetLeft;
        viewport.classList.add('is-looping');
        updateToggle();
    }

    function frame(time) {
        const elapsed = lastTime ? Math.min(time - lastTime, 50) : 0;
        lastTime = time;
        if (loop && playing && !motion.matches && !hovering && !focusing && !touching && visible && !document.hidden) {
            fraction += elapsed * 0.03;
            const step = Math.floor(fraction);
            if (step) {
                fraction -= step;
                viewport.scrollLeft += step;
                if (viewport.scrollLeft >= loop) viewport.scrollLeft -= loop;
            }
        }
        requestAnimationFrame(frame);
    }

    function step(direction) {
        if (!loop) return;
        viewport.scrollLeft = (viewport.scrollLeft + direction * span + loop) % loop;
    }

    viewport.addEventListener('scroll', () => {
        if (loop && viewport.scrollLeft >= loop) viewport.scrollLeft -= loop;
    });
    toggle.addEventListener('click', () => { playing = !playing; updateToggle(); });
    prev.addEventListener('click', () => step(-1));
    next.addEventListener('click', () => step(1));
    viewport.addEventListener('pointerenter', event => { if (event.pointerType !== 'touch') hovering = true; });
    viewport.addEventListener('pointerleave', () => { hovering = false; touching = false; });
    viewport.addEventListener('pointerdown', () => { touching = true; });
    window.addEventListener('pointerup', () => { touching = false; });
    window.addEventListener('pointercancel', () => { touching = false; });
    viewport.addEventListener('focusin', () => { focusing = true; });
    viewport.addEventListener('focusout', event => { if (!viewport.contains(event.relatedTarget)) focusing = false; });
    motion.addEventListener('change', () => { if (motion.matches) playing = false; updateToggle(); });
    if ('IntersectionObserver' in window) {
        new IntersectionObserver(entries => { visible = entries[0].isIntersecting; }).observe(viewport);
    }
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(setup, 150);
    });
    setup();
    requestAnimationFrame(frame);
})();
