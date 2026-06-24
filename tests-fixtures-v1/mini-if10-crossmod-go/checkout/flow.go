package checkout

import "example.com/app/flags"

func Flow() {
	if flags.NewCheckout {
		newCheckoutPath() // DEAD: NewCheckout is const false in package flags
	}
}

func newCheckoutPath() {}
