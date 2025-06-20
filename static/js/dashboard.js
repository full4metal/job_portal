// Dashboard specific JavaScript functionality

document.addEventListener("DOMContentLoaded", () => {
  initUserDropdown()
  initActiveNavigation()
  initFlashMessages()
  initMobileDashboardMenu()
})

// User Dropdown Functionality
function initUserDropdown() {
  const dropdownBtn = document.getElementById("userDropdownBtn")
  const dropdownMenu = document.getElementById("userDropdownMenu")

  if (dropdownBtn && dropdownMenu) {
    dropdownBtn.addEventListener("click", (e) => {
      e.stopPropagation()
      dropdownMenu.classList.toggle("show")
    })

    // Close dropdown when clicking outside
    document.addEventListener("click", (e) => {
      if (!dropdownBtn.contains(e.target) && !dropdownMenu.contains(e.target)) {
        dropdownMenu.classList.remove("show")
      }
    })

    // Close dropdown when pressing escape
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        dropdownMenu.classList.remove("show")
      }
    })
  }
}

// Active Navigation State
function initActiveNavigation() {
  const currentPath = window.location.pathname
  const navLinks = document.querySelectorAll(".nav-center .nav-link")

  navLinks.forEach((link) => {
    if (link.getAttribute("href") === currentPath) {
      link.classList.add("active")
    }
  })
}

// Flash Messages Auto-hide
function initFlashMessages() {
  const flashMessages = document.querySelectorAll(".flash-message")

  flashMessages.forEach((message) => {
    // Auto-hide success messages after 5 seconds
    if (message.classList.contains("flash-success")) {
      setTimeout(() => {
        message.style.opacity = "0"
        setTimeout(() => {
          message.remove()
        }, 300)
      }, 5000)
    }

    // Auto-hide info messages after 7 seconds
    if (message.classList.contains("flash-info")) {
      setTimeout(() => {
        message.style.opacity = "0"
        setTimeout(() => {
          message.remove()
        }, 300)
      }, 7000)
    }
  })
}

// Mobile Dashboard Menu
function initMobileDashboardMenu() {
  const hamburger = document.getElementById("hamburger")
  const navMenu = document.querySelector(".nav-center .nav-menu")

  if (hamburger && navMenu) {
    hamburger.addEventListener("click", () => {
      navMenu.classList.toggle("active")
      hamburger.classList.toggle("active")
    })

    // Close menu when clicking on nav links
    const navLinks = navMenu.querySelectorAll(".nav-link")
    navLinks.forEach((link) => {
      link.addEventListener("click", () => {
        navMenu.classList.remove("active")
        hamburger.classList.remove("active")
      })
    })
  }
}

// Dashboard Utilities
const Dashboard = {
  // Show loading state for cards
  showCardLoading: (cardElement) => {
    const content = cardElement.querySelector(".card-body") || cardElement
    content.innerHTML = '<div class="loading-skeleton" style="height: 100px; border-radius: 8px;"></div>'
  },

  // Update stat card
  updateStatCard: (cardElement, number, label) => {
    const statNumber = cardElement.querySelector(".stat-number")
    const statLabel = cardElement.querySelector(".stat-label")

    if (statNumber) statNumber.textContent = number
    if (statLabel) statLabel.textContent = label
  },

  // Show notification
  showNotification: (message, type = "info") => {
    const container = document.querySelector(".flash-messages-container .container")
    if (!container) return

    const notification = document.createElement("div")
    notification.className = `flash-message flash-${type}`
    notification.innerHTML = `
            <span>${message}</span>
            <button class="flash-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `

    container.appendChild(notification)

    // Auto-hide after 5 seconds
    setTimeout(() => {
      notification.style.opacity = "0"
      setTimeout(() => {
        notification.remove()
      }, 300)
    }, 5000)
  },

  // Confirm action
  confirmAction: (message, callback) => {
    if (confirm(message)) {
      callback()
    }
  },
}

// Export for use in other scripts
window.Dashboard = Dashboard
