/**
 * CloudQR Commercial SaaS Client Engine
 * Features:
 * - Persistent Light/Dark Theme Switcher (with smooth transitions)
 * - 4 Dynamic Interactive QR Type Selectors (URL, Text, Email, Phone)
 * - Dedicated Generator Workspace with Live B&W Canvas
 * - Dashboard Overview & PostgreSQL Activity Distribution
 * - XSS-Safe QR History Management & Deletion Engine
 */

// Helper to extract CSRF Token from meta tag
function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
}

// Global active blob URL tracker to prevent browser memory leaks
let activeBlobUrl = null;
let activePreviewBlobUrl = null;

/**
 * 1. THEME TOGGLE SYSTEM (Light & Dark with LocalStorage Persistence)
 */
function initThemeToggle() {
    const toggleBtns = document.querySelectorAll(".theme-toggle-btn");
    
    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("cloudqr_theme", theme);
        
        toggleBtns.forEach(btn => {
            if (theme === "dark") {
                btn.innerHTML = '<i class="bi bi-sun-fill text-warning"></i>';
                btn.setAttribute("title", "Switch to Light Mode");
                btn.setAttribute("aria-label", "Switch to Light Mode");
            } else {
                btn.innerHTML = '<i class="bi bi-moon-stars-fill text-secondary"></i>';
                btn.setAttribute("title", "Switch to Dark Mode");
                btn.setAttribute("aria-label", "Switch to Dark Mode");
            }
        });
    }

    // Determine current theme
    const currentTheme = document.documentElement.getAttribute("data-theme") || 
                         localStorage.getItem("cloudqr_theme") || 
                         (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    
    applyTheme(currentTheme);

    toggleBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const active = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
            applyTheme(active);
        });
    });
}

/**
 * 2. DYNAMIC QR TYPE CONFIGURATOR
 * Updates form labels, placeholders, input types, and helpful hints
 */
function updateTypeInputConfig(type, elements) {
    const { label, input, helper } = elements;
    if (!input) return;

    if (type === "url") {
        if (label) label.textContent = "Website URL";
        input.placeholder = "https://example.com";
        if (helper) helper.textContent = "Target destination web address. Include valid domain (e.g. https://www.google.com).";
    } else if (type === "text") {
        if (label) label.textContent = "Your Text";
        input.placeholder = "Enter the text you want to encode...";
        if (helper) helper.textContent = "Plain text memos, instructions, or raw data (up to 2048 bytes).";
    } else if (type === "email") {
        if (label) label.textContent = "Email Address";
        input.placeholder = "user@example.com";
        if (helper) helper.textContent = "Contact email. Encodes into a standardized mailto: payload.";
    } else if (type === "phone") {
        if (label) label.textContent = "Phone Number";
        input.placeholder = "+91 9876543210";
        if (helper) helper.textContent = "Phone number formatted for one-touch dialing (7 to 15 digits).";
    }
}

/**
 * 3. DEDICATED QR GENERATOR WORKSPACE INITIALIZATION (/generate)
 */
