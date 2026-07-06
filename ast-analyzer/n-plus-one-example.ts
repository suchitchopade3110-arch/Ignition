export async function getUsersWithPosts(userIds: number[]) {
  const results = [];
  for (const id of userIds) {
    const posts = await db.query('SELECT * FROM posts WHERE user_id = ?', [id]);
    results.push(posts);
  }
  return results;
}
