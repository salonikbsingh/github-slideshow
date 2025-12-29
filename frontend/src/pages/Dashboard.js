import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Outlet } from 'react-router-dom';
import { dashboardAPI } from '@/lib/api';
import { formatCurrency, formatPercent } from '@/lib/utils';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  TrendingUp, TrendingDown, DollarSign, Receipt, Car, Zap, 
  Target, Wallet, PiggyBank, Building2, RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell
} from 'recharts';

const COLORS = ['#10b981', '#f59e0b', '#8b5cf6', '#3b82f6', '#ef4444'];

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = async () => {
    try {
      const response = await dashboardAPI.get();
      setData(response.data);
    } catch (error) {
      toast.error('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-emerald-500"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center text-zinc-400 py-12">
        <p>Unable to load dashboard data.</p>
        <button 
          onClick={fetchDashboard} 
          className="mt-4 text-emerald-400 hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  const taxBreakdown = [
    { name: 'Federal', value: data.tax_liability.federal },
    { name: 'Ontario', value: data.tax_liability.ontario },
    { name: 'CPP', value: data.tax_liability.cpp },
    { name: 'CPP2', value: data.tax_liability.cpp2 },
  ].filter(item => item.value > 0);

  return (
    <div className="space-y-6" data-testid="dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl md:text-3xl font-bold text-white">Command Center</h1>
          <p className="text-zinc-400">Your financial overview for 2026</p>
        </div>
        <button 
          onClick={fetchDashboard}
          className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 transition-colors"
          data-testid="refresh-dashboard"
        >
          <RefreshCw className="w-5 h-5 text-zinc-400" />
        </button>
      </div>

      {/* Hero Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Net Worth Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="finance-card p-6 col-span-1 md:col-span-2 lg:col-span-1 lg:row-span-2"
        >
          <div className="flex items-center gap-2 mb-4">
            <div className="p-2 rounded-lg bg-emerald-500/20">
              <Wallet className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="text-zinc-400 font-medium">Net Worth</h3>
          </div>
          <p className={`text-4xl font-mono font-bold ${data.net_worth >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
            {formatCurrency(data.net_worth)}
          </p>
          <div className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-zinc-500">Savings</span>
              <span className="text-zinc-300">{formatCurrency(data.total_savings)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">TFSA</span>
              <span className="text-zinc-300">{formatCurrency(data.tfsa_balance)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">RRSP</span>
              <span className="text-zinc-300">{formatCurrency(data.rrsp_balance)}</span>
            </div>
            <div className="flex justify-between border-t border-zinc-800 pt-2">
              <span className="text-zinc-500">Total Debt</span>
              <span className="text-red-400">-{formatCurrency(data.total_debt)}</span>
            </div>
          </div>
        </motion.div>

        {/* Tax Liability Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="finance-card p-6"
        >
          <div className="flex items-center gap-2 mb-4">
            <div className="p-2 rounded-lg bg-amber-500/20">
              <Receipt className="w-5 h-5 text-amber-400" />
            </div>
            <h3 className="text-zinc-400 font-medium">Tax Liability</h3>
          </div>
          <p className="text-3xl font-mono font-bold text-amber-400">
            {formatCurrency(data.tax_liability.total)}
          </p>
          <div className="mt-4">
            {taxBreakdown.length > 0 ? (
              <div className="h-32">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={taxBreakdown}
                      cx="50%"
                      cy="50%"
                      innerRadius={30}
                      outerRadius={50}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {taxBreakdown.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value) => formatCurrency(value)}
                      contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: '8px' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-sm text-zinc-500">No tax liability calculated yet</p>
            )}
          </div>
        </motion.div>

        {/* Income Summary Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="finance-card p-6"
        >
          <div className="flex items-center gap-2 mb-4">
            <div className="p-2 rounded-lg bg-emerald-500/20">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
            </div>
            <h3 className="text-zinc-400 font-medium">Business Income</h3>
          </div>
          <p className="text-3xl font-mono font-bold text-emerald-400">
            {formatCurrency(data.income_summary.business_income)}
          </p>
          <div className="mt-4 space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-zinc-500">Expenses</span>
              <span className="text-red-400">-{formatCurrency(data.income_summary.business_expenses)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Home Office</span>
              <span className="text-emerald-400">-{formatCurrency(data.income_summary.home_office_deduction)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">EV Depreciation</span>
              <span className="text-emerald-400">-{formatCurrency(data.income_summary.ev_depreciation)}</span>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Goal Tracker - Waterfall */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="finance-card p-6"
      >
        <div className="flex items-center gap-2 mb-6">
          <div className="p-2 rounded-lg bg-violet-500/20">
            <Target className="w-5 h-5 text-violet-400" />
          </div>
          <h3 className="text-lg font-heading font-semibold text-white">Goal Tracker (Waterfall)</h3>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Debt Paydown */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <TrendingDown className="w-4 h-4 text-red-400" />
                <span className="text-sm font-medium">Debt Paydown</span>
              </div>
              <span className="text-xs text-zinc-500">{formatPercent(data.goals.debt.progress)}</span>
            </div>
            <Progress value={Math.min(100, data.goals.debt.progress)} className="h-3 bg-zinc-800" />
            <div className="flex justify-between text-xs text-zinc-500">
              <span>{formatCurrency(data.goals.debt.current)} remaining</span>
              <span>Goal: {formatCurrency(data.goals.debt.target)}</span>
            </div>
          </div>

          {/* TFSA */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <PiggyBank className="w-4 h-4 text-emerald-400" />
                <span className="text-sm font-medium">TFSA</span>
              </div>
              <span className="text-xs text-zinc-500">{formatPercent(data.goals.tfsa.progress)}</span>
            </div>
            <Progress value={Math.min(100, data.goals.tfsa.progress)} className="h-3 bg-zinc-800" />
            <div className="flex justify-between text-xs text-zinc-500">
              <span>{formatCurrency(data.goals.tfsa.current)}</span>
              <span>Goal: {formatCurrency(data.goals.tfsa.target)}</span>
            </div>
          </div>

          {/* RRSP */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-blue-400" />
                <span className="text-sm font-medium">RRSP</span>
              </div>
              <span className="text-xs text-zinc-500">{formatPercent(data.goals.rrsp.progress)}</span>
            </div>
            <Progress value={Math.min(100, data.goals.rrsp.progress)} className="h-3 bg-zinc-800" />
            <div className="flex justify-between text-xs text-zinc-500">
              <span>{formatCurrency(data.goals.rrsp.current)}</span>
              <span>Goal: {formatCurrency(data.goals.rrsp.target)}</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Quick Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Mileage */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="finance-card p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Car className="w-4 h-4 text-zinc-400" />
            <span className="text-xs text-zinc-500">Business Mileage</span>
          </div>
          <p className="text-xl font-mono font-bold text-white">
            {data.mileage.business_km.toLocaleString()} km
          </p>
        </motion.div>

        {/* EV Charging */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="finance-card p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-blue-400" />
            <span className="text-xs text-zinc-500">EV Charging</span>
          </div>
          <p className="text-xl font-mono font-bold text-white">
            {data.charging.total_kwh.toFixed(1)} kWh
          </p>
          <p className="text-xs text-emerald-400">+{formatCurrency(data.charging.total_rebate)} rebate</p>
        </motion.div>

        {/* Total Income */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="finance-card p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-xs text-zinc-500">Total Income</span>
          </div>
          <p className="text-xl font-mono font-bold text-emerald-400">
            {formatCurrency(data.income_summary.total_income)}
          </p>
        </motion.div>

        {/* Total Expenses */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="finance-card p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown className="w-4 h-4 text-red-400" />
            <span className="text-xs text-zinc-500">Total Expenses</span>
          </div>
          <p className="text-xl font-mono font-bold text-red-400">
            {formatCurrency(data.income_summary.total_expenses)}
          </p>
        </motion.div>
      </div>

      {/* Tax Breakdown */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
        className="finance-card p-6"
      >
        <h3 className="text-lg font-heading font-semibold text-white mb-4">2026 Tax Breakdown</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-lg bg-zinc-800/50">
            <p className="text-xs text-zinc-500 mb-1">Federal Tax</p>
            <p className="text-lg font-mono font-bold text-white">{formatCurrency(data.tax_liability.federal)}</p>
          </div>
          <div className="p-4 rounded-lg bg-zinc-800/50">
            <p className="text-xs text-zinc-500 mb-1">Ontario Tax</p>
            <p className="text-lg font-mono font-bold text-white">{formatCurrency(data.tax_liability.ontario)}</p>
          </div>
          <div className="p-4 rounded-lg bg-zinc-800/50">
            <p className="text-xs text-zinc-500 mb-1">CPP (11.9%)</p>
            <p className="text-lg font-mono font-bold text-white">{formatCurrency(data.tax_liability.cpp)}</p>
          </div>
          <div className="p-4 rounded-lg bg-zinc-800/50">
            <p className="text-xs text-zinc-500 mb-1">CPP2 (8%)</p>
            <p className="text-lg font-mono font-bold text-white">{formatCurrency(data.tax_liability.cpp2)}</p>
          </div>
        </div>
      </motion.div>

      <Outlet />
    </div>
  );
}
