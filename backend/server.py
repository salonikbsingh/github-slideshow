from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, status
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pyotp
import qrcode
from io import BytesIO
import base64
import bcrypt
import jwt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'cad-finance-suite-secret-key-2026')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

app = FastAPI(title="CAD Finance & Business Suite API")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =============== PYDANTIC MODELS ===============

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TOTPVerify(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)

class ProfileCreate(BaseModel):
    province: str = "Ontario"
    home_sqft: float = 0
    office_sqft: float = 0
    ev_purchase_price: float = 0
    ev_purchase_date: Optional[str] = None
    opening_ucc: float = 0
    total_debt: float = 0
    total_savings: float = 0
    tfsa_balance: float = 0
    rrsp_balance: float = 0
    # Contribution room (includes unused room from previous years)
    tfsa_contribution_room: float = 7000  # Available room to contribute
    rrsp_contribution_room: float = 31560  # Available room to contribute
    # Annual goals (how much to contribute this year)
    tfsa_goal: float = 7000
    rrsp_goal: float = 31560
    debt_goal: float = 0
    business_use_percent: float = 100  # Default business use % for EV
    ei_opt_in: bool = False  # EI is optional for self-employed

class TransactionCreate(BaseModel):
    date: str
    amount: float
    category: str
    type: str  # Income, Expense
    is_business: bool = False
    business_use_percent: float = 100
    split_with_sister: bool = False
    description: Optional[str] = ""

class MileageLogCreate(BaseModel):
    date: str
    start_km: float
    end_km: float
    purpose: str  # Business or Personal

class ChargingSessionCreate(BaseModel):
    date: str
    kwh: float
    cost: float
    location: str

class SisterBillCreate(BaseModel):
    date: str
    category: str
    amount: float
    description: str

# =============== HELPER FUNCTIONS ===============

