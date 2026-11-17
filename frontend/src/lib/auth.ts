import { User, UserRole } from '../types';
import { MOCK_USER } from './mockData';

const TOKEN_KEY = 'medisync_access_token';
const USER_KEY = 'medisync_user';

export const getStoredToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
};

export const setStoredAuth = (token: string, user: User): void => {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
};

export const clearStoredAuth = (): void => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
};

export const getStoredUser = (): User => {
  if (typeof window === 'undefined') return MOCK_USER;
  const userJson = localStorage.getItem(USER_KEY);
  if (!userJson) return MOCK_USER;
  try {
    return JSON.parse(userJson);
  } catch {
    return MOCK_USER;
  }
};

export const hasRole = (user: User, allowedRoles: UserRole[]): boolean => {
  if (user.is_superuser || user.role === 'ADMIN') return true;
  return allowedRoles.includes(user.role);
};
