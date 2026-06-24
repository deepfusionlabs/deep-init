package config

func computeFlag() bool { return true }

// A VAR (runtime-assigned, rebindable) — NOT a const-literal, so it must NOT be folded.
var DynamicFlag = computeFlag()