def generate_user_id():
    return str(uuid.uuid4())

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request):
    # Check cookie first, then Authorization header
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check user_sessions collection
    session = await db.user_sessions.find_one({"session_token": session_token, "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}}, {"_id": 0})
    if session:
        user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
        if user:
            return user
    
    # Try JWT decode for local auth
    try:
        payload = jwt.decode(session_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if user:
            return user
    except jwt.PyJWTError:
        pass
    
    raise HTTPException(status_code=401, detail="Invalid or expired token")

# =============== TAX CALCULATION ENGINE (2026 Official Specifications) ===============

class TaxEngine:
    # 2026 OFFICIAL Federal Tax Brackets
    FEDERAL_BRACKETS = [
        (58523, 0.14),      # Rate 1: 14% on first $58,523
        (58522, 0.205),     # Rate 2: 20.5% on $58,523 to $117,045
        (64395, 0.26),      # Rate 3: 26% on $117,045 to $181,440
        (77042, 0.29),      # Rate 4: 29% on $181,440 to $258,482
        (float('inf'), 0.33) # Rate 5: 33% on income over $258,482
    ]
    
    # 2026 Ontario Tax Brackets (Indexed)
    ONTARIO_BRACKETS = [
        (53891, 0.0505),     # 5.05% on first $53,891
        (53894, 0.0915),     # 9.15% on $53,891 to $107,785
        (42215, 0.1116),     # 11.16% on $107,785 to $150,000
        (70000, 0.1216),     # 12.16% on $150,000 to $220,000
        (float('inf'), 0.1316) # 13.16% on everything over $220,000
    ]
    
    # 2026 Basic Personal Amounts
    FEDERAL_BPA = 16452
    ONTARIO_BPA = 12989
    
    # 2026 CPP/CPP2 rates (Self-Employed pays both portions)
    CPP_MAX_EARNINGS = 74600
    CPP2_MAX_EARNINGS = 85000
    CPP_RATE = 0.119  # 11.9% for self-employed (employee + employer)
    CPP2_RATE = 0.08  # 8% for CPP2
    CPP_EXEMPTION = 3500
    
    # 2026 EI for Self-Employed (Optional)
    EI_RATE = 0.0163  # 1.63%
    EI_MAX_INSURABLE = 68900
    EI_MAX_PREMIUM = 1123.07
    
    # Class 54 EV Depreciation - 55% on first $61,000 + tax
    EV_CLASS_54_RATE = 0.55
    EV_CLASS_54_LIMIT = 61000
    
    # Grizzl-E Club Rebate
    GRIZZLE_REBATE_PER_KWH = 0.03
    
    @classmethod
    def calculate_federal_tax(cls, income: float) -> float:
        """Calculate Federal tax with BPA applied"""
        taxable_income = max(0, income - cls.FEDERAL_BPA)
        tax = 0
        remaining = taxable_income
        for bracket_size, rate in cls.FEDERAL_BRACKETS:
            if remaining <= 0:
                break
            taxable = min(remaining, bracket_size)
            tax += taxable * rate
            remaining -= bracket_size
        return tax
    
    @classmethod
    def calculate_ontario_tax(cls, income: float) -> float:
        """Calculate Ontario Provincial tax with BPA applied"""
        taxable_income = max(0, income - cls.ONTARIO_BPA)
        tax = 0
        remaining = taxable_income
        for bracket_size, rate in cls.ONTARIO_BRACKETS:
            if remaining <= 0:
                break
            taxable = min(remaining, bracket_size)
            tax += taxable * rate
            remaining -= bracket_size
        return tax
    
    @classmethod
    def calculate_ontario_health_premium(cls, taxable_income: float) -> float:
        """
        Ontario Health Premium (OHP) - Sliding Scale
        Based on taxable income thresholds
        """
        if taxable_income <= 20000:
            return 0
        elif taxable_income <= 25000:
            # $0 + 6% of income over $20,000 (max $300)
            return min(300, (taxable_income - 20000) * 0.06)
        elif taxable_income <= 36000:
            # $300 base
            return 300
        elif taxable_income <= 38500:
            # $300 + 6% of income over $36,000 (max $450)
            return min(450, 300 + (taxable_income - 36000) * 0.06)
        elif taxable_income <= 48000:
            # $450 base
            return 450
        elif taxable_income <= 48600:
            # $450 + 25% of income over $48,000 (max $600)
            return min(600, 450 + (taxable_income - 48000) * 0.25)
        elif taxable_income <= 72000:
            # $600 base
            return 600
        elif taxable_income <= 72600:
            # $600 + 25% of income over $72,000 (max $750)
            return min(750, 600 + (taxable_income - 72000) * 0.25)
        elif taxable_income <= 200000:
            # $750 base
            return 750
        elif taxable_income <= 200600:
            # $750 + 25% of income over $200,000 (max $900)
            return min(900, 750 + (taxable_income - 200000) * 0.25)
        else:
            # Maximum $900
            return 900
    
    @classmethod
    def calculate_cpp(cls, net_income: float) -> dict:
        """
        CPP/CPP2 for Self-Employed
        Self-employed pay both employee AND employer portions (11.9% total)
        """
        # CPP on first $74,600 (minus $3,500 exemption)
        cpp_pensionable = max(0, min(net_income, cls.CPP_MAX_EARNINGS) - cls.CPP_EXEMPTION)
        cpp = cpp_pensionable * cls.CPP_RATE
        
        # CPP2 on income between $74,600 and $85,000
        cpp2_pensionable = max(0, min(net_income, cls.CPP2_MAX_EARNINGS) - cls.CPP_MAX_EARNINGS)
        cpp2 = cpp2_pensionable * cls.CPP2_RATE
        
        return {"cpp": cpp, "cpp2": cpp2, "total": cpp + cpp2}
    
    @classmethod
    def calculate_ei(cls, net_income: float, opt_in: bool = False) -> float:
        """
        EI for Self-Employed (OPTIONAL)
        Rate: 1.63%, Max Insurable: $68,900, Max Premium: $1,123.07
        """
        if not opt_in:
            return 0
        insurable_earnings = min(net_income, cls.EI_MAX_INSURABLE)
        ei_premium = insurable_earnings * cls.EI_RATE
        return min(ei_premium, cls.EI_MAX_PREMIUM)
    
    @classmethod
    def calculate_total_tax(cls, net_income: float, ei_opt_in: bool = False) -> dict:
        """
        Calculate complete tax liability:
        Federal + Ontario + OHP + CPP + CPP2 + EI (optional)
        """
        federal = cls.calculate_federal_tax(net_income)
        ontario = cls.calculate_ontario_tax(net_income)
        ohp = cls.calculate_ontario_health_premium(net_income)
        cpp = cls.calculate_cpp(net_income)
        ei = cls.calculate_ei(net_income, ei_opt_in)
        
        total = federal + ontario + ohp + cpp["total"] + ei
        
        return {
            "federal": federal,
            "ontario": ontario,
            "ontario_health_premium": ohp,
            "cpp": cpp["cpp"],
            "cpp2": cpp["cpp2"],
            "ei": ei,
            "ei_opted_in": ei_opt_in,
            "total": total
        }
    
    @classmethod
    def calculate_ev_depreciation(cls, ucc: float, is_first_year: bool = False) -> dict:
        """Class 54 EV Depreciation - 55% on first $61,000 + tax"""
        applicable_ucc = min(ucc, cls.EV_CLASS_54_LIMIT * 1.13)
        rate = cls.EV_CLASS_54_RATE
        if is_first_year:
            rate = rate / 2  # Half-year rule
        depreciation = applicable_ucc * rate
        cca_capped = ucc > cls.EV_CLASS_54_LIMIT
        return {
            "depreciation": depreciation,
            "ending_ucc": ucc - depreciation,
            "cca_capped": cca_capped,
            "cap_limit": cls.EV_CLASS_54_LIMIT
        }
    
    @classmethod
    def calculate_home_office_deduction(cls, home_sqft: float, office_sqft: float, total_expenses: float) -> float:
        if home_sqft <= 0:
            return 0
        ratio = office_sqft / home_sqft
        return total_expenses * ratio
    
    @classmethod
    def calculate_grizzle_energy_cost(cls, total_kwh: float, utility_rate: float, business_use_percent: float = 100) -> dict:
        """
        Grizzl-E Club Rebate Logic for EV charging
        - Rebate: $0.03/kWh cashback
        - Net cost used for business deduction
        - Rebate tracked as Revenue Offset (personal credit, not split with sister)
        """
        gross_cost = total_kwh * utility_rate
        grizzle_rebate = total_kwh * cls.GRIZZLE_REBATE_PER_KWH
        net_cost = gross_cost - grizzle_rebate
        
        # Business deduction is based on NET cost × business use %
        business_deduction = net_cost * (business_use_percent / 100)
        
        return {
            "gross_utility_expense": gross_cost,
            "grizzle_cashback": grizzle_rebate,
            "net_energy_cost": net_cost,
            "business_use_percent": business_use_percent,
            "net_deductible_amount": business_deduction,  # For T2125
            "revenue_offset": grizzle_rebate  # Personal credit, not split
        }
    
    @classmethod
    def calculate_tax_projection(cls, current_income: float, rrsp_contribution: float = 0) -> dict:
        """
        What-If Tax Projection Calculator
        Shows how RRSP contributions affect tax liability and brackets
        """
        # Current tax without RRSP
        current_taxable = current_income
        current_federal = cls.calculate_federal_tax(current_taxable)
        current_ontario = cls.calculate_ontario_tax(current_taxable)
        current_cpp = cls.calculate_cpp(current_taxable)
        current_total = current_federal + current_ontario + current_cpp["total"]
        
        # Projected tax with RRSP contribution
        projected_taxable = max(0, current_income - rrsp_contribution)
        projected_federal = cls.calculate_federal_tax(projected_taxable)
        projected_ontario = cls.calculate_ontario_tax(projected_taxable)
        projected_cpp = cls.calculate_cpp(projected_taxable)  # CPP not reduced by RRSP
        projected_total = projected_federal + projected_ontario + current_cpp["total"]  # CPP same
        
        # Tax savings
        federal_savings = current_federal - projected_federal
        ontario_savings = current_ontario - projected_ontario
        total_savings = federal_savings + ontario_savings
        
        # Determine current and projected brackets
        def get_federal_bracket(income):
            brackets = [
                (58523, "14%"),
                (117045, "20.5%"),
                (181440, "26%"),
                (258482, "29%"),
                (float('inf'), "33%")
            ]
            for threshold, rate in brackets:
                if income <= threshold:
                    return rate
            return "33%"
        
        current_bracket = get_federal_bracket(current_taxable - cls.FEDERAL_BPA)
        projected_bracket = get_federal_bracket(projected_taxable - cls.FEDERAL_BPA)
        bracket_dropped = current_bracket != projected_bracket
        
        # Calculate optimal RRSP to drop a bracket
        bracket_thresholds = [58523, 117045, 181440, 258482]
        optimal_rrsp = 0
        for threshold in bracket_thresholds:
            if current_taxable - cls.FEDERAL_BPA > threshold:
                excess = (current_taxable - cls.FEDERAL_BPA) - threshold
                if excess > 0 and excess < optimal_rrsp or optimal_rrsp == 0:
                    optimal_rrsp = excess + 1  # +1 to cross threshold
        
        # Calculate OHP for both scenarios
        current_ohp = cls.calculate_ontario_health_premium(current_taxable)
        projected_ohp = cls.calculate_ontario_health_premium(projected_taxable)
        ohp_savings = current_ohp - projected_ohp
        
        # Complete totals including OHP
        current_complete_total = current_federal + current_ontario + current_ohp + current_cpp["total"]
        projected_complete_total = projected_federal + projected_ontario + projected_ohp + current_cpp["total"]
        
        return {
            "current": {
                "taxable_income": current_taxable,
                "federal_tax": current_federal,
                "ontario_tax": current_ontario,
                "ontario_health_premium": current_ohp,
                "cpp_total": current_cpp["total"],
                "total_tax": current_complete_total,
                "bracket": current_bracket
            },
            "projected": {
                "rrsp_contribution": rrsp_contribution,
                "taxable_income": projected_taxable,
                "federal_tax": projected_federal,
                "ontario_tax": projected_ontario,
                "ontario_health_premium": projected_ohp,
                "cpp_total": current_cpp["total"],  # CPP unchanged by RRSP
                "total_tax": projected_complete_total,
                "bracket": projected_bracket
            },
            "savings": {
                "federal": federal_savings,
                "ontario": ontario_savings,
                "ohp": ohp_savings,
                "total": federal_savings + ontario_savings + ohp_savings,
                "effective_rate": ((federal_savings + ontario_savings + ohp_savings) / rrsp_contribution * 100) if rrsp_contribution > 0 else 0
            },
            "bracket_dropped": bracket_dropped,
            "optimal_rrsp_to_drop_bracket": optimal_rrsp,
            "rrsp_limit_2026": 31560
        }

# =============== AUTH ENDPOINTS ===============

@api_router.post("/auth/register")
async def register(data: UserRegister):
    existing = await db.users.find_one({"email": data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = generate_user_id()
    user = {
        "user_id": user_id,
        "email": data.email,
        "name": data.name,
        "password_hash": hash_password(data.password),
        "totp_enabled": False,
        "totp_verified": False,
        "totp_secret": None,
        "setup_completed": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user)
    
    token = create_jwt_token(user_id)
    return {"user_id": user_id, "email": data.email, "name": data.name, "token": token, "totp_enabled": False, "setup_completed": False}

@api_router.post("/auth/login")
async def login(data: UserLogin, response: Response):
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user.get("totp_enabled") and user.get("totp_verified"):
        # Return partial token that requires TOTP
        temp_token = jwt.encode(
            {"user_id": user["user_id"], "requires_totp": True, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            JWT_SECRET, algorithm=JWT_ALGORITHM
        )
        return {"requires_totp": True, "temp_token": temp_token}
    
    token = create_jwt_token(user["user_id"])
    response.set_cookie(key="session_token", value=token, httponly=True, secure=True, samesite="none", path="/", max_age=86400)
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "token": token,
        "totp_enabled": user.get("totp_enabled", False),
        "setup_completed": user.get("setup_completed", False)
    }

@api_router.post("/auth/verify-totp")
async def verify_totp_login(data: TOTPVerify, request: Request, response: Response):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing temp token")
    
    temp_token = auth_header[7:]
    try:
        payload = jwt.decode(temp_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if not payload.get("requires_totp"):
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = payload["user_id"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    totp = pyotp.TOTP(user["totp_secret"])
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
    
    token = create_jwt_token(user_id)
    response.set_cookie(key="session_token", value=token, httponly=True, secure=True, samesite="none", path="/", max_age=86400)
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "token": token,
        "totp_enabled": True,
        "setup_completed": user.get("setup_completed", False)
    }

# REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
@api_router.get("/auth/session-data")
async def get_session_data(request: Request, response: Response):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session ID")
    
    # Fetch from Emergent Auth
    import requests
    try:
        resp = requests.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
            timeout=10
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        data = resp.json()
        user_id = data.get("id")
        email = data.get("email")
        name = data.get("name")
        picture = data.get("picture")
        session_token = data.get("session_token")
        
        # Check if user exists
        existing_user = await db.users.find_one({"email": email}, {"_id": 0})
        if existing_user:
            user_id = existing_user["user_id"]
            await db.users.update_one({"user_id": user_id}, {"$set": {"name": name, "picture": picture}})
        else:
            user_id = generate_user_id()
            await db.users.insert_one({
                "user_id": user_id,
                "email": email,
                "name": name,
                "picture": picture,
                "totp_enabled": False,
                "totp_verified": False,
                "setup_completed": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
        
        # Store session
        await db.user_sessions.insert_one({
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        response.set_cookie(key="session_token", value=session_token, httponly=True, secure=True, samesite="none", path="/", max_age=604800)
        
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        return {
            "user_id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "session_token": session_token,
            "totp_enabled": user.get("totp_enabled", False),
            "setup_completed": user.get("setup_completed", False)
        }
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "picture": user.get("picture"),
        "totp_enabled": user.get("totp_enabled", False),
        "setup_completed": user.get("setup_completed", False)
    }

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out"}

# =============== TOTP 2FA ENDPOINTS ===============

def generate_backup_codes(count: int = 10) -> list:
    """Generate random backup codes for 2FA recovery"""
    import secrets
    return [f"{secrets.token_hex(3)}-{secrets.token_hex(3)}" for _ in range(count)]

@api_router.post("/auth/totp/setup")
async def setup_totp(user: dict = Depends(get_current_user)):
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user["email"], issuer_name="CAD Finance Suite")
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # Generate backup codes
    backup_codes = generate_backup_codes(10)
    hashed_backup_codes = [hash_password(code) for code in backup_codes]
    
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "totp_secret": secret, 
            "totp_enabled": True, 
            "totp_verified": False,
            "backup_codes": hashed_backup_codes
        }}
    )
    
    return {
        "secret": secret, 
        "qr_code": f"data:image/png;base64,{qr_base64}", 
        "provisioning_uri": provisioning_uri,
        "backup_codes": backup_codes  # Only returned once during setup!
    }

@api_router.post("/auth/totp/verify")
async def verify_totp_setup(data: TOTPVerify, user: dict = Depends(get_current_user)):
    if not user.get("totp_secret"):
        raise HTTPException(status_code=400, detail="TOTP not set up")
    
    totp = pyotp.TOTP(user["totp_secret"])
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
    
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"totp_verified": True}})
    return {"success": True, "message": "2FA enabled successfully"}

@api_router.post("/auth/totp/disable")
async def disable_totp(data: TOTPVerify, user: dict = Depends(get_current_user)):
    if not user.get("totp_secret"):
        raise HTTPException(status_code=400, detail="TOTP not enabled")
    
    totp = pyotp.TOTP(user["totp_secret"])
    if not totp.verify(data.code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
    
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"totp_enabled": False, "totp_verified": False, "totp_secret": None, "backup_codes": []}}
    )
    return {"success": True, "message": "2FA disabled"}

