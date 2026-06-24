// commentstr/doc.ts — COMMENT/STRING trap: FLAG is a const false, but the real gate is a member
// read (cfg.flag), NOT a sole-operand if-test. Its name appears only inside a comment and a string
// literal below; the detector must blank comments + string CONTENT before the if-anchor search, so
// neither triggers a (mislocated, high-stakes "your branch is dead") fire. Must NOT fire.
const FLAG = false;

export function doc(cfg: { flag: boolean }): string {
  const help = 'pass if (FLAG) semantics via cfg'; // string literal — must NOT trigger a fire
  if (cfg.flag) {
    return run();
  }
  return help; // historical: if (FLAG) once gated this — a comment, must NOT fire
}
declare function run(): string;
