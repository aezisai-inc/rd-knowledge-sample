'use client';

import { useEffect, ReactNode } from 'react';
import { configureAmplify } from '../lib/amplify-config';

interface AmplifyProviderProps {
  children: ReactNode;
}

/**
 * Amplify Provider
 *
 * アプリケーション全体で Amplify を使用可能にする
 */
export function AmplifyProvider({ children }: AmplifyProviderProps) {
  useEffect(() => {
    configureAmplify();
  }, []);

  return <>{children}</>;
}
