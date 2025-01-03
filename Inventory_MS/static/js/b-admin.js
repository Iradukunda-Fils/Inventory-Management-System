        // Previous JavaScript remains, add these new functions

        document.addEventListener('DOMContentLoaded', function() {
            // Previous event listeners and functions remain
        
            // Notifications System
            const notificationBell = document.getElementById('notificationBell');
            const notificationDropdown = document.getElementById('notificationDropdown');
            const notificationList = document.getElementById('notificationList');
            const notificationCount = document.getElementById('notificationCount');
            const markAllRead = document.getElementById('markAllRead');
            const notificationTemplate = document.getElementById('notificationTemplate');
        
            let notifications = [];
        
            // Toggle notification dropdown
            notificationBell.addEventListener('click', function(e) {
                e.stopPropagation();
                notificationDropdown.classList.toggle('show');
            });
        
            // Close dropdown when clicking outside
            document.addEventListener('click', function(e) {
                if (!notificationDropdown.contains(e.target) && !notificationBell.contains(e.target)) {
                    notificationDropdown.classList.remove('show');
                }
            });
        
            // Mark all notifications as read
            markAllRead.addEventListener('click', function() {
                notifications.forEach(notification => {
                    notification.read = true;
                });
                updateNotifications();
                saveNotifications();
            });
        
            // Function to add a new notification
            function addNotification(message, type = 'info') {
                const notification = {
                    id: Date.now(),
                    message,
                    type,
                    timestamp: new Date(),
                    read: false
                };
                
                notifications.unshift(notification);
                updateNotifications();
                saveNotifications();
            }
        
            // Function to update notification display
            function updateNotifications() {
                // Update notification count
                const unreadCount = notifications.filter(n => !n.read).length;
                notificationCount.textContent = unreadCount;
                notificationCount.style.display = unreadCount > 0 ? 'flex' : 'none';
        
                // Clear current notifications
                notificationList.innerHTML = '';
        
                // Add notifications to dropdown
                notifications.forEach(notification => {
                    const clone = notificationTemplate.content.cloneNode(true);
                    const item = clone.querySelector('.notification-item');
                    const text = clone.querySelector('.notification-text');
                    const time = clone.querySelector('.notification-time');
        
                    if (!notification.read) {
                        item.classList.add('unread');
                    }
        
                    text.textContent = notification.message;
                    time.textContent = formatTimestamp(notification.timestamp);
        
                    // Add click handler to mark as read
                    item.addEventListener('click', () => {
                        notification.read = true;
                        updateNotifications();
                        saveNotifications();
                    });
        
                    notificationList.appendChild(clone);
                });
            }
        
            // Format timestamp
            function formatTimestamp(timestamp) {
                const date = new Date(timestamp);
                const now = new Date();
                const diff = (now - date) / 1000; // difference in seconds
        
                if (diff < 60) {
                    return 'Just now';
                } else if (diff < 3600) {
                    const minutes = Math.floor(diff / 60);
                    return `${minutes}m ago`;
                } else if (diff < 86400) {
                    const hours = Math.floor(diff / 3600);
                    return `${hours}h ago`;
                } else {
                    return date.toLocaleDateString();
                }
            }
        
            // Save notifications to localStorage
            function saveNotifications() {
                localStorage.setItem('notifications', JSON.stringify(notifications));
            }
        
            // Load notifications from localStorage
            function loadNotifications() {
                const saved = localStorage.getItem('notifications');
                if (saved) {
                    notifications = JSON.parse(saved);
                    notifications.forEach(n => n.timestamp = new Date(n.timestamp));
                    updateNotifications();
                }
            }
        
            // Load saved notifications on page load
            loadNotifications();
        
            // Websocket connection for real-time notifications
            function connectWebSocket() {
                const ws = new WebSocket(`ws://${window.location.host}/ws/notifications/`);
        
                ws.onmessage = function(e) {
                    const data = JSON.parse(e.data);
                    addNotification(data.message, data.type);
                };
        
                ws.onclose = function() {
                    // Attempt to reconnect after 5 seconds
                    setTimeout(connectWebSocket, 5000);
                };
            }
        
            // Initialize WebSocket connection
            connectWebSocket();
        
            // Example function to simulate new notifications (remove in production)
            function simulateNewNotification() {
                const messages = [
                    'New user registration',
                    'Order #123 has been completed',
                    'Stock level low for product XYZ',
                    'New sales report available',
                    'System maintenance scheduled'
                ];
                const randomMessage = messages[Math.floor(Math.random() * messages.length)];
                addNotification(randomMessage);
            }
        
            // Simulate notifications every 30 seconds (remove in production)
            setInterval(simulateNewNotification, 30000);
        });
        
        //--------------------------------------------------------------------------------------------------------------------------------
        
        
        document.addEventListener('DOMContentLoaded', function() {
            // Elements
            const sidebar = document.getElementById('sidebar');
            const mainContent = document.getElementById('mainContent');
            const sidebarToggle = document.getElementById('sidebarToggle');
            const spinner = document.getElementById('spinner');
            let isSidebarCollapsed = false;
        
            // Toggle Sidebar
            function toggleSidebar() {
                isSidebarCollapsed = !isSidebarCollapsed;
                sidebar.classList.toggle('collapsed');
                mainContent.classList.toggle('expanded');
                sidebarToggle.classList.toggle('collapsed');
                
                // Store preference
                localStorage.setItem('sidebarCollapsed', isSidebarCollapsed);
            }
        
            // Initialize sidebar state from localStorage
            if (localStorage.getItem('sidebarCollapsed') === 'true') {
                toggleSidebar();
            }
        
            // Event Listeners
            sidebarToggle.addEventListener('click', toggleSidebar);
        
            // Handle mobile responsiveness
            function handleMobileView() {
                if (window.innerWidth <= 768) {
                    sidebar.classList.remove('collapsed');
                    mainContent.classList.remove('expanded');
                    sidebarToggle.classList.remove('collapsed');
                    
                    // Add mobile-specific event handling
                    document.addEventListener('click', function(e) {
                        if (!sidebar.contains(e.target) && 
                            !sidebarToggle.contains(e.target) && 
                            sidebar.classList.contains('mobile-visible')) {
                            sidebar.classList.remove('mobile-visible');
                        }
                    });
                }
            }
        
            // Mobile sidebar toggle
            sidebarToggle.addEventListener('click', function(e) {
                if (window.innerWidth <= 768) {
                    e.stopPropagation();
                    sidebar.classList.toggle('mobile-visible');
                }
            });
        
            // Loading spinner
            function showSpinner() {
                spinner.style.display = 'flex';
            }
        
            function hideSpinner() {
                spinner.style.display = 'none';
            }
        
            // Show spinner before page load
            window.addEventListener('beforeunload', showSpinner);
        
            // Hide spinner after page load
            window.addEventListener('load', hideSpinner);
        
            // Handle window resize
            window.addEventListener('resize', handleMobileView);
        
            // Initialize mobile view
            handleMobileView();
        
            // Smooth scrolling for sidebar links
            document.querySelectorAll('.sidebar-menu a').forEach(link => {
                link.addEventListener('click', function(e) {
                    showSpinner();
                    // Hide sidebar on mobile after clicking a link
                    if (window.innerWidth <= 768) {
                        sidebar.classList.remove('mobile-visible');
                    }
                });
            });
        
            // Add hover effects for sidebar item
        })

        
        
        