function initGeneratorWorkspace() {
    const form = document.getElementById("generatorWorkspaceForm") || document.getElementById("dashboardGenerateForm");
    const titleInput = document.getElementById("qrTitle");
    const contentInput = document.getElementById("qrContent");
    const contentLabel = document.getElementById("qrContentLabel");
    const contentHelper = document.getElementById("qrContentHelper");

    const previewImg = document.getElementById("qrPreview");
    const previewCanvas = document.getElementById("qrPreviewCanvas");
    const previewSpinner = document.getElementById("renderSpinner");
    const previewStatus = document.getElementById("previewStatusBadge");
    const previewTitleDisplay = document.getElementById("previewTitleDisplay");
    const previewContentDisplay = document.getElementById("previewContentDisplay");
    const previewTypeBadge = document.getElementById("previewTypeBadge");
    const emptyPlaceholder = document.getElementById("previewEmptyPlaceholder");
    const downloadBtn = document.getElementById("downloadBtn");
    const copyBtn = document.getElementById("copyContentBtn");
    const generateSubmitBtn = document.getElementById("generateSubmitBtn");

    const typeCards = document.querySelectorAll(".qr-type-card");

    // Function to select QR type
    function selectQRType(typeVal) {
        typeCards.forEach(card => {
            const radio = card.querySelector('input[type="radio"]');
            if (card.getAttribute("data-type") === typeVal) {
                card.classList.add("active");
                if (radio) radio.checked = true;
            } else {
                card.classList.remove("active");
                if (radio) radio.checked = false;
            }
        });

        if (previewTypeBadge) {
            previewTypeBadge.textContent = typeVal.toUpperCase();
            previewTypeBadge.className = `badge badge-${typeVal}`;
        }

        updateTypeInputConfig(typeVal, {
            label: contentLabel,
            input: contentInput,
            helper: contentHelper
        });
    }

    // Attach click listeners to 4 interactive QR type cards
    typeCards.forEach(card => {
        card.addEventListener("click", () => {
            const typeVal = card.getAttribute("data-type");
            selectQRType(typeVal);
            if (contentInput) contentInput.focus();
        });
    });

    // Check URL parameters for preset type (e.g. from Dashboard quick action cards)
    const urlParams = new URLSearchParams(window.location.search);
    const initialType = urlParams.get("type");
    if (initialType && ["url", "text", "email", "phone"].includes(initialType.toLowerCase())) {
        selectQRType(initialType.toLowerCase());
    }

    // Copy Content button interaction
    if (copyBtn && contentInput) {
        copyBtn.addEventListener("click", () => {
            const textToCopy = contentInput.value.trim();
            if (!textToCopy) return;

            navigator.clipboard.writeText(textToCopy).then(() => {
                const origHtml = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="bi bi-check2 text-success me-1"></i> Copied!';
                copyBtn.classList.add("btn-outline-success");
                setTimeout(() => {
                    copyBtn.innerHTML = origHtml;
                    copyBtn.classList.remove("btn-outline-success");
                }, 2000);
            });
        });
    }

    // Live typing title & content update on right panel
    if (titleInput && previewTitleDisplay) {
        titleInput.addEventListener("input", () => {
            previewTitleDisplay.textContent = titleInput.value.trim() || "My QR Code";
        });
    }

    if (contentInput && previewContentDisplay) {
        contentInput.addEventListener("input", () => {
            previewContentDisplay.textContent = contentInput.value.trim() || "Enter your information on the left...";
        });
    }

    // Generator Form Submit Handler (Strictly Black & White)
    if (form) {
        form.addEventListener("submit", async function(e) {
            e.preventDefault();

            const activeCard = document.querySelector(".qr-type-card.active");
            const qrType = activeCard ? activeCard.getAttribute("data-type") : "url";
            let title = (titleInput ? titleInput.value : "").trim();
            let content = (contentInput ? contentInput.value : "").trim();

            // Intelligent Safety Correction: URL in title with empty content
            if (!content && title) {
                content = title;
                title = "My QR Code";
                if (contentInput) contentInput.value = content;
                if (titleInput) titleInput.value = "";
            } else if (title.startsWith("http://") || title.startsWith("https://") || title.startsWith("www.")) {
                if (!content || content.toLowerCase() === "https://example.com" || content.toLowerCase() === "example.com") {
                    content = title;
                    title = "My QR Code";
                    if (contentInput) contentInput.value = content;
                    if (titleInput) titleInput.value = "";
                }
            }

            if (!content) {
                alert("Please enter the content to encode into the QR code.");
                if (contentInput) contentInput.focus();
                return;
            }

            if (!title) {
                title = "My QR Code";
            }

            // UI Loading state
            if (previewSpinner) previewSpinner.classList.remove("d-none");
            if (previewImg) previewImg.classList.add("opacity-25");
            if (emptyPlaceholder) emptyPlaceholder.classList.add("d-none");
            if (previewStatus) {
                previewStatus.textContent = "Generating...";
                previewStatus.className = "badge bg-warning-subtle text-warning";
            }
            if (generateSubmitBtn) {
                generateSubmitBtn.disabled = true;
                generateSubmitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Saving to Cloud DB...';
            }

            try {
                const response = await fetch("/api/generate", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCsrfToken()
                    },
                    body: JSON.stringify({
                        title: title,
                        qr_type: qrType,
                        content: content
                    })
                });

                if (!response.ok) {
                    const errData = await response.json().catch(() => ({}));
                    alert(errData.error || `QR Generation error (${response.status})`);
                    if (emptyPlaceholder && !previewImg.src) {
                        emptyPlaceholder.classList.remove("d-none");
                    }
                    return;
                }

                // Revoke old object URL if exists
                if (activeBlobUrl) {
                    URL.revokeObjectURL(activeBlobUrl);
                }

                const imageBlob = await response.blob();
                activeBlobUrl = URL.createObjectURL(imageBlob);

                // Update Preview image & info
                if (previewImg) {
                    previewImg.src = activeBlobUrl;
                    previewImg.classList.remove("opacity-25", "d-none");
                }
                if (previewCanvas) {
                    previewCanvas.classList.remove("d-none");
                }
                if (emptyPlaceholder) {
                    emptyPlaceholder.classList.add("d-none");
                }
                if (previewTitleDisplay) previewTitleDisplay.textContent = title;
                if (previewContentDisplay) previewContentDisplay.textContent = content;

                // Configure Download link
                if (downloadBtn) {
                    downloadBtn.href = activeBlobUrl;
                    const cleanFileName = title.replace(/[^\w\-_\. ]/g, "_").trim().replace(/ +/g, "_");
                    downloadBtn.download = `${cleanFileName || "cloud_qr"}.png`;
                    downloadBtn.classList.remove("disabled");
                }

                if (copyBtn) {
                    copyBtn.classList.remove("disabled");
                }

                if (previewStatus) {
                    previewStatus.textContent = "Saved to Cloud";
                    previewStatus.className = "badge bg-success-subtle text-success";
                }
            } catch (err) {
                console.error("Generate error:", err);
                alert("Failed to communicate with cloud backend. Please check network connection.");
            } finally {
                if (previewSpinner) previewSpinner.classList.add("d-none");
                if (previewImg) previewImg.classList.remove("opacity-25");
                if (generateSubmitBtn) {
                    generateSubmitBtn.disabled = false;
                    generateSubmitBtn.innerHTML = '<i class="bi bi-cloud-arrow-up me-1"></i> Generate & Save to Cloud';
                }
            }
        });
    }
}

