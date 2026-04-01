/**
 * AMAREN - Main JavaScript
 * Mobile-First Architecture
 */

// ======================================
// HAMBURGER MENU MANAGEMENT
// ======================================
class HamburgerManager {
  constructor() {
    this.hamburgerBtn = document.querySelector('.hamburger-btn');
    this.sidebar = document.querySelector('.sidebar');
    this.navbar = document.querySelector('.navbar');
    
    if (this.hamburgerBtn && this.sidebar) {
      this.init();
    }
  }

  init() {
    // Toggle menu on hamburger click
    this.hamburgerBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggle();
    });

    // Close menu when clicking on a link
    this.sidebar.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => this.close());
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.hamburger-btn') && 
          !e.target.closest('.sidebar') && 
          this.sidebar.classList.contains('active')) {
        this.close();
      }
    });

    // Close menu on window resize (when reaching tablet size)
    window.addEventListener('resize', () => {
      if (window.innerWidth >= 768 && this.sidebar.classList.contains('active')) {
        this.close();
      }
    });
  }

  toggle() {
    this.hamburgerBtn.classList.toggle('active');
    this.sidebar.classList.toggle('active');
    document.body.style.overflow = this.sidebar.classList.contains('active') ? 'hidden' : '';
  }

  close() {
    this.hamburgerBtn.classList.remove('active');
    this.sidebar.classList.remove('active');
    document.body.style.overflow = '';
  }
}

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

    // Close on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
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
// MODAL MANAGEMENT
// ======================================
class ModalManager {
  constructor() {
    this.modals = document.querySelectorAll('[data-modal]');
    this.triggers = document.querySelectorAll('[data-modal-open]');
    this.init();
  }

  init() {
    // Open modals
    this.triggers.forEach(trigger => {
      trigger.addEventListener('click', (e) => {
        e.preventDefault();
        const modalId = trigger.getAttribute('data-modal-open');
        this.open(modalId);
      });
    });

    // Close modals
    document.querySelectorAll('[data-modal-close]').forEach(closeBtn => {
      closeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const modal = closeBtn.closest('[data-modal]');
        if (modal) this.close(modal.getAttribute('data-modal'));
      });
    });

    // Close on background click
    this.modals.forEach(modal => {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          this.close(modal.getAttribute('data-modal'));
        }
      });
    });

    // Close on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeAll();
      }
    });
  }

  open(modalId) {
    const modal = document.querySelector(`[data-modal="${modalId}"]`);
    if (modal) {
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  }

  close(modalId) {
    const modal = document.querySelector(`[data-modal="${modalId}"]`);
    if (modal) {
      modal.classList.remove('active');
      if (!document.querySelector('[data-modal].active')) {
        document.body.style.overflow = '';
      }
    }
  }

  closeAll() {
    this.modals.forEach(modal => {
      modal.classList.remove('active');
    });
    document.body.style.overflow = '';
  }
}

// ======================================
// INIT ON DOM READY
// ======================================
document.addEventListener('DOMContentLoaded', () => {
  new HamburgerManager();
  new DropdownManager();
  new TabManager();
  new ModalManager();

  // Add keyboard navigation for accessibility
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      document.body.classList.add('focus-visible');
    }
  });

  document.addEventListener('mousedown', () => {
    document.body.classList.remove('focus-visible');
  });
});

