import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';
import { profileAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { 
  DollarSign, Car, Home, Target, ArrowRight, ArrowLeft, Check, 
  Wallet, CreditCard, PiggyBank, TrendingUp
} from 'lucide-react';
import { toast } from 'sonner';

const steps = [
  { id: 1, title: 'Welcome', icon: DollarSign },
  { id: 2, title: 'Home Office', icon: Home },
  { id: 3, title: 'EV Details', icon: Car },
  { id: 4, title: 'Balances', icon: Wallet },
  { id: 5, title: 'Goals', icon: Target },
];

export default function SetupWizard() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    province: 'Ontario',
    home_sqft: '',
    office_sqft: '',
    ev_purchase_price: '',
    ev_purchase_date: '',
    opening_ucc: '',
    total_debt: '',
    total_savings: '',
    tfsa_balance: '',
    rrsp_balance: '',
    tfsa_contribution_room: '',
    rrsp_contribution_room: '',
    tfsa_goal: '7000',
    rrsp_goal: '31560',
    debt_goal: '',
    ei_opt_in: false,
  });

  const updateField = (field, value) => {
    setFormData({ ...formData, [field]: value });
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const profileData = {
        ...formData,
        home_sqft: parseFloat(formData.home_sqft) || 0,
        office_sqft: parseFloat(formData.office_sqft) || 0,
        ev_purchase_price: parseFloat(formData.ev_purchase_price) || 0,
        opening_ucc: parseFloat(formData.opening_ucc) || 0,
        total_debt: parseFloat(formData.total_debt) || 0,
        total_savings: parseFloat(formData.total_savings) || 0,
        tfsa_balance: parseFloat(formData.tfsa_balance) || 0,
        rrsp_balance: parseFloat(formData.rrsp_balance) || 0,
        tfsa_goal: parseFloat(formData.tfsa_goal) || 7000,
        rrsp_goal: parseFloat(formData.rrsp_goal) || 31560,
        debt_goal: parseFloat(formData.debt_goal) || 0,
      };
      await profileAPI.create(profileData);
      await refreshUser();
      toast.success('Setup complete! Welcome to your financial command center.');
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save profile');
    } finally {
      setLoading(false);
    }
  };

  const progress = (step / steps.length) * 100;

  return (
    <div className="min-h-screen bg-[#09090b] flex flex-col items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-lg"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-600 flex items-center justify-center">
              <DollarSign className="w-7 h-7 text-white" />
            </div>
          </div>
          <h1 className="font-heading text-2xl font-bold text-white">
            {step === 1 ? `Welcome, ${user?.name?.split(' ')[0] || 'there'}!` : steps[step - 1].title}
          </h1>
          <p className="text-zinc-400 mt-1">
            {step === 1 ? "Let's set up your financial command center" : 
             step === 2 ? "Set up your home office for deductions" :
             step === 3 ? "Enter your EV details for Class 54 depreciation" :
             step === 4 ? "Enter your current financial balances" :
             "Set your financial goals for 2026"}
          </p>
        </div>

        {/* Progress */}
        <div className="mb-8">
          <Progress value={progress} className="h-2 bg-zinc-800" />
          <div className="flex justify-between mt-2">
            {steps.map((s) => (
              <div
                key={s.id}
                className={`text-xs ${step >= s.id ? 'text-emerald-400' : 'text-zinc-600'}`}
              >
                {s.id}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="finance-card p-6"
          >
            {step === 1 && (
              <div className="space-y-6 text-center">
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                    <TrendingUp className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                    <p className="text-sm text-zinc-300">Track Income</p>
                  </div>
                  <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30">
                    <CreditCard className="w-8 h-8 text-amber-400 mx-auto mb-2" />
                    <p className="text-sm text-zinc-300">Manage Expenses</p>
                  </div>
                  <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
                    <Car className="w-8 h-8 text-blue-400 mx-auto mb-2" />
                    <p className="text-sm text-zinc-300">EV Tracking</p>
                  </div>
                  <div className="p-4 rounded-lg bg-violet-500/10 border border-violet-500/30">
                    <PiggyBank className="w-8 h-8 text-violet-400 mx-auto mb-2" />
                    <p className="text-sm text-zinc-300">Tax Planning</p>
                  </div>
                </div>
                <p className="text-zinc-400 text-sm">
                  This wizard will help you set up your initial balances for January 1st, 2026. 
                  You can always update these later in Settings.
                </p>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="home_sqft">Total Home Square Footage</Label>
                  <Input
                    id="home_sqft"
                    type="number"
                    placeholder="e.g., 1200"
                    value={formData.home_sqft}
                    onChange={(e) => updateField('home_sqft', e.target.value)}
                    className="finance-input"
                    data-testid="input-home-sqft"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="office_sqft">Office Space Square Footage</Label>
                  <Input
                    id="office_sqft"
                    type="number"
                    placeholder="e.g., 150"
                    value={formData.office_sqft}
                    onChange={(e) => updateField('office_sqft', e.target.value)}
                    className="finance-input"
                    data-testid="input-office-sqft"
                  />
                </div>
                {formData.home_sqft && formData.office_sqft && (
                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                    <p className="text-sm text-emerald-400">
                      Deductible Ratio: {((parseFloat(formData.office_sqft) / parseFloat(formData.home_sqft)) * 100).toFixed(1)}%
                    </p>
                    <p className="text-xs text-zinc-500">
                      This percentage of home expenses can be deducted as business expenses.
                    </p>
                  </div>
                )}
              </div>
            )}

            {step === 3 && (
              <div className="space-y-4">
                <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/30 mb-4">
                  <p className="text-sm text-blue-400">Class 54 EV Depreciation</p>
                  <p className="text-xs text-zinc-500">
                    2026 Rate: 55% on first $61,000 + tax of vehicle cost
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ev_purchase_price">EV Purchase Price (CAD)</Label>
                  <Input
                    id="ev_purchase_price"
                    type="number"
                    placeholder="e.g., 55000"
                    value={formData.ev_purchase_price}
                    onChange={(e) => updateField('ev_purchase_price', e.target.value)}
                    className="finance-input"
                    data-testid="input-ev-price"
                  />
                  {parseFloat(formData.ev_purchase_price) > 61000 && (
                    <div className="p-2 rounded bg-amber-500/20 border border-amber-500/40">
                      <p className="text-xs text-amber-400 flex items-center gap-1">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                        Note: CCA Class 54 is capped at $61k + tax for 2026 calculations.
                      </p>
                    </div>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="opening_ucc">Opening UCC (Undepreciated Capital Cost)</Label>
                  <Input
                    id="opening_ucc"
                    type="number"
                    placeholder="Vehicle value on Jan 1, 2026"
                    value={formData.opening_ucc}
                    onChange={(e) => updateField('opening_ucc', e.target.value)}
                    className="finance-input"
                    data-testid="input-ucc"
                  />
                  <p className="text-xs text-zinc-500">
                    This is the vehicle's value for tax purposes at the start of 2026.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ev_purchase_date">Purchase Date (optional)</Label>
                  <Input
                    id="ev_purchase_date"
                    type="date"
                    value={formData.ev_purchase_date}
                    onChange={(e) => updateField('ev_purchase_date', e.target.value)}
                    className="finance-input"
                    data-testid="input-ev-date"
                  />
                </div>
              </div>
            )}

            {step === 4 && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="total_savings">Total Savings (CAD)</Label>
                  <Input
                    id="total_savings"
                    type="number"
                    placeholder="0.00"
                    value={formData.total_savings}
                    onChange={(e) => updateField('total_savings', e.target.value)}
                    className="finance-input"
                    data-testid="input-savings"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="total_debt">Total Debt (CAD)</Label>
                  <Input
                    id="total_debt"
                    type="number"
                    placeholder="0.00"
                    value={formData.total_debt}
                    onChange={(e) => updateField('total_debt', e.target.value)}
                    className="finance-input"
                    data-testid="input-debt"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tfsa_balance">TFSA Balance (CAD)</Label>
                  <Input
                    id="tfsa_balance"
                    type="number"
                    placeholder="0.00"
                    value={formData.tfsa_balance}
                    onChange={(e) => updateField('tfsa_balance', e.target.value)}
                    className="finance-input"
                    data-testid="input-tfsa"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="rrsp_balance">RRSP Balance (CAD)</Label>
                  <Input
                    id="rrsp_balance"
                    type="number"
                    placeholder="0.00"
                    value={formData.rrsp_balance}
                    onChange={(e) => updateField('rrsp_balance', e.target.value)}
                    className="finance-input"
                    data-testid="input-rrsp"
                  />
                </div>
                {formData.total_savings && formData.total_debt && (
                  <div className="p-3 rounded-lg bg-zinc-800">
                    <p className="text-sm text-zinc-400">Net Worth</p>
                    <p className={`text-xl font-mono font-bold ${
                      (parseFloat(formData.total_savings) + parseFloat(formData.tfsa_balance || 0) + parseFloat(formData.rrsp_balance || 0) - parseFloat(formData.total_debt)) >= 0 
                        ? 'text-emerald-400' 
                        : 'text-red-400'
                    }`}>
                      ${((parseFloat(formData.total_savings || 0) + parseFloat(formData.tfsa_balance || 0) + parseFloat(formData.rrsp_balance || 0) - parseFloat(formData.total_debt || 0))).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            )}

            {step === 5 && (
              <div className="space-y-4">
                <p className="text-sm text-zinc-400 mb-4">
                  Set your financial goals for 2026. We'll track your progress using the "Waterfall" method: 
                  Debt Paydown → TFSA → RRSP
                </p>
                <div className="space-y-2">
                  <Label htmlFor="debt_goal">Debt Paydown Goal (CAD)</Label>
                  <Input
                    id="debt_goal"
                    type="number"
                    placeholder="How much debt to pay off?"
                    value={formData.debt_goal}
                    onChange={(e) => updateField('debt_goal', e.target.value)}
                    className="finance-input"
                    data-testid="input-debt-goal"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tfsa_goal">TFSA Contribution Goal (CAD)</Label>
                  <Input
                    id="tfsa_goal"
                    type="number"
                    placeholder="7000"
                    value={formData.tfsa_goal}
                    onChange={(e) => updateField('tfsa_goal', e.target.value)}
                    className="finance-input"
                    data-testid="input-tfsa-goal"
                  />
                  <p className="text-xs text-zinc-500">2026 TFSA contribution limit: $7,000</p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="rrsp_goal">RRSP Contribution Goal (CAD)</Label>
                  <Input
                    id="rrsp_goal"
                    type="number"
                    placeholder="31560"
                    value={formData.rrsp_goal}
                    onChange={(e) => updateField('rrsp_goal', e.target.value)}
                    className="finance-input"
                    data-testid="input-rrsp-goal"
                  />
                  <p className="text-xs text-zinc-500">2026 RRSP contribution limit: $31,560 (18% of income)</p>
                </div>
              </div>
            )}
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex justify-between mt-6">
          <Button
            variant="ghost"
            onClick={() => setStep(step - 1)}
            disabled={step === 1}
            className="text-zinc-400"
            data-testid="btn-back"
          >
            <ArrowLeft className="w-4 h-4 mr-2" /> Back
          </Button>
          
          {step < steps.length ? (
            <Button
              className="finance-btn-primary"
              onClick={() => setStep(step + 1)}
              data-testid="btn-next"
            >
              Next <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          ) : (
            <Button
              className="finance-btn-primary"
              onClick={handleSubmit}
              disabled={loading}
              data-testid="btn-finish"
            >
              {loading ? 'Saving...' : <>Finish Setup <Check className="w-4 h-4 ml-2" /></>}
            </Button>
          )}
        </div>

        {/* Skip option */}
        {step < steps.length && (
          <button
            className="w-full text-center text-sm text-zinc-500 hover:text-zinc-300 mt-4"
            onClick={() => setStep(step + 1)}
            data-testid="btn-skip"
          >
            Skip for now
          </button>
        )}
      </motion.div>
    </div>
  );
}
