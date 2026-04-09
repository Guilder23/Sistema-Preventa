/* ============================================================================
   TEMA CLARO / OSCURO (GLOBAL)
   - Usa: html[data-theme]
   - Guarda preferencia en localStorage: 'theme' ('light' | 'dark')
   ============================================================================ */

(function () {
    const STORAGE_KEY = 'theme';

    // Gating por plan (inyectado desde base.html)
    const THEME_ALLOWED = (window.THEME_ALLOWED !== false);

    if (!THEME_ALLOWED) {
        try {
            localStorage.removeItem(STORAGE_KEY);
        } catch (e) {
            // ignore
        }
        document.documentElement.setAttribute('data-theme', 'light');
        return;
    }

    function isValidTheme(theme) {
        return theme === 'light' || theme === 'dark';
    }

    function getSystemTheme() {
        try {
            return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
                ? 'dark'
                : 'light';
        } catch (e) {
            return 'light';
        }
    }

    function getStoredTheme() {
        try {
            const theme = localStorage.getItem(STORAGE_KEY);
            return isValidTheme(theme) ? theme : null;
        } catch (e) {
            return null;
        }
    }

    function getCurrentTheme() {
        const attr = document.documentElement.getAttribute('data-theme');
        return isValidTheme(attr) ? attr : 'light';
    }

    function applyTheme(theme, persist = true) {
        const normalized = isValidTheme(theme) ? theme : 'light';
        document.documentElement.setAttribute('data-theme', normalized);

        if (persist) {
            try {
                localStorage.setItem(STORAGE_KEY, normalized);
            } catch (e) {
                // ignore
            }
        }

        updateToggleButton();
    }

    function updateToggleButton() {
        const btn = document.getElementById('themeToggleBtn');
        const icon = document.getElementById('themeToggleIcon');
        if (!btn || !icon) return;

        const theme = getCurrentTheme();
        const next = theme === 'dark' ? 'light' : 'dark';

        // En dark mostramos "sol" (para cambiar a claro). En light mostramos "luna".
        if (theme === 'dark') {
            icon.className = 'fas fa-sun';
            btn.title = 'Modo claro';
            btn.setAttribute('aria-label', 'Cambiar a modo claro');
            btn.setAttribute('data-next-theme', 'light');
        } else {
            icon.className = 'fas fa-moon';
            btn.title = 'Modo oscuro';
            btn.setAttribute('aria-label', 'Cambiar a modo oscuro');
            btn.setAttribute('data-next-theme', 'dark');
        }

        btn.setAttribute('data-theme', theme);
        btn.setAttribute('data-next', next);
    }

    function toggleTheme() {
        const current = getCurrentTheme();
        const next = current === 'dark' ? 'light' : 'dark';
        applyTheme(next, true);
    }

    function initThemeToggle() {
        updateToggleButton();

        const btn = document.getElementById('themeToggleBtn');
        if (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                toggleTheme();
            });
        }

        // Si el usuario no eligió manualmente, seguir el sistema.
        const stored = getStoredTheme();
        if (!stored && window.matchMedia) {
            try {
                const mq = window.matchMedia('(prefers-color-scheme: dark)');
                mq.addEventListener('change', function () {
                    const theme = getSystemTheme();
                    applyTheme(theme, false);
                });
            } catch (e) {
                // ignore
            }
        }
    }

    // Exponer utilidades por si se necesita en el futuro.
    window.Theme = {
        applyTheme,
        toggleTheme,
        getCurrentTheme,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initThemeToggle);
    } else {
        initThemeToggle();
    }
})();
