// Forking barrel: FORKED comes from BOTH stars (ambiguous); DEADEND re-exports a missing module.
export * from './a';
export * from './b';
export { DEADEND } from './missing';
