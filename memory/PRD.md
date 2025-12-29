# CAD Finance & Business Suite - Product Requirements Document

## Original Problem Statement
Build a professional-grade, mobile-responsive CAD Finance & Business Suite for an Ontario resident, starting January 1, 2026.

## User Personas
- **Primary User**: Ontario resident freelancer/gig worker (Uber Eats driver)
- **Secondary Stakeholder**: Sister (for household bill splitting)

## What's Been Implemented (December 29, 2025)

### Backend (FastAPI + MongoDB)
- [x] User registration and login with JWT
- [x] Emergent Google OAuth integration
- [x] TOTP 2FA setup with 10 backup codes
- [x] Profile management with home office, EV details, goals
- [x] Transaction CRUD with business/personal categorization
- [x] Mileage log tracking (Business vs Personal)
- [x] EV Charging sessions with Grizzl-E rebate ($0.03/kWh)
- [x] Sister module with 50/50 bill splitting
- [x] PDF generation with Grizzl-E Energy Credit section
- [x] CSV export for CRA backup
- [x] **Tax Projection Calculator** (What-If RRSP analysis)
- [x] Tax Engine with **2026 Official Rates**:
  - Federal: 14% (first $58,523), 20.5%, 26%, 29%, 33%
  - Basic Personal Amount: $16,452
  - Ontario brackets with BPA $12,399
  - CPP 11.9% on first $74,600
  - CPP2 8% on $74,600-$85,000
  - Class 54 EV depreciation (55% on first $61,000)
- [x] **Grizzl-E Rebate Logic**:
  - Net Energy Cost = Gross - Rebate
  - Business Deduction based on NET cost
  - Rebate as Personal Credit (not split with sister)

### Frontend (React + Tailwind + Shadcn)
- [x] Professional dark theme with emerald accents
- [x] Mobile-first responsive design
- [x] Login/Register with Google OAuth
- [x] Setup Wizard with **EV $61k cap tooltip**
- [x] Dashboard with Net Worth, Tax Liability, Goals
- [x] **Tax Projection Calculator Page**:
  - RRSP contribution slider
  - Real-time tax savings calculation
  - Bracket drop detection
  - Optimal RRSP suggestion
  - 2026 brackets reference
- [x] Transactions, Mileage, EV Charging pages
- [x] Sister Module with PDF export
- [x] Settings with **2FA backup codes download**

## 2026 Tax Specifications Implemented

### Federal Brackets
| Threshold | Rate |
|-----------|------|
| First $58,523 | 14% |
| $58,523 - $117,045 | 20.5% |
| $117,045 - $181,440 | 26% |
| $181,440 - $258,482 | 29% |
| Above $258,482 | 33% |

### Key Limits
- Basic Personal Amount: $16,452
- RRSP Limit: $31,560
- TFSA Limit: $7,000
- CPP Max Pensionable: $74,600
- CPP2 Max: $85,000
- Class 54 CCA Cap: $61,000 + tax

## Prioritized Backlog

### P0 (Done)
- All core features ✓
- 2026 tax brackets ✓
- Tax projection calculator ✓
- Grizzl-E rebate logic ✓
- 2FA backup codes ✓

### P1 (Next Sprint)
- [ ] Edit functionality for transactions/mileage/charging
- [ ] Monthly income/expense trends chart
- [ ] Recurring transaction automation

### P2 (Future)
- [ ] Receipt image upload with OCR
- [ ] Bank integration (Plaid)
- [ ] T2125 form generation
