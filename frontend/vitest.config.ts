import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./', import.meta.url)),
    },
  },
  test: {
    include: ['./test/**/*.{test,spec}.{js,jsx,ts,tsx}'],
    environment: 'jsdom',
    setupFiles: ['./test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json-summary', 'html'],
      reportsDirectory: './coverage',
      include: ['app/**/*.{ts,tsx}', 'components/**/*.{js,jsx,ts,tsx}', 'contexts/**/*.{js,jsx,ts,tsx}', 'hooks/**/*.{js,jsx,ts,tsx}', 'lib/**/*.{ts,tsx}', 'lib/pagination/**/*.{js,jsx}', 'utils/**/*.{js,jsx,ts,tsx}', 'views/**/*.{js,jsx,ts,tsx}'],
      exclude: ['app/**/layout.tsx', 'app/**/loading.tsx', 'app/**/error.tsx', 'app/**/not-found.tsx'],
      thresholds: {
        // Ratcheted from the 2026-07-15 post-refactor baseline. Raise these as
        // new tests land; CI should fail if the existing safety net regresses.
        statements: 70,
        branches: 54,
        functions: 60,
        lines: 72,
        'contexts/AuthContext.jsx': {
          statements: 65,
          branches: 33,
          functions: 61,
          lines: 70,
        },
        'hooks/auth/**': {
          statements: 85,
          branches: 63,
          functions: 92,
          lines: 91,
        },
        'hooks/stream/insights/useStreamInsightsQuery.js': {
          statements: 100,
          branches: 94,
          functions: 100,
          lines: 100,
        },
        'hooks/stream/report/useStreamReportQuery.js': {
          statements: 90,
          branches: 75,
          functions: 100,
          lines: 92,
        },
        'hooks/stream/timeline/useStreamTimelineQuery.js': {
          statements: 90,
          branches: 66,
          functions: 90,
          lines: 89,
        },
        'hooks/creator/useAudienceMovementQuery.js': {
          statements: 100,
          branches: 88,
          functions: 100,
          lines: 100,
        },
        'hooks/creator/useCreatorSummaryQuery.js': {
          statements: 100,
          branches: 83,
          functions: 100,
          lines: 100,
        },
        'hooks/creator/useCreatorRegularsQuery.js': {
          statements: 100,
          branches: 100,
          functions: 100,
          lines: 100,
        },
        'hooks/creator/useCreatorTrendsQuery.js': {
          statements: 100,
          branches: 100,
          functions: 100,
          lines: 100,
        },
        'components/admin/users/UserManagementTable.jsx': {
          statements: 90,
          branches: 50,
          functions: 100,
          lines: 90,
        },
        'components/admin/users/UserManagementModals.jsx': {
          statements: 100,
          branches: 100,
          functions: 100,
          lines: 100,
        },
        'components/admin/users/EditUserForm.jsx': {
          statements: 90,
          branches: 100,
          functions: 83,
          lines: 90,
        },
        'views/admin/SystemInfo.jsx': {
          statements: 94,
          branches: 69,
          functions: 100,
          lines: 94,
        },
        'components/admin/system/RequestStatistics.jsx': {
          statements: 100,
          branches: 100,
          functions: 100,
          lines: 100,
        },
        'components/stream/list/StreamThumbnail.jsx': {
          statements: 100,
          branches: 83,
          functions: 100,
          lines: 100,
        },
        'components/stream/list/ThumbImage.jsx': {
          statements: 100,
          branches: 100,
          functions: 100,
          lines: 100,
        },
      },
    },
  },
})
