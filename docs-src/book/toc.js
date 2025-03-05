// Populate the sidebar
//
// This is a script, and not included directly in the page, to control the total size of the book.
// The TOC contains an entry for each page, so if each page includes a copy of the TOC,
// the total size of the page becomes O(n**2).
class MDBookSidebarScrollbox extends HTMLElement {
    constructor() {
        super();
    }
    connectedCallback() {
        this.innerHTML = '<ol class="chapter"><li class="chapter-item expanded "><a href="index.html"><strong aria-hidden="true">1.</strong> Introduction</a></li><li class="chapter-item expanded "><div><strong aria-hidden="true">2.</strong> Audio</div><a class="toggle"><div>❱</div></a></li><li><ol class="section"><li class="chapter-item "><a href="audio/audio_processor.html"><strong aria-hidden="true">2.1.</strong> audio_processor</a></li><li class="chapter-item "><a href="audio/audio_recorder.html"><strong aria-hidden="true">2.2.</strong> audio_recorder</a></li><li class="chapter-item "><a href="audio/continuous_recorder.html"><strong aria-hidden="true">2.3.</strong> continuous_recorder</a></li><li class="chapter-item "><a href="audio/neural_voice_client.html"><strong aria-hidden="true">2.4.</strong> neural_voice_client</a></li><li class="chapter-item "><a href="audio/resource_manager.html"><strong aria-hidden="true">2.5.</strong> resource_manager</a></li><li class="chapter-item "><a href="audio/speech_synthesis.html"><strong aria-hidden="true">2.6.</strong> speech_synthesis</a></li><li class="chapter-item "><a href="audio/trigger_detection.html"><strong aria-hidden="true">2.7.</strong> trigger_detection</a></li><li class="chapter-item "><a href="audio/voice_training.html"><strong aria-hidden="true">2.8.</strong> voice_training</a></li></ol></li><li class="chapter-item expanded "><div><strong aria-hidden="true">3.</strong> Config</div><a class="toggle"><div>❱</div></a></li><li><ol class="section"><li class="chapter-item "><a href="config/config.html"><strong aria-hidden="true">3.1.</strong> config</a></li></ol></li><li class="chapter-item expanded "><div><strong aria-hidden="true">4.</strong> Core</div><a class="toggle"><div>❱</div></a></li><li><ol class="section"><li class="chapter-item "><a href="core/core_dictation.html"><strong aria-hidden="true">4.1.</strong> core_dictation</a></li><li class="chapter-item "><a href="core/error_handler.html"><strong aria-hidden="true">4.2.</strong> error_handler</a></li><li class="chapter-item "><a href="core/logging_config.html"><strong aria-hidden="true">4.3.</strong> logging_config</a></li><li class="chapter-item "><a href="core/state_manager.html"><strong aria-hidden="true">4.4.</strong> state_manager</a></li></ol></li><li class="chapter-item expanded "><a href="daemon.html"><strong aria-hidden="true">5.</strong> daemon</a></li><li class="chapter-item expanded "><a href="permissions_check.html"><strong aria-hidden="true">6.</strong> permissions_check</a></li><li class="chapter-item expanded "><div><strong aria-hidden="true">7.</strong> Ui</div><a class="toggle"><div>❱</div></a></li><li><ol class="section"><li class="chapter-item "><a href="ui/toast_notifications.html"><strong aria-hidden="true">7.1.</strong> toast_notifications</a></li></ol></li><li class="chapter-item expanded "><div><strong aria-hidden="true">8.</strong> Utils</div><a class="toggle"><div>❱</div></a></li><li><ol class="section"><li class="chapter-item "><a href="utils/assistant.html"><strong aria-hidden="true">8.1.</strong> assistant</a></li><li class="chapter-item "><a href="utils/command_processor.html"><strong aria-hidden="true">8.2.</strong> command_processor</a></li><li class="chapter-item "><a href="utils/dictation.html"><strong aria-hidden="true">8.3.</strong> dictation</a></li><li class="chapter-item "><a href="utils/direct_typing.html"><strong aria-hidden="true">8.4.</strong> direct_typing</a></li><li class="chapter-item "><a href="utils/hotkey_manager.html"><strong aria-hidden="true">8.5.</strong> hotkey_manager</a></li><li class="chapter-item "><a href="utils/llm_interpreter.html"><strong aria-hidden="true">8.6.</strong> llm_interpreter</a></li><li class="chapter-item "><a href="utils/simple_dictation.html"><strong aria-hidden="true">8.7.</strong> simple_dictation</a></li><li class="chapter-item "><a href="utils/ultra_simple_dictation.html"><strong aria-hidden="true">8.8.</strong> ultra_simple_dictation</a></li></ol></li></ol>';
        // Set the current, active page, and reveal it if it's hidden
        let current_page = document.location.href.toString().split("#")[0];
        if (current_page.endsWith("/")) {
            current_page += "index.html";
        }
        var links = Array.prototype.slice.call(this.querySelectorAll("a"));
        var l = links.length;
        for (var i = 0; i < l; ++i) {
            var link = links[i];
            var href = link.getAttribute("href");
            if (href && !href.startsWith("#") && !/^(?:[a-z+]+:)?\/\//.test(href)) {
                link.href = path_to_root + href;
            }
            // The "index" page is supposed to alias the first chapter in the book.
            if (link.href === current_page || (i === 0 && path_to_root === "" && current_page.endsWith("/index.html"))) {
                link.classList.add("active");
                var parent = link.parentElement;
                if (parent && parent.classList.contains("chapter-item")) {
                    parent.classList.add("expanded");
                }
                while (parent) {
                    if (parent.tagName === "LI" && parent.previousElementSibling) {
                        if (parent.previousElementSibling.classList.contains("chapter-item")) {
                            parent.previousElementSibling.classList.add("expanded");
                        }
                    }
                    parent = parent.parentElement;
                }
            }
        }
        // Track and set sidebar scroll position
        this.addEventListener('click', function(e) {
            if (e.target.tagName === 'A') {
                sessionStorage.setItem('sidebar-scroll', this.scrollTop);
            }
        }, { passive: true });
        var sidebarScrollTop = sessionStorage.getItem('sidebar-scroll');
        sessionStorage.removeItem('sidebar-scroll');
        if (sidebarScrollTop) {
            // preserve sidebar scroll position when navigating via links within sidebar
            this.scrollTop = sidebarScrollTop;
        } else {
            // scroll sidebar to current active section when navigating via "next/previous chapter" buttons
            var activeSection = document.querySelector('#sidebar .active');
            if (activeSection) {
                activeSection.scrollIntoView({ block: 'center' });
            }
        }
        // Toggle buttons
        var sidebarAnchorToggles = document.querySelectorAll('#sidebar a.toggle');
        function toggleSection(ev) {
            ev.currentTarget.parentElement.classList.toggle('expanded');
        }
        Array.from(sidebarAnchorToggles).forEach(function (el) {
            el.addEventListener('click', toggleSection);
        });
    }
}
window.customElements.define("mdbook-sidebar-scrollbox", MDBookSidebarScrollbox);
