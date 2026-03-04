/**
 * AMAREN - Main JavaScript
 * Clean and modular script
 */

// ======================================
// DROPDOWN MANAGEMENT
// ======================================
class DropdownManager {
  constructor() {
    this.dropdowns = document.querySelectorAll('[data-dropdown]');
    this.init();
  }

  init() {
    this.dropdowns.forEach(button => {
      button.addEventListener('click', (e) => this.handleClick(e, button));
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.dropdown')) {
        this.closeAll();
      }
    });
  }

  handleClick(e, button) {
    e.stopPropagation();
    const menuId = button.getAttribute('data-dropdown');
    const menu = document.getElementById(menuId);

    if (!menu) return;

    // Close other menus
    this.closeAll();

    // Toggle current menu
    menu.classList.toggle('active');
  }

  closeAll() {
    document.querySelectorAll('.dropdown-menu.active').forEach(menu => {
      menu.classList.remove('active');
    });
  }
}

// ======================================
// TAB MANAGEMENT
// ======================================
class TabManager {
  constructor() {
    this.tabs = document.querySelectorAll('[data-tab]');
    this.init();
  }

  init() {
    this.tabs.forEach(tab => {
      tab.addEventListener('click', (e) => this.handleClick(e, tab));
    });
  }

  handleClick(e, tab) {
    e.preventDefault();

    const tabGroup = tab.getAttribute('data-tab');
    const tabName = tab.getAttribute('data-tab-content');

    // Remove active from all tabs and contents in this group
    document.querySelectorAll(`[data-tab="${tabGroup}"]`).forEach(t => {
      t.classList.remove('active');
    });
    document.querySelectorAll(`[data-tab-pane="${tabGroup}"]`).forEach(content => {
      content.classList.remove('active');
    });

    // Add active to clicked tab and content
    tab.classList.add('active');
    const content = document.querySelector(
      `[data-tab-pane="${tabGroup}"][data-pane-name="${tabName}"]`
    );
    if (content) {
      content.classList.add('active');
    }
  }
}

// ======================================
// INIT ON DOM READY
// ======================================
document.addEventListener('DOMContentLoaded', () => {
  new DropdownManager();
  new TabManager();
});
