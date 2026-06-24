package sched

// Scheduler dispatches jobs onto worker goroutines. Synthetic fixture file:
// its only job is to make the CLAUDE.md citation `src/sched/scheduler.go:10`
// resolve, so the §A2 integration auditor can re-derive citation-resolution
// against the committed snapshot itself (clone-independent).

type Scheduler struct {
	workers int
}

func (s *Scheduler) Dispatch(job Job) error { // line 10 — the cited line
	return s.enqueue(job)
}
