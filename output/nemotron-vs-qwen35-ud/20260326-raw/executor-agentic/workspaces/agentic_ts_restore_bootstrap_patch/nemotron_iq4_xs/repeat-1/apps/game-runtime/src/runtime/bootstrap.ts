export class ThreadBootstrapper {
  created: string[] = [];

  ensureThread(agentId: string): string {
    const threadId = `thread-${agentId}`;
    this.created.push(threadId);
    return threadId;
  }
}
