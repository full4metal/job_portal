// DOM Content Loaded
document.addEventListener("DOMContentLoaded", () => {
  // Initialize all functionality
  initMobileMenu()
  initSmoothScrolling()
  initScrollEffects()
  initCounterAnimation()
  initScrollAnimations()
  initLoadingAnimation()
})

// Mobile Menu Functionality
function initMobileMenu() {
  const hamburger = document.getElementById("hamburger")
  const navMenu = document.getElementById("nav-menu")

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

    // Close menu when clicking outside
    document.addEventListener("click", (event) => {
      if (!hamburger.contains(event.target) && !navMenu.contains(event.target)) {
        navMenu.classList.remove("active")
        hamburger.classList.remove("active")
      }
    })
  }
}

// Smooth Scrolling for Anchor Links
function initSmoothScrolling() {
  const links = document.querySelectorAll('a[href^="#"]')

  links.forEach((link) => {
    link.addEventListener("click", function (e) {
      e.preventDefault()

      const targetId = this.getAttribute("href")
      const targetElement = document.querySelector(targetId)

      if (targetElement) {
        const headerHeight = document.querySelector(".header").offsetHeight
        const targetPosition = targetElement.offsetTop - headerHeight - 20

        window.scrollTo({
          top: targetPosition,
          behavior: "smooth",
        })
      }
    })
  })
}

// Header Scroll Effects
function initScrollEffects() {
  const header = document.querySelector(".header")
  let lastScrollTop = 0

  window.addEventListener("scroll", () => {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop

    // Add/remove scrolled class
    if (scrollTop > 100) {
      header.classList.add("scrolled")
      header.style.background = "rgba(255, 255, 255, 0.95)"
      header.style.backdropFilter = "blur(10px)"
    } else {
      header.classList.remove("scrolled")
      header.style.background = "#ffffff"
      header.style.backdropFilter = "none"
    }

    // Hide/show header on scroll
    if (scrollTop > lastScrollTop && scrollTop > 200) {
      header.style.transform = "translateY(-100%)"
    } else {
      header.style.transform = "translateY(0)"
    }

    lastScrollTop = scrollTop
  })
}

// Counter Animation
function initCounterAnimation() {
  const counters = document.querySelectorAll(".stat-number")
  const speed = 200 // Animation speed

  const animateCounter = (counter) => {
    const target = Number.parseInt(counter.getAttribute("data-target"))
    const count = Number.parseInt(counter.innerText)
    const increment = target / speed

    if (count < target) {
      counter.innerText = Math.ceil(count + increment)
      setTimeout(() => animateCounter(counter), 1)
    } else {
      counter.innerText = target
    }
  }

  // Intersection Observer for counter animation
  const counterObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const counter = entry.target
          if (!counter.classList.contains("animated")) {
            counter.classList.add("animated")
            animateCounter(counter)
          }
        }
      })
    },
    {
      threshold: 0.5,
    },
  )

  counters.forEach((counter) => {
    counterObserver.observe(counter)
  })
}

// Scroll Animations
function initScrollAnimations() {
  const animatedElements = document.querySelectorAll("[data-aos]")

  const animationObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const element = entry.target
          const delay = element.getAttribute("data-aos-delay") || 0

          setTimeout(() => {
            element.classList.add("animate")
            element.style.opacity = "1"
            element.style.transform = "translateY(0)"
          }, delay)
        }
      })
    },
    {
      threshold: 0.1,
      rootMargin: "0px 0px -50px 0px",
    },
  )

  animatedElements.forEach((element) => {
    element.style.opacity = "0"
    element.style.transform = "translateY(30px)"
    element.style.transition = "opacity 0.6s ease, transform 0.6s ease"
    animationObserver.observe(element)
  })
}

// Loading Animation
function initLoadingAnimation() {
  document.body.classList.add("loading")

  window.addEventListener("load", () => {
    setTimeout(() => {
      document.body.classList.remove("loading")
      document.body.classList.add("loaded")
    }, 100)
  })
}

// Utility Functions
function debounce(func, wait, immediate) {
  let timeout
  return function executedFunction() {
    
    const args = arguments
    const later = () => {
      timeout = null
      if (!immediate) func.apply(this, args)
    }
    const callNow = immediate && !timeout
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
    if (callNow) func.apply(this, args)
  }
}

// Form Validation (for future use)
function validateForm(form) {
  const inputs = form.querySelectorAll("input[required], select[required], textarea[required]")
  let isValid = true

  inputs.forEach((input) => {
    if (!input.value.trim()) {
      showError(input, "This field is required")
      isValid = false
    } else {
      clearError(input)
    }

    // Email validation
    if (input.type === "email" && input.value) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailRegex.test(input.value)) {
        showError(input, "Please enter a valid email address")
        isValid = false
      }
    }
  })

  return isValid
}

function showError(input, message) {
  clearError(input)
  input.classList.add("error")

  const errorDiv = document.createElement("div")
  errorDiv.className = "error-message"
  errorDiv.textContent = message
  input.parentNode.appendChild(errorDiv)
}

function clearError(input) {
  input.classList.remove("error")
  const errorMessage = input.parentNode.querySelector(".error-message")
  if (errorMessage) {
    errorMessage.remove()
  }
}

// Toast Notifications (for future use)
function showToast(message, type = "info") {
  const toast = document.createElement("div")
  toast.className = `toast toast-${type}`
  toast.textContent = message

  document.body.appendChild(toast)

  setTimeout(() => {
    toast.classList.add("show")
  }, 100)

  setTimeout(() => {
    toast.classList.remove("show")
    setTimeout(() => {
      document.body.removeChild(toast)
    }, 300)
  }, 3000)
}

// Local Storage Utilities (for future use)
function saveToLocalStorage(key, data) {
  try {
    localStorage.setItem(key, JSON.stringify(data))
  } catch (error) {
    console.error("Error saving to localStorage:", error)
  }
}

function getFromLocalStorage(key) {
  try {
    const data = localStorage.getItem(key)
    return data ? JSON.parse(data) : null
  } catch (error) {
    console.error("Error reading from localStorage:", error)
    return null
  }
}

// API Utilities (for future Flask integration)
async function apiRequest(url, options = {}) {
  const defaultOptions = {
    headers: {
      "Content-Type": "application/json",
    },
  }

  const config = { ...defaultOptions, ...options }

  try {
    const response = await fetch(url, config)

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return await response.json()
  } catch (error) {
    console.error("API request failed:", error)
    throw error
  }
}

// Export functions for use in other scripts
window.JobPortal = {
  validateForm,
  showToast,
  saveToLocalStorage,
  getFromLocalStorage,
  apiRequest,
}
