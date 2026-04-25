const statusNode = document.querySelector<HTMLParagraphElement>("#status");
const buttonNode = document.querySelector<HTMLButtonElement>("#capture-button");

const setStatus = (message: string): void => {
  if (statusNode) {
    statusNode.textContent = message;
  }
};

buttonNode?.addEventListener("click", async () => {
  setStatus("Capture endpoint wiring arrives in Stage 4.");
});
