import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { mileageAPI } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow 
} from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Car, Plus, Trash2, Briefcase, User } from 'lucide-react';
import { toast } from 'sonner';

export default function MileagePage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    start_km: '',
    end_km: '',
    purpose: 'Business',
  });

  const fetchLogs = async () => {
    try {
      const response = await mileageAPI.getAll();
      setLogs(response.data);
    } catch (error) {
      toast.error('Failed to load mileage logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await mileageAPI.create({
        ...formData,
        start_km: parseFloat(formData.start_km),
        end_km: parseFloat(formData.end_km),
      });
      toast.success('Mileage log added');
      setDialogOpen(false);
      setFormData({
        date: new Date().toISOString().split('T')[0],
        start_km: '',
        end_km: '',
        purpose: 'Business',
      });
      fetchLogs();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add log');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this mileage log?')) return;
    try {
      await mileageAPI.delete(id);
      setLogs(logs.filter(l => l.id !== id));
      toast.success('Log deleted');
    } catch (error) {
      toast.error('Failed to delete log');
    }
  };

  const totals = logs.reduce((acc, log) => {
    const distance = log.distance || (log.end_km - log.start_km);
    if (log.purpose === 'Business') {
      acc.business += distance;
    } else {
      acc.personal += distance;
    }
    return acc;
  }, { business: 0, personal: 0 });

  const businessPercent = totals.business + totals.personal > 0 
    ? ((totals.business / (totals.business + totals.personal)) * 100).toFixed(1)
    : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="mileage-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl md:text-3xl font-bold text-white">Mileage Log</h1>
          <p className="text-zinc-400">Track your business and personal driving</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="finance-btn-primary" data-testid="add-mileage-btn">
              <Plus className="w-4 h-4 mr-2" /> Add Trip
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-zinc-900 border-zinc-800">
            <DialogHeader>
              <DialogTitle>Log Mileage</DialogTitle>
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
                  data-testid="mileage-date"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="start_km">Start (km)</Label>
                  <Input
                    id="start_km"
                    type="number"
                    step="0.1"
                    placeholder="0"
                    value={formData.start_km}
                    onChange={(e) => setFormData({ ...formData, start_km: e.target.value })}
                    className="finance-input"
                    required
                    data-testid="mileage-start"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="end_km">End (km)</Label>
                  <Input
                    id="end_km"
                    type="number"
                    step="0.1"
                    placeholder="0"
                    value={formData.end_km}
                    onChange={(e) => setFormData({ ...formData, end_km: e.target.value })}
                    className="finance-input"
                    required
                    data-testid="mileage-end"
                  />
                </div>
              </div>
              {formData.start_km && formData.end_km && (
                <p className="text-sm text-zinc-400">
                  Distance: <span className="text-white font-mono">{(parseFloat(formData.end_km) - parseFloat(formData.start_km)).toFixed(1)} km</span>
                </p>
              )}
              <div className="space-y-2">
                <Label>Purpose</Label>
                <Select 
                  value={formData.purpose} 
                  onValueChange={(v) => setFormData({ ...formData, purpose: v })}
                >
                  <SelectTrigger className="finance-input" data-testid="mileage-purpose">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Business">Business</SelectItem>
                    <SelectItem value="Personal">Personal</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button type="submit" className="w-full finance-btn-primary" data-testid="mileage-submit">
                Save Mileage Log
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
            <Briefcase className="w-5 h-5 text-amber-400" />
            <span className="text-zinc-400">Business</span>
          </div>
          <p className="text-3xl font-mono font-bold text-white">
            {totals.business.toLocaleString()} km
          </p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="finance-card p-6"
        >
          <div className="flex items-center gap-2 mb-2">
            <User className="w-5 h-5 text-zinc-400" />
            <span className="text-zinc-400">Personal</span>
          </div>
          <p className="text-3xl font-mono font-bold text-white">
            {totals.personal.toLocaleString()} km
          </p>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="finance-card p-6"
        >
          <div className="flex items-center gap-2 mb-2">
            <Car className="w-5 h-5 text-emerald-400" />
            <span className="text-zinc-400">Business %</span>
          </div>
          <p className="text-3xl font-mono font-bold text-emerald-400">
            {businessPercent}%
          </p>
        </motion.div>
      </div>

      {/* Mileage Table */}
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
                <TableHead className="text-zinc-400">Start</TableHead>
                <TableHead className="text-zinc-400">End</TableHead>
                <TableHead className="text-zinc-400">Distance</TableHead>
                <TableHead className="text-zinc-400">Purpose</TableHead>
                <TableHead className="text-zinc-400 w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-zinc-500 py-12">
                    No mileage logs yet. Add your first trip!
                  </TableCell>
                </TableRow>
              ) : (
                logs.map((log) => (
                  <TableRow 
                    key={log.id} 
                    className="border-zinc-800 hover:bg-zinc-800/50"
                    data-testid={`mileage-${log.id}`}
                  >
                    <TableCell className="font-mono text-sm">{formatDate(log.date)}</TableCell>
                    <TableCell className="font-mono">{log.start_km.toLocaleString()}</TableCell>
                    <TableCell className="font-mono">{log.end_km.toLocaleString()}</TableCell>
                    <TableCell className="font-mono font-bold">
                      {(log.distance || log.end_km - log.start_km).toFixed(1)} km
                    </TableCell>
                    <TableCell>
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
                        log.purpose === 'Business' 
                          ? 'bg-amber-500/20 text-amber-400' 
                          : 'bg-zinc-700 text-zinc-400'
                      }`}>
                        {log.purpose === 'Business' ? <Briefcase className="w-3 h-3" /> : <User className="w-3 h-3" />}
                        {log.purpose}
                      </span>
                    </TableCell>
                    <TableCell>
                      <button
                        onClick={() => handleDelete(log.id)}
                        className="p-1 rounded hover:bg-red-500/20 text-zinc-400 hover:text-red-400 transition-colors"
                        data-testid={`delete-mileage-${log.id}`}
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
