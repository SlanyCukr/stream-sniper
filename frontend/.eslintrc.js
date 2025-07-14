module.exports = {
    'env': {
        'browser': true,
        'es2021': true,
    },
    'extends': [
        'eslint:recommended',
        'plugin:react/recommended',
    ],
    'parser': '@babel/eslint-parser',
    'parserOptions': {
        'requireConfigFile': false,
        'babelOptions': {
            'presets': ['@babel/preset-react'],
        },
        'ecmaFeatures': {
            'jsx': true,
        },
        'ecmaVersion': 'latest',
        'sourceType': 'module',
    },
    'plugins': [
        'react',
    ],
    'overrides': [
        {
            'files': [
                '*.jsx',
                '*.js',
            ],
        },
    ],
    'rules': {
        'no-warning-comments': [
            'warn',
            {
                'terms': [
                    'fixme',
                ],
                'location': 'anywhere',
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
                'ignoreDestructuring': true,
                'properties': 'never',
            },
        ],
        'dot-notation': [
            'error',
            {
                'allowPattern': '^[a-z]+(_[a-z]+)+$',
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
                'includeExports': true,
            },
        ],
        'indent': [
            'error',
            4,
            {
                'SwitchCase': 1,
            },
        ],
        'react/jsx-uses-vars': [
            2,
        ],
        'react/react-in-jsx-scope': 'off',
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
        'react/jsx-max-props-per-line': [
            'error',
            {
                'maximum': 1,
                'when': 'always',
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
        'no-unused-vars': 'warn',
        'react/prefer-es6-class': [
            'warn',
            'always',
        ],
        'react/prefer-read-only-props': 'warn',
        'react/jsx-max-depth': [
            'warn',
            {
                'max': 9,
            },
        ],
        'semi': [
            'error',
            'never',
        ],
        'quotes': [
            'error',
            'single',
            {
                'avoidEscape': true,
            },
        ],
        'object-curly-spacing': [
            'error',
            'always',
            {
                'arraysInObjects': true,
                'objectsInObjects': true,
            },
        ],
        'object-curly-newline': [
            'error',
            {
                'minProperties': 2,
                'consistent': true,
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
                'ignoreExport': true,
                'ignoreDestructuring': true,
            },
        ],
        'prefer-numeric-literals': 'error',
        'no-extra-boolean-cast': 'error',
        'no-trailing-spaces': [
            'error',
            {
                'ignoreComments': true,
            },
        ],
        'max-lines': [
            'error',
            {
                'max': 300,
                'skipComments': true,
                'skipBlankLines': true,
            },
        ],
        'no-async-promise-executor': 'error',
        'no-await-in-loop': 'error',
        'no-prototype-builtins': 'error',
    }
}
