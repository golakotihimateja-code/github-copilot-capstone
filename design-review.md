# Architecture Design Review

**Scope:** Review of [architecture.md](architecture.md) against [requirements.md](requirements.md)  
**Date:** 2026-11-02

## Summary

The proposed architecture has sensible separation between webhook intake, synchronization, Markdown processing, GitHub access, and email. The following items should be resolved before implementation, especially webhook/job durability, write-back permissions, and prevention of self-triggered synchronization loops. Several infrastructure choices and non-functional targets remain proposals or open decisions.

## Security Risks

### High: Webhook replay and event acceptance are underspecified

The design calls for signature verification and event-ID tracking, but does not state how repository/event allowlisting is enforced or how event acceptance is made durable before GitHub receives an acknowledgment. A replayed delivery or a crash between recording an event and queueing it could cause duplicate work or lose a push. See [architecture.md](architecture.md#L39) and [architecture.md](architecture.md#L48).

**Recommendation:** Verify the webhook HMAC using a constant-time comparison, allow only configured repositories and event types, and persist the delivery ID with durable job acceptance before acknowledging GitHub. Make duplicate deliveries idempotent.

### High: Repository write authority and generated content need tighter boundaries

The architecture permits publishing through the GitHub adapter but does not define token scope, protected-branch behavior, or which paths the automation may change. See [architecture.md](architecture.md#L28), [architecture.md](architecture.md#L42), and [architecture.md](architecture.md#L55).

**Recommendation:** Use a GitHub App with least-privilege permissions limited to configured repositories and documentation paths. Prefer a bot branch or pull request. Validate generated Markdown and keep credentials out of logs, email, and repository content.

## Performance Risks

### Medium: Processing limits and API usage are not defined

The architecture does not specify whether a job reads only changed files or scans the repository, or how it handles large pushes, API pagination, rate limits, timeouts, and backoff. See [architecture.md](architecture.md#L40) and [architecture.md](architecture.md#L51).

**Recommendation:** Process the push's commit range and relevant paths where possible. Set payload, file-count, and execution-time limits; use bounded API calls with rate-limit-aware retries.

### Medium: Notification delivery could delay or obscure job outcomes

Email is part of the synchronization flow, but provider outages and notification retries are not addressed. See [architecture.md](architecture.md#L43) and [architecture.md](architecture.md#L44).

**Recommendation:** Decouple notification delivery from job completion, retry notifications independently, and record notification failures without replacing the original synchronization status.

## Scalability Concerns

### High: Concurrent pushes can process out of order

The queue and worker are asynchronous, but the design does not define per-repository ordering or prevent an older job from publishing after a newer one. See [architecture.md](architecture.md#L13) and [architecture.md](architecture.md#L40).

**Recommendation:** Serialize or coalesce jobs per repository, and verify that the source commit is still current before publishing.

### Medium: Queue growth and repeatedly failing jobs have no operating model

Retries are mentioned, but backoff, dead-letter handling, worker concurrency limits, and backlog monitoring are not defined. See [architecture.md](architecture.md#L44).

**Recommendation:** Define bounded exponential retries, a dead-letter queue, and alerts for queue age and failure rate. Size worker concurrency against GitHub and email-provider limits.

## Design Gaps

### High: Publishing can trigger another synchronization cycle

A generated commit can emit the same `push` event that starts the workflow. The architecture recognizes this as an open question but does not establish a loop-prevention policy. See [architecture.md](architecture.md#L42) and [architecture.md](architecture.md#L87).

**Recommendation:** Choose and document a policy, such as ignoring the automation identity's commits or limiting triggers to relevant source paths, while retaining idempotency safeguards.

### Medium: The publisher is used but not defined consistently

The flow and diagram rely on a Documentation Publisher, but it is absent from the component and technology tables. The destination and publishing method also remain open. See [architecture.md](architecture.md#L15), [architecture.md](architecture.md#L42), and [architecture.md](architecture.md#L71).

**Recommendation:** Define the publisher's interface, destination, authentication, and failure behavior, then include it in the component responsibilities and technology stack.

### Medium: User configuration and operational visibility are unclear

Developers are identified as users, but there is no defined way to onboard a repository, set documentation rules or recipients, or inspect job status. See [architecture.md](architecture.md#L14), [architecture.md](architecture.md#L19), and [architecture.md](architecture.md#L84).

**Recommendation:** Specify whether configuration is repository-based, centrally managed, or both, and define the minimum job-status and support workflow.

### Medium: Measurable non-functional targets are missing

Availability, processing time, retention, and recovery targets are listed as decisions rather than requirements. See [architecture.md](architecture.md#L89).

**Recommendation:** Set measurable targets before selecting queue, database, hosting, and retry policies so capacity and resilience choices can be validated.
