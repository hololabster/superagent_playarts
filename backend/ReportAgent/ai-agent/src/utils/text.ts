export function truncateText(
  text: string | null | undefined,
  front: number = 6,
  back: number = 4,
  placeholder: string = "..."
): string | null {
  if (!text) {
    return null;
  }
  if (text.length <= front + back) {
    return text;
  }

  return text.slice(0, front) + placeholder + text.slice(-back);
}
