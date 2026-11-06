// Vanilla JavaScript helper functions for FSMD frontend

document.addEventListener("DOMContentLoaded", () => {
    // Recalculate derived features live from text inputs
    function recalculateDerivedFeatures() {
        const u = document.getElementById("input-username") ? document.getElementById("input-username").value.trim() : "";
        const fn = document.getElementById("input-fullname") ? document.getElementById("input-fullname").value.trim() : "";
        const bio = document.getElementById("input-bio") ? document.getElementById("input-bio").value.trim() : "";

        // Username digit ratio
        if (document.getElementById("nums_length_username")) {
            const uDigits = (u.match(/\d/g) || []).length;
            const uRatio = u.length > 0 ? (uDigits / u.length) : 0.0;
            document.getElementById("nums_length_username").value = uRatio.toFixed(2);
        }

        // Fullname words and digits
        if (document.getElementById("fullname_words")) {
            const words = fn.length > 0 ? fn.split(/\s+/).filter(Boolean).length : 0;
            document.getElementById("fullname_words").value = words;
        }
        if (document.getElementById("nums_length_fullname")) {
            const fnDigits = (fn.match(/\d/g) || []).length;
            const fnRatio = fn.length > 0 ? (fnDigits / fn.length) : 0.0;
            document.getElementById("nums_length_fullname").value = fnRatio.toFixed(2);
        }

        // Name == Username
        if (document.getElementById("name_equals_username")) {
            const normFn = fn.toLowerCase().replace(/[\s._]/g, '');
            const normU = u.toLowerCase().replace(/[\s._]/g, '');
            const eq = (u.length > 0 && normFn.length > 0 && normFn === normU) ? 1 : 0;
            document.getElementById("name_equals_username").value = eq;
        }

        // Bio length
        if (document.getElementById("description_length")) {
            document.getElementById("description_length").value = bio.length;
        }

        // External URL
        if (document.getElementById("external_url")) {
            const urlPat = /(https?:\/\/[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.(?:com|org|net|io|me|co|link|app)[^\s]*)/i;
            document.getElementById("external_url").value = urlPat.test(bio) ? 1 : 0;
        }
    }

    const inputUser = document.getElementById("input-username");
    const inputFn = document.getElementById("input-fullname");
    const inputBio = document.getElementById("input-bio");
    if (inputUser) inputUser.addEventListener("input", recalculateDerivedFeatures);
    if (inputFn) inputFn.addEventListener("input", recalculateDerivedFeatures);
    if (inputBio) inputBio.addEventListener("input", recalculateDerivedFeatures);

    function highlightField(el, state) {
        if (!el) return;
        el.classList.remove("border-danger", "border-warning", "bg-warning-subtle", "bg-danger-subtle");
        if (state === "none") {
            el.classList.add("border-danger", "bg-danger-subtle");
        } else if (state === "low") {
            el.classList.add("border-warning", "bg-warning-subtle");
        }
    }

    function clearHighlights() {
        document.querySelectorAll(".field-input").forEach(el => {
            el.classList.remove("border-danger", "border-warning", "bg-warning-subtle", "bg-danger-subtle");
        });
    }

    // Reset button handler
    const resetBtn = document.getElementById("screenshot-reset-btn");
    if (resetBtn) {
        resetBtn.addEventListener("click", () => {
            const fileInput = document.getElementById("screenshot-input");
            if (fileInput) fileInput.value = "";
            clearHighlights();
            document.getElementById("screenshot-status-box")?.classList.add("d-none");
            document.getElementById("claude-privacy-notice")?.classList.add("d-none");
            document.getElementById("fields-validation-alert")?.classList.add("d-none");
            resetBtn.classList.add("d-none");

            // Clear inputs
            if (document.getElementById("input-username")) document.getElementById("input-username").value = "";
            if (document.getElementById("input-fullname")) document.getElementById("input-fullname").value = "";
            if (document.getElementById("input-bio")) document.getElementById("input-bio").value = "";
            if (document.getElementById("posts")) document.getElementById("posts").value = "";
            if (document.getElementById("followers")) document.getElementById("followers").value = "";
            if (document.getElementById("follows")) document.getElementById("follows").value = "";
            if (document.getElementById("profile_pic")) document.getElementById("profile_pic").value = "";
            if (document.getElementById("private")) document.getElementById("private").value = "";
            
            recalculateDerivedFeatures();
        });
    }

    // Screenshot OCR Handler
    const screenshotForm = document.getElementById("screenshot-form");
    if (screenshotForm) {
        screenshotForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById("screenshot-input");
            const spinner = document.getElementById("screenshot-spinner");
            const btn = document.getElementById("screenshot-btn");
            const errorBox = document.getElementById("screenshot-error");
            const statusBox = document.getElementById("screenshot-status-box");
            const backendName = document.getElementById("status-backend-name");
            const confSummary = document.getElementById("status-confidence-summary");
            const warningsList = document.getElementById("status-warnings-list");
            const claudeNotice = document.getElementById("claude-privacy-notice");
            const valAlert = document.getElementById("fields-validation-alert");

            if (!fileInput.files.length) return;

            btn.disabled = true;
            spinner.classList.remove("d-none");
            errorBox.classList.add("d-none");
            statusBox.classList.add("d-none");
            if (valAlert) valAlert.classList.add("d-none");
            clearHighlights();

            const formData = new FormData();
            formData.append("file", fileInput.files[0]);

            try {
                const res = await fetch("/api/screenshot/extract", {
                    method: "POST",
                    body: formData
                });
                
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || "Screenshot extraction failed.");
                }
                const data = await res.json();

                // Show reset button
                if (resetBtn) resetBtn.classList.remove("d-none");

                // Update backend badge and privacy notice
                const backend = data.backend_used || "tesseract";
                if (backendName) backendName.textContent = backend;
                if (backend === "claude") {
                    claudeNotice?.classList.remove("d-none");
                } else {
                    claudeNotice?.classList.add("d-none");
                }

                // Show warnings if any
                statusBox.classList.remove("d-none");
                if (warningsList) {
                    warningsList.innerHTML = "";
                    if (data.warnings && data.warnings.length > 0) {
                        data.warnings.forEach(w => {
                            const d = document.createElement("div");
                            d.textContent = "• " + w;
                            warningsList.appendChild(d);
                        });
                    }
                }

                const parsed = data.parsed || {};
                const conf = data.confidence || {};

                // Username
                const uEl = document.getElementById("input-username");
                if (uEl) {
                    uEl.value = parsed.username || "";
                    highlightField(uEl, conf.username || "none");
                }

                // Full Name
                const fnEl = document.getElementById("input-fullname");
                if (fnEl) {
                    fnEl.value = parsed.full_name || "";
                    highlightField(fnEl, conf.full_name || "none");
                }

                // Bio
                const bioEl = document.getElementById("input-bio");
                if (bioEl) {
                    bioEl.value = parsed.bio || "";
                    highlightField(bioEl, conf.bio || "none");
                }

                // Posts
                const postsEl = document.getElementById("posts");
                if (postsEl) {
                    postsEl.value = (parsed.posts !== null && parsed.posts !== undefined) ? parsed.posts : "";
                    highlightField(postsEl, conf.posts || "none");
                }

                // Followers
                const fersEl = document.getElementById("followers");
                if (fersEl) {
                    fersEl.value = (parsed.followers !== null && parsed.followers !== undefined) ? parsed.followers : "";
                    highlightField(fersEl, conf.followers || "none");
                }

                // Following
                const fingEl = document.getElementById("follows");
                if (fingEl) {
                    fingEl.value = (parsed.following !== null && parsed.following !== undefined) ? parsed.following : "";
                    highlightField(fingEl, conf.following || "none");
                }

                // Profile Picture
                const picEl = document.getElementById("profile_pic");
                const picHint = document.getElementById("pic-autodetect-hint");
                if (picEl) {
                    if (parsed.has_custom_profile_picture === true) {
                        picEl.value = "1";
                        picHint?.classList.remove("d-none");
                    } else if (parsed.has_custom_profile_picture === false) {
                        picEl.value = "0";
                        picHint?.classList.remove("d-none");
                    } else {
                        picEl.value = "";
                        picHint?.classList.add("d-none");
                    }
                    highlightField(picEl, conf.has_custom_profile_picture || "none");
                }

                // Private Account
                const privEl = document.getElementById("private");
                const privHint = document.getElementById("private-autodetect-hint");
                if (privEl) {
                    if (parsed.is_private === true) {
                        privEl.value = "1";
                        privHint?.classList.remove("d-none");
                    } else if (parsed.is_private === false) {
                        privEl.value = "0";
                        privHint?.classList.remove("d-none");
                    } else {
                        privEl.value = "";
                        privHint?.classList.add("d-none");
                    }
                    highlightField(privEl, conf.is_private || "none");
                }

                // Summary confidence text
                const unconfidentCount = Object.values(conf).filter(c => c === "none" || c === "low").length;
                if (confSummary) {
                    if (unconfidentCount === 0) {
                        confSummary.className = "badge bg-success";
                        confSummary.textContent = "High Confidence";
                    } else {
                        confSummary.className = "badge bg-warning text-dark";
                        confSummary.textContent = `${unconfidentCount} fields need review`;
                    }
                }

                recalculateDerivedFeatures();
            } catch (err) {
                errorBox.textContent = err.message;
                errorBox.classList.remove("d-none");
            } finally {
                btn.disabled = false;
                spinner.classList.add("d-none");
            }
        });
    }

    // Quick Fill Parse Handler
    const qfForm = document.getElementById("quickfill-parse-form");
    if (qfForm) {
        qfForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = document.getElementById("qf-parse-btn");
            const spinner = document.getElementById("qf-spinner");
            const errorBox = document.getElementById("quickfill-error");

            btn.disabled = true;
            spinner.classList.remove("d-none");
            errorBox.classList.add("d-none");

            const payload = {
                raw_text: document.getElementById("qf-raw-text").value,
                username_or_url: document.getElementById("qf-handle").value
            };

            try {
                const res = await fetch("/api/quickfill/parse", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || "Quick fill parsing failed.");
                }
                const data = await res.json();

                if (data.detected_username && document.getElementById("input-username")) {
                    document.getElementById("input-username").value = data.detected_username;
                }
                if (data.full_name && document.getElementById("input-fullname")) {
                    document.getElementById("input-fullname").value = data.full_name;
                }
                if (data.bio && document.getElementById("input-bio")) {
                    document.getElementById("input-bio").value = data.bio;
                }
                if (data.posts !== undefined && document.getElementById("posts")) {
                    document.getElementById("posts").value = data.posts;
                }
                if (data.followers !== undefined && document.getElementById("followers")) {
                    document.getElementById("followers").value = data.followers;
                }
                if (data.following !== undefined && document.getElementById("follows")) {
                    document.getElementById("follows").value = data.following;
                }

                recalculateDerivedFeatures();
            } catch (err) {
                errorBox.textContent = err.message;
                errorBox.classList.remove("d-none");
            } finally {
                btn.disabled = false;
                spinner.classList.add("d-none");
            }
        });
    }

    // Unified Predict Form Handler
    const unifiedForm = document.getElementById("unified-predict-form");
    if (unifiedForm) {
        unifiedForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = document.getElementById("predict-submit-btn");
            const spinner = document.getElementById("predict-spinner");
            const errorBox = document.getElementById("predict-error");
            const resultCard = document.getElementById("predict-result-card");
            const valAlert = document.getElementById("fields-validation-alert");
            const missingText = document.getElementById("missing-fields-text");

            // Validate mandatory fields
            const u = document.getElementById("input-username")?.value.trim();
            const p = document.getElementById("posts")?.value.trim();
            const fers = document.getElementById("followers")?.value.trim();
            const fing = document.getElementById("follows")?.value.trim();
            const pic = document.getElementById("profile_pic")?.value;
            const priv = document.getElementById("private")?.value;

            const missing = [];
            if (!u) missing.push("Username");
            if (p === "" || isNaN(p) || parseInt(p) < 0) missing.push("Posts Count");
            if (fers === "" || isNaN(fers) || parseInt(fers) < 0) missing.push("Followers Count");
            if (fing === "" || isNaN(fing) || parseInt(fing) < 0) missing.push("Following Count");
            if (pic === "" || pic === null || pic === undefined) missing.push("Profile Picture Present");
            if (priv === "" || priv === null || priv === undefined) missing.push("Account Private");

            if (missing.length > 0) {
                if (valAlert && missingText) {
                    missingText.textContent = missing.join(", ");
                    valAlert.classList.remove("d-none");
                    valAlert.scrollIntoView({ behavior: "smooth" });
                }
                return;
            } else {
                if (valAlert) valAlert.classList.add("d-none");
            }

            btn.disabled = true;
            spinner.classList.remove("d-none");
            errorBox.classList.add("d-none");
            resultCard.classList.add("d-none");

            recalculateDerivedFeatures();

            const payload = {
                "profile pic": parseInt(pic),
                "nums/length username": parseFloat(document.getElementById("nums_length_username").value || "0"),
                "fullname words": parseInt(document.getElementById("fullname_words").value || "0"),
                "nums/length fullname": parseFloat(document.getElementById("nums_length_fullname").value || "0"),
                "name==username": parseInt(document.getElementById("name_equals_username").value || "0"),
                "description length": parseInt(document.getElementById("description_length").value || "0"),
                "external URL": parseInt(document.getElementById("external_url").value || "0"),
                "private": parseInt(priv),
                "#posts": parseInt(p),
                "#followers": parseInt(fers),
                "#follows": parseInt(fing)
            };

            try {
                const res = await fetch("/api/predict", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });

                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.detail || "Prediction request failed.");
                }

                const data = await res.json();
                displaySingleResult(data);
            } catch (err) {
                errorBox.textContent = err.message;
                errorBox.classList.remove("d-none");
            } finally {
                btn.disabled = false;
                spinner.classList.add("d-none");
            }
        });
    }

    // Batch Prediction Form Handler
    const batchForm = document.getElementById("batch-upload-form");
    if (batchForm) {
        batchForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById("batch-csv-file");
            if (!fileInput.files.length) {
                alert("Please select a CSV file to upload.");
                return;
            }

            const btn = document.getElementById("batch-submit-btn");
            const spinner = document.getElementById("batch-spinner");
            const errorBox = document.getElementById("batch-error");
            const resultsSection = document.getElementById("batch-results-section");

            btn.disabled = true;
            spinner.classList.remove("d-none");
            errorBox.classList.add("d-none");
            resultsSection.classList.add("d-none");

            const formData = new FormData();
            formData.append("file", fileInput.files[0]);

            try {
                const res = await fetch("/api/predict-batch", {
                    method: "POST",
                    body: formData
                });

                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.detail || "Batch prediction request failed.");
                }

                const data = await res.json();
                displayBatchResults(data);
            } catch (err) {
                errorBox.textContent = err.message;
                errorBox.classList.remove("d-none");
            } finally {
                btn.disabled = false;
                spinner.classList.add("d-none");
            }
        });
    }

    // History Table Clear Handler
    const clearHistoryBtn = document.getElementById("clear-history-btn");
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener("click", async () => {
            if (!confirm("Are you sure you want to delete all prediction logs?")) return;
            try {
                const res = await fetch("/api/history", { method: "DELETE" });
                if (res.ok) {
                    window.location.reload();
                } else {
                    alert("Failed to clear database logs.");
                }
            } catch (err) {
                alert("Error connecting to server: " + err.message);
            }
        });
    }
});

