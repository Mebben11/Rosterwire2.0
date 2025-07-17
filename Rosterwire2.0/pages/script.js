export async function fetchPlayers() {
  try {
    const res = await fetch('/api/players');
    const data = await res.json();
    return data.players || [];
  } catch (error) {
    console.error('Error fetching players:', error);
    return [];
  }
}
