package orders

import "example.com/app/flags"

func Process() {
	if !flags.LegacyMode {
		legacyPath() // DEAD: LegacyMode is const true → !true is false
	}
}

func legacyPath() {}
