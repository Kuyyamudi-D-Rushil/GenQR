/**
 * CloudQR Client Engine
 * Asynchronous QR Generation, Cloud Persistence, Color Customizer, History Management & XSS-Safe Modals
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
 * Configure dynamic QR type inputs (placeholders, labels, helpers)
 */
function updateTypeInputConfig(type, elements) {
    const { label, input, helper } = elements;
    if (!input) return;

    if (type === "url") {
        if (label) label.textContent = "TARGET WEB URL";
        input.placeholder = "https://yourdomain.com";
        if (helper) helper.textContent = "Destination website link. Include a valid domain (e.g. https://example.com).";
    } else if (type === "text") {
        if (label) label.textContent = "PLAIN TEXT CONTENT";
        input.placeholder = "Enter any message, memo, or raw data...";
        if (helper) helper.textContent = "Standard text information encoded into the QR matrix (up to 2048 bytes).";
    } else if (type === "email") {
        if (label) label.textContent = "RECIPIENT EMAIL ADDRESS";
        input.placeholder = "contact@company.com";
        if (helper) helper.textContent = "Email address. When scanned, opens standard email composer.";
    } else if (type === "phone") {
        if (label) label.textContent = "PHONE NUMBER";
        input.placeholder = "+1 555-123-4567";
        if (helper) helper.textContent = "Contact phone number formatted for one-touch dialing (7 to 15 digits).";
    }
}

/**
 * Dashboard QR Generator Initialization
 */
function initDashboard() {
    const form = document.getElementById("dashboardGenerateForm");
    const titleInput = document.getElementById("qrTitle");
    const contentInput = document.getElementById("qrContent");
    const contentLabel = document.getElementById("qrContentLabel");
    const contentHelper = document.getElementById("qrContentHelper");

    const fgColor = document.getElementById("qrForeground");
    const fgHex = document.getElementById("qrForegroundHex");
    const bgColor = document.getElementById("qrBackground");
    const bgHex = document.getElementById("qrBackgroundHex");

    const previewImg = document.getElementById("qrPreview");
    const previewSpinner = document.getElementById("renderSpinner");
    const previewStatus = document.getElementById("previewStatusBadge");
    const previewTitleDisplay = document.getElementById("previewTitleDisplay");
    const previewContentDisplay = document.getElementById("previewContentDisplay");
    const downloadBtn = document.getElementById("downloadBtn");
    const copyBtn = document.getElementById("copyContentBtn");
    const generateSubmitBtn = document.getElementById("generateSubmitBtn");

    // Sync Color Pickers and Hex Inputs
    function syncColors() {
        if (fgColor && fgHex) {
            fgColor.addEventListener("input", () => { fgHex.value = fgColor.value.toUpperCase(); });
            fgHex.addEventListener("input", () => {
                if (/^#[0-9A-Fa-f]{6}$/.test(fgHex.value)) {
                    fgColor.value = fgHex.value;
                }
            });
        }
        if (bgColor && bgHex) {
            bgColor.addEventListener("input", () => { bgHex.value = bgColor.value.toUpperCase(); });
            bgHex.addEventListener("input", () => {
                if (/^#[0-9A-Fa-f]{6}$/.test(bgHex.value)) {
                    bgColor.value = bgHex.value;
                }
            });
        }
    }
    syncColors();

    // Preset color buttons
    document.querySelectorAll(".btn-preset-dot").forEach(btn => {
        btn.addEventListener("click", () => {
            const fg = btn.getAttribute("data-fg");
            const bg = btn.getAttribute("data-bg");
            if (fg && fgColor && fgHex) {
                fgColor.value = fg;
                fgHex.value = fg.toUpperCase();
            }
            if (bg && bgColor && bgHex) {
                bgColor.value = bg;
                bgHex.value = bg.toUpperCase();
            }
        });
    });

    // QR Type radio change handler
    document.querySelectorAll('input[name="qrType"]').forEach(radio => {
        radio.addEventListener("change", (e) => {
            updateTypeInputConfig(e.target.value, {
                label: contentLabel,
                input: contentInput,
                helper: contentHelper
            });
        });
    });

    // Copy button
    if (copyBtn && contentInput) {
        copyBtn.addEventListener("click", () => {
            navigator.clipboard.writeText(contentInput.value).then(() => {
                const origHtml = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="bi bi-check2 text-success"></i>';
                setTimeout(() => { copyBtn.innerHTML = origHtml; }, 1800);
            });
        });
    }

    // Submit handler: Generate and Save to Cloud
    if (form) {
        form.addEventListener("submit", async function(e) {
            e.preventDefault();

            const selectedTypeRadio = document.querySelector('input[name="qrType"]:checked');
            const qrType = selectedTypeRadio ? selectedTypeRadio.value : "url";
            const title = (titleInput ? titleInput.value : "").trim() || "My QR Code";
            const content = (contentInput ? contentInput.value : "").trim();
            const foreground = (fgColor ? fgColor.value : "#000000").trim();
            const background = (bgColor ? bgColor.value : "#FFFFFF").trim();

            if (!content) {
                alert("Please provide content to encode into the QR code.");
                return;
            }

            if (foreground.toLowerCase() === background.toLowerCase()) {
                alert("Foreground and background colors must be different for QR scanners to read the code.");
                return;
            }

            // UI Loading state
            if (previewSpinner) previewSpinner.classList.remove("d-none");
            if (previewImg) previewImg.classList.add("opacity-25");
            if (previewStatus) {
                previewStatus.textContent = "Generating...";
                previewStatus.className = "badge bg-warning-subtle text-warning rounded-pill";
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
                        content: content,
                        foreground: foreground,
                        background: background
                    })
                });

                if (!response.ok) {
                    const errData = await response.json().catch(() => ({}));
                    alert(errData.error || `QR Generation error (${response.status})`);
                    return;
                }

                // Revoke old object URL if exists
                if (activeBlobUrl) {
                    URL.revokeObjectURL(activeBlobUrl);
                }

                const imageBlob = await response.blob();
                activeBlobUrl = URL.createObjectURL(imageBlob);

                // Update Preview image & info safely using textContent
                if (previewImg) {
                    previewImg.src = activeBlobUrl;
                    previewImg.classList.remove("opacity-25", "d-none");
                }
                const previewEmptyPlaceholder = document.getElementById("previewEmptyPlaceholder");
                if (previewEmptyPlaceholder) {
                    previewEmptyPlaceholder.classList.add("d-none");
                }
                if (previewTitleDisplay) previewTitleDisplay.textContent = title;
                if (previewContentDisplay) previewContentDisplay.textContent = content;

                // Update Download link
                if (downloadBtn) {
                    downloadBtn.href = activeBlobUrl;
                    const cleanFileName = title.replace(/[^\w\-_\. ]/g, "_").trim().replace(/ +/g, "_");
                    downloadBtn.download = `${cleanFileName || "cloud_qr"}.png`;
                    downloadBtn.classList.remove("disabled");
                }

                if (previewStatus) {
                    previewStatus.textContent = "Saved to Cloud";
                    previewStatus.className = "badge bg-success-subtle text-success rounded-pill";
                }

                // Reload smoothly if on dashboard to show in recent table
                const newQrId = response.headers.get("X-QR-ID");
                if (newQrId) {
                    setTimeout(() => {
                        window.location.reload();
                    }, 1200);
                }
            } catch (err) {
                console.error("Generate error:", err);
                alert("Failed to communicate with cloud backend. Please check network connection.");
            } finally {
                if (previewSpinner) previewSpinner.classList.add("d-none");
                if (generateSubmitBtn) {
                    generateSubmitBtn.disabled = false;
                    generateSubmitBtn.innerHTML = '<i class="bi bi-cloud-arrow-up me-1"></i> Generate & Save to PostgreSQL';
                }
            }
        });
    }

    // Attach delete handlers
    attachDeleteHandlers();
}

