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
      include: ['app/**/*.{ts,tsx}', 'components/**/*.{ts,tsx}', 'contexts/**/*.{ts,tsx}', 'hooks/**/*.{ts,tsx}', 'lib/**/*.{ts,tsx}', 'utils/**/*.{ts,tsx}', 'views/**/*.{ts,tsx}'],
      exclude: ['app/**/layout.tsx', 'app/**/loading.tsx', 'app/**/error.tsx', 'app/**/not-found.tsx'],
      thresholds: {
        // Ratcheted from the 2026-07-15 post-refactor baseline. Raise these as
        // new tests land; CI should fail if the existing safety net regresses.
        statements: 70,
        branches: 54,
        functions: 60,
        lines: 72,
        'contexts/AuthContext.tsx': {
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
        'hooks/stream/insights/useStreamInsightsQuery.ts': {
          statements: 100,
          branches: 94,
          functions: 100,
          lines: 100,
        },
        'hooks/stream/report/useStreamReportQuery.ts': {
          statements: 90,
          branches: 75,
          functions: 100,
          lines: 92,
        },
        'hooks/stream/timeline/useStreamTimelineQuery.ts': {
          statements: 90,
          branches: 66,
          functions: 90,
          lines: 89,
        },
        'hooks/creator/useAudienceMovementQuery.ts': {
          statements: 100,
          branches: 88,
          functions: 100,
          lines: 100,
        },
        'hooks/creator/useCreatorSummaryQuery.ts': {
          statements: 100,
          branches: 83,
          functions: 100,
          lines: 100,
        },
        'hooks/creator/useCreatorRegularsQuery.ts': {
          statements: 100,
          branches: 100,
          functions: 100,
          lines: 100,
        },
        'hooks/creator/useCreatorTrendsQuery.ts': {
          statements: 100,
          branches: 100,
          functions: 100,
          lines: 100,
        },
        'components/admin/users/UserManagementTable.tsx': {
          statements: 90,
          branches: 50,
          functions: 100,
          lines: 90,
        },
        'components/admin/users/UserManagementModals.tsx': {
          statements: 100,
          branches: 100,
          functions: 100,
          lines: 100,
        },
        'components/admin/users/EditUserForm.tsx': {
          statements: 90,
          branches: 100,
          functions: 83,
          lines: 90,
        },
        'views/admin/SystemInfo.tsx': {
          statements: 94,
          branches: 69,
          functions: 100,
          lines: 94,
        },
        'components/admin/system/RequestStatistics.tsx': {
          statements: 100,
          branches: 100,
          functions: 100,
          lines: 100,
        },
        'components/stream/list/StreamThumbnail.tsx': {
          statements: 100,
          branches: 83,
          functions: 100,
          lines: 100,
        },
        'components/stream/list/ThumbImage.tsx': {
          statements: 100,
          branches: 100,
          functions: 100,
          lines: 100,
        },
        'views/creator/AudienceMovement.tsx': {
          statements: 100,
          branches: 80,
          functions: 100,
          lines: 100,
        },
        'views/community/ChatterVersus.tsx': {
          statements: 100,
          branches: 80,
          functions: 100,
          lines: 100,
        },
        'views/scene/EmoteDetail.tsx': {
          statements: 100,
          branches: 75,
          functions: 100,
          lines: 100,
        },
      },
    },
  },
})
