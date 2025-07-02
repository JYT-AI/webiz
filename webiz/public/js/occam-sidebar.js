// Occam Global Sidebar - Injected into all Frappe pages
(function() {
    'use strict';

    // Prevent multiple initializations
    if (window.occamSidebarInitialized) {
        return;
    }
    window.occamSidebarInitialized = true;

    class OccamGlobalSidebar {
        constructor() {
            this.apps = [];
            this.sidebarVisible = false;
            this.init();
        }

        async init() {
            await this.loadApps();
            this.createSidebar();
            this.setupEventListeners();
        }

        async loadApps() {
            const response = await fetch('/api/method/frappe.apps.get_apps');
            const data = await response.json();

            this.apps = data.message;

            // Add Drive app
            this.apps.unshift({
                name: 'occam-drive',
                title: 'Drive',
                route: '/occam/drive',
                logo: '/assets/occam/images/drive-logo.svg',
                icon: 'folder'
            });

            // Add AI Chatbot app
            this.apps.unshift({
                name: 'occam-ai',
                title: 'AI',
                route: '/occam/ai',
                logo: '/assets/occam/images/ai-logo.svg',
                icon: 'message-circle'
            });

            console.log('Occam Sidebar: Loaded', this.apps.length, 'apps');
        }

        createSidebar() {
            // Check if sidebar already exists
            if (document.getElementById('occam-global-sidebar')) {
                return;
            }

            console.log('Occam Sidebar: Creating responsive sidebar...');

            // Check if mobile
            const isMobile = window.innerWidth <= 768;

            // Create sidebar HTML
            const sidebar = document.createElement('div');
            sidebar.id = 'occam-global-sidebar';
            sidebar.className = isMobile ? 'occam-global-sidebar mobile' : 'occam-global-sidebar desktop';

            sidebar.innerHTML = `
                <div class="occam-sidebar-content">
                    <div class="occam-app-list" id="occam-global-app-list">
                        <!-- Apps will be loaded here -->
                    </div>
                </div>
            `;

            // Insert sidebar
            if (isMobile) {
                // Mobile: append to body (bottom)
                document.body.appendChild(sidebar);
            } else {
                // Desktop: insert at beginning (left)
                document.body.insertBefore(sidebar, document.body.firstChild);
            }

            // Adjust body layout
            this.adjustBodyLayout();

            // Handle window resize
            this.handleResize();

            // Render apps
            this.renderApps();
        }

        adjustBodyLayout() {
            const isMobile = window.innerWidth <= 768;

            // Add class to body for CSS targeting
            document.body.classList.add('occam-sidebar-active');

            if (isMobile) {
                // Mobile: set CSS custom property for bottom offset
                document.documentElement.style.setProperty('--occam-bottom-offset', '70px');
                document.body.style.marginLeft = '0';
            } else {
                // Desktop: add left margin for left sidebar
                document.documentElement.style.setProperty('--occam-bottom-offset', '0px');
                document.body.style.marginLeft = '60px';
                this.handleDeskUI();
            }
        }

        handleDeskUI() {
            // Check if this is Frappe Desk
            const deskContainer = document.querySelector('#body-sidebar-container, .layout-main, .main-section');
            if (deskContainer) {
                // Adjust desk layout
                deskContainer.style.marginLeft = '0';
                deskContainer.style.paddingLeft = '0';
            }

            // Handle navbar
            const navbar = document.querySelector('.navbar, .nav-container');
            if (navbar) {
                navbar.style.marginLeft = '0';
                navbar.style.paddingLeft = '60px';
            }

            // Handle Frappe's left sidebar to prevent overlap
            const frappeLeftSidebar = document.querySelector('.layout-side-section, .desk-sidebar');
            if (frappeLeftSidebar) {
                frappeLeftSidebar.style.zIndex = '9998'; // Lower than Occam sidebar
            }
        }

        handleResize() {
            window.addEventListener('resize', () => {
                const sidebar = document.getElementById('occam-global-sidebar');
                if (!sidebar) return;

                const isMobile = window.innerWidth <= 768;

                if (isMobile && !sidebar.classList.contains('mobile')) {
                    // Switch to mobile
                    sidebar.className = 'occam-global-sidebar mobile';
                    document.body.appendChild(sidebar);
                } else if (!isMobile && !sidebar.classList.contains('desktop')) {
                    // Switch to desktop
                    sidebar.className = 'occam-global-sidebar desktop';
                    document.body.insertBefore(sidebar, document.body.firstChild);
                }

                this.adjustBodyLayout();
            });
        }

        renderApps() {
            const appList = document.getElementById('occam-global-app-list');
            if (!appList) return;

            appList.innerHTML = '';

            this.apps.forEach(app => {
                const appItem = document.createElement('div');
                appItem.className = 'occam-global-app-item';
                appItem.title = app.title;

                // Check if current page is this app
                const isCurrentApp = this.isCurrentApp(app);
                if (isCurrentApp) {
                    appItem.classList.add('active');
                }

                appItem.innerHTML = `
                    <div class="occam-global-app-icon">
                        <img src="${app.logo || '/assets/frappe/images/frappe-framework-logo.svg'}"
                             alt="${app.title}"
                             onerror="this.src='/assets/frappe/images/frappe-framework-logo.svg'">
                    </div>
                `;

                appItem.addEventListener('click', () => {
                    this.navigateToApp(app);
                });

                appList.appendChild(appItem);
            });
        }

        isCurrentApp(app) {
            const currentPath = window.location.pathname;

            // Check if current path matches app route
            if (app.route && currentPath.startsWith(app.route)) {
                return true;
            }

            // Special handling for different app patterns
            if (app.name === 'frappe' && currentPath.startsWith('/app')) {
                return true;
            }

            // Special handling for Drive app
            if (app.name === 'occam-drive' && currentPath.startsWith('/occam-drive')) {
                return true;
            }

            // Special handling for AI app
            if (app.name === 'occam-ai' && currentPath.startsWith('/occam-ai')) {
                return true;
            }

            return false;
        }

        navigateToApp(app) {
            window.location.href = app.route;
        }

        setupEventListeners() {
            // No event listeners needed for icon-only sidebar
        }
    }

    // Single initialization to prevent duplicates
    function initializeSidebar() {
        // Check if already initialized
        if (document.getElementById('occam-global-sidebar')) {
            return;
        }

        try {
            new OccamGlobalSidebar();
        } catch (error) {
            console.error('Occam Sidebar: Failed to initialize:', error);
        }
    }

    // Simple initialization strategy
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeSidebar);
    } else {
        initializeSidebar();
    }

})();
