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
    tfsa_goal: float = 7000
    rrsp_goal: float = 31560
    debt_goal: float = 0

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
    
    # 2026 Ontario Tax Brackets
    ONTARIO_BRACKETS = [
        (51446, 0.0505),
        (51446, 0.0915),
        (67526, 0.1116),
        (70000, 0.1216),
        (float('inf'), 0.1316)
    ]
    
    # 2026 Basic Personal Amount
    BASIC_PERSONAL_AMOUNT = 16452
    
    # 2026 CPP/CPP2 rates
    CPP_MAX_EARNINGS = 74600
    CPP2_MAX_EARNINGS = 85000
    CPP_RATE = 0.119  # 11.9% for self-employed
    CPP2_RATE = 0.08  # 8% for CPP2
    CPP_EXEMPTION = 3500
    
    # Class 54 EV Depreciation - 55% on first $61,000 + tax
    EV_CLASS_54_RATE = 0.55
    EV_CLASS_54_LIMIT = 61000
    
    # Grizzl-E Club Rebate
    GRIZZLE_REBATE_PER_KWH = 0.03
    
    @classmethod
    def calculate_federal_tax(cls, income: float) -> float:
        # Apply Basic Personal Amount
        taxable_income = max(0, income - cls.BASIC_PERSONAL_AMOUNT)
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
        # Ontario also has a basic personal amount (~$12,399 for 2026)
        ontario_bpa = 12399
        taxable_income = max(0, income - ontario_bpa)
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
    def calculate_cpp(cls, net_income: float) -> dict:
        # CPP on first $74,600 (minus $3,500 exemption)
        cpp_pensionable = max(0, min(net_income, cls.CPP_MAX_EARNINGS) - cls.CPP_EXEMPTION)
        cpp = cpp_pensionable * cls.CPP_RATE
        
        # CPP2 on income between $74,600 and $85,000
        cpp2_pensionable = max(0, min(net_income, cls.CPP2_MAX_EARNINGS) - cls.CPP_MAX_EARNINGS)
        cpp2 = cpp2_pensionable * cls.CPP2_RATE
        
        return {"cpp": cpp, "cpp2": cpp2, "total": cpp + cpp2}
    
    @classmethod
    def calculate_ev_depreciation(cls, ucc: float, is_first_year: bool = False) -> dict:
        # Apply half-year rule in first year
        # Cap at $61,000 + 13% HST = $68,930
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
        
        current_bracket = get_federal_bracket(current_taxable - cls.BASIC_PERSONAL_AMOUNT)
        projected_bracket = get_federal_bracket(projected_taxable - cls.BASIC_PERSONAL_AMOUNT)
        bracket_dropped = current_bracket != projected_bracket
        
        # Calculate optimal RRSP to drop a bracket
        bracket_thresholds = [58523, 117045, 181440, 258482]
        optimal_rrsp = 0
        for threshold in bracket_thresholds:
            if current_taxable - cls.BASIC_PERSONAL_AMOUNT > threshold:
                excess = (current_taxable - cls.BASIC_PERSONAL_AMOUNT) - threshold
                if excess > 0 and excess < optimal_rrsp or optimal_rrsp == 0:
                    optimal_rrsp = excess + 1  # +1 to cross threshold
        
        return {
            "current": {
                "taxable_income": current_taxable,
                "federal_tax": current_federal,
                "ontario_tax": current_ontario,
                "cpp_total": current_cpp["total"],
                "total_tax": current_total,
                "bracket": current_bracket
            },
            "projected": {
                "rrsp_contribution": rrsp_contribution,
                "taxable_income": projected_taxable,
                "federal_tax": projected_federal,
                "ontario_tax": projected_ontario,
                "cpp_total": current_cpp["total"],  # CPP unchanged
                "total_tax": projected_total,
                "bracket": projected_bracket
            },
            "savings": {
                "federal": federal_savings,
                "ontario": ontario_savings,
                "total": total_savings,
                "effective_rate": (total_savings / rrsp_contribution * 100) if rrsp_contribution > 0 else 0
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
    
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"totp_secret": secret, "totp_enabled": True, "totp_verified": False}}
    )
    
    return {"secret": secret, "qr_code": f"data:image/png;base64,{qr_base64}", "provisioning_uri": provisioning_uri}

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
        {"$set": {"totp_enabled": False, "totp_verified": False, "totp_secret": None}}
    )
    return {"success": True, "message": "2FA disabled"}

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
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, spaceAfter=20, textColor=colors.HexColor("#10b981"))
    elements.append(Paragraph(f"Household Expense Summary - {month}", title_style))
    elements.append(Spacer(1, 20))
    
    # Summary
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
    elements.append(Spacer(1, 30))
    
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
    
    # Tax calculations
    federal_tax = TaxEngine.calculate_federal_tax(adjusted_net_income)
    ontario_tax = TaxEngine.calculate_ontario_tax(adjusted_net_income)
    cpp = TaxEngine.calculate_cpp(adjusted_net_income)
    
    total_tax = federal_tax + ontario_tax + cpp["total"]
    
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
        bpa = TaxEngine.BASIC_PERSONAL_AMOUNT
        taxable = income - bpa
        if taxable <= 58523: return "14%"
        elif taxable <= 117045: return "20.5%"
        elif taxable <= 181440: return "26%"
        elif taxable <= 258482: return "29%"
        else: return "33%"
    
    current_bracket = get_current_bracket(adjusted_net_income)
    
    return {
        "net_worth": net_worth,
        "total_savings": total_savings,
        "total_debt": total_debt,
        "tfsa_balance": tfsa_balance,
        "rrsp_balance": rrsp_balance,
        "tax_liability": {
            "federal": federal_tax,
            "ontario": ontario_tax,
            "cpp": cpp["cpp"],
            "cpp2": cpp["cpp2"],
            "total": total_tax,
            "current_bracket": current_bracket,
            "basic_personal_amount": TaxEngine.BASIC_PERSONAL_AMOUNT
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
    
    # Calculate projection
    projection = TaxEngine.calculate_tax_projection(adjusted_income, data.rrsp_contribution)
    
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
            "basic_personal_amount": TaxEngine.BASIC_PERSONAL_AMOUNT
        },
        "ontario": {
            "brackets": [
                {"threshold": 51446, "rate": "5.05%"},
                {"threshold": 51446, "rate": "9.15%"},
                {"threshold": 67526, "rate": "11.16%"},
                {"threshold": 70000, "rate": "12.16%"},
                {"threshold": "∞", "rate": "13.16%"}
            ],
            "basic_personal_amount": 12399
        },
        "cpp": {
            "max_pensionable_earnings": TaxEngine.CPP_MAX_EARNINGS,
            "exemption": TaxEngine.CPP_EXEMPTION,
            "rate": "11.9% (self-employed)",
            "cpp2_threshold": TaxEngine.CPP2_MAX_EARNINGS,
            "cpp2_rate": "8%"
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
        "https://wealthflow-18.preview.emergentagent.com"
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
