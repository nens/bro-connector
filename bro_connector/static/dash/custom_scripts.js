(function trackActiveElement() {

    document.lastActiveElement = undefined;

    document.addEventListener("focusout", function (focusEvent) {
        var target = focusEvent.target;
        document.lastActiveElement = target
    })

}())

// Synchronize scrolling between the two corrections DataTables (supports virtualization)
(function syncCorrectionsTables() {
    const TABLE_IDS = [
        "corrections-observations-table-1",
        "corrections-observations-table-2",
    ];

    // Minimal debug surface for console checks
    window.gwdlCorrectionsSync = {
        attached: false,
        lastCheck: null,
        lastAttached: null,
    };

    function findScrollable(el) {
        if (!el) return null;
        const selectors = [
            ".dash-spreadsheet-container",
            ".dash-virtualized",
            ".dash-spreadsheet-inner",
        ];
        for (const sel of selectors) {
            const cand = el.querySelector(sel);
            if (cand && cand.scrollHeight > cand.clientHeight) return cand;
        }
        // Fallback: breadth-first search for any scrollable child
        const queue = Array.from(el.children);
        while (queue.length) {
            const node = queue.shift();
            const style = window.getComputedStyle(node);
            const overflowY = style.getPropertyValue("overflow-y");
            if (
                (overflowY === "auto" || overflowY === "scroll") &&
                node.scrollHeight > node.clientHeight
            ) {
                return node;
            }
            queue.push(...Array.from(node.children));
        }
        return null;
    }

    function getScroller(id) {
        const table = document.getElementById(id);
        if (!table) return null;
        return findScrollable(table);
    }

    function attachIfReady() {
        window.gwdlCorrectionsSync.lastCheck = Date.now();
        const scrollerA = getScroller(TABLE_IDS[0]);
        const scrollerB = getScroller(TABLE_IDS[1]);

        if (!scrollerA || !scrollerB) return;

        if (scrollerA.dataset.scrollSyncBound === "true") {
            window.gwdlCorrectionsSync.attached = true;
            return;
        }

        let syncing = false;
        let scrollEndTimeoutId = null;
        const SCROLL_END_DELAY = 150; // Wait for scroll to finish

        const sync = (from, to) => {
            from.addEventListener(
                "scroll",
                () => {
                    if (syncing) return;

                    // Clear any pending sync - wait for scrolling to stop
                    if (scrollEndTimeoutId !== null) {
                        clearTimeout(scrollEndTimeoutId);
                    }

                    // Only sync after user has stopped scrolling
                    scrollEndTimeoutId = setTimeout(() => {
                        syncing = true;
                        requestAnimationFrame(() => {
                            to.scrollTop = from.scrollTop;
                            to.scrollLeft = from.scrollLeft;

                            // Allow next sync after a brief moment
                            setTimeout(() => {
                                syncing = false;
                                scrollEndTimeoutId = null;
                            }, 100);
                        });
                    }, SCROLL_END_DELAY);
                },
                { passive: true }
            );
        };

        sync(scrollerA, scrollerB);
        sync(scrollerB, scrollerA);
        scrollerA.dataset.scrollSyncBound = "true";
        scrollerB.dataset.scrollSyncBound = "true";
        window.gwdlCorrectionsSync.attached = true;
        window.gwdlCorrectionsSync.lastAttached = Date.now();
    }

    // Bind on load and keep retrying for dynamic renders
    document.addEventListener("DOMContentLoaded", attachIfReady);
    window.addEventListener("load", attachIfReady);
    setInterval(attachIfReady, 400);

    // Re-attach on DOM changes (Dash re-renders)
    const observer = new MutationObserver(() => {
        // If tables were recreated, drop the bound flag so we can rebind
        const scrollerA = getScroller(TABLE_IDS[0]);
        const scrollerB = getScroller(TABLE_IDS[1]);
        if (scrollerA) delete scrollerA.dataset.scrollSyncBound;
        if (scrollerB) delete scrollerB.dataset.scrollSyncBound;
        window.gwdlCorrectionsSync.attached = false;
        attachIfReady();
    });
    observer.observe(document.body, { childList: true, subtree: true });
}());