# CAD Finance & Business Suite - Product Requirements Document

## Original Problem Statement
Build a professional-grade, mobile-responsive CAD Finance & Business Suite for an Ontario resident, starting January 1, 2026.

## User Personas
- **Primary User**: Ontario resident freelancer/gig worker (Uber Eats driver)
- **Secondary Stakeholder**: Sister (for household bill splitting)

## Core Requirements
1. **Command Center Dashboard**: Net Worth, Tax Liability, Goal Tracker
2. **Quick-Entry Wizard**: FAB (+) with 3-step wizard for Income, Business Expense, Personal Expense, EV Charge
3. **Tax Engine**: 2026 Canadian tax compliance with CPP/CPP2, Class 54 EV depreciation
4. **Sister Module**: Household bill splitting with PDF export (data siloed)
5. **Security**: TOTP 2FA, JWT auth, Google OAuth

## User Choices
- Auth: Email/Password + Google Social Login
- Database: MongoDB
- 2FA: TOTP-based (Google Authenticator style)
- PDF: Server-side generation (ReportLab)
- Theme: Professional dark theme

## What's Been Implemented (December 29, 2025)

### Backend (FastAPI + MongoDB)
- [x] User registration and login with JWT
- [x] Emergent Google OAuth integration
- [x] TOTP 2FA setup and verification
- [x] Profile management with home office, EV details, goals
- [x] Transaction CRUD with business/personal categorization
- [x] Mileage log tracking (Business vs Personal)
- [x] EV Charging sessions with $0.03/kWh rebate
- [x] Sister module with 50/50 bill splitting
- [x] PDF generation for household expense reports
- [x] CSV export for CRA backup
- [x] Tax Engine with 2026 rates:
  - Federal brackets (15%-33%)
  - Ontario brackets (5.05%-13.16%)
  - CPP 11.9% on first $74,600
  - CPP2 8% on $74,600-$85,000
  - Class 54 EV depreciation (55% on first $61,000)
  - Home office deduction calculation

### Frontend (React + Tailwind + Shadcn)
- [x] Professional dark theme with emerald accents
- [x] Mobile-first responsive design
- [x] Login/Register pages with Google OAuth
- [x] Setup Wizard (5 steps: Welcome, Home Office, EV, Balances, Goals)
- [x] Dashboard with:
  - Net Worth card (Savings + TFSA + RRSP - Debt)
  - Tax Liability with pie chart
  - Business Income with deductions
  - Goal Tracker (Waterfall: Debt → TFSA → RRSP)
  - Quick stats (Mileage, EV Charging, Income, Expenses)
- [x] Transactions page with filtering
- [x] Mileage page with business % calculation
- [x] EV Charging page with rebate tracking
- [x] Sister Module with violet accent theme
- [x] Settings page with 2FA and profile management
- [x] Quick Entry Wizard via FAB

## Prioritized Backlog

### P0 (Done)
- All core features implemented

### P1 (Next Sprint)
- [ ] Edit functionality for transactions, mileage, charging sessions
- [ ] Monthly income/expense trends chart
- [ ] Tax projection calculator
- [ ] Recurring transaction support

### P2 (Future)
- [ ] Receipt image upload and OCR
- [ ] Bank account integration (Plaid)
- [ ] Multi-year historical data
- [ ] Tax form generation (T2125)

## Next Tasks
1. Add edit functionality for all CRUD entities
2. Implement monthly trends visualization
3. Add tax projection "what-if" calculator
4. Build recurring transaction automation
