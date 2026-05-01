// Flash message handling
class FlashMessage {
  constructor() {
    this.container = document.getElementById("flashMessages");
    this.autoHideDelay = 5000; // 5 seconds
    this.init();
  }

  init() {
    if (!this.container) return;
    this.setupAutoHide();
    this.setupCloseButtons();
  }

  show(message, type = "info") {
    const flashDiv = document.createElement("div");
    flashDiv.className = `flash-message ${type}`;
    flashDiv.setAttribute("role", "alert");

    let icon = "";
    switch (type) {
      case "success":
        icon = '<i class="fas fa-check-circle"></i>';
        break;
      case "danger":
        icon = '<i class="fas fa-exclamation-circle"></i>';
        break;
      case "warning":
        icon = '<i class="fas fa-exclamation-triangle"></i>';
        break;
      case "info":
        icon = '<i class="fas fa-info-circle"></i>';
        break;
      default:
        icon = '<i class="fas fa-bell"></i>';
    }

    flashDiv.innerHTML = `
            <div class="flash-message-content">
                ${icon}
                <span>${message}</span>
            </div>
            <button type="button" class="flash-close">&times;</button>
        `;

    this.container.appendChild(flashDiv);

    // Setup auto-hide for this message
    setTimeout(() => {
      this.hide(flashDiv);
    }, this.autoHideDelay);

    // Setup close button
    const closeBtn = flashDiv.querySelector(".flash-close");
    closeBtn.addEventListener("click", () => this.hide(flashDiv));

    return flashDiv;
  }

  hide(element) {
    element.classList.add("fade-out");
    setTimeout(() => {
      if (element.parentElement) {
        element.remove();
      }
    }, 300);
  }

  setupAutoHide() {
    const messages = this.container.querySelectorAll(".flash-message");
    messages.forEach((message) => {
      setTimeout(() => {
        this.hide(message);
      }, this.autoHideDelay);
    });
  }

  setupCloseButtons() {
    const closeButtons = this.container.querySelectorAll(".flash-close");
    closeButtons.forEach((button) => {
      button.addEventListener("click", (e) => {
        const message = e.target.closest(".flash-message");
        this.hide(message);
      });
    });
  }
}

// Initialize flash messages when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  window.flashMessages = new FlashMessage();
});

// Helper function to show flash messages from JavaScript
function showFlash(message, type = "info") {
  if (window.flashMessages) {
    window.flashMessages.show(message, type);
  } else {
    alert(message);
  }
}
