import { createContext, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { api } from './api';
import type { User } from './types';

interface UserContextValue {
  users: User[];
  currentUserId: number | null;
  setCurrentUserId: (id: number) => void;
  loadError: string | null;
}

const UserContext = createContext<UserContextValue | null>(null);

const STORAGE_KEY = 'tavora_current_user_id';

export function UserProvider({ children }: { children: ReactNode }) {
  const [users, setUsers] = useState<User[]>([]);
  const [currentUserId, setCurrentUserIdState] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listUsers()
      .then((fetched) => {
        setUsers(fetched);
        const stored = localStorage.getItem(STORAGE_KEY);
        const storedId = stored ? Number(stored) : null;
        const valid = fetched.find((u) => u.id === storedId);
        setCurrentUserIdState(valid ? valid.id : (fetched[0]?.id ?? null));
      })
      .catch((err) => {
        /*
         * Without this, a failed fetch here leaves "Loading users..." shown
         * forever with no indication anything went wrong - an unhandled
         * promise rejection the user would never see.
         */
        setLoadError(err instanceof Error ? err.message : 'Failed to load users');
      });
  }, []);

  const setCurrentUserId = (id: number) => {
    setCurrentUserIdState(id);
    localStorage.setItem(STORAGE_KEY, String(id));
  };

  return (
    <UserContext.Provider value={{ users, currentUserId, setCurrentUserId, loadError }}>
      {children}
    </UserContext.Provider>
  );
}

export function useCurrentUser() {
  const ctx = useContext(UserContext);
  if (!ctx) {
    throw new Error('useCurrentUser must be used within a UserProvider');
  }
  return ctx;
}
