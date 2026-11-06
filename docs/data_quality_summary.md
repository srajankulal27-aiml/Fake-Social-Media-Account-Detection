# Data Quality and Preprocessing Summary

## 1. Dataset Origin & Provenance
- **Dataset Identification:** Instagram Fake Spammer Genuine Accounts
- **Source Repository:** `https://github.com/deepd1534/instagram-fake-account-detection` (Mirrored from original benchmark on Kaggle: `free4ever1/instagram-fake-spammer-genuine-accounts`)
- **Direct Raw Download Links:**
  - `https://raw.githubusercontent.com/deepd1534/instagram-fake-account-detection/master/train.csv`
  - `https://raw.githubusercontent.com/deepd1534/instagram-fake-account-detection/master/test.csv`
- **Original Author:** Deep Sasmal (GitHub mirror) / Kaggle user `free4ever1`
- **Licence:** TBD (Public academic & educational benchmark repository; Kaggle standard dataset terms; subject to platform data harvesting terms)

---

## 2. Ingestion & Raw Data Inspection

### Raw File Shapes
- `data/raw/train.csv`: 576 rows × 12 columns
- `data/raw/test.csv`: 120 rows × 12 columns
- **Combined Raw Dataset:** 696 rows × 12 columns

### Column Names and Data Types (Combined Raw)
| Column Name | Raw Data Type | Description |
| :--- | :--- | :--- |
| `profile pic` | `int64` | Binary flag (1 = profile picture present, 0 = absent) |
| `nums/length username` | `float64` | Ratio of digits to total username character length |
| `fullname words` | `int64` | Count of whitespace-separated tokens in full name |
| `nums/length fullname` | `float64` | Ratio of digits to total full name character length |
| `name==username` | `int64` | Binary flag (1 = full name matches username, 0 = distinct) |
| `description length` | `int64` | Character count of user biography |
| `external URL` | `int64` | Binary flag (1 = website URL present, 0 = absent) |
| `private` | `int64` | Binary flag (1 = private account, 0 = public) |
| `#posts` | `int64` | Total media posts published by account |
| `#followers` | `int64` | Number of accounts following this profile |
| `#follows` | `int64` | Number of accounts this profile follows |
| `fake` | `int64` | Target classification label (1 = fake/bot, 0 = genuine) |

---

## 3. Data Quality Audit & Cleaning Operations

### Duplicate Detection
- Duplicates in raw `train.csv`: 2 rows
- Duplicates in raw `test.csv`: 2 rows
- **Total Duplicate Rows Removed Across Combined Data:** 4 rows
- **Rows Remaining After Deduplication:** 692 rows (from 696)

### Missing Value Inspection
- Missing values identified across all 12 columns in raw ingestion: **0 missing cells**.
- Imputation architecture: Robust `handle_missing_values()` mechanism implemented (numeric median, categorical mode) fitted strictly on the training partition to prevent leakage in inference or evaluation.

### Impossible & Out-of-Bounds Value Audit
- Tested constraints: All count metrics (`#posts`, `#followers`, `#follows`, `fullname words`, `description length`) and ratios (`nums/length username`, `nums/length fullname`) verified non-negative (min values $\ge 0.0$).
- No impossible negative values detected in raw records.

---

## 4. Train/Test Stratified Partitioning

To avoid reliance on arbitrary legacy splits, the deduplicated dataset was partitioned using a strict stratified 80/20 split with fixed random seed (`RANDOM_STATE = 42`).

- **Total Cleaned Records:** 692
- **Training Set (`data/processed/train.csv`):** 553 rows (80.0%)
- **Hold-out Test Set (`data/processed/test.csv`):** 139 rows (20.0%)

### Class Balance Comparison
| Partition | Genuine (`fake = 0`) | Fake/Bot (`fake = 1`) | Total Rows | Fake Ratio |
| :--- | :--- | :--- | :--- | :--- |
| **Combined Clean** | 347 | 345 | 692 | 49.86% |
| **Train Set** | 277 | 276 | 553 | 49.91% |
| **Test Set** | 70 | 69 | 139 | 49.64% |

> **Audit Note:** The dataset displays near-perfect class balance (~50% genuine vs ~50% fake). The hold-out test set (`data/processed/test.csv`) is preserved untouched for final evaluation only.

