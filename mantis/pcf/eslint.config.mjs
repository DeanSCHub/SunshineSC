import tseslint from "typescript-eslint";

export default [
  { ignores: ["**/generated/**", "out/**", "node_modules/**"] },
  ...tseslint.configs.recommended,
];
