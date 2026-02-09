const all = ['chats'];
export const chatsKeys = {
  all,
  list: [...all, 'list'],
  history: (id: string) => [...all, id, 'history'],
};
