import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { X, DollarSign, Briefcase, ShoppingCart, Zap, ArrowRight, ArrowLeft, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { transactionsAPI, chargingAPI } from '@/lib/api';
import { toast } from 'sonner';

const categories = {
  Income: ['Uber Eats', 'DoorDash', 'Other Gig', 'Freelance', 'Other Income'],
  'Business Expense': ['Fuel', 'Vehicle Maintenance', 'Phone/Data', 'Commercial Insurance', 'Safety Gear', 'Other Business'],
  'Personal Expense': ['Groceries', 'Dining', 'Entertainment', 'Utilities', 'Rent', 'Other Personal'],
  'EV Charge': [],
};

const categoryIcons = {
  Income: DollarSign,
  'Business Expense': Briefcase,
  'Personal Expense': ShoppingCart,
  'EV Charge': Zap,
};

export default function QuickEntryWizard({ onClose }) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    type: '',
    category: '',
    amount: '',
    date: new Date().toISOString().split('T')[0],
    description: '',
    is_business: false,
    business_use_percent: 100,
    split_with_sister: false,
    // EV Charge specific
    kwh: '',
    location: '',
  });

  const handleTypeSelect = (type) => {
    setFormData({
      ...formData,
      type,
      is_business: type === 'Income' || type === 'Business Expense',
      category: '',
    });
    setStep(2);
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      if (formData.type === 'EV Charge') {
        await chargingAPI.create({
          date: formData.date,
          kwh: parseFloat(formData.kwh),
          cost: parseFloat(formData.amount),
          location: formData.location,
        });
        toast.success('EV charging session logged!');
      } else {
        const transactionType = formData.type === 'Income' ? 'Income' : 'Expense';
        await transactionsAPI.create({
          date: formData.date,
          amount: parseFloat(formData.amount),
          category: formData.category,
          type: transactionType,
          is_business: formData.is_business,
          business_use_percent: formData.business_use_percent,
          split_with_sister: formData.split_with_sister,
          description: formData.description,
        });
        toast.success('Transaction added!');
      }
      onClose();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-end md:items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 100, opacity: 0 }}
        transition={{ type: 'spring', damping: 25 }}
        className="bg-zinc-900 rounded-t-2xl md:rounded-2xl w-full max-w-md border border-zinc-800 overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            {step > 1 && (
              <Button variant="ghost" size="icon" onClick={() => setStep(step - 1)} data-testid="wizard-back">
                <ArrowLeft className="w-4 h-4" />
              </Button>
            )}
            <h2 className="font-heading font-semibold text-lg">
              {step === 1 ? 'Quick Entry' : step === 2 ? 'Details' : 'Confirm'}
            </h2>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} data-testid="wizard-close">
            <X className="w-5 h-5" />
          </Button>
        </div>

        {/* Step Indicator */}
        <div className="flex gap-1 p-4 pb-0">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`h-1 flex-1 rounded-full transition-colors ${
                s <= step ? 'bg-emerald-500' : 'bg-zinc-700'
              }`}
            />
          ))}
        </div>

        {/* Content */}
        <div className="p-4">
          {step === 1 && (
            <div className="grid grid-cols-2 gap-3">
              {Object.keys(categories).map((type) => {
                const Icon = categoryIcons[type];
                return (
                  <button
                    key={type}
                    onClick={() => handleTypeSelect(type)}
                    data-testid={`type-${type.toLowerCase().replace(' ', '-')}`}
                    className={`p-6 rounded-xl border transition-all hover:scale-105 ${
                      type === 'Income'
                        ? 'border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500/20'
                        : type === 'Business Expense'
                        ? 'border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20'
                        : type === 'EV Charge'
                        ? 'border-blue-500/30 bg-blue-500/10 hover:bg-blue-500/20'
                        : 'border-zinc-700 bg-zinc-800/50 hover:bg-zinc-800'
                    }`}
                  >
                    <Icon className={`w-8 h-8 mx-auto mb-2 ${
                      type === 'Income' ? 'text-emerald-400' :
                      type === 'Business Expense' ? 'text-amber-400' :
                      type === 'EV Charge' ? 'text-blue-400' : 'text-zinc-400'
                    }`} />
                    <span className="text-sm font-medium">{type}</span>
                  </button>
                );
              })}
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              {/* Date */}
              <div className="space-y-2">
                <Label htmlFor="date">Date</Label>
                <Input
                  id="date"
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="finance-input"
                  data-testid="input-date"
                />
              </div>

              {/* Amount */}
              <div className="space-y-2">
                <Label htmlFor="amount">{formData.type === 'EV Charge' ? 'Cost (CAD)' : 'Amount (CAD)'}</Label>
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                  className="finance-input text-2xl font-mono"
                  data-testid="input-amount"
                />
              </div>

              {/* Category or EV-specific fields */}
              {formData.type === 'EV Charge' ? (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="kwh">kWh Charged</Label>
                    <Input
                      id="kwh"
                      type="number"
                      step="0.1"
                      placeholder="0.0"
                      value={formData.kwh}
                      onChange={(e) => setFormData({ ...formData, kwh: e.target.value })}
                      className="finance-input"
                      data-testid="input-kwh"
                    />
                    <p className="text-xs text-zinc-500">Rebate: ${(parseFloat(formData.kwh || 0) * 0.03).toFixed(2)}</p>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="location">Location</Label>
                    <Input
                      id="location"
                      placeholder="e.g., Home, Supercharger"
                      value={formData.location}
                      onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                      className="finance-input"
                      data-testid="input-location"
                    />
                  </div>
                </>
              ) : (
                <div className="space-y-2">
                  <Label>Category</Label>
                  <Select
                    value={formData.category}
                    onValueChange={(v) => setFormData({ ...formData, category: v })}
                  >
                    <SelectTrigger className="finance-input" data-testid="select-category">
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      {categories[formData.type]?.map((cat) => (
                        <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="description">Notes (optional)</Label>
                <Input
                  id="description"
                  placeholder="Add a note..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="finance-input"
                  data-testid="input-description"
                />
              </div>

              <Button
                className="w-full finance-btn-primary"
                onClick={() => setStep(3)}
                disabled={!formData.amount || (formData.type !== 'EV Charge' && !formData.category)}
                data-testid="wizard-next"
              >
                Next <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              {/* Business Use Toggle (for expenses) */}
              {formData.type === 'Business Expense' && (
                <div className="finance-card p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="split-home">Split with Home?</Label>
                    <Switch
                      id="split-home"
                      checked={formData.business_use_percent < 100}
                      onCheckedChange={(checked) =>
                        setFormData({ ...formData, business_use_percent: checked ? 50 : 100 })
                      }
                      data-testid="switch-split-home"
                    />
                  </div>
                  {formData.business_use_percent < 100 && (
                    <div className="space-y-2">
                      <Label>Business Use %</Label>
                      <Input
                        type="number"
                        min="0"
                        max="100"
                        value={formData.business_use_percent}
                        onChange={(e) =>
                          setFormData({ ...formData, business_use_percent: parseFloat(e.target.value) })
                        }
                        className="finance-input"
                        data-testid="input-business-percent"
                      />
                    </div>
                  )}
                </div>
              )}

              {/* Sister Split Toggle (for home expenses) */}
              {formData.type === 'Personal Expense' && (
                <div className="finance-card p-4 sister-accent-bg border-violet-500/30">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="split-sister" className="text-violet-300">Split with Sister?</Label>
                      <p className="text-xs text-zinc-500">Add to household shared bills</p>
                    </div>
                    <Switch
                      id="split-sister"
                      checked={formData.split_with_sister}
                      onCheckedChange={(checked) => setFormData({ ...formData, split_with_sister: checked })}
                      data-testid="switch-split-sister"
                    />
                  </div>
                </div>
              )}

              {/* Summary */}
              <div className="finance-card p-4 space-y-3">
                <h3 className="font-heading font-semibold text-zinc-300">Summary</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Type</span>
                    <span>{formData.type}</span>
                  </div>
                  {formData.category && (
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Category</span>
                      <span>{formData.category}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Date</span>
                    <span>{formData.date}</span>
                  </div>
                  <div className="flex justify-between text-lg font-mono">
                    <span className="text-zinc-500">Amount</span>
                    <span className={formData.type === 'Income' ? 'text-emerald-400' : 'text-white'}>
                      ${parseFloat(formData.amount || 0).toFixed(2)}
                    </span>
                  </div>
                  {formData.type === 'EV Charge' && formData.kwh && (
                    <div className="flex justify-between text-emerald-400">
                      <span className="text-zinc-500">Rebate Earned</span>
                      <span>+${(parseFloat(formData.kwh) * 0.03).toFixed(2)}</span>
                    </div>
                  )}
                </div>
              </div>

              <Button
                className="w-full finance-btn-primary"
                onClick={handleSubmit}
                disabled={loading}
                data-testid="wizard-submit"
              >
                {loading ? (
                  <span className="flex items-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-black mr-2"></div>
                    Saving...
                  </span>
                ) : (
                  <>
                    <Check className="w-4 h-4 mr-2" /> Confirm
                  </>
                )}
              </Button>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