@api_router.post("/auth/totp/use-backup")
async def use_backup_code(code: str, request: Request, response: Response):
    """Use a backup code for emergency 2FA recovery"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing temp token")
    
    temp_token = auth_header[7:]
    try:
        payload = jwt.decode(temp_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if not payload.get("requires_totp"):
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = payload["user_id"]
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check backup codes
    backup_codes = user.get("backup_codes", [])
    code_valid = False
    remaining_codes = []
    
    for hashed_code in backup_codes:
        if verify_password(code, hashed_code):
            code_valid = True
        else:
            remaining_codes.append(hashed_code)
    
    if not code_valid:
        raise HTTPException(status_code=401, detail="Invalid backup code")
    
    # Remove used code
    await db.users.update_one({"user_id": user_id}, {"$set": {"backup_codes": remaining_codes}})
    
    # Generate session token
    token = create_jwt_token(user_id)
    response.set_cookie(key="session_token", value=token, httponly=True, secure=True, samesite="none", path="/", max_age=86400)
    
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "token": token,
        "remaining_backup_codes": len(remaining_codes)
    }

# =============== PROFILE ENDPOINTS ===============

@api_router.post("/profile")
async def create_profile(data: ProfileCreate, user: dict = Depends(get_current_user)):
    profile = {
        "user_id": user["user_id"],
        **data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.profiles.update_one(
        {"user_id": user["user_id"]},
        {"$set": profile},
        upsert=True
    )
    await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"setup_completed": True}})
    return {"success": True, "profile": profile}

@api_router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    profile = await db.profiles.find_one({"user_id": user["user_id"]}, {"_id": 0})
    return profile or {}

@api_router.put("/profile")
async def update_profile(data: ProfileCreate, user: dict = Depends(get_current_user)):
    update_data = data.model_dump()
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.profiles.update_one({"user_id": user["user_id"]}, {"$set": update_data})
    return {"success": True}

# =============== TRANSACTION ENDPOINTS ===============

@api_router.post("/transactions")
async def create_transaction(data: TransactionCreate, user: dict = Depends(get_current_user)):
    transaction = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        **data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.transactions.insert_one(transaction)
    return {"success": True, "transaction": {k: v for k, v in transaction.items() if k != "_id"}}

@api_router.get("/transactions")
async def get_transactions(user: dict = Depends(get_current_user), limit: int = 100, skip: int = 0):
    cursor = db.transactions.find({"user_id": user["user_id"]}, {"_id": 0}).sort("date", -1).skip(skip).limit(limit)
    transactions = await cursor.to_list(limit)
    return transactions

@api_router.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str, user: dict = Depends(get_current_user)):
    result = await db.transactions.delete_one({"id": transaction_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"success": True}

# =============== MILEAGE LOG ENDPOINTS ===============

@api_router.post("/mileage")
async def create_mileage_log(data: MileageLogCreate, user: dict = Depends(get_current_user)):
    log = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        **data.model_dump(),
        "distance": data.end_km - data.start_km,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.mileage_log.insert_one(log)
    return {"success": True, "log": {k: v for k, v in log.items() if k != "_id"}}

@api_router.get("/mileage")
async def get_mileage_logs(user: dict = Depends(get_current_user)):
    cursor = db.mileage_log.find({"user_id": user["user_id"]}, {"_id": 0}).sort("date", -1)
    logs = await cursor.to_list(1000)
    return logs

@api_router.delete("/mileage/{log_id}")
async def delete_mileage_log(log_id: str, user: dict = Depends(get_current_user)):
    result = await db.mileage_log.delete_one({"id": log_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Log not found")
    return {"success": True}

# =============== CHARGING SESSION ENDPOINTS ===============

@api_router.post("/charging")
async def create_charging_session(data: ChargingSessionCreate, user: dict = Depends(get_current_user)):
    rebate = data.kwh * 0.03  # $0.03/kWh rebate
    session = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        **data.model_dump(),
        "rebate_earned": rebate,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.charging_sessions.insert_one(session)
    return {"success": True, "session": {k: v for k, v in session.items() if k != "_id"}}

@api_router.get("/charging")
async def get_charging_sessions(user: dict = Depends(get_current_user)):
    cursor = db.charging_sessions.find({"user_id": user["user_id"]}, {"_id": 0}).sort("date", -1)
    sessions = await cursor.to_list(1000)
    return sessions

@api_router.delete("/charging/{session_id}")
async def delete_charging_session(session_id: str, user: dict = Depends(get_current_user)):
    result = await db.charging_sessions.delete_one({"id": session_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}

# =============== SISTER MODULE ENDPOINTS ===============

@api_router.post("/sister/bills")
async def create_sister_bill(data: SisterBillCreate, user: dict = Depends(get_current_user)):
    bill = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        **data.model_dump(),
        "split_amount": data.amount / 2,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.sister_bills.insert_one(bill)
    return {"success": True, "bill": {k: v for k, v in bill.items() if k != "_id"}}

@api_router.get("/sister/bills")
async def get_sister_bills(user: dict = Depends(get_current_user)):
    cursor = db.sister_bills.find({"user_id": user["user_id"]}, {"_id": 0}).sort("date", -1)
    bills = await cursor.to_list(1000)
    return bills

@api_router.delete("/sister/bills/{bill_id}")
async def delete_sister_bill(bill_id: str, user: dict = Depends(get_current_user)):
    result = await db.sister_bills.delete_one({"id": bill_id, "user_id": user["user_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bill not found")
    return {"success": True}

@api_router.get("/sister/summary/{month}")
async def get_sister_summary(month: str, user: dict = Depends(get_current_user)):
    # month format: "2026-01"
    bills = await db.sister_bills.find(
        {"user_id": user["user_id"], "date": {"$regex": f"^{month}"}},
        {"_id": 0}
    ).to_list(1000)
    
    total = sum(b["amount"] for b in bills)
    split = total / 2
    
    by_category = {}
    for bill in bills:
        cat = bill["category"]
        by_category[cat] = by_category.get(cat, 0) + bill["amount"]
    
    return {
        "month": month,
        "total_expenses": total,
        "your_share": split,
        "sister_share": split,
        "by_category": by_category,
        "bills": bills
    }

@api_router.get("/sister/pdf/{month}")
async def generate_sister_pdf(month: str, user: dict = Depends(get_current_user)):
    summary = await get_sister_summary(month, user)
    
    # Get Grizzl-E rebate data for the month (personal credit, NOT split)
    charging_sessions = await db.charging_sessions.find(
        {"user_id": user["user_id"], "date": {"$regex": f"^{month}"}},
        {"_id": 0}
    ).to_list(1000)
    
    total_kwh = sum(s["kwh"] for s in charging_sessions)
    total_charging_cost = sum(s["cost"] for s in charging_sessions)
    grizzle_rebate = total_kwh * TaxEngine.GRIZZLE_REBATE_PER_KWH
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, spaceAfter=20, textColor=colors.HexColor("#10b981"))
    elements.append(Paragraph(f"Household Expense Summary - {month}", title_style))
    elements.append(Spacer(1, 20))
    
    # Summary Table
    summary_data = [
        ["Total Home Expenses:", f"${summary['total_expenses']:,.2f}"],
        ["Your 50% Share:", f"${summary['your_share']:,.2f}"],
        ["Sister's 50% Share:", f"${summary['sister_share']:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[200, 150])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#18181b")),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Grizzl-E Energy Credit Section (Personal Credit - NOT split)
    if total_kwh > 0:
        credit_style = ParagraphStyle('CreditTitle', parent=styles['Heading2'], textColor=colors.HexColor("#10b981"))
        elements.append(Paragraph("Grizzl-E Energy Credit Applied", credit_style))
        elements.append(Spacer(1, 10))
        
        credit_note = ParagraphStyle('CreditNote', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#71717a"))
        elements.append(Paragraph("Note: This rebate is a Personal Credit allocated to the primary account holder only and is NOT included in the 50/50 split calculation.", credit_note))
        elements.append(Spacer(1, 10))
        
        credit_data = [
            ["EV Charging (kWh):", f"{total_kwh:,.1f} kWh"],
            ["Gross Energy Cost:", f"${total_charging_cost:,.2f}"],
            ["Grizzl-E Rebate ($0.03/kWh):", f"-${grizzle_rebate:,.2f}"],
            ["Net Energy Cost:", f"${(total_charging_cost - grizzle_rebate):,.2f}"],
            ["", ""],
            ["Personal Credit (Your Ledger):", f"${grizzle_rebate:,.2f}"],
        ]
        credit_table = Table(credit_data, colWidths=[200, 150])
        credit_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 3), colors.HexColor("#0c4a2c")),
            ('BACKGROUND', (0, 5), (-1, 5), colors.HexColor("#065f46")),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(credit_table)
        elements.append(Spacer(1, 20))
    
    # Category Breakdown
    elements.append(Paragraph("By Category:", styles['Heading2']))
    for cat, amount in summary['by_category'].items():
        elements.append(Paragraph(f"  • {cat}: ${amount:,.2f}", styles['Normal']))
    elements.append(Spacer(1, 30))
    
    # Bills Table
    if summary['bills']:
        elements.append(Paragraph("Detailed Bills:", styles['Heading2']))
        bill_data = [["Date", "Category", "Description", "Amount"]]
        for bill in summary['bills']:
            bill_data.append([bill['date'], bill['category'], bill['description'], f"${bill['amount']:,.2f}"])
        
        bill_table = Table(bill_data, colWidths=[80, 100, 180, 80])
        bill_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#27272a")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#3f3f46")),
        ]))
        elements.append(bill_table)
    
    # Footer note
    elements.append(Spacer(1, 40))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor("#71717a"))
    elements.append(Paragraph("Generated by CAD Finance & Business Suite | For T2125 Business Expense Reporting", footer_style))
    
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=household_expenses_{month}.pdf"}
    )

# =============== DASHBOARD & TAX ENDPOINTS ===============

@api_router.get("/dashboard")
async def get_dashboard(user: dict = Depends(get_current_user)):
    profile = await db.profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    
    # Get current year transactions
    current_year = datetime.now().year
    transactions = await db.transactions.find(
        {"user_id": user["user_id"], "date": {"$regex": f"^{current_year}"}},
        {"_id": 0}
    ).to_list(10000)
    
    # Calculate totals
    total_income = sum(t["amount"] for t in transactions if t["type"] == "Income")
    total_business_income = sum(t["amount"] for t in transactions if t["type"] == "Income" and t.get("is_business"))
    total_expenses = sum(t["amount"] for t in transactions if t["type"] == "Expense")
    total_business_expenses = sum(
        t["amount"] * (t.get("business_use_percent", 100) / 100)
        for t in transactions if t["type"] == "Expense" and t.get("is_business")
    )
    
    # Net income for tax calculation
    net_business_income = total_business_income - total_business_expenses
    
    # Calculate home office deduction
    home_sqft = profile.get("home_sqft", 0)
    office_sqft = profile.get("office_sqft", 0)
    home_expenses = sum(
        t["amount"] for t in transactions
        if t["type"] == "Expense" and t.get("split_with_sister")
    )
    home_office_deduction = TaxEngine.calculate_home_office_deduction(home_sqft, office_sqft, home_expenses)
    
    # EV Depreciation
    opening_ucc = profile.get("opening_ucc", 0)
    ev_purchase_price = profile.get("ev_purchase_price", 0)
    ev_depreciation = TaxEngine.calculate_ev_depreciation(opening_ucc, is_first_year=True) if opening_ucc > 0 else {"depreciation": 0, "cca_capped": False}
    
    # Charging summary with Grizzl-E rebate logic
    charging_sessions = await db.charging_sessions.find(
        {"user_id": user["user_id"], "date": {"$regex": f"^{current_year}"}},
        {"_id": 0}
    ).to_list(10000)
    total_kwh = sum(s["kwh"] for s in charging_sessions)
    total_charging_cost = sum(s["cost"] for s in charging_sessions)
    
    # Calculate Grizzl-E energy cost breakdown
    avg_utility_rate = (total_charging_cost / total_kwh) if total_kwh > 0 else 0.15
    business_use_percent = profile.get("business_use_percent", 100)
    grizzle_breakdown = TaxEngine.calculate_grizzle_energy_cost(
        total_kwh, avg_utility_rate, business_use_percent
    )
    
    # Adjust business expenses to use NET energy cost (after Grizzl-E rebate)
    adjusted_business_expenses = total_business_expenses
    # Add net deductible charging cost to business expenses
    adjusted_business_expenses += grizzle_breakdown["net_deductible_amount"]
    
    # Adjust net income with Grizzl-E logic
    adjusted_net_income = net_business_income - home_office_deduction - ev_depreciation.get("depreciation", 0)
    
    # Get EI opt-in preference
    ei_opt_in = profile.get("ei_opt_in", False)
    
    # Complete tax calculations using new calculate_total_tax
    tax_breakdown = TaxEngine.calculate_total_tax(adjusted_net_income, ei_opt_in)
    
    # Net worth
    total_savings = profile.get("total_savings", 0)
    total_debt = profile.get("total_debt", 0)
    tfsa_balance = profile.get("tfsa_balance", 0)
    rrsp_balance = profile.get("rrsp_balance", 0)
    net_worth = total_savings + tfsa_balance + rrsp_balance - total_debt
    
    # Goals
    debt_goal = profile.get("debt_goal", 0)
    tfsa_goal = profile.get("tfsa_goal", 7000)
    rrsp_goal = profile.get("rrsp_goal", 31560)
    
    # Mileage summary
    mileage_logs = await db.mileage_log.find(
        {"user_id": user["user_id"], "date": {"$regex": f"^{current_year}"}},
        {"_id": 0}
    ).to_list(10000)
    total_business_km = sum(l["distance"] for l in mileage_logs if l["purpose"] == "Business")
    total_personal_km = sum(l["distance"] for l in mileage_logs if l["purpose"] == "Personal")
    
    # Get current federal bracket
    def get_current_bracket(income):
        bpa = TaxEngine.FEDERAL_BPA
        taxable = income - bpa
        if taxable <= 58523: return "14%"
        elif taxable <= 117045: return "20.5%"
        elif taxable <= 181440: return "26%"
        elif taxable <= 258482: return "29%"
        else: return "33%"
    
    # Get current Ontario bracket  
    def get_ontario_bracket(income):
        bpa = TaxEngine.ONTARIO_BPA
        taxable = income - bpa
        if taxable <= 53891: return "5.05%"
        elif taxable <= 107785: return "9.15%"
        elif taxable <= 150000: return "11.16%"
        elif taxable <= 220000: return "12.16%"
        else: return "13.16%"
    
    current_federal_bracket = get_current_bracket(adjusted_net_income)
    current_ontario_bracket = get_ontario_bracket(adjusted_net_income)
    
    return {
        "net_worth": net_worth,
        "total_savings": total_savings,
        "total_debt": total_debt,
        "tfsa_balance": tfsa_balance,
        "rrsp_balance": rrsp_balance,
        "tax_liability": {
            "federal": tax_breakdown["federal"],
            "ontario": tax_breakdown["ontario"],
            "ontario_health_premium": tax_breakdown["ontario_health_premium"],
            "cpp": tax_breakdown["cpp"],
            "cpp2": tax_breakdown["cpp2"],
            "ei": tax_breakdown["ei"],
            "ei_opted_in": tax_breakdown["ei_opted_in"],
            "total": tax_breakdown["total"],
            "federal_bracket": current_federal_bracket,
            "ontario_bracket": current_ontario_bracket,
            "federal_bpa": TaxEngine.FEDERAL_BPA,
            "ontario_bpa": TaxEngine.ONTARIO_BPA
        },
        "income_summary": {
            "total_income": total_income,
            "business_income": total_business_income,
            "total_expenses": total_expenses,
            "business_expenses": total_business_expenses,
            "net_business_income": net_business_income,
            "home_office_deduction": home_office_deduction,
            "ev_depreciation": ev_depreciation.get("depreciation", 0),
            "ev_cca_capped": ev_depreciation.get("cca_capped", False)
        },
        "goals": {
            "debt": {"current": total_debt, "target": debt_goal, "progress": ((debt_goal - total_debt) / debt_goal * 100) if debt_goal > 0 else 100},
            "tfsa": {"current": tfsa_balance, "target": tfsa_goal, "progress": (tfsa_balance / tfsa_goal * 100) if tfsa_goal > 0 else 0},
            "rrsp": {"current": rrsp_balance, "target": rrsp_goal, "progress": (rrsp_balance / rrsp_goal * 100) if rrsp_goal > 0 else 0}
        },
        "mileage": {
            "business_km": total_business_km,
            "personal_km": total_personal_km,
            "total_km": total_business_km + total_personal_km
        },
        "charging": {
            "total_kwh": total_kwh,
            "gross_cost": grizzle_breakdown["gross_utility_expense"],
            "grizzle_rebate": grizzle_breakdown["grizzle_cashback"],
            "net_cost": grizzle_breakdown["net_energy_cost"],
            "net_deductible": grizzle_breakdown["net_deductible_amount"],
            "revenue_offset": grizzle_breakdown["revenue_offset"]
        },
        "profile": profile
    }

@api_router.get("/export/csv")
async def export_all_data(user: dict = Depends(get_current_user)):
    import csv
    from io import StringIO
    
    # Get all data
    transactions = await db.transactions.find({"user_id": user["user_id"]}, {"_id": 0, "user_id": 0}).to_list(100000)
    mileage = await db.mileage_log.find({"user_id": user["user_id"]}, {"_id": 0, "user_id": 0}).to_list(100000)
    charging = await db.charging_sessions.find({"user_id": user["user_id"]}, {"_id": 0, "user_id": 0}).to_list(100000)
    
    output = StringIO()
    
    # Transactions
    output.write("=== TRANSACTIONS ===\n")
    if transactions:
        writer = csv.DictWriter(output, fieldnames=transactions[0].keys())
        writer.writeheader()
        writer.writerows(transactions)
    
    output.write("\n=== MILEAGE LOG ===\n")
    if mileage:
        writer = csv.DictWriter(output, fieldnames=mileage[0].keys())
        writer.writeheader()
        writer.writerows(mileage)
    
    output.write("\n=== CHARGING SESSIONS ===\n")
    if charging:
        writer = csv.DictWriter(output, fieldnames=charging[0].keys())
        writer.writeheader()
        writer.writerows(charging)
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=cad_finance_backup_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

# =============== TAX PROJECTION CALCULATOR ===============

class TaxProjectionRequest(BaseModel):
    rrsp_contribution: float = 0

@api_router.post("/tax/projection")
async def calculate_tax_projection(data: TaxProjectionRequest, user: dict = Depends(get_current_user)):
    """What-If Tax Projection Calculator - See how RRSP affects your tax bracket"""
    profile = await db.profiles.find_one({"user_id": user["user_id"]}, {"_id": 0}) or {}
    
    # Get current year transactions for income calculation
    current_year = datetime.now().year
    transactions = await db.transactions.find(
        {"user_id": user["user_id"], "date": {"$regex": f"^{current_year}"}},
        {"_id": 0}
    ).to_list(10000)
    
    total_business_income = sum(t["amount"] for t in transactions if t["type"] == "Income" and t.get("is_business"))
    total_business_expenses = sum(
        t["amount"] * (t.get("business_use_percent", 100) / 100)
        for t in transactions if t["type"] == "Expense" and t.get("is_business")
    )
    
    # Calculate deductions
    home_sqft = profile.get("home_sqft", 0)
    office_sqft = profile.get("office_sqft", 0)
    home_expenses = sum(t["amount"] for t in transactions if t["type"] == "Expense" and t.get("split_with_sister"))
    home_office_deduction = TaxEngine.calculate_home_office_deduction(home_sqft, office_sqft, home_expenses)
    
    opening_ucc = profile.get("opening_ucc", 0)
    ev_depreciation = TaxEngine.calculate_ev_depreciation(opening_ucc, is_first_year=True) if opening_ucc > 0 else {"depreciation": 0}
    
    net_business_income = total_business_income - total_business_expenses
    adjusted_income = net_business_income - home_office_deduction - ev_depreciation.get("depreciation", 0)
    
    # Get user's actual contribution room (cumulative)
    rrsp_contribution_room = profile.get("rrsp_contribution_room", 31560)
    
    # Calculate projection
    projection = TaxEngine.calculate_tax_projection(adjusted_income, data.rrsp_contribution)
    
    # Override the default RRSP limit with user's actual contribution room
    projection["rrsp_limit_2026"] = rrsp_contribution_room
    projection["rrsp_contribution_room"] = rrsp_contribution_room
    
    return projection

@api_router.get("/tax/brackets")
async def get_tax_brackets():
    """Get 2026 Official Tax Bracket Information"""
    return {
        "federal": {
            "brackets": [
                {"threshold": 58523, "rate": "14%", "cumulative_threshold": 58523},
                {"threshold": 58522, "rate": "20.5%", "cumulative_threshold": 117045},
                {"threshold": 64395, "rate": "26%", "cumulative_threshold": 181440},
                {"threshold": 77042, "rate": "29%", "cumulative_threshold": 258482},
                {"threshold": "∞", "rate": "33%", "cumulative_threshold": "Above $258,482"}
            ],
            "basic_personal_amount": TaxEngine.FEDERAL_BPA
        },
        "ontario": {
            "brackets": [
                {"threshold": 53891, "rate": "5.05%", "cumulative_threshold": 53891},
                {"threshold": 53894, "rate": "9.15%", "cumulative_threshold": 107785},
                {"threshold": 42215, "rate": "11.16%", "cumulative_threshold": 150000},
                {"threshold": 70000, "rate": "12.16%", "cumulative_threshold": 220000},
                {"threshold": "∞", "rate": "13.16%", "cumulative_threshold": "Above $220,000"}
            ],
            "basic_personal_amount": TaxEngine.ONTARIO_BPA,
            "health_premium": "Sliding scale $0-$900 based on income"
        },
        "cpp": {
            "max_pensionable_earnings": TaxEngine.CPP_MAX_EARNINGS,
            "exemption": TaxEngine.CPP_EXEMPTION,
            "rate": "11.9% (self-employed)",
            "cpp2_threshold": TaxEngine.CPP2_MAX_EARNINGS,
            "cpp2_rate": "8%"
        },
        "ei": {
            "rate": "1.63% (optional for self-employed)",
            "max_insurable_earnings": TaxEngine.EI_MAX_INSURABLE,
            "max_premium": TaxEngine.EI_MAX_PREMIUM
        },
        "rrsp_limit_2026": 31560,
        "tfsa_limit_2026": 7000
    }

# =============== ROOT & HEALTH ===============

@api_router.get("/")
async def root():
    return {"message": "CAD Finance & Business Suite API", "version": "1.0.0"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include router
app.include_router(api_router)

# CORS configuration - must specify origins when credentials are allowed
cors_origins = os.environ.get('CORS_ORIGINS', '')
if cors_origins and cors_origins != '*':
    origins = [o.strip() for o in cors_origins.split(',') if o.strip()]
else:
    # Default allowed origins for development and production
    origins = [
        "http://localhost:3000",
        "https://finance-suite-10.preview.emergentagent.com"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
