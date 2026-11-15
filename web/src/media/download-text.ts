const CSV_TYPE = "text/csv;charset=utf-8";

export function downloadText(name: string, text: string): void {
  const url = URL.createObjectURL(new Blob([text], { type: CSV_TYPE }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
