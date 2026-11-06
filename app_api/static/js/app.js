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
            const eq = (u.length > 0 && fn.toLowerCase().replace(/\s+/g, '') === u.toLowerCase()) ? 1 : 0;
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

    // Screenshot OCR Handler
    const screenshotForm = document.getElementById("screenshot-form");
    if (screenshotForm) {
        screenshotForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById("screenshot-input");
            const spinner = document.getElementById("screenshot-spinner");
            const btn = document.getElementById("screenshot-btn");
            const errorBox = document.getElementById("screenshot-error");

            if (!fileInput.files.length) return;

            btn.disabled = true;
            spinner.classList.remove("d-none");
            errorBox.classList.add("d-none");

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
                if (data.error) {
                    throw new Error("OCR Note: " + data.error);
                }

                // Populate fields
                const parsed = data.parsed || {};
                if (parsed.username && document.getElementById("input-username")) {
                    document.getElementById("input-username").value = parsed.username;
                }
                if (parsed.full_name && document.getElementById("input-fullname")) {
                    document.getElementById("input-fullname").value = parsed.full_name;
                }
                if (parsed.bio && document.getElementById("input-bio")) {
                    document.getElementById("input-bio").value = parsed.bio;
                }
                if (parsed.posts !== undefined && document.getElementById("posts")) {
                    document.getElementById("posts").value = parsed.posts;
                }
                if (parsed.followers !== undefined && document.getElementById("followers")) {
                    document.getElementById("followers").value = parsed.followers;
                }
                if (parsed.following !== undefined && document.getElementById("follows")) {
                    document.getElementById("follows").value = parsed.following;
                }
                if (parsed.is_private !== undefined && document.getElementById("private")) {
                    document.getElementById("private").value = parsed.is_private;
                }
                if (parsed.profile_pic !== undefined && document.getElementById("profile_pic")) {
                    document.getElementById("profile_pic").value = parsed.profile_pic;
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

    // Single Prediction Form Handler (Works with unified form or classic form)
    const unifiedForm = document.getElementById("unified-predict-form") || document.getElementById("predict-form");
    if (unifiedForm) {
        unifiedForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = document.getElementById("predict-submit-btn");
            const spinner = document.getElementById("predict-spinner");
            const errorBox = document.getElementById("predict-error");
            const resultCard = document.getElementById("predict-result-card");

            btn.disabled = true;
            spinner.classList.remove("d-none");
            errorBox.classList.add("d-none");
            resultCard.classList.add("d-none");

            // Recalculate first
            recalculateDerivedFeatures();

            const payload = {
                "profile pic": parseInt(document.getElementById("profile_pic").value),
                "nums/length username": parseFloat(document.getElementById("nums_length_username").value),
                "fullname words": parseInt(document.getElementById("fullname_words").value),
                "nums/length fullname": parseFloat(document.getElementById("nums_length_fullname").value),
                "name==username": parseInt(document.getElementById("name_equals_username").value),
                "description length": parseInt(document.getElementById("description_length").value),
                "external URL": parseInt(document.getElementById("external_url").value),
                "private": parseInt(document.getElementById("private").value),
                "#posts": parseInt(document.getElementById("posts").value),
                "#followers": parseInt(document.getElementById("followers").value),
                "#follows": parseInt(document.getElementById("follows").value)
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