/**
 * 4. DASHBOARD OVERVIEW INITIALIZATION (/dashboard)
 */
function initDashboardOverview() {
    // Delete handlers for recent records table
    attachDeleteHandlers();

    // Calculate dynamic distribution progress bar if data attributes exist
    const distContainer = document.getElementById("qrTypeDistribution");
    if (distContainer) {
        const total = parseInt(distContainer.getAttribute("data-total") || "0", 10);
        const urlCount = parseInt(distContainer.getAttribute("data-url") || "0", 10);
        const textCount = parseInt(distContainer.getAttribute("data-text") || "0", 10);
        const emailCount = parseInt(distContainer.getAttribute("data-email") || "0", 10);
        const phoneCount = parseInt(distContainer.getAttribute("data-phone") || "0", 10);

        if (total > 0) {
            const urlPct = Math.round((urlCount / total) * 100);
            const textPct = Math.round((textCount / total) * 100);
            const emailPct = Math.round((emailCount / total) * 100);
            const phonePct = 100 - (urlPct + textPct + emailPct);

            const segUrl = document.getElementById("distSegUrl");
            const segText = document.getElementById("distSegText");
            const segEmail = document.getElementById("distSegEmail");
            const segPhone = document.getElementById("distSegPhone");

            if (segUrl) segUrl.style.width = `${urlPct}%`;
            if (segText) segText.style.width = `${textPct}%`;
            if (segEmail) segEmail.style.width = `${emailPct}%`;
            if (segPhone) segPhone.style.width = `${phonePct}%`;
        }
    }
}

