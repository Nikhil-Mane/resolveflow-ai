export function ToolStatus({ tools }: { tools: Record<string, string> }) {
  const entries = Object.entries(tools);
  if (!entries.length) return null;
  return (
    <div className="tools" aria-live="polite">
      {entries.map(([name, status]) => (
        <span key={name}>Tool: {name} - {status}</span>
      ))}
    </div>
  );
}
