import tseslint from 'typescript-eslint';
import hooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
export default [{ignores:['dist/**','node_modules/**','test-results/**']},{files:['src/**/*.{ts,tsx}'],languageOptions:{parser:tseslint.parser,parserOptions:{ecmaVersion:'latest',sourceType:'module',ecmaFeatures:{jsx:true}},globals:globals.browser},plugins:{'@typescript-eslint':tseslint.plugin,'react-hooks':hooks},rules:{'@typescript-eslint/no-unused-vars':['error',{argsIgnorePattern:'^_',varsIgnorePattern:'^_'}],'react-hooks/rules-of-hooks':'error','react-hooks/exhaustive-deps':'warn'}}];