/**
 * 5. PUBLIC LANDING PAGE PREVIEW SANDBOX (/)
 */
function initLandingPreview() {
    const previewInput = document.getElementById("previewContent");
    const previewLabel = document.getElementById("previewContentLabel");
    const previewImg = document.getElementById("publicQrImage");
    const previewSpinner = document.getElementById("previewSpinner");
    const generateBtn = document.getElementById("publicGenerateBtn");
    const downloadBtn = document.getElementById("publicDownloadBtn");

    document.querySelectorAll('input[name="preview_type"]').forEach(radio => {
        radio.addEventListener("change", (e) => {
            updateTypeInputConfig(e.target.value, {
                label: previewLabel,
                input: previewInput
            });
            renderPublicPreview();
        });
    });

    async function renderPublicPreview() {
        const selectedType = document.querySelector('input[name="preview_type"]:checked');
        const qrType = selectedType ? selectedType.value : "url";
        const content = previewInput ? previewInput.value.trim() : "https://cloud-qr-generator.onrender.com";

        if (!content) return;

        if (previewSpinner) previewSpinner.classList.remove("d-none");
        if (previewImg) previewImg.classList.add("opacity-25");

        try {
            const response = await fetch("/api/preview", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    content: content,
                    qr_type: qrType
                })
            });

            if (response.ok) {
                if (activePreviewBlobUrl) {
                    URL.revokeObjectURL(activePreviewBlobUrl);
                }
                const blob = await response.blob();
                activePreviewBlobUrl = URL.createObjectURL(blob);
                if (previewImg) {
                    previewImg.src = activePreviewBlobUrl;
                    previewImg.classList.remove("opacity-25");
                }
                if (downloadBtn) {
                    downloadBtn.href = activePreviewBlobUrl;
                    downloadBtn.download = "cloud_qr_preview.png";
                    downloadBtn.classList.remove("disabled");
                }
            } else {
                const err = await response.json().catch(() => ({}));
                if (response.status === 429) {
                    alert(err.error || "Rate limit reached. Please wait a moment.");
                }
            }
        } catch (err) {
            console.error("Preview render failed", err);
        } finally {
            if (previewSpinner) previewSpinner.classList.add("d-none");
            if (previewImg) previewImg.classList.remove("opacity-25");
        }
    }

    if (generateBtn) {
        generateBtn.addEventListener("click", renderPublicPreview);
    }
    if (previewInput) {
        previewInput.addEventListener("change", renderPublicPreview);
    }

    // Initial render
    renderPublicPreview();
}

/**
 * 6. QR CODE DELETION ENGINE (Live Announcements & State Updates)
 */
