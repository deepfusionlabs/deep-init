package gateway

import "example.com/app/config"

func Use() {
	if config.DynamicFlag {
		dynamicPath() // NOT dead: DynamicFlag is a var (runtime value), not a const-literal → suppress
	}
}

func dynamicPath() {}
