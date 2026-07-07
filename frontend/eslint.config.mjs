import js from '@eslint/js'
import next from 'eslint-config-next'
import globals from 'globals'

export default [
  { ignores: ['.next/**', 'node_modules/**', 'next-env.d.ts'] },
  js.configs.recommended,
  ...next,                         // Next core-web-vitals + react-hooks (flat-config array)
  {
    files: ['**/*.{js,jsx,ts,tsx}'],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
      ecmaVersion: 'latest',
      sourceType: 'module',
    },
    rules: {
      'no-unused-vars': 'warn',
      'no-console': 'off',
      // Migration-friendly downgrades of the old house style:
      'complexity': 'off',
      'max-lines': 'off',
      'consistent-return': 'off',
      // React 19 / next core-web-vitals rules that fire on standard
      // lift-and-shift patterns (async fetch-in-effect, random chat colors,
      // stray quotes in JSX copy). Advisory, not build-blocking.
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/purity': 'warn',
      'react/no-unescaped-entities': 'warn',
    },
  },
  {
    // TypeScript understands type-only references (e.g. React.ReactNode) and
    // globals itself; the core `no-undef` rule is a known false-positive on
    // .ts/.tsx and is disabled per typescript-eslint guidance.
    files: ['**/*.{ts,tsx}'],
    rules: {
      'no-undef': 'off',
    },
  },
]