function attachDeleteHandlers() {
    document.querySelectorAll(".delete-qr-btn").forEach(btn => {
        btn.addEventListener("click", async function(e) {
            e.preventDefault();
            e.stopPropagation();

            const qrId = this.getAttribute("data-id");
            const qrTitle = this.getAttribute("data-title") || "this QR code";

            if (!confirm(`Are you sure you want to delete "${qrTitle}" from your cloud database? This action cannot be undone.`)) {
                return;
            }

            try {
                const response = await fetch(`/api/qr/${encodeURIComponent(qrId)}`, {
                    method: "DELETE",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCsrfToken()
                    }
                });

                if (response.ok) {
                    const resData = await response.json().catch(() => ({}));

                    // Update live accessibility announcement
                    const liveRegion = document.getElementById("deletionLiveRegion");
                    if (liveRegion) {
                        liveRegion.textContent = `QR code "${qrTitle}" was deleted successfully.`;
                    }

                    // Update visible record badges and stat cards
                    if (resData.remaining_count !== undefined) {
                        const totalBadge = document.getElementById("historyTotalBadge");
                        if (totalBadge) {
                            totalBadge.textContent = `${resData.remaining_count} total`;
                        }
                        const statsCount = document.getElementById("statsTotalCount");
                        if (statsCount) {
                            statsCount.textContent = resData.remaining_count;
                        }
                    }

                    // Remove card from history grid or row from dashboard table
                    const card = document.getElementById(`qr-card-${qrId}`);
                    const row = document.getElementById(`qr-row-${qrId}`);

                    if (card) {
                        card.remove();
                        const remainingCards = document.querySelectorAll("#historyCardsGrid tr, #historyCardsGrid .col-md-6");
                        if (remainingCards.length === 0) {
                            const emptyState = document.getElementById("historyEmptyState");
                            if (emptyState) emptyState.classList.remove("d-none");
                        }
                    }

                    if (row) {
                        row.remove();
                        const remainingRows = document.querySelectorAll("#recentTableBody tr");
                        if (remainingRows.length === 0) {
                            const tableWrapper = document.getElementById("recentTableWrapper");
                            if (tableWrapper) tableWrapper.classList.add("d-none");
                            const emptyState = document.getElementById("recentEmptyState");
                            if (emptyState) emptyState.classList.remove("d-none");
                        }
                    }
                } else {
                    const err = await response.json().catch(() => ({}));
                    alert(err.error || "Failed to delete QR code from cloud.");
                }
            } catch (err) {
                console.error("Delete error:", err);
                alert("Network error while attempting to delete record.");
            }
        });
    });
}

/**
 * 7. XSS-SAFE HISTORY PREVIEW MODAL
 */
function openPreviewModal(id, title, content, type) {
    const modalEl = document.getElementById("qrDetailModal");
    if (!modalEl) return;

    // Plain text assignment prevents HTML/JS injection
    const titleEl = document.getElementById("modalQrTitle");
    if (titleEl) titleEl.textContent = title || "QR Code Details";

    const contentEl = document.getElementById("modalQrContent");
    if (contentEl) contentEl.textContent = content || "";

    const typeBadge = document.getElementById("modalQrTypeBadge");
    if (typeBadge && type) {
        typeBadge.textContent = type.toUpperCase();
        typeBadge.className = `badge badge-${type}`;
    }

    const imgEl = document.getElementById("modalQrImage");
    if (imgEl) imgEl.src = `/api/qr/${encodeURIComponent(id)}/image`;

    const downloadLink = document.getElementById("modalDownloadBtn");
    if (downloadLink) {
        downloadLink.href = `/api/qr/${encodeURIComponent(id)}/download`;
    }

    const modal = new bootstrap.Modal(modalEl);
    modal.show();
}

/**
 * 8. HISTORY PREVIEW TRIGGERS
 */
function initPreviewTriggers() {
    document.querySelectorAll(".qr-preview-trigger").forEach(trigger => {
        trigger.addEventListener("click", function(e) {
            e.preventDefault();
            const id = this.getAttribute("data-id");
            const title = this.getAttribute("data-title");
            const content = this.getAttribute("data-content");
            const type = this.getAttribute("data-type") || "url";
            openPreviewModal(id, title, content, type);
        });

        trigger.addEventListener("keydown", function(e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                const id = this.getAttribute("data-id");
                const title = this.getAttribute("data-title");
                const content = this.getAttribute("data-content");
                const type = this.getAttribute("data-type") || "url";
                openPreviewModal(id, title, content, type);
            }
        });
    });
}

/**
 * 9. HISTORY PAGE INITIALIZATION (/history)
 */
function initHistoryPage() {
    initPreviewTriggers();
    attachDeleteHandlers();
}

// Automatically initialize theme toggle on DOM load across every page
document.addEventListener("DOMContentLoaded", function() {
    initThemeToggle();
});
