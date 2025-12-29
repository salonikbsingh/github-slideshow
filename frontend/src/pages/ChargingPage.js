import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { chargingAPI } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow 
} from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Zap, Plus, Trash2, Battery, DollarSign, MapPin } from 'lucide-react';
import { toast } from 'sonner';

export default function ChargingPage() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    kwh: '',
    cost: '',
    location: '',
  });

  const fetchSessions = async () => {
    try {
      const response = await chargingAPI.getAll();
      setSessions(response.data);
    } catch (error) {
      toast.error('Failed to load charging sessions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await chargingAPI.create({
        ...formData,
        kwh: parseFloat(formData.kwh),
        cost: parseFloat(formData.cost),
      });
      toast.success('Charging session logged');
      setDialogOpen(false);
      setFormData({
        date: new Date().toISOString().split('T')[0],
        kwh: '',
        cost: '',
        location: '',
      });
      fetchSessions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add session');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this charging session?')) return;
    try {
      await chargingAPI.delete(id);
      setSessions(sessions.filter(s => s.id !== id));
      toast.success('Session deleted');
    } catch (error) {
      toast.error('Failed to delete session');
    }
  };

  const totals = sessions.reduce((acc, session) => {
    acc.kwh += session.kwh;
    acc.cost += session.cost;
    acc.rebate += session.rebate_earned || (session.kwh * 0.03);
    return acc;
  }, { kwh: 0, cost: 0, rebate: 0 });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="charging-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl md:text-3xl font-bold text-white">EV Charging</h1>
          <p className="text-zinc-400">Track your electric vehicle charging sessions</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="finance-btn-primary" data-testid="add-charging-btn">
              <Plus className="w-4 h-4 mr-2" /> Add Session
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-zinc-900 border-zinc-800">
            <DialogHeader>
              <DialogTitle>Log Charging Session</DialogTitle>
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
                  data-testid="charging-date"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
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
                    required
                    data-testid="charging-kwh"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="cost">Cost (CAD)</Label>
                  <Input
                    id="cost"
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={formData.cost}
                    onChange={(e) => setFormData({ ...formData, cost: e.target.value })}
                    className="finance-input"
                    required
                    data-testid="charging-cost"
                  />
                </div>
              </div>
              {formData.kwh && (
                <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                  <p className="text-sm text-emerald-400">
                    Rebate Earned: ${(parseFloat(formData.kwh) * 0.03).toFixed(2)}
                  </p>
                  <p className="text-xs text-zinc-500">$0.03 per kWh</p>
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="location">Location</Label>
                <Input
                  id="location"
                  type="text"
                  placeholder="e.g., Home, Tesla Supercharger"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="finance-input"
                  required
                  data-testid="charging-location"
                />
              </div>
              <Button type="submit" className="w-full finance-btn-primary" data-testid="charging-submit">
                Save Charging Session
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="finance-card p-6"
        >
          <div className="flex items-center gap-2 mb-2">
            <Battery className="w-5 h-5 text-blue-400" />
            <span className="text-zinc-400">Total Energy</span>
          </div>
          <p className="text-3xl font-mono font-bold text-white">
            {totals.kwh.toFixed(1)} kWh
          </p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="finance-card p-6"
        >
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="w-5 h-5 text-amber-400" />
            <span className="text-zinc-400">Total Cost</span>
          </div>
          <p className="text-3xl font-mono font-bold text-white">
            {formatCurrency(totals.cost)}
          </p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="finance-card p-6"
        >
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-5 h-5 text-emerald-400" />
            <span className="text-zinc-400">Rebate Earned</span>
          </div>
          <p className="text-3xl font-mono font-bold text-emerald-400">
            +{formatCurrency(totals.rebate)}
          </p>
          <p className="text-xs text-zinc-500 mt-1">$0.03/kWh</p>
        </motion.div>
      </div>

      {/* Charging Table */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="finance-card overflow-hidden"
      >
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-transparent">
                <TableHead className="text-zinc-400">Date</TableHead>
                <TableHead className="text-zinc-400">Location</TableHead>
                <TableHead className="text-zinc-400">Energy</TableHead>
                <TableHead className="text-zinc-400">Cost</TableHead>
                <TableHead className="text-zinc-400">Rebate</TableHead>
                <TableHead className="text-zinc-400 w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sessions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-zinc-500 py-12">
                    No charging sessions yet. Log your first charge!
                  </TableCell>
                </TableRow>
              ) : (
                sessions.map((session) => (
                  <TableRow 
                    key={session.id} 
                    className="border-zinc-800 hover:bg-zinc-800/50"
                    data-testid={`charging-${session.id}`}
                  >
                    <TableCell className="font-mono text-sm">{formatDate(session.date)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-zinc-500" />
                        {session.location}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono">{session.kwh.toFixed(1)} kWh</TableCell>
                    <TableCell className="font-mono">{formatCurrency(session.cost)}</TableCell>
                    <TableCell className="font-mono text-emerald-400">
                      +{formatCurrency(session.rebate_earned || session.kwh * 0.03)}
                    </TableCell>
                    <TableCell>
                      <button
                        onClick={() => handleDelete(session.id)}
                        className="p-1 rounded hover:bg-red-500/20 text-zinc-400 hover:text-red-400 transition-colors"
                        data-testid={`delete-charging-${session.id}`}
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
