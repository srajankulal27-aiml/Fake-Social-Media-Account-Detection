// Vanilla JavaScript helper functions for FSMD frontend

document.addEventListener("DOMContentLoaded", () => {
    // Single Prediction Form Handler
    const predictForm = document.getElementById("predict-form");
    if (predictForm) {
        predictForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = document.getElementById("predict-submit-btn");
            const spinner = document.getElementById("predict-spinner");
            const errorBox = document.getElementById("predict-error");
            const resultCard = document.getElementById("predict-result-card");

            btn.disabled = true;
            spinner.classList.remove("d-none");
            errorBox.classList.add("d-none");
            resultCard.classList.add("d-none");

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
                    throw new Error(errData.detail || "Batch detection failed.");
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

    // Clear History Handler
    const clearHistoryBtn = document.getElementById("clear-history-btn");
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener("click", async () => {
            if (!confirm("Are you sure you want to clear all prediction history?")) return;
            try {
                const res = await fetch("/api/history", { method: "DELETE" });
                if (res.ok) {
                    window.location.reload();
                } else {
                    alert("Failed to clear history.");
                }
            } catch (e) {
                alert("Error connecting to server.");
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

    const isFake = data.is_fake === 1;
    badge.className = isFake ? "badge bg-danger p-2 fs-5" : "badge bg-success p-2 fs-5";
    badge.textContent = data.label;

    const probPercent = Math.round(data.fake_probability * 100);
    probBar.style.width = probPercent + "%";
    probBar.textContent = probPercent + "%";
    probBar.className = isFake ? "progress-bar bg-danger" : "progress-bar bg-success";

    probText.textContent = `Fake Probability: ${probPercent}% | Genuine Probability: ${Math.round(data.genuine_probability * 100)}%`;

    riskBadge.textContent = data.risk_level;
    if (data.risk_level === "Low Risk") {
        riskBadge.className = "badge badge-risk-low px-3 py-2 fs-6";
    } else if (data.risk_level === "Needs Review") {
        riskBadge.className = "badge badge-risk-review px-3 py-2 fs-6";
    } else {
        riskBadge.className = "badge badge-risk-high px-3 py-2 fs-6";
    }

    featuresList.innerHTML = "";
    if (data.top_features && data.top_features.length) {
        data.top_features.forEach((f) => {
            const isTowardFake = f.direction === "Toward Fake";
            const dirBadgeClass = isTowardFake ? "bg-danger" : (f.type === "global" ? "bg-secondary" : "bg-success");
            const barBgClass = isTowardFake ? "bg-danger" : (f.type === "global" ? "bg-primary" : "bg-success");
            const absPct = Math.min(Math.round(Math.abs(f.contribution) * 200), 100); // scaled percentage for visualization
            
            const item = document.createElement("div");
            item.className = "feature-bar-container mb-3";
            item.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <div>
                        <strong class="font-monospace">${f.feature}</strong>
                        <span class="text-muted small ms-1">(value: ${f.value !== null && f.value !== undefined ? f.value : 'N/A'})</span>
                    </div>
                    <div>
                        <span class="badge ${dirBadgeClass}">${f.direction}</span>
                        <span class="small fw-bold ms-1">${f.contribution > 0 ? '+' : ''}${f.contribution.toFixed(4)}</span>
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
