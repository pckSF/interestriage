const statusNode = document.querySelector<HTMLParagraphElement>("#status");

const setStatus = (message: string): void => {
  if (statusNode) {
    statusNode.textContent = message;
  }
};

const checkHealth = async (): Promise<void> => {
  try {
    const response = await fetch("/api/v1/health");
    if (!response.ok) {
      setStatus(`Backend health check failed: ${response.status}`);
      return;
    }

    const payload = (await response.json()) as { mode: string; status: string };
    setStatus(`Backend status: ${payload.status} (mode=${payload.mode})`);
  } catch {
    setStatus("Backend is not reachable yet. Start the dev stack with make dev.");
  }
};

void checkHealth();
