/**
 * Wagmi v2 configuration — Base L2 (chain ID 8453)
 * USDC on Base: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 (6 decimals)
 *
 * IMPORTANT: USDC is ERC-20 — use parseUnits("100", 6), NOT parseEther.
 * Verify payments via Transfer event logs, NOT transaction.value (always 0n for ERC-20).
 */

import { createConfig, http } from 'wagmi';
import { base } from 'wagmi/chains';
import { getDefaultConfig } from 'connectkit';

export const wagmiConfig = createConfig(
  getDefaultConfig({
    chains: [base],
    transports: {
      [base.id]: http(
        process.env.NEXT_PUBLIC_BASE_RPC_URL || 'https://mainnet.base.org'
      ),
    },
    walletConnectProjectId: process.env.NEXT_PUBLIC_WC_PROJECT_ID || '',
    appName: 'Crevia Cockpit',
    appDescription: 'Crypto Market Intelligence Platform',
    appUrl: process.env.NEXT_PUBLIC_SITE_URL || 'https://creviacockpit.com',
  })
);

// USDC contract on Base mainnet
export const USDC_ADDRESS = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' as const;

// Minimal ERC-20 ABI — only transfer needed for payments
export const USDC_ABI = [
  {
    name: 'transfer',
    type: 'function',
    stateMutability: 'nonpayable',
    inputs: [
      { name: 'to',    type: 'address' },
      { name: 'value', type: 'uint256' },
    ],
    outputs: [{ name: '', type: 'bool' }],
  },
  {
    name: 'balanceOf',
    type: 'function',
    stateMutability: 'view',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
  },
  {
    name: 'decimals',
    type: 'function',
    stateMutability: 'view',
    inputs: [],
    outputs: [{ name: '', type: 'uint8' }],
  },
] as const;

export const BASE_CHAIN_ID = base.id; // 8453
