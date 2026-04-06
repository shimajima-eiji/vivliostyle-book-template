module.exports = {
  title: '{{BOOK_TITLE}}',
  language: 'ja',
  size: 'A5',
  theme: './theme/book.css',
  toc: { title: '目次' },
  entry: [
    { path: 'manuscript/ch01/main.md', title: '第1章　章タイトルをここに' },
    // { path: 'manuscript/ch02/main.md', title: '第2章　章タイトルをここに' },
    { path: 'manuscript/index.md',     title: '索引' },
    { path: 'manuscript/colophon.md',  title: '奥付' },
  ],
  output: [
    {
      path: './dist/book-digital.pdf',
      renderMode: 'local',
    },
  ],
};
