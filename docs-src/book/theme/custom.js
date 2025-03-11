/* Custom JavaScript for Whisper Voice Control Documentation */

// Wait for the document to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add version badge to the header
    const header = document.querySelector('.menu-title');
    if (header) {
        const versionBadge = document.createElement('span');
        versionBadge.className = 'version-badge';
        versionBadge.textContent = 'v1.0';
        versionBadge.style.fontSize = '0.7em';
        versionBadge.style.padding = '2px 5px';
        versionBadge.style.backgroundColor = '#eef';
        versionBadge.style.borderRadius = '3px';
        versionBadge.style.marginLeft = '10px';
        header.appendChild(versionBadge);
    }

    // Enhance code blocks with copy button
    const codeBlocks = document.querySelectorAll('pre');
    codeBlocks.forEach(function(block) {
        // Create copy button
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-button';
        copyButton.textContent = 'Copy';
        copyButton.style.position = 'absolute';
        copyButton.style.top = '5px';
        copyButton.style.right = '5px';
        copyButton.style.padding = '3px 8px';
        copyButton.style.fontSize = '0.8em';
        copyButton.style.backgroundColor = '#f8f8f8';
        copyButton.style.border = '1px solid #ddd';
        copyButton.style.borderRadius = '3px';
        copyButton.style.cursor = 'pointer';

        // Make the code block relative positioning for the button
        block.style.position = 'relative';

        // Add click event to copy code
        copyButton.addEventListener('click', function() {
            const code = block.querySelector('code').textContent;
            navigator.clipboard.writeText(code).then(function() {
                copyButton.textContent = 'Copied!';
                setTimeout(function() {
                    copyButton.textContent = 'Copy';
                }, 2000);
            });
        });

        block.appendChild(copyButton);
    });

    // Add collapsible sections for API documentation
    const apiSections = document.querySelectorAll('h2[id^="function-"], h2[id^="class-"]');
    apiSections.forEach(function(section) {
        section.style.cursor = 'pointer';
        section.classList.add('collapsible');

        // Find content to collapse (everything until the next h2)
        const contentElements = [];
        let nextElement = section.nextElementSibling;

        while (nextElement && nextElement.tagName !== 'H2') {
            contentElements.push(nextElement);
            nextElement = nextElement.nextElementSibling;
        }

        // Create a container for the content
        const contentContainer = document.createElement('div');
        contentContainer.className = 'collapsible-content';
        contentContainer.style.transition = 'max-height 0.3s ease-out';

        // Move content into container
        contentElements.forEach(element => {
            contentContainer.appendChild(element.cloneNode(true));
        });

        // Replace original elements with the container
        contentElements.forEach(element => {
            element.remove();
        });

        section.parentNode.insertBefore(contentContainer, section.nextSibling);

        // Add click event to toggle
        section.addEventListener('click', function() {
            this.classList.toggle('active');
            if (contentContainer.style.maxHeight) {
                contentContainer.style.maxHeight = null;
            } else {
                contentContainer.style.maxHeight = contentContainer.scrollHeight + 'px';
            }
        });
    });

    // Add anchor links to headings
    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    headings.forEach(function(heading) {
        if (heading.id) {
            const anchor = document.createElement('a');
            anchor.className = 'anchor-link';
            anchor.href = '#' + heading.id;
            anchor.innerHTML = ' <span class="anchor-symbol">¶</span>';
            anchor.style.textDecoration = 'none';
            anchor.style.opacity = '0.5';
            heading.appendChild(anchor);

            heading.addEventListener('mouseenter', function() {
                anchor.style.opacity = '1';
            });

            heading.addEventListener('mouseleave', function() {
                anchor.style.opacity = '0.5';
            });
        }
    });

    // Add dark mode toggle if not already present
    if (!document.querySelector('#theme-toggle')) {
        const themeToggle = document.createElement('button');
        themeToggle.id = 'custom-theme-toggle';
        themeToggle.innerHTML = '🌙';
        themeToggle.style.position = 'fixed';
        themeToggle.style.bottom = '20px';
        themeToggle.style.right = '20px';
        themeToggle.style.width = '40px';
        themeToggle.style.height = '40px';
        themeToggle.style.borderRadius = '50%';
        themeToggle.style.backgroundColor = '#f8f8f8';
        themeToggle.style.border = '1px solid #ddd';
        themeToggle.style.cursor = 'pointer';
        themeToggle.style.zIndex = '1000';

        themeToggle.addEventListener('click', function() {
            const htmlElement = document.documentElement;
            const currentTheme = htmlElement.getAttribute('data-theme');

            if (currentTheme === 'dark' || currentTheme === 'navy') {
                htmlElement.setAttribute('data-theme', 'light');
                themeToggle.innerHTML = '🌙';
            } else {
                htmlElement.setAttribute('data-theme', 'navy');
                themeToggle.innerHTML = '☀️';
            }
        });

        document.body.appendChild(themeToggle);
    }
});
