export function highlightText(text: string, searchQuery: string): string {
  if (!searchQuery.trim()) {
    return text;
  }

  // Escape special regex characters in the search query
  const escapedQuery = searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

  // Create a case-insensitive regex to find all matches
  const regex = new RegExp(`(${escapedQuery})`, 'gi');

  // Replace matches with highlighted version
  return text.replace(regex, '<mark class="bg-yellow-200 text-yellow-900 rounded px-1">$1</mark>');
}

export function searchFAQs(faqs: any[], searchQuery: string) {
  if (!searchQuery.trim()) {
    return faqs;
  }

  const query = searchQuery.toLowerCase();

  return faqs.filter(faq =>
    faq.question.toLowerCase().includes(query) ||
    faq.answer.toLowerCase().includes(query)
  );
}