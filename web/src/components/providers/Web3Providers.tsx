'use client';

/**
 * Client-side Web3 provider wrapper.
 * Wraps the app in WagmiProvider + QueryClientProvider + ConnectKitProvider.
 * Must be a separate 'use client' component because layout.tsx is a server component.
 */

import { WagmiProvider } from 'wagmi';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConnectKitProvider } from 'connectkit';
import { wagmiConfig } from '@/lib/wagmi';
import { ReactNode, useState } from 'react';

export function Web3Providers({ children }: { children: ReactNode }) {
  // Create QueryClient per render to avoid shared state between requests
  const [queryClient] = useState(() => new QueryClient());

  return (
    <WagmiProvider config={wagmiConfig}>
      <QueryClientProvider client={queryClient}>
        <ConnectKitProvider
          theme="midnight"
          customTheme={{
            '--ck-font-family': 'var(--font-mono)',
            '--ck-border-radius': '6px',
            '--ck-overlay-background': 'rgba(7,8,9,0.85)',
            '--ck-body-background': '#0d1117',
            '--ck-body-background-secondary': '#10141c',
            '--ck-body-color': '#e2e6f0',
            '--ck-body-color-muted': '#788098',
            '--ck-primary-button-background': '#00d68f',
            '--ck-primary-button-color': '#08090c',
            '--ck-primary-button-hover-background': '#00b87a',
            '--ck-focus-color': '#00d68f',
            '--ck-modal-box-shadow': '0 0 40px rgba(0,214,143,0.1)',
          }}
        >
          {children}
        </ConnectKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
}
