import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { transactionsAPI } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { 
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow 
} from '@/components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  TrendingUp, TrendingDown, Search, Filter, Trash2, Plus, Download,
  Briefcase, ShoppingCart, Home
} from 'lucide-react';
import { toast } from 'sonner';

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  const fetchTransactions = async () => {
    try {
      const response = await transactionsAPI.getAll();
      setTransactions(response.data);
    } catch (error) {
      toast.error('Failed to load transactions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, []);

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this transaction?')) return;
    try {
      await transactionsAPI.delete(id);
      setTransactions(transactions.filter(t => t.id !== id));
      toast.success('Transaction deleted');
    } catch (error) {
      toast.error('Failed to delete transaction');
    }
  };

  const filteredTransactions = transactions.filter(t => {
    const matchesSearch = t.category.toLowerCase().includes(search.toLowerCase()) ||
                          t.description?.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === 'all' || 
                          (filter === 'income' && t.type === 'Income') ||
                          (filter === 'expense' && t.type === 'Expense') ||
                          (filter === 'business' && t.is_business);
    return matchesSearch && matchesFilter;
  });

  const totals = filteredTransactions.reduce((acc, t) => {
    if (t.type === 'Income') {
      acc.income += t.amount;
    } else {
      acc.expenses += t.amount;
    }
    return acc;
  }, { income: 0, expenses: 0 });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="transactions-page">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl md:text-3xl font-bold text-white">Transactions</h1>
          <p className="text-zinc-400">Manage your income and expenses</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="finance-card p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-zinc-400">Income</span>
          </div>
          <p className="text-2xl font-mono font-bold text-emerald-400">
            {formatCurrency(totals.income)}
          </p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="finance-card p-4"
        >
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown className="w-4 h-4 text-red-400" />
            <span className="text-sm text-zinc-400">Expenses</span>
          </div>
          <p className="text-2xl font-mono font-bold text-red-400">
            {formatCurrency(totals.expenses)}
          </p>
        </motion.div>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <Input
            placeholder="Search transactions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="finance-input pl-10"
            data-testid="search-transactions"
          />
        </div>
        <Select value={filter} onValueChange={setFilter}>
          <SelectTrigger className="w-full md:w-48 finance-input" data-testid="filter-transactions">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Filter" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Transactions</SelectItem>
            <SelectItem value="income">Income Only</SelectItem>
            <SelectItem value="expense">Expenses Only</SelectItem>
            <SelectItem value="business">Business Only</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Transactions Table */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="finance-card overflow-hidden"
      >
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-transparent">
                <TableHead className="text-zinc-400">Date</TableHead>
                <TableHead className="text-zinc-400">Category</TableHead>
                <TableHead className="text-zinc-400">Type</TableHead>
                <TableHead className="text-zinc-400 text-right">Amount</TableHead>
                <TableHead className="text-zinc-400 w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredTransactions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-zinc-500 py-12">
                    No transactions found. Use the + button to add one!
                  </TableCell>
                </TableRow>
              ) : (
                filteredTransactions.map((transaction) => (
                  <TableRow 
                    key={transaction.id} 
                    className="border-zinc-800 hover:bg-zinc-800/50"
                    data-testid={`transaction-${transaction.id}`}
                  >
                    <TableCell className="font-mono text-sm">
                      {formatDate(transaction.date)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {transaction.is_business ? (
                          <Briefcase className="w-4 h-4 text-amber-400" />
                        ) : transaction.split_with_sister ? (
                          <Home className="w-4 h-4 text-violet-400" />
                        ) : (
                          <ShoppingCart className="w-4 h-4 text-zinc-400" />
                        )}
                        <span>{transaction.category}</span>
                        {transaction.description && (
                          <span className="text-xs text-zinc-500 hidden md:inline">
                            - {transaction.description}
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
                        transaction.type === 'Income' 
                          ? 'bg-emerald-500/20 text-emerald-400' 
                          : 'bg-red-500/20 text-red-400'
                      }`}>
                        {transaction.type === 'Income' ? (
                          <TrendingUp className="w-3 h-3" />
                        ) : (
                          <TrendingDown className="w-3 h-3" />
                        )}
                        {transaction.type}
                      </span>
                    </TableCell>
                    <TableCell className={`text-right font-mono ${
                      transaction.type === 'Income' ? 'text-emerald-400' : 'text-white'
                    }`}>
                      {transaction.type === 'Income' ? '+' : '-'}
                      {formatCurrency(transaction.amount)}
                    </TableCell>
                    <TableCell>
                      <button
                        onClick={() => handleDelete(transaction.id)}
                        className="p-1 rounded hover:bg-red-500/20 text-zinc-400 hover:text-red-400 transition-colors"
                        data-testid={`delete-${transaction.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </motion.div>
    </div>
  );
}
