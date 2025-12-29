import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';
import { authAPI, profileAPI, exportAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { 
  User, Shield, Download, Settings, Home, Car, Target,
  Check, X, QrCode
} from 'lucide-react';
import { toast } from 'sonner';

export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [totpSetup, setTotpSetup] = useState(null);
  const [totpCode, setTotpCode] = useState('');

  const fetchProfile = async () => {
    try {
      const response = await profileAPI.get();
      setProfile(response.data);
    } catch (error) {
      toast.error('Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      await profileAPI.update(profile);
      toast.success('Profile updated');
    } catch (error) {
      toast.error('Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const handleSetupTOTP = async () => {
    try {
      const response = await authAPI.setupTOTP();
      setTotpSetup(response.data);
    } catch (error) {
      toast.error('Failed to setup 2FA');
    }
  };

  const handleVerifyTOTP = async () => {
    if (totpCode.length !== 6) {
      toast.error('Enter a 6-digit code');
      return;
    }
    try {
      await authAPI.verifyTOTPSetup(totpCode);
      toast.success('2FA enabled successfully!');
      setTotpSetup(null);
      setTotpCode('');
      await refreshUser();
    } catch (error) {
      toast.error('Invalid code. Please try again.');
    }
  };

  const handleDisableTOTP = async () => {
    const code = window.prompt('Enter your 2FA code to disable:');
    if (!code || code.length !== 6) {
      toast.error('Invalid code');
      return;
    }
    try {
      await authAPI.disableTOTP(code);
      toast.success('2FA disabled');
      await refreshUser();
    } catch (error) {
      toast.error('Failed to disable 2FA');
    }
  };

  const handleExportData = async () => {
    try {
      const response = await exportAPI.downloadCSV();
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cad_finance_backup_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('Data exported for CRA backup!');
    } catch (error) {
      toast.error('Failed to export data');
    }
  };

  const updateProfile = (field, value) => {
    setProfile({ ...profile, [field]: value });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-emerald-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-2xl" data-testid="settings-page">
      {/* Header */}
      <div>
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-white">Settings</h1>
        <p className="text-zinc-400">Manage your account and preferences</p>
      </div>

      {/* Profile Section */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="finance-card p-6 space-y-6"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/20">
            <User className="w-5 h-5 text-emerald-400" />
          </div>
          <h2 className="font-heading text-lg font-semibold">Profile</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label className="text-zinc-400">Name</Label>
            <p className="text-white font-medium">{user?.name}</p>
          </div>
          <div>
            <Label className="text-zinc-400">Email</Label>
            <p className="text-white font-medium">{user?.email}</p>
          </div>
        </div>
      </motion.section>

      {/* Home Office Section */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="finance-card p-6 space-y-6"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-amber-500/20">
            <Home className="w-5 h-5 text-amber-400" />
          </div>
          <h2 className="font-heading text-lg font-semibold">Home Office</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="home_sqft">Total Home (sq ft)</Label>
            <Input
              id="home_sqft"
              type="number"
              value={profile?.home_sqft || ''}
              onChange={(e) => updateProfile('home_sqft', parseFloat(e.target.value) || 0)}
              className="finance-input"
              data-testid="setting-home-sqft"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="office_sqft">Office Space (sq ft)</Label>
            <Input
              id="office_sqft"
              type="number"
              value={profile?.office_sqft || ''}
              onChange={(e) => updateProfile('office_sqft', parseFloat(e.target.value) || 0)}
              className="finance-input"
              data-testid="setting-office-sqft"
            />
          </div>
        </div>
        
        {profile?.home_sqft > 0 && profile?.office_sqft > 0 && (
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
            <p className="text-sm text-emerald-400">
              Deductible Ratio: {((profile.office_sqft / profile.home_sqft) * 100).toFixed(1)}%
            </p>
          </div>
        )}
      </motion.section>

      {/* EV Section */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="finance-card p-6 space-y-6"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-500/20">
            <Car className="w-5 h-5 text-blue-400" />
          </div>
          <h2 className="font-heading text-lg font-semibold">EV Details (Class 54)</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="ev_price">Purchase Price (CAD)</Label>
            <Input
              id="ev_price"
              type="number"
              value={profile?.ev_purchase_price || ''}
              onChange={(e) => updateProfile('ev_purchase_price', parseFloat(e.target.value) || 0)}
              className="finance-input"
              data-testid="setting-ev-price"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ucc">Opening UCC (Jan 1, 2026)</Label>
            <Input
              id="ucc"
              type="number"
              value={profile?.opening_ucc || ''}
              onChange={(e) => updateProfile('opening_ucc', parseFloat(e.target.value) || 0)}
              className="finance-input"
              data-testid="setting-ucc"
            />
          </div>
        </div>
      </motion.section>

      {/* Goals Section */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="finance-card p-6 space-y-6"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-violet-500/20">
            <Target className="w-5 h-5 text-violet-400" />
          </div>
          <h2 className="font-heading text-lg font-semibold">Financial Goals</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="debt_goal">Debt Paydown Goal</Label>
            <Input
              id="debt_goal"
              type="number"
              value={profile?.debt_goal || ''}
              onChange={(e) => updateProfile('debt_goal', parseFloat(e.target.value) || 0)}
              className="finance-input"
              data-testid="setting-debt-goal"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="tfsa_goal">TFSA Goal</Label>
            <Input
              id="tfsa_goal"
              type="number"
              value={profile?.tfsa_goal || ''}
              onChange={(e) => updateProfile('tfsa_goal', parseFloat(e.target.value) || 0)}
              className="finance-input"
              data-testid="setting-tfsa-goal"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="rrsp_goal">RRSP Goal</Label>
            <Input
              id="rrsp_goal"
              type="number"
              value={profile?.rrsp_goal || ''}
              onChange={(e) => updateProfile('rrsp_goal', parseFloat(e.target.value) || 0)}
              className="finance-input"
              data-testid="setting-rrsp-goal"
            />
          </div>
        </div>
        
        <Button 
          onClick={handleSaveProfile} 
          className="finance-btn-primary"
          disabled={saving}
          data-testid="save-profile-btn"
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </Button>
      </motion.section>

      {/* Security Section */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="finance-card p-6 space-y-6"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/20">
            <Shield className="w-5 h-5 text-emerald-400" />
          </div>
          <h2 className="font-heading text-lg font-semibold">Security</h2>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg bg-zinc-800/50">
            <div className="flex items-center gap-3">
              <QrCode className="w-5 h-5 text-zinc-400" />
              <div>
                <p className="font-medium">Two-Factor Authentication</p>
                <p className="text-sm text-zinc-500">
                  {user?.totp_enabled ? 'Enabled - Your account is protected' : 'Add an extra layer of security'}
                </p>
              </div>
            </div>
            {user?.totp_enabled ? (
              <Button 
                variant="outline" 
                className="border-red-500/50 text-red-400 hover:bg-red-500/10"
                onClick={handleDisableTOTP}
                data-testid="disable-2fa-btn"
              >
                Disable
              </Button>
            ) : (
              <Button 
                className="finance-btn-primary"
                onClick={handleSetupTOTP}
                data-testid="enable-2fa-btn"
              >
                Enable 2FA
              </Button>
            )}
          </div>

          {/* TOTP Setup Modal */}
          {totpSetup && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="p-4 rounded-lg bg-zinc-800 space-y-4"
            >
              <h3 className="font-medium">Scan QR Code with your Authenticator App</h3>
              <div className="flex justify-center">
                <img 
                  src={totpSetup.qr_code} 
                  alt="TOTP QR Code" 
                  className="w-48 h-48 bg-white p-2 rounded-lg"
                />
              </div>
              <div className="text-center">
                <p className="text-sm text-zinc-400 mb-2">Or enter this code manually:</p>
                <code className="px-3 py-1 bg-zinc-700 rounded text-sm font-mono">
                  {totpSetup.secret}
                </code>
              </div>
              <Separator className="bg-zinc-700" />
              <div className="space-y-2">
                <Label htmlFor="totp-code">Enter the 6-digit code from your app</Label>
                <div className="flex gap-2">
                  <Input
                    id="totp-code"
                    type="text"
                    maxLength={6}
                    placeholder="000000"
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
                    className="finance-input font-mono text-center text-xl tracking-widest"
                    data-testid="totp-verify-input"
                  />
                  <Button 
                    onClick={handleVerifyTOTP}
                    className="finance-btn-primary"
                    data-testid="verify-2fa-btn"
                  >
                    <Check className="w-4 h-4" />
                  </Button>
                  <Button 
                    variant="ghost"
                    onClick={() => { setTotpSetup(null); setTotpCode(''); }}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </motion.section>

      {/* Export Section */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="finance-card p-6 space-y-6"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-blue-500/20">
            <Download className="w-5 h-5 text-blue-400" />
          </div>
          <h2 className="font-heading text-lg font-semibold">Data Export</h2>
        </div>
        
        <div className="flex items-center justify-between p-4 rounded-lg bg-zinc-800/50">
          <div>
            <p className="font-medium">Export All Data to CSV</p>
            <p className="text-sm text-zinc-500">Download a backup for CRA audit purposes</p>
          </div>
          <Button 
            onClick={handleExportData}
            className="finance-btn-secondary"
            data-testid="export-csv-btn"
          >
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </motion.section>
    </div>
  );
}
