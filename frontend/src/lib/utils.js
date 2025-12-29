import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount, currency = 'CAD') {
  return new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency: currency,
  }).format(amount);
}

export function formatPercent(value) {
  return `${Math.min(100, Math.max(0, value)).toFixed(1)}%`;
}

export function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('en-CA', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function getCurrentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

export function getMonthName(monthString) {
  const [year, month] = monthString.split('-');
  return new Date(year, month - 1).toLocaleDateString('en-CA', { month: 'long', year: 'numeric' });
}
