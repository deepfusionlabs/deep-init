package flags

// Intra-package use of NewCheckout via a BARE reference (not flags.NewCheckout) — same component,
// so it is §25 in-file territory, NOT a cross-module fire; the cross-module fold must not flag it.
func gate() bool {
	if NewCheckout {
		return false
	}
	return true
}
