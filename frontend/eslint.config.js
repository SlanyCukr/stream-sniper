const js = require('@eslint/js')
const react = require('eslint-plugin-react')
const reactHooks = require('eslint-plugin-react-hooks')
const globals = require('globals')

module.exports = [
    js.configs.recommended,
    {
        files: [
            '**/*.{js,jsx}',
        ],
        plugins: {
            react,
            'react-hooks': reactHooks,
        },
        languageOptions: {
            globals: {
                ...globals.browser,
                ...globals.node,
                ...globals.es2021,
            },
            ecmaVersion: 'latest',
            sourceType: 'module',
            parserOptions: {
                ecmaFeatures: {
                    jsx: true,
                },
            },
        },
        settings: {
            react: {
                version: 'detect',
            },
        },
        rules: {
            // Warning and error rules
            'no-warning-comments': [
                'warn',
                {
                    terms: [
                        'fixme',
                    ],
                    location: 'anywhere',
                },
            ],
            'brace-style': [
                'warn',
                '1tbs',
            ],
            'comma-dangle': [
                'warn',
                'always-multiline',
            ],
            'complexity': [
                'error',
                10,
            ],
            'curly': 'warn',
            'no-eq-null': 'error',
            'no-eval': 'error',
            'no-implied-eval': 'error',
            'prefer-promise-reject-errors': 'error',
            'no-shadow': 'error',
            'no-undefined': 'error',
            'consistent-return': 'error',
            'camelcase': [
                2,
                {
                    ignoreDestructuring: true,
                    properties: 'never',
                },
            ],
            'dot-notation': [
                'error',
                {
                    allowPattern: '^[a-z]+(_[a-z]+)+$',
                },
            ],
            'comma-style': [
                'error',
                'last',
            ],
            'eol-last': [
                'error',
                'always',
            ],
            'max-params': [
                'error',
                4,
            ],
            'no-duplicate-imports': [
                'error',
                {
                    includeExports: true,
                },
            ],
            'indent': [
                'error',
                4,
                {
                    SwitchCase: 1,
                },
            ],
            'array-bracket-newline': [
                'error',
                'always',
            ],
            'array-bracket-spacing': [
                'error',
                'always',
            ],
            'array-element-newline': [
                'error',
                'always',
            ],
            'semi': [
                'error',
                'never',
            ],
            'quotes': [
                'error',
                'single',
                {
                    avoidEscape: true,
                },
            ],
            'object-curly-spacing': [
                'error',
                'always',
                {
                    arraysInObjects: true,
                    objectsInObjects: true,
                },
            ],
            'object-curly-newline': [
                'error',
                {
                    minProperties: 2,
                    consistent: true,
                },
            ],
            'object-property-newline': 'error',
            'arrow-body-style': [
                'error',
                'as-needed',
            ],
            'arrow-parens': [
                'error',
                'as-needed',
            ],
            'no-var': 'error',
            'no-useless-rename': [
                'error',
                {
                    ignoreExport: true,
                    ignoreDestructuring: true,
                },
            ],
            'prefer-numeric-literals': 'error',
            'no-extra-boolean-cast': 'error',
            'no-trailing-spaces': [
                'error',
                {
                    ignoreComments: true,
                },
            ],
            'max-lines': [
                'error',
                {
                    max: 300,
                    skipComments: true,
                    skipBlankLines: true,
                },
            ],
            'no-async-promise-executor': 'error',
            'no-await-in-loop': 'error',
            'no-prototype-builtins': 'error',
            'no-unused-vars': 'warn',

            // React specific rules
            'react/jsx-uses-vars': [
                2,
            ],
            'react/react-in-jsx-scope': 'off',
            'react/jsx-max-props-per-line': [
                'error',
                {
                    maximum: 1,
                    when: 'always',
                },
            ],
            'react/jsx-first-prop-new-line': 'error',
            'react/display-name': 'off',
            'react/no-access-state-in-setstate': 'warn',
            'react/no-deprecated': 'warn',
            'react/no-adjacent-inline-elements': 'warn',
            'react/no-danger': 'warn',
            'react/no-multi-comp': 'warn',
            'react/no-redundant-should-component-update': 'error',
            'react/no-typos': 'warn',
            'react/no-unsafe': 'error',
            'react/no-unused-prop-types': 'warn',
            'react/no-unused-state': 'warn',
            'react/no-will-update-set-state': 'warn',
            'react/prop-types': 'warn',
            'react/prefer-es6-class': [
                'warn',
                'always',
            ],
            'react/prefer-read-only-props': 'warn',
            'react/jsx-max-depth': [
                'warn',
                {
                    max: 9,
                },
            ],

            // React Hooks rules
            'react-hooks/rules-of-hooks': 'error',
            'react-hooks/exhaustive-deps': 'warn',
        },
    },
]