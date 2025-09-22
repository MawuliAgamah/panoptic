/**
 * Simple Component Loader
 * Auto-discovers components and enables simple slotting/composition
 */

const SimpleLoader = {
    loadedComponents: new Set(),
    availableComponents: new Map(),
    componentsPath: '/frontend/components',
    /**
     * Load a component from an HTML file
     * @param {string} componentPath - Path to the component HTML file
     * @param {string} targetSelector - CSS selector where to insert the component
     * @param {Object} options - Options for loading
     */
    async loadComponent(componentPath, targetSelector, options = {}) {
        try {
            console.log(`📦 Loading component: ${componentPath}`);

            // Check if already loaded and not allowing duplicates
            if (this.loadedComponents.has(componentPath) && !options.allowDuplicates) {
                console.log(`⚠️ Component ${componentPath} already loaded`);
                return false;
            }

            // Fetch the component HTML
            const response = await fetch(componentPath);
            if (!response.ok) {
                throw new Error(`Failed to load component: ${response.status}`);
            }

            const html = await response.text();

            // Find target container
            const container = document.querySelector(targetSelector);
            if (!container) {
                throw new Error(`Target container not found: ${targetSelector}`);
            }

            // Create a temporary container to parse the HTML
            const tempContainer = document.createElement('div');
            tempContainer.innerHTML = html;

            // Extract and handle styles
            const styles = tempContainer.querySelectorAll('style');
            styles.forEach(style => {
                if (!document.querySelector(`style[data-component="${componentPath}"]`)) {
                    style.setAttribute('data-component', componentPath);
                    document.head.appendChild(style);
                }
            });

            // Extract and handle scripts
            const scripts = tempContainer.querySelectorAll('script');
            scripts.forEach(script => {
                if (!document.querySelector(`script[data-component="${componentPath}"]`)) {
                    const newScript = document.createElement('script');
                    newScript.textContent = script.textContent;
                    newScript.setAttribute('data-component', componentPath);
                    document.body.appendChild(newScript);
                }
            });

            // Insert the HTML content (everything except style and script tags)
            const htmlContent = tempContainer.querySelector('div, section, article, main, aside, header, footer, nav');
            if (htmlContent) {
                if (options.replace) {
                    container.innerHTML = '';
                }

                const clonedContent = htmlContent.cloneNode(true);

                // Process slots for composition
                this.processSlots(clonedContent, options.slots);

                container.appendChild(clonedContent);
            }

            this.loadedComponents.add(componentPath);
            console.log(`✅ Component loaded: ${componentPath}`);

            // Trigger custom event
            document.dispatchEvent(new CustomEvent('componentLoaded', {
                detail: { path: componentPath, container: targetSelector }
            }));

            return true;

        } catch (error) {
            console.error(`❌ Error loading component ${componentPath}:`, error);
            return false;
        }
    },

    /**
     * Process slots for HTML composition
     * @param {Element} component - The component element
     * @param {Object} slots - Slot content to insert
     */
    processSlots(component, slots = {}) {
        if (!component || !slots) return;

        // Find all <slot> tags in the component
        const slotElements = component.querySelectorAll('slot');

        slotElements.forEach(slot => {
            const slotName = slot.getAttribute('name') || 'default';
            const slotContent = slots[slotName];

            if (slotContent) {
                if (typeof slotContent === 'string') {
                    slot.innerHTML = slotContent;
                } else if (slotContent instanceof Element) {
                    slot.replaceWith(slotContent.cloneNode(true));
                } else if (slotContent instanceof NodeList || Array.isArray(slotContent)) {
                    const fragment = document.createDocumentFragment();
                    [...slotContent].forEach(node => {
                        fragment.appendChild(node.cloneNode ? node.cloneNode(true) : document.createTextNode(node));
                    });
                    slot.replaceWith(fragment);
                }
            }
            // If no slot content provided, keep default content inside <slot> tags
        });
    },

    /**
     * Auto-discover available components
     */
    async discoverComponents() {
        try {
            // Auto-discover by trying actual components that exist
            const potentialComponents = [
                'graph-canvas.html',
                'graph-stats.html',
                'graph-controls.html',
                'graph-search.html',
                'file-upload.html',
                'data-loader.html'
            ];

            for (const component of potentialComponents) {
                const componentName = component.replace('.html', '');
                const componentPath = `${this.componentsPath}/${component}`;

                // Test if component exists by trying to fetch it
                try {
                    const response = await fetch(componentPath);
                    if (response.ok) {
                        this.availableComponents.set(componentName, componentPath);
                        console.log(`📦 Discovered component: ${componentName} at ${componentPath}`);
                    } else {
                        console.log(`❌ Component not found: ${componentName} at ${componentPath} (${response.status})`);
                    }
                } catch (e) {
                    console.log(`❌ Error checking component ${componentName}:`, e.message);
                }
            }

            console.log(`✅ Discovered ${this.availableComponents.size} components`);
            return Array.from(this.availableComponents.keys());

        } catch (error) {
            console.warn('Could not auto-discover components:', error);
            return [];
        }
    },

    /**
     * Load a component by name (auto-discovery)
     * @param {string} componentName - Name of component (without .html)
     * @param {string} targetSelector - Where to slot it in
     * @param {Object} options - Loading options
     */
    async slot(componentName, targetSelector, options = {}) {
        // Auto-discover if not done yet
        if (this.availableComponents.size === 0) {
            await this.discoverComponents();
        }

        const componentPath = this.availableComponents.get(componentName);
        if (!componentPath) {
            console.error(`❌ Component not found: ${componentName}`);
            console.log('Available components:', Array.from(this.availableComponents.keys()));
            return false;
        }

        return this.loadComponent(componentPath, targetSelector, options);
    },

    /**
     * Get list of available components
     */
    async getAvailableComponents() {
        if (this.availableComponents.size === 0) {
            await this.discoverComponents();
        }
        return Array.from(this.availableComponents.keys());
    },

    /**
     * Load multiple components
     * @param {Array} components - Array of {path, target, options} objects
     */
    async loadComponents(components) {
        const results = [];

        for (const component of components) {
            const result = await this.loadComponent(
                component.path,
                component.target,
                component.options || {}
            );
            results.push({
                path: component.path,
                target: component.target,
                success: result
            });
        }

        console.log(`📦 Loaded ${results.filter(r => r.success).length}/${results.length} components`);
        return results;
    },

    /**
     * Remove a component
     * @param {string} componentPath - Path of the component to remove
     * @param {string} targetSelector - CSS selector of the container
     */
    removeComponent(componentPath, targetSelector) {
        try {
            // Remove HTML content
            const container = document.querySelector(targetSelector);
            if (container) {
                const componentElement = container.querySelector(`[data-component-path="${componentPath}"]`);
                if (componentElement) {
                    componentElement.remove();
                }
            }

            // Remove styles
            const styleElement = document.querySelector(`style[data-component="${componentPath}"]`);
            if (styleElement) {
                styleElement.remove();
            }

            // Remove scripts (Note: scripts can't be truly "removed" once executed)
            const scriptElement = document.querySelector(`script[data-component="${componentPath}"]`);
            if (scriptElement) {
                scriptElement.remove();
            }

            this.loadedComponents.delete(componentPath);
            console.log(`🗑️ Removed component: ${componentPath}`);

            // Trigger custom event
            document.dispatchEvent(new CustomEvent('componentRemoved', {
                detail: { path: componentPath, container: targetSelector }
            }));

        } catch (error) {
            console.error(`❌ Error removing component ${componentPath}:`, error);
        }
    },

    /**
     * Dynamic presets - built from available components
     */
    presets: {},

    /**
     * Build dynamic presets based on available components
     */
    async buildPresets() {
        if (this.availableComponents.size === 0) {
            await this.discoverComponents();
        }

        // Build common presets dynamically
        this.presets = {};

        if (this.availableComponents.has('graph-canvas') && this.availableComponents.has('data-loader')) {
            this.presets.minimal = [
                { name: 'graph-canvas', target: '#graph-container' },
                { name: 'data-loader', target: '#loader-container' }
            ];
        }

        if (this.availableComponents.has('graph-stats') && this.availableComponents.has('graph-controls')) {
            this.presets.basic = [
                ...(this.presets.minimal || []),
                { name: 'graph-stats', target: '#stats-container' },
                { name: 'graph-controls', target: '#controls-container' }
            ];
        }

        console.log(`📦 Built ${Object.keys(this.presets).length} dynamic presets`);
    },

    /**
     * Load a preset configuration
     * @param {string} presetName - Name of the preset to load
     */
    async loadPreset(presetName) {
        // Build presets if not done yet
        if (Object.keys(this.presets).length === 0) {
            await this.buildPresets();
        }

        const preset = this.presets[presetName];
        if (!preset) {
            console.error(`❌ Preset not found: ${presetName}`);
            console.log('Available presets:', Object.keys(this.presets));
            return false;
        }

        console.log(`🎯 Loading preset: ${presetName}`);

        // Load using slot method for each component
        const results = await Promise.allSettled(
            preset.map(component => this.slot(component.name, component.target))
        );

        const successful = results.filter(r => r.status === 'fulfilled').length;
        console.log(`📦 Loaded ${successful}/${preset.length} components from preset`);

        return successful === preset.length;
    },

    /**
     * Clear all loaded components
     */
    clearAll() {
        // Clear containers
        const containers = ['#stats-container', '#controls-container', '#search-container'];
        containers.forEach(selector => {
            const container = document.querySelector(selector);
            if (container) {
                container.innerHTML = '';
            }
        });

        // Remove component styles and scripts
        document.querySelectorAll('style[data-component], script[data-component]').forEach(el => {
            el.remove();
        });

        this.loadedComponents.clear();
        console.log('🧹 Cleared all components');
    },

    /**
     * Check if a component is loaded
     * @param {string} componentPath 
     */
    isLoaded(componentPath) {
        return this.loadedComponents.has(componentPath);
    },

    /**
     * Get list of loaded components
     */
    getLoaded() {
        return Array.from(this.loadedComponents);
    }
};

// Global access
window.SimpleLoader = SimpleLoader;

// Usage examples:
/*

// Load a single component
SimpleLoader.loadComponent('simple-components/graph-stats.html', '#stats-container');

// Load multiple components
SimpleLoader.loadComponents([
    { path: 'simple-components/graph-stats.html', target: '#stats-container' },
    { path: 'simple-components/graph-controls.html', target: '#controls-container' }
]);

// Load a preset
SimpleLoader.loadPreset('basic');

// Remove a component
SimpleLoader.removeComponent('simple-components/graph-stats.html', '#stats-container');

// Clear all
SimpleLoader.clearAll();

*/
