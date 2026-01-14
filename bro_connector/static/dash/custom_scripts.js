(function trackActiveElement() {

    document.lastActiveElement = undefined;

    document.addEventListener("focusout", function (focusEvent) {
        var target = focusEvent.target;
        document.lastActiveElement = target
    })

}())

// Synchronize scrolling between the two corrections DataTables
(function syncCorrectionsTables() {
    const TABLE1_ID = "corrections-observations-table-1";
    const TABLE2_ID = "corrections-observations-table-2";

    function findScrollContainer(el) {
        if (!el) return null;
        // Dash DataTable renders a nested structure; the spreadsheet container is scrollable
        // Fallback to the element itself if we cannot find the inner container
        return el.querySelector('.dash-spreadsheet-container') || el;
    }

    let bound = false;
    let handlersBound = false;

    function bindIfReady() {
        const t1 = document.getElementById(TABLE1_ID);
        const t2 = document.getElementById(TABLE2_ID);
        if (!t1 || !t2) return; // tables not yet in DOM

        const s1 = findScrollContainer(t1);
        const s2 = findScrollContainer(t2);
        if (!s1 || !s2) return; // scroll containers not found yet

        if (s1.dataset.scrollSyncBound === 'true' && s2.dataset.scrollSyncBound === 'true') {
            bound = true;
            return;
        }

        let syncing = false;

        function mirrorScroll(src, dst) {
            src.addEventListener('scroll', function () {
                if (syncing) return;
                syncing = true;
                try {
                    dst.scrollTop = src.scrollTop;
                    dst.scrollLeft = src.scrollLeft;
                } finally {
                    // Allow next scroll in next frame to avoid feedback loops
                    window.requestAnimationFrame(function () { syncing = false; });
                }
            }, { passive: true });
        }

        mirrorScroll(s1, s2);
        mirrorScroll(s2, s1);
        s1.dataset.scrollSyncBound = 'true';
        s2.dataset.scrollSyncBound = 'true';

        bound = true;
        handlersBound = true;
    }

    // Attempt to bind after initial load and when Dash updates the DOM
    document.addEventListener('DOMContentLoaded', bindIfReady);
    window.addEventListener('load', bindIfReady);

    // Periodically attempt binding until successful (covers async component renders)
    const intervalId = setInterval(function () {
        if (bound) return;
        bindIfReady();
    }, 500);

    // React to DOM mutations to re-bind if tables are re-rendered
    const observer = new MutationObserver(function () {
        // Reset and try again on significant DOM changes
        bound = false;
        bindIfReady();
        if (handlersBound && bound) {
            // Once bound again, we can keep observing for further changes
            return;
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
}());