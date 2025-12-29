import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { sisterAPI } from '@/lib/api';
import { formatCurrency, formatDate, getCurrentMonth, getMonthName } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow 
} from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { 
  Users, Plus, Trash2, Download, FileText, Home, Wifi, Zap, 
  DollarSign, Receipt 
} from 'lucide-react';
import { toast } from 'sonner';

const billCategories = [
  { value: 'Rent', icon: Home },
  { value: 'Utilities', icon: Zap },
  { value: 'Internet', icon: Wifi },
  { value: 'Insurance', icon: FileText },
  { value: 'Groceries', icon: Receipt },
  { value: 'Other', icon: DollarSign },
];

export default function SisterModule() {
  const [bills, setBills] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState(getCurrentMonth());
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    category: 'Utilities',
    amount: '',
    description: '',
  });

  const fetchData = async () => {
    try {
      const [billsRes, summaryRes] = await Promise.all([
        sisterAPI.getBills(),
        sisterAPI.getSummary(selectedMonth),
      ]);
      setBills(billsRes.data);
      setSummary(summaryRes.data);
    } catch (error) {
      toast.error('Failed to load household data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedMonth]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await sisterAPI.createBill({
        ...formData,
        amount: parseFloat(formData.amount),
      });
      toast.success('Bill added');
      setDialogOpen(false);
      setFormData({
        date: new Date().toISOString().split('T')[0],
        category: 'Utilities',
        amount: '',
        description: '',
      });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add bill');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this bill?')) return;
    try {
      await sisterAPI.deleteBill(id);
      setBills(bills.filter(b => b.id !== id));
      fetchData();
      toast.success('Bill deleted');
    } catch (error) {
      toast.error('Failed to delete bill');
    }
  };

  const handleDownloadPDF = async () => {
    try {
      const response = await sisterAPI.downloadPDF(selectedMonth);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `household_expenses_${selectedMonth}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('PDF downloaded!');
    } catch (error) {
      toast.error('Failed to download PDF');
    }
  };

  // Generate last 12 months for selector
  const months = Array.from({ length: 12 }, (_, i) => {
    const d = new Date();
    d.setMonth(d.getMonth() - i);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-violet-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="sister-module">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl md:text-3xl font-bold text-white flex items-center gap-3">
            <span className="p-2 rounded-lg bg-violet-500/20">
              <Users className="w-6 h-6 text-violet-400" />
            </span>
            Household Bills
          </h1>
          <p className="text-zinc-400 mt-1">Split expenses with your sister - 50/50</p>
        </div>
        <div className="flex gap-2">
          <Select value={selectedMonth} onValueChange={setSelectedMonth}>
            <SelectTrigger className="w-40 finance-input" data-testid="month-selector">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {months.map((m) => (
                <SelectItem key={m} value={m}>{getMonthName(m)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button className="bg-violet-600 hover:bg-violet-500 text-white" data-testid="add-bill-btn">
                <Plus className="w-4 h-4 mr-2" /> Add Bill
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-zinc-900 border-zinc-800">
              <DialogHeader>
                <DialogTitle>Add Household Bill</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="date">Date</Label>
                  <Input
                    id="date"
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    className="finance-input"
                    required
                    data-testid="bill-date"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Category</Label>
                  <Select 
                    value={formData.category} 
                    onValueChange={(v) => setFormData({ ...formData, category: v })}
                  >
                    <SelectTrigger className="finance-input" data-testid="bill-category">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {billCategories.map((cat) => (
                        <SelectItem key={cat.value} value={cat.value}>
                          <span className="flex items-center gap-2">
                            <cat.icon className="w-4 h-4" />
                            {cat.value}
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="amount">Amount (CAD)</Label>
                  <Input
                    id="amount"
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                    className="finance-input text-xl font-mono"
                    required
                    data-testid="bill-amount"
                  />
                  {formData.amount && (
                    <p className="text-sm text-violet-400">
                      Your share: {formatCurrency(parseFloat(formData.amount) / 2)}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Input
                    id="description"
                    type="text"
                    placeholder="e.g., Hydro bill - December"
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="finance-input"
                    required
                    data-testid="bill-description"
                  />
                </div>
                <Button type="submit" className="w-full bg-violet-600 hover:bg-violet-500" data-testid="bill-submit">
                  Add Bill
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="finance-card p-6 sister-accent border-violet-500/30"
        >
          <div className="flex items-center gap-2 mb-2">
            <Receipt className="w-5 h-5 text-violet-400" />
            <span className="text-zinc-400">Total Expenses</span>
          </div>
          <p className="text-3xl font-mono font-bold text-white">
            {formatCurrency(summary?.total_expenses || 0)}
          </p>
          <p className="text-sm text-zinc-500 mt-1">{getMonthName(selectedMonth)}</p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="finance-card p-6"
        >
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="w-5 h-5 text-emerald-400" />
            <span className="text-zinc-400">Your Share (50%)</span>
          </div>
          <p className="text-3xl font-mono font-bold text-emerald-400">
            {formatCurrency(summary?.your_share || 0)}
          </p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="finance-card p-6"
        >
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-5 h-5 text-violet-400" />
            <span className="text-zinc-400">Sister's Share (50%)</span>
          </div>
          <p className="text-3xl font-mono font-bold text-violet-400">
            {formatCurrency(summary?.sister_share || 0)}
          </p>
        </motion.div>
      </div>

      {/* One-Click Split PDF */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="finance-card p-6 sister-accent border-violet-500/30"
      >
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <h3 className="font-heading font-semibold text-lg text-white">Generate Summary Report</h3>
            <p className="text-sm text-zinc-400">
              Create a PDF summary for {getMonthName(selectedMonth)} to share with your sister
            </p>
          </div>
          <Button 
            onClick={handleDownloadPDF}
            className="bg-violet-600 hover:bg-violet-500 text-white"
            data-testid="download-pdf-btn"
          >
            <Download className="w-4 h-4 mr-2" />
            Download PDF
          </Button>
        </div>
      </motion.div>

      {/* Category Breakdown */}
      {summary?.by_category && Object.keys(summary.by_category).length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="finance-card p-6"
        >
          <h3 className="font-heading font-semibold text-lg text-white mb-4">By Category</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {Object.entries(summary.by_category).map(([cat, amount]) => {
              const catInfo = billCategories.find(c => c.value === cat) || { icon: Receipt };
              const Icon = catInfo.icon;
              return (
                <div key={cat} className="p-4 rounded-lg bg-zinc-800/50">
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className="w-4 h-4 text-violet-400" />
                    <span className="text-sm text-zinc-400">{cat}</span>
                  </div>
                  <p className="text-lg font-mono font-bold text-white">{formatCurrency(amount)}</p>
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* Bills Table */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="finance-card overflow-hidden"
      >
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-transparent">
                <TableHead className="text-zinc-400">Date</TableHead>
                <TableHead className="text-zinc-400">Category</TableHead>
                <TableHead className="text-zinc-400">Description</TableHead>
                <TableHead className="text-zinc-400 text-right">Amount</TableHead>
                <TableHead className="text-zinc-400 text-right">Your Share</TableHead>
                <TableHead className="text-zinc-400 w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {bills.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-zinc-500 py-12">
                    No household bills yet. Add your first bill!
                  </TableCell>
                </TableRow>
              ) : (
                bills.map((bill) => {
                  const catInfo = billCategories.find(c => c.value === bill.category) || { icon: Receipt };
                  const Icon = catInfo.icon;
                  return (
                    <TableRow 
                      key={bill.id} 
                      className="border-zinc-800 hover:bg-zinc-800/50"
                      data-testid={`bill-${bill.id}`}
                    >
                      <TableCell className="font-mono text-sm">{formatDate(bill.date)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Icon className="w-4 h-4 text-violet-400" />
                          {bill.category}
                        </div>
                      </TableCell>
                      <TableCell className="text-zinc-400">{bill.description}</TableCell>
                      <TableCell className="text-right font-mono">{formatCurrency(bill.amount)}</TableCell>
                      <TableCell className="text-right font-mono text-violet-400">
                        {formatCurrency(bill.split_amount || bill.amount / 2)}
                      </TableCell>
                      <TableCell>
                        <button
                          onClick={() => handleDelete(bill.id)}
                          className="p-1 rounded hover:bg-red-500/20 text-zinc-400 hover:text-red-400 transition-colors"
                          data-testid={`delete-bill-${bill.id}`}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </div>
      </motion.div>

      {/* Privacy Notice */}
      <div className="text-center text-sm text-zinc-500">
        <p>
          <span className="text-violet-400">Privacy Note:</span> This view only shows shared household expenses. 
          Your personal income and debt information is never visible here.
        </p>
      </div>
    </div>
  );
}