/**
 * Public Landing Page Preview Sandbox
 */
function initLandingPreview() {
    const previewForm = document.getElementById("publicPreviewForm");
    const previewInput = document.getElementById("previewContent");
    const previewLabel = document.getElementById("previewContentLabel");
    const previewFg = document.getElementById("previewFg");
    const previewFgText = document.getElementById("previewFgText");
    const previewBg = document.getElementById("previewBg");
    const previewBgText = document.getElementById("previewBgText");
    const previewImg = document.getElementById("publicQrImage");
    const previewSpinner = document.getElementById("previewSpinner");
    const generateBtn = document.getElementById("publicGenerateBtn");
    const downloadBtn = document.getElementById("publicDownloadBtn");

    if (previewFg && previewFgText) {
        previewFg.addEventListener("input", () => {
            previewFgText.textContent = previewFg.value.toUpperCase();
        });
    }
    if (previewBg && previewBgText) {
        previewBg.addEventListener("input", () => {
            previewBgText.textContent = previewBg.value.toUpperCase();
        });
    }

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
        const fg = previewFg ? previewFg.value : "#4F46E5";
        const bg = previewBg ? previewBg.value : "#FFFFFF";

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
                    qr_type: qrType,
                    foreground: fg,
                    background: bg
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
                }
            } else {
                const err = await response.json().catch(() => ({}));
                if (response.status === 429) {
                    alert(err.error || "Rate limit reached. Please wait a moment.");
                } else if (err.error) {
                    alert(err.error);
                }
            }
        } catch (err) {
            console.error("Preview render failed", err);
        } finally {
            if (previewSpinner) previewSpinner.classList.add("d-none");
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
 * QR Code Delete Handlers with accessible UI updates and empty-state handling
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

                    // Update visible record badges
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

                        // Check if grid is now empty
                        const remainingCards = document.querySelectorAll("#historyCardsGrid .col-md-6");
                        if (remainingCards.length === 0) {
                            const emptyState = document.getElementById("historyEmptyState");
                            if (emptyState) {
                                emptyState.classList.remove("d-none");
                            }
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
 * XSS-Safe History Preview Modal Handler
 */
function openPreviewModal(id, title, content) {
    const modalEl = document.getElementById("qrDetailModal");
    if (!modalEl) return;

    // Plain text assignment prevents HTML/JS execution
    const titleEl = document.getElementById("modalQrTitle");
    if (titleEl) titleEl.textContent = title || "QR Code Details";

    const contentEl = document.getElementById("modalQrContent");
    if (contentEl) contentEl.textContent = content || "";

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
 * Initialize event listeners for safe preview triggers in history
 */
function initPreviewTriggers() {
    document.querySelectorAll(".qr-preview-trigger").forEach(trigger => {
        trigger.addEventListener("click", function(e) {
            e.preventDefault();
            const id = this.getAttribute("data-id");
            const title = this.getAttribute("data-title");
            const content = this.getAttribute("data-content");
            openPreviewModal(id, title, content);
        });

        trigger.addEventListener("keydown", function(e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                const id = this.getAttribute("data-id");
                const title = this.getAttribute("data-title");
                const content = this.getAttribute("data-content");
                openPreviewModal(id, title, content);
            }
        });
    });
}

/**
 * History Page Initialization
 */
function initHistoryPage() {
    initPreviewTriggers();
    attachDeleteHandlers();
}
