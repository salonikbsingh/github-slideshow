import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { taxAPI, dashboardAPI } from '@/lib/api';
import { formatCurrency, formatPercent } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Progress } from '@/components/ui/progress';
import { 
  Calculator, TrendingDown, ArrowRight, DollarSign, 
  PiggyBank, Target, Info, ChevronDown, ChevronUp
} from 'lucide-react';
import { toast } from 'sonner';

export default function TaxProjectionPage() {
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [dashboardData, setDashboardData] = useState(null);
  const [brackets, setBrackets] = useState(null);
  const [rrspContribution, setRrspContribution] = useState(0);
  const [projection, setProjection] = useState(null);
  const [showBrackets, setShowBrackets] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [dashRes, bracketsRes] = await Promise.all([
          dashboardAPI.get(),
          taxAPI.getBrackets(),
        ]);
        setDashboardData(dashRes.data);
        setBrackets(bracketsRes.data);
        // Initial projection with 0 RRSP
        calculateProjection(0);
      } catch (error) {
        toast.error('Failed to load tax data');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const calculateProjection = async (amount) => {
    setCalculating(true);
    try {
      const response = await taxAPI.getProjection(amount);
      setProjection(response.data);
    } catch (error) {
      toast.error('Failed to calculate projection');
    } finally {
      setCalculating(false);
    }
  };

  const handleSliderChange = (value) => {
    setRrspContribution(value[0]);
  };

  const handleCalculate = () => {
    calculateProjection(rrspContribution);
  };

  const handleOptimalRRSP = () => {
    if (projection?.optimal_rrsp_to_drop_bracket) {
      setRrspContribution(Math.min(projection.optimal_rrsp_to_drop_bracket, brackets?.rrsp_limit_2026 || 31560));
      calculateProjection(Math.min(projection.optimal_rrsp_to_drop_bracket, brackets?.rrsp_limit_2026 || 31560));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl" data-testid="tax-projection-page">
      {/* Header */}
      <div>
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-white flex items-center gap-3">
          <span className="p-2 rounded-lg bg-violet-500/20">
            <Calculator className="w-6 h-6 text-violet-400" />
          </span>
          Tax Projection Calculator
        </h1>
        <p className="text-zinc-400 mt-1">See how RRSP contributions affect your tax bracket in real-time</p>
      </div>

      {/* RRSP Input Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="finance-card p-6"
      >
        <div className="flex items-center gap-2 mb-6">
          <PiggyBank className="w-5 h-5 text-emerald-400" />
          <h2 className="font-heading font-semibold text-lg">RRSP Contribution</h2>
        </div>

        <div className="space-y-6">
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <Label>Contribution Amount</Label>
              <span className="text-2xl font-mono font-bold text-emerald-400">
                {formatCurrency(rrspContribution)}
              </span>
            </div>
            
            <Slider
              value={[rrspContribution]}
              onValueChange={handleSliderChange}
              max={brackets?.rrsp_limit_2026 || 31560}
              step={100}
              className="w-full"
              data-testid="rrsp-slider"
            />
            
            <div className="flex justify-between text-xs text-zinc-500">
              <span>$0</span>
              <span>2026 Limit: {formatCurrency(brackets?.rrsp_limit_2026 || 31560)}</span>
            </div>
          </div>

          <div className="flex gap-3">
            <Input
              type="number"
              value={rrspContribution}
              onChange={(e) => setRrspContribution(parseFloat(e.target.value) || 0)}
              className="finance-input font-mono"
              placeholder="Enter amount"
              data-testid="rrsp-input"
            />
            <Button 
              onClick={handleCalculate} 
              className="finance-btn-primary"
              disabled={calculating}
              data-testid="calculate-btn"
            >
              {calculating ? 'Calculating...' : 'Calculate'}
            </Button>
          </div>

          {projection?.optimal_rrsp_to_drop_bracket > 0 && (
            <Button 
              variant="outline" 
              className="w-full border-violet-500/50 text-violet-400 hover:bg-violet-500/10"
              onClick={handleOptimalRRSP}
              data-testid="optimal-rrsp-btn"
            >
              <Target className="w-4 h-4 mr-2" />
              Use Optimal Amount to Drop Bracket: {formatCurrency(projection.optimal_rrsp_to_drop_bracket)}
            </Button>
          )}
        </div>
      </motion.div>

      {/* Results Comparison */}
      {projection && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Current Tax */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="finance-card p-6"
          >
            <h3 className="font-heading font-semibold text-zinc-400 mb-4">Current (No RRSP)</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-zinc-500">Taxable Income</span>
                <span className="font-mono">{formatCurrency(projection.current.taxable_income)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Federal Tax</span>
                <span className="font-mono">{formatCurrency(projection.current.federal_tax)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Ontario Tax</span>
                <span className="font-mono">{formatCurrency(projection.current.ontario_tax)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Ontario Health Premium</span>
                <span className="font-mono">{formatCurrency(projection.current.ontario_health_premium || 0)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">CPP/CPP2</span>
                <span className="font-mono">{formatCurrency(projection.current.cpp_total)}</span>
              </div>
              <div className="border-t border-zinc-700 pt-3 flex justify-between">
                <span className="font-medium">Total Tax</span>
                <span className="font-mono text-xl text-red-400">{formatCurrency(projection.current.total_tax)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-500">Federal Bracket</span>
                <span className="px-3 py-1 rounded-full bg-amber-500/20 text-amber-400 text-sm font-medium">
                  {projection.current.bracket}
                </span>
              </div>
            </div>
          </motion.div>

          {/* Projected Tax */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className={`finance-card p-6 ${projection.bracket_dropped ? 'border-emerald-500/50 shadow-glow' : ''}`}
          >
            <h3 className="font-heading font-semibold text-emerald-400 mb-4">
              With {formatCurrency(projection.projected.rrsp_contribution)} RRSP
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-zinc-500">Taxable Income</span>
                <span className="font-mono">{formatCurrency(projection.projected.taxable_income)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Federal Tax</span>
                <span className="font-mono">{formatCurrency(projection.projected.federal_tax)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Ontario Tax</span>
                <span className="font-mono">{formatCurrency(projection.projected.ontario_tax)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">Ontario Health Premium</span>
                <span className="font-mono">{formatCurrency(projection.projected.ontario_health_premium || 0)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-zinc-500">CPP/CPP2</span>
                <span className="font-mono">{formatCurrency(projection.projected.cpp_total)}</span>
              </div>
              <div className="border-t border-zinc-700 pt-3 flex justify-between">
                <span className="font-medium">Total Tax</span>
                <span className="font-mono text-xl text-emerald-400">{formatCurrency(projection.projected.total_tax)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-500">Federal Bracket</span>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  projection.bracket_dropped 
                    ? 'bg-emerald-500/20 text-emerald-400' 
                    : 'bg-amber-500/20 text-amber-400'
                }`}>
                  {projection.projected.bracket}
                  {projection.bracket_dropped && ' ✓'}
                </span>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* Savings Summary */}
      {projection && projection.savings.total > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="finance-card p-6 border-emerald-500/30 bg-emerald-500/5"
        >
          <div className="flex items-center gap-3 mb-4">
            <TrendingDown className="w-6 h-6 text-emerald-400" />
            <h3 className="font-heading font-semibold text-lg">Your Tax Savings</h3>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="p-4 rounded-lg bg-zinc-900">
              <p className="text-xs text-zinc-500 mb-1">Federal Savings</p>
              <p className="text-xl font-mono font-bold text-emerald-400">
                {formatCurrency(projection.savings.federal)}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-zinc-900">
              <p className="text-xs text-zinc-500 mb-1">Ontario Savings</p>
              <p className="text-xl font-mono font-bold text-emerald-400">
                {formatCurrency(projection.savings.ontario)}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-zinc-900">
              <p className="text-xs text-zinc-500 mb-1">OHP Savings</p>
              <p className="text-xl font-mono font-bold text-emerald-400">
                {formatCurrency(projection.savings.ohp || 0)}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-zinc-900">
              <p className="text-xs text-zinc-500 mb-1">Total Savings</p>
              <p className="text-2xl font-mono font-bold text-emerald-400">
                {formatCurrency(projection.savings.total)}
              </p>
            </div>
            <div className="p-4 rounded-lg bg-zinc-900">
              <p className="text-xs text-zinc-500 mb-1">Effective Rate</p>
              <p className="text-xl font-mono font-bold text-violet-400">
                {projection.savings.effective_rate.toFixed(1)}%
              </p>
              <p className="text-xs text-zinc-500">return on RRSP</p>
            </div>
          </div>

          {projection.bracket_dropped && (
            <div className="mt-4 p-3 rounded-lg bg-emerald-500/20 border border-emerald-500/40">
              <p className="text-sm text-emerald-400 font-medium flex items-center gap-2">
                <Target className="w-4 h-4" />
                You dropped a tax bracket! From {projection.current.bracket} to {projection.projected.bracket}
              </p>
            </div>
          )}
        </motion.div>
      )}

      {/* 2026 Tax Brackets Reference */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="finance-card overflow-hidden"
      >
        <button
          onClick={() => setShowBrackets(!showBrackets)}
          className="w-full p-4 flex items-center justify-between hover:bg-zinc-800/50 transition-colors"
          data-testid="toggle-brackets"
        >
          <div className="flex items-center gap-2">
            <Info className="w-5 h-5 text-zinc-400" />
            <span className="font-medium">2026 Official Tax Brackets</span>
          </div>
          {showBrackets ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
        
        {showBrackets && brackets && (
          <div className="p-4 border-t border-zinc-800 space-y-6">
            {/* Federal Brackets */}
            <div>
              <h4 className="font-medium text-zinc-300 mb-3">Federal Tax Brackets</h4>
              <div className="space-y-2">
                {brackets.federal.brackets.map((b, i) => (
                  <div key={i} className="flex justify-between items-center p-2 rounded bg-zinc-800/50">
                    <span className="text-sm text-zinc-400">
                      {i === 0 
                        ? `First ${formatCurrency(b.cumulative_threshold)}` 
                        : i === brackets.federal.brackets.length - 1
                        ? `Above ${formatCurrency(brackets.federal.brackets[i-1].cumulative_threshold)}`
                        : `${formatCurrency(brackets.federal.brackets[i-1].cumulative_threshold)} - ${formatCurrency(b.cumulative_threshold)}`
                      }
                    </span>
                    <span className="font-mono text-emerald-400">{b.rate}</span>
                  </div>
                ))}
              </div>
              <p className="text-xs text-zinc-500 mt-2">
                Basic Personal Amount: {formatCurrency(brackets.federal.basic_personal_amount)}
              </p>
            </div>

            {/* CPP Info */}
            <div>
              <h4 className="font-medium text-zinc-300 mb-3">CPP/CPP2 (Self-Employed)</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 rounded bg-zinc-800/50">
                  <p className="text-xs text-zinc-500">CPP Rate</p>
                  <p className="font-mono text-white">{brackets.cpp.rate}</p>
                  <p className="text-xs text-zinc-500">on first {formatCurrency(brackets.cpp.max_pensionable_earnings)}</p>
                </div>
                <div className="p-3 rounded bg-zinc-800/50">
                  <p className="text-xs text-zinc-500">CPP2 Rate</p>
                  <p className="font-mono text-white">{brackets.cpp.cpp2_rate}</p>
                  <p className="text-xs text-zinc-500">on {formatCurrency(brackets.cpp.max_pensionable_earnings)} - {formatCurrency(brackets.cpp.cpp2_threshold)}</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