function displaySingleResult(data) {
    const card = document.getElementById("predict-result-card");
    const badge = document.getElementById("result-badge");
    const probBar = document.getElementById("result-prob-bar");
    const probText = document.getElementById("result-prob-text");
    const riskBadge = document.getElementById("result-risk-badge");
    const featuresList = document.getElementById("result-features-list");
    const sourceBadge = document.getElementById("shap-source-badge");

    // Label
    badge.textContent = data.label;
    if (data.is_fake === 1) {
        badge.className = "badge bg-danger fs-5";
    } else {
        badge.className = "badge bg-success fs-5";
    }

    // Probability
    const fakePct = (data.fake_probability * 100).toFixed(1);
    probText.textContent = `${fakePct}%`;
    probBar.style.width = `${fakePct}%`;
    if (fakePct > 60) {
        probBar.className = "progress-bar bg-danger";
    } else if (fakePct > 35) {
        probBar.className = "progress-bar bg-warning";
    } else {
        probBar.className = "progress-bar bg-success";
    }

    // Risk
    riskBadge.textContent = data.risk_level;
    if (data.risk_level === "High Risk") {
        riskBadge.className = "badge badge-risk-high px-3 py-2 fs-6";
    } else if (data.risk_level === "Needs Review") {
        riskBadge.className = "badge badge-risk-review px-3 py-2 fs-6";
    } else {
        riskBadge.className = "badge badge-risk-low px-3 py-2 fs-6";
    }

    // Explanations
    featuresList.innerHTML = "";
    if (data.top_features && data.top_features.length > 0) {
        const isLocal = data.top_features[0].type === "local";
        if (sourceBadge) {
            sourceBadge.textContent = isLocal ? "Local SHAP Explanations" : "Global Importances";
            sourceBadge.className = isLocal ? "badge bg-primary-subtle text-primary border" : "badge bg-warning-subtle text-warning border";
        }

        data.top_features.forEach(feat => {
            const item = document.createElement("div");
            item.className = "mb-3";
            const valStr = feat.value !== null && feat.value !== undefined ? ` (value: ${feat.value})` : "";
            
            const isFakePush = (feat.direction === "Toward Fake") || (feat.contribution > 0);
            const badgeColor = isFakePush ? "bg-danger" : "bg-success";
            const barBgClass = isFakePush ? "bg-danger" : "bg-success";
            const directionLabel = feat.direction || (isFakePush ? "Toward Fake" : "Toward Genuine");
            const absPct = Math.min(100, Math.round(Math.abs(feat.contribution) * 150));

            item.innerHTML = `
                <div class="d-flex justify-content-between small mb-1 align-items-center">
                    <span class="fw-semibold">${feat.feature}${valStr}</span>
                    <div>
                        <span class="badge ${badgeColor} me-1">${directionLabel}</span>
                        <span class="text-muted">${feat.contribution > 0 ? "+" : ""}${feat.contribution.toFixed(4)}</span>
                    </div>
                </div>
                <div class="progress" style="height: 10px;">
                    <div class="progress-bar ${barBgClass}" role="progressbar" style="width: ${absPct || 10}%"></div>
                </div>
            `;
            featuresList.appendChild(item);
        });
    }

    card.classList.remove("d-none");
    card.scrollIntoView({ behavior: "smooth" });
}

