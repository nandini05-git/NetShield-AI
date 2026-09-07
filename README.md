# NetShield AI: Network Anomaly Detection & Threat Monitoring System

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![React: 18](https://img.shields.io/badge/Frontend-React_18-61DAFB.svg)](https://react.dev/)
[![Database: PostgreSQL + MongoDB](https://img.shields.io/badge/Databases-PostgreSQL_|_MongoDB-336791.svg)]()
[![AI: Random Forest](https://img.shields.io/badge/AI_Engine-Random_Forest-brightgreen.svg)]()

> **NetShield AI** is an enterprise-grade, AI-powered network anomaly detection and threat monitoring system designed for Security Operations Centers (SOCs). It leverages a high-performance **Random Forest Classifier** (78 statistical flow features) to monitor network flows, classify malicious incursions (`BENIGN`, `DDoS`, `FTP-Patator`, `SSH-Patator`), calculate real-time risk scores (0–100), and orchestrate automated incident responses.

---

## 📑 Table of Contents
1. [Objective & Scope](#-objective--scope)
2. [System Architecture & Pipeline](#-system-architecture--pipeline)
3. [Core Modules](#-core-modules)
4. [Milestones Summary](#-milestones-summary)
5. [Model Evaluation & Metrics](#-model-evaluation--metrics)
6. [Tech Stack](#-tech-stack)
7. [Getting Started & Running](#-getting-started--running)
8. [Default Credentials](#-default-credentials)

---

## 🎯 Objective & Scope
The platform provides centralized, end-to-end network security monitoring:
- **Continuous Traffic Telemetry**: Analyzes PCAP flow extracts and real-time network streams.
- **Intrusion Prediction**: Classifies multi-class traffic using 78 statistical network flow features via a Random Forest Classifier.
- **Threat Intelligence**: Dynamic aggregation of attacker IPs, target destination endpoints, and risk distributions.
- **SOC Alert & Incident Management**: Automated alert generation, analyst assignment, and incident resolution tracking.

---

## 🏛️ System Architecture & Pipeline

```
 [ Traffic Collection ] ──► [ Preprocessing ] ──► [ Feature Extraction (78 Features) ]
                                                            │
                                                            ▼
 [ Alert & Response ] ◄── [ Risk Scoring (0-100) ] ◄── [ Random Forest Inference ]
```

1. **Traffic Collection**: Wireshark PCAP captures, CICFlowMeter CSV datasets, network interfaces.
2. **Traffic Preprocessing**: Missing value imputation, standard scaling, label encoding.
3. **Feature Extraction**: 78 statistical features (Flow duration, packet rates, byte rates, TCP flags, window sizes).
4. **Random Forest Inference**: High-precision multi-class classification (`BENIGN`, `DDoS`, `FTP-Patator`, `SSH-Patator`).
5. **Risk Scoring Engine**: 0–100 severity index mapped to 4 threat tiers (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
6. **SOC Alert & Response**: Automatic alert dispatch, incident escalation, and notifications.

---

## 🧩 Core Modules

| Module | Description | Key Features |
| :--- | :--- | :--- |
| **1. User Management** | Access Control & Auditing | JWT Authentication, RBAC (Admin, Analyst, Auditor), Audit Logs |
| **2. Network Monitoring** | Real-time Traffic Diagnostics | Throughput Curves (KB/s), Protocol Donut, Port Inspector, Interface Stats |
| **3. Anomaly Detection** | Behavioral Flow Analysis | 78-feature vector analysis, packet length variance, flow duration heuristics |
| **4. Intrusion Prediction** | Random Forest Classifier | Real-time prediction, confidence scoring (%), risk score calculation |
| **5. Alert Management** | Incident Management System | Prioritized SOC alerts, incident escalation, assign analyst, resolve tracking |
| **6. Analytics Dashboard** | Visual Intelligence Suite | Executive KPIs, 7-day Weekly Security Trends, Attack Visualizations |
| **7. Threat Intelligence** | Signature & Risk Profiling | Top threat vectors, attacker IP profiling, attack class accuracy telemetry |

---

## 🗓️ Milestones Summary

- **Milestone 1 (Weeks 1 & 2)**: Core setup, authentication, database schema, network monitoring workflows, traffic dashboard.
- **Milestone 2 (Weeks 3 & 4)**: Random Forest model training, 78-feature extraction, model evaluation, risk scoring engine.
- **Milestone 3 (Weeks 5 & 6)**: Alert management, incident response workflows, threat intelligence reporting, attack visualization.
- **Milestone 4 (Weeks 7 & 8)**: FastAPI migration, PostgreSQL & MongoDB integration, test suites (`pytest`), Docker containerization (`docker-compose`), production evaluation metrics against ground-truth flow labels.

---

## 📊 Model Evaluation & Metrics

- **Production Model**: Random Forest Classifier (`sklearn.ensemble.RandomForestClassifier`)
- **Features Extracted**: 78 statistical network flow features
- **Attack Classes**: 4 (`BENIGN`, `DDoS`, `FTP-Patator`, `SSH-Patator`)
- **Evaluation Mechanism**: Evaluated dynamically using `sklearn.metrics` (`accuracy_score`, `precision_score`, `recall_score`, `f1_score`, `confusion_matrix`) comparing `actual_label` vs `predicted_label` from database predictions.
- **Risk Score Mapping**:
  - `BENIGN`: 5 (Low)
  - `FTP-Patator`: 65 (Medium)
  - `SSH-Patator`: 80 (High)
  - `DDoS`: 95 (Critical)

---

## 💻 Tech Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn, SQLAlchemy, PyMongo
- **Frontend**: React.js 18, Recharts, React Icons, Axios, CSS3
- **Databases**: PostgreSQL 16 (Relational/Telemetry), MongoDB 7.0 (Unstructured Logs/Packets)
- **Machine Learning**: Scikit-Learn (Random Forest), Pandas, NumPy, Joblib
- **DevOps**: Docker, Docker Compose, Nginx

---

## 🚀 Getting Started & Running

### Using Docker Compose (Recommended)
```powershell
docker compose up -d --build
```
- **Web Application**: `http://localhost:3000`
- **FastAPI REST API & Docs**: `http://localhost:5000` / `http://localhost:5000/docs`
- **PostgreSQL**: `localhost:5432`
- **MongoDB**: `localhost:27017`

### Running Backend Tests
```powershell
python -m pytest -q test_fastapi_endpoints.py
```

---

## 🔐 Default Credentials

- **Administrator**: `admin@netshield.ai` / `Admin@123`
- **Security Analyst**: `analyst@netshield.ai` / `Analyst@123`
