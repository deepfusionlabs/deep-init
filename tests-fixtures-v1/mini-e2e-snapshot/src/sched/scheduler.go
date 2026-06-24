// Package sched orders due jobs deterministically (synthetic §A3 fixture).
package sched

// Schedule returns due jobs in priority order; equal-priority jobs keep insertion order.
func Schedule(jobs []Job) []Job {
	out := append([]Job(nil), jobs...)
	// stable sort by priority — equal priorities preserve insertion order (deterministic).
	for i := 1; i < len(out); i++ {
		for j := i; j > 0 && out[j-1].Priority > out[j].Priority; j-- {
			out[j-1], out[j] = out[j], out[j-1]
		}
	}
	return out
}

// Job is a unit of scheduled work.
type Job struct {
	ID       string
	Priority int
}