let batchChartInstance = null;

function displayBatchResults(data) {
    const section = document.getElementById("batch-results-section");
    const summary = data.summary;

    document.getElementById("sum-total").textContent = summary.total_accounts;
    document.getElementById("sum-fake").textContent = summary.fake_count;
    document.getElementById("sum-genuine").textContent = summary.genuine_count;
    document.getElementById("sum-low").textContent = summary.low_risk_count;
    document.getElementById("sum-review").textContent = summary.needs_review_count;
    document.getElementById("sum-high").textContent = summary.high_risk_count;

    // Render Table
    const tbody = document.getElementById("batch-table-body");
    tbody.innerHTML = "";
    data.predictions.slice(0, 50).forEach((row, idx) => {
        const tr = document.createElement("tr");
        let badgeClass = "badge-risk-low";
        if (row.risk_level === "Needs Review") badgeClass = "badge-risk-review";
        if (row.risk_level === "High Risk") badgeClass = "badge-risk-high";

        tr.innerHTML = `
            <td>${idx + 1}</td>
            <td><strong>${row.predicted_label}</strong></td>
            <td>${(row.fake_probability * 100).toFixed(1)}%</td>
            <td><span class="badge ${badgeClass}">${row.risk_level}</span></td>
            <td>${row["#followers"] ?? "-"}</td>
            <td>${row["#follows"] ?? "-"}</td>
            <td>${row["#posts"] ?? "-"}</td>
        `;
        tbody.appendChild(tr);
    });

    // Render Chart.js Donut
    const ctx = document.getElementById("batch-doughnut-chart");
    if (ctx && typeof Chart !== "undefined") {
        if (batchChartInstance) {
            batchChartInstance.destroy();
        }
        batchChartInstance = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["Low Risk", "Needs Review", "High Risk"],
                datasets: [{
                    data: [summary.low_risk_count, summary.needs_review_count, summary.high_risk_count],
                    backgroundColor: ["#198754", "#ffc107", "#dc3545"]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom" }
                }
            }
        });
    }

    section.classList.remove("d-none");
    section.scrollIntoView({ behavior: "smooth" });
}